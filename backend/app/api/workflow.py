"""项目方案生成工作流总控 API。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_kb
from app.db import models
from app.engine.cost_estimator import CostEstimator
from app.engine.equipment_selector import EquipmentSelector
from app.engine.process_selector import ProcessSelector
from app.knowledge.loader import KnowledgeLoader

router = APIRouter(prefix="/api/v1/projects", tags=["workflow"])


class WorkflowStepRequest(BaseModel):
    """请求执行某个安全的工作流步骤。"""

    step: str


STEP_DEFS = [
    ("scheme", "方案向导", "scheme"),
    ("input", "水质输入", ""),
    ("process", "工艺选择", "process"),
    ("calculation", "设计计算", "calculation"),
    ("drawings", "图纸导入", "drawings"),
    ("mapping", "构筑物映射", "mapping"),
    ("verification", "设计校核", "verification"),
    ("equipment", "设备选型", "equipment"),
    ("cost", "造价估算", "equipment"),
    ("report", "方案报告", "report"),
    ("package", "成果打包", "scheme"),
]


def _project_route(project_id: str, suffix: str) -> str:
    return f"/projects/{project_id}" if not suffix else f"/projects/{project_id}/{suffix}"


def _question(
    question_id: str,
    step: str,
    severity: str,
    question_type: str,
    message: str,
    route: str,
) -> dict[str, str]:
    return {
        "id": question_id,
        "step": step,
        "severity": severity,
        "type": question_type,
        "message": message,
        "route": route,
    }


def _count_query(db: Session, model: Any, project_id: str) -> int:
    return db.query(model).filter(model.project_id == project_id).count()


@router.get("/{project_id}/workflow")
def get_workflow(project_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """返回项目当前工作流状态、待确认项和下一步建议。"""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    water_quality_count = _count_query(db, models.WaterQualityParameter, project_id)
    selected_route = db.query(models.ProjectProcessRoute).filter(
        models.ProjectProcessRoute.project_id == project_id,
        models.ProjectProcessRoute.is_selected == True,  # noqa: E712
    ).first()
    calculation_records = db.query(models.CalculationResult).filter(
        models.CalculationResult.project_id == project_id
    ).all()
    drawing_count = _count_query(db, models.Drawing, project_id)
    mapping_count = _count_query(db, models.ElementMapping, project_id)
    equipment_count = _count_query(db, models.EquipmentSelection, project_id)
    cost_count = _count_query(db, models.CostEstimate, project_id)
    report = db.query(models.ProjectReport).filter(models.ProjectReport.project_id == project_id).first()

    questions: list[dict[str, str]] = []
    states = _build_step_states(
        project=project,
        water_quality_count=water_quality_count,
        selected_route=selected_route,
        calculation_records=calculation_records,
        drawing_count=drawing_count,
        mapping_count=mapping_count,
        equipment_count=equipment_count,
        cost_count=cost_count,
        has_report=bool(report),
        questions=questions,
    )

    steps = [
        {
            "key": key,
            "label": label,
            "state": states[key],
            "route": _project_route(project_id, suffix),
        }
        for key, label, suffix in STEP_DEFS
    ]

    next_step = _find_next_step(steps)
    blocking_items = [q for q in questions if q["severity"] == "blocking"]
    warnings = [q for q in questions if q["severity"] == "warning"]

    return {
        "project_id": project_id,
        "status": project.status,
        "steps": steps,
        "next_step": next_step,
        "questions": questions,
        "blocking_items": blocking_items,
        "warnings": warnings,
    }


def _build_step_states(
    *,
    project: models.Project,
    water_quality_count: int,
    selected_route: models.ProjectProcessRoute | None,
    calculation_records: list[models.CalculationResult],
    drawing_count: int,
    mapping_count: int,
    equipment_count: int,
    cost_count: int,
    has_report: bool,
    questions: list[dict[str, str]],
) -> dict[str, str]:
    project_id = project.id
    states = {key: "pending" for key, _, _ in STEP_DEFS}
    states["scheme"] = "active"

    has_input = bool(project.flow_rate and project.target_standard_id and water_quality_count > 0)
    if has_input:
        states["input"] = "complete"
    else:
        states["input"] = "needs_input"
        questions.append(
            _question(
                "missing_project_input",
                "input",
                "blocking",
                "input_required",
                "请补充设计水量、排放标准和主要进水水质参数。",
                _project_route(project_id, ""),
            )
        )

    if selected_route:
        states["process"] = "complete"
    elif has_input:
        states["process"] = "needs_confirmation"
        questions.append(
            _question(
                "confirm_process_route",
                "process",
                "blocking",
                "confirmation",
                "请运行工艺推荐并确认采用的工艺路线。",
                _project_route(project_id, "process"),
            )
        )

    calc_warnings = sum(len(record.warnings or []) for record in calculation_records)
    if calculation_records:
        states["calculation"] = "warning" if calc_warnings else "complete"
        if calc_warnings:
            questions.append(
                _question(
                    "review_calculation_warnings",
                    "calculation",
                    "warning",
                    "review",
                    f"设计计算存在 {calc_warnings} 条警告，请审查参数后继续。",
                    _project_route(project_id, "calculation"),
                )
            )
    elif selected_route:
        states["calculation"] = "action_required"
        questions.append(
            _question(
                "run_calculation",
                "calculation",
                "blocking",
                "action_required",
                "请执行设计计算，必要时先修改经验参数。",
                _project_route(project_id, "calculation"),
            )
        )

    if drawing_count:
        states["drawings"] = "complete"
    elif calculation_records:
        states["drawings"] = "optional"
        questions.append(
            _question(
                "upload_drawings",
                "drawings",
                "warning",
                "optional_upload",
                "建议上传平面图/高程图，用于构筑物尺寸和布置校核。",
                _project_route(project_id, "drawings"),
            )
        )

    if drawing_count and mapping_count:
        states["mapping"] = "complete"
    elif drawing_count:
        states["mapping"] = "action_required"
        questions.append(
            _question(
                "map_drawing_elements",
                "mapping",
                "blocking",
                "action_required",
                "图纸已上传，请把识别出的尺寸/标注映射到对应构筑物参数。",
                _project_route(project_id, "mapping"),
            )
        )

    if calculation_records and (mapping_count or not drawing_count):
        states["verification"] = "ready" if drawing_count else "optional"

    if equipment_count:
        states["equipment"] = "complete"
    elif calculation_records:
        states["equipment"] = "action_required"
        questions.append(
            _question(
                "select_equipment",
                "equipment",
                "blocking",
                "action_required",
                "请根据计算结果执行设备选型。",
                _project_route(project_id, "equipment"),
            )
        )

    if cost_count:
        states["cost"] = "complete"
    elif equipment_count:
        states["cost"] = "action_required"
        questions.append(
            _question(
                "estimate_cost",
                "cost",
                "blocking",
                "action_required",
                "请执行投资估算和运行成本估算。",
                _project_route(project_id, "equipment"),
            )
        )

    if has_report:
        states["report"] = "complete"
        states["package"] = "ready"
    elif cost_count or equipment_count:
        states["report"] = "action_required"
        questions.append(
            _question(
                "generate_report",
                "report",
                "blocking",
                "action_required",
                "请生成最终方案报告。",
                _project_route(project_id, "report"),
            )
        )

    return states


def _find_next_step(steps: list[dict[str, str]]) -> str | None:
    for step in steps:
        if step["key"] == "scheme":
            continue
        if step["state"] in {"needs_input", "needs_confirmation", "action_required", "warning", "ready"}:
            return step["key"]
    return None


@router.post("/{project_id}/workflow/run-step")
def run_workflow_step(
    project_id: str,
    body: WorkflowStepRequest,
    db: Session = Depends(get_db),
    kb: KnowledgeLoader = Depends(get_kb),
) -> dict[str, Any]:
    """执行可安全自动触发的工作流步骤。"""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    if body.step == "process":
        return _run_process_selection(project, db, kb)
    if body.step == "equipment":
        return _run_equipment_selection(project, db, kb)
    if body.step == "cost":
        return _run_cost_estimation(project, db, kb)

    raise HTTPException(status_code=400, detail=f"暂不支持自动执行步骤: {body.step}")


def _run_process_selection(
    project: models.Project,
    db: Session,
    kb: KnowledgeLoader,
) -> dict[str, Any]:
    if not project.target_standard_id:
        raise HTTPException(status_code=400, detail="请先设置目标排放标准")

    wq_params = db.query(models.WaterQualityParameter).filter(
        models.WaterQualityParameter.project_id == project.id
    ).all()
    water_quality = {p.parameter_code: p.value for p in wq_params}
    result = ProcessSelector(kb).select(
        wastewater_type=project.wastewater_type,
        flow_rate=project.flow_rate or 0,
        design_temp_min=project.design_temp_min or 10,
        water_quality=water_quality,
        target_standard_id=project.target_standard_id,
    )
    _save_process_recommendations(project, db, result.get("recommendations", []))
    return {"step": "process", "result": result}


def _save_process_recommendations(
    project: models.Project,
    db: Session,
    recommendations: list[dict[str, Any]],
) -> None:
    db.query(models.ProjectProcessRoute).filter(
        models.ProjectProcessRoute.project_id == project.id,
        models.ProjectProcessRoute.is_selected == False,  # noqa: E712
    ).delete()

    for rank, recommendation in enumerate(recommendations, start=1):
        route = models.ProjectProcessRoute(
            project_id=project.id,
            route_id=recommendation["route_id"],
            route_name_zh=recommendation.get("route_name_zh"),
            rank=rank,
            total_score=recommendation.get("total_score", 0),
            is_selected=False,
        )
        db.add(route)
        db.flush()
        for unit in recommendation.get("units", []):
            db.add(models.RouteUnit(
                route_id=route.id,
                sequence_order=unit.get("sequence", 0),
                unit_code=unit["unit_code"],
                unit_name_zh=unit.get("unit_name_zh", unit["unit_code"]),
                is_mandatory=unit.get("is_mandatory", True),
            ))
    db.commit()


def _run_equipment_selection(
    project: models.Project,
    db: Session,
    kb: KnowledgeLoader,
) -> dict[str, Any]:
    if project.status not in ("calculated", "equipment_selected", "cost_estimated"):
        raise HTTPException(status_code=400, detail="请先完成设计计算")

    route = db.query(models.ProjectProcessRoute).filter(
        models.ProjectProcessRoute.project_id == project.id,
        models.ProjectProcessRoute.is_selected == True,  # noqa: E712
    ).first()
    if not route:
        raise HTTPException(status_code=400, detail="未找到已选工艺路线")

    route_units = db.query(models.RouteUnit).filter(models.RouteUnit.route_id == route.id).all()
    calc_results = db.query(models.CalculationResult).filter(
        models.CalculationResult.project_id == project.id
    ).all()
    selector = EquipmentSelector(kb)
    result = selector.select(
        route_units=[{"unit_code": u.unit_code, "unit_name_zh": u.unit_name_zh} for u in route_units],
        calculation_results=[
            {"calculator_code": r.calculator_code, "output_parameters": r.output_parameters}
            for r in calc_results
        ],
        flow_rate=project.flow_rate or 0,
    )

    db.query(models.EquipmentSelection).filter(models.EquipmentSelection.project_id == project.id).delete()
    for item in result["equipment_list"]:
        db.add(models.EquipmentSelection(
            project_id=project.id,
            category=item["category"],
            process_unit_code=item["process_unit_code"],
            equipment_type=item["equipment_type"],
            model_id=item["model_id"],
            model_name_zh=item["model_name_zh"],
            quantity=item["quantity"],
            unit_price_cny=item["unit_price_cny"],
            total_price_cny=item["total_price_cny"],
            specs=item.get("specs", {}),
            manufacturer=item.get("manufacturer"),
            is_chinese=item.get("is_chinese", True),
            selection_rationale=item.get("selection_rationale"),
        ))
    project.status = "equipment_selected"
    db.commit()
    return {"step": "equipment", "result": result}


def _run_cost_estimation(
    project: models.Project,
    db: Session,
    kb: KnowledgeLoader,
) -> dict[str, Any]:
    if project.status not in ("equipment_selected", "cost_estimated"):
        raise HTTPException(status_code=400, detail="请先完成设备选型")

    calc_results = db.query(models.CalculationResult).filter(
        models.CalculationResult.project_id == project.id
    ).all()
    equipment_records = db.query(models.EquipmentSelection).filter(
        models.EquipmentSelection.project_id == project.id
    ).all()
    result = CostEstimator(kb).estimate(
        flow_rate=project.flow_rate or 0,
        calculation_results=[
            {"calculator_code": r.calculator_code, "output_parameters": r.output_parameters}
            for r in calc_results
        ],
        equipment_list=[
            {
                "category": e.category,
                "equipment_type": e.equipment_type,
                "model_id": e.model_id,
                "model_name_zh": e.model_name_zh,
                "quantity": e.quantity,
                "unit_price_cny": e.unit_price_cny,
                "total_price_cny": e.total_price_cny,
                "specs": e.specs or {},
                "manufacturer": e.manufacturer,
            }
            for e in equipment_records
        ],
    )

    db.query(models.CostEstimate).filter(models.CostEstimate.project_id == project.id).delete()
    db.add(models.CostEstimate(
        project_id=project.id,
        capex_breakdown=result["capex"],
        opex_breakdown=result["opex"],
        total_capex=result["total_capex"],
        total_annual_opex=result["total_annual_opex"],
        cost_per_m3=result["cost_per_m3"],
        assumptions=result["assumptions"],
    ))
    project.status = "cost_estimated"
    db.commit()
    return {"step": "cost", "result": result}
