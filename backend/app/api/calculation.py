"""设计计算 API。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_db, get_kb
from app.db import models
from app.models import CalculationOutput, CalculationResponse, ParameterOverride, CalculateRequest
from app.engine.orchestration import CalculationOrchestrator
from app.engine.calculators.registry import CalculatorRegistry
from app.knowledge.loader import KnowledgeLoader

router = APIRouter(prefix="/api/v1/projects", tags=["calculation"])


@router.post("/{project_id}/calculate")
def run_calculation(
    project_id: str,
    body: CalculateRequest = CalculateRequest(),
    db: Session = Depends(get_db),
    kb: KnowledgeLoader = Depends(get_kb),
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    route = db.query(models.ProjectProcessRoute).filter(
        models.ProjectProcessRoute.project_id == project_id,
        models.ProjectProcessRoute.is_selected == True,
    ).first()
    if not route:
        raise HTTPException(status_code=400, detail="请先选择工艺路线")

    wq_params = db.query(models.WaterQualityParameter).filter(
        models.WaterQualityParameter.project_id == project_id
    ).all()
    raw_water = {p.parameter_code: p.value for p in wq_params}

    target_limits = kb.resolve_standard_limits(project.target_standard_id or "GB18918-2002-1A")

    # 获取工艺路线单元
    template = _get_template(kb, route.route_id, project.wastewater_type)
    if not template:
        raise HTTPException(status_code=400, detail=f"未找到工艺模板: {route.route_id}")

    registry = CalculatorRegistry()
    orchestrator = CalculationOrchestrator(kb, registry)

    results = orchestrator.run_route(
        route_units=template.get("units", []),
        raw_water=raw_water,
        flow_rate=project.flow_rate or 0,
        flow_rate_peak=(project.flow_rate or 0) * (project.flow_rate_peak_factor or 1.3),
        target_standard_limits=target_limits,
        design_temp=project.design_temp_min or 10,
        parameter_overrides=body.parameter_overrides,
    )

    # 保存结果
    db.query(models.CalculationResult).filter(
        models.CalculationResult.project_id == project_id
    ).delete()

    for i, output in enumerate(results):
        calc_result = models.CalculationResult(
            project_id=project_id,
            calculator_code=output.unit_code,
            input_snapshot=raw_water,
            output_parameters=output.computed_params,
            formulas_applied=output.formulas,
            warnings=output.warnings,
        )
        db.add(calc_result)

    project.status = "calculated"
    db.commit()

    output_list = [
        CalculationOutput(
            unit_code=r.unit_code,
            unit_name_zh=r.unit_name_zh,
            sequence_order=i + 1,
            computed_parameters=r.computed_params,
            formulas=r.formulas,
            warnings=r.warnings,
            notes=r.notes,
        )
        for i, r in enumerate(results)
    ]

    return CalculationResponse(
        project_id=project_id,
        route_id=route.route_id,
        results=output_list,
        summary=_build_summary(results),
    )


@router.get("/{project_id}/calculations")
def get_calculations(project_id: str, db: Session = Depends(get_db)):
    results = db.query(models.CalculationResult).filter(
        models.CalculationResult.project_id == project_id
    ).all()

    return {
        "project_id": project_id,
        "results": [
            {
                "calculator_code": r.calculator_code,
                "output_parameters": r.output_parameters,
                "formulas": r.formulas_applied,
                "warnings": r.warnings,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in results
        ],
    }


@router.post("/{project_id}/calculate/{unit_code}")
def recalculate_unit(project_id: str, unit_code: str, override: ParameterOverride,
                     db: Session = Depends(get_db), kb: KnowledgeLoader = Depends(get_kb)):
    """对单个单元重新计算（工程师覆盖参数后）。"""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    wq_params = db.query(models.WaterQualityParameter).filter(
        models.WaterQualityParameter.project_id == project_id
    ).all()
    raw_water = {p.parameter_code: p.value for p in wq_params}

    target_limits = kb.resolve_standard_limits(project.target_standard_id or "GB18918-2002-1A")

    registry = CalculatorRegistry()
    orchestrator = CalculationOrchestrator(kb, registry)

    output = orchestrator.run_single_unit(
        unit_code=unit_code,
        raw_water=raw_water,
        flow_rate=project.flow_rate or 0,
        target_standard_limits=target_limits,
        design_temp=project.design_temp_min or 10,
        parameter_overrides=override.parameters,
    )

    return CalculationOutput(
        unit_code=output.unit_code,
        unit_name_zh=output.unit_name_zh,
        sequence_order=0,
        computed_parameters=output.computed_params,
        formulas=output.formulas,
        warnings=output.warnings,
        notes=output.notes,
    )


def _get_template(kb, route_id, ww_type):
    for t in kb.templates:
        if t["id"] == route_id:
            return t
    return None


def _build_summary(results) -> dict:
    total_volume = sum(r.computed_params.get("tank_volume_total", 0)
                       or r.computed_params.get("tank_volume", 0)
                       or r.computed_params.get("total_volume", 0)
                       or r.computed_params.get("effective_volume", 0)
                       or r.computed_params.get("tank_volume_total", 0)
                       for r in results)
    total_power = sum(r.power_estimate or 0 for r in results)
    total_sludge = sum(r.sludge_production or 0 for r in results)

    total_chem = {}
    for r in results:
        for chem, amount in r.chemical_consumption.items():
            total_chem[chem] = total_chem.get(chem, 0) + amount

    return {
        "total_tank_volume_m3": round(total_volume, 1),
        "total_power_kw": round(total_power, 1),
        "total_sludge_production_kg_d": round(total_sludge, 1),
        "total_chemical_consumption_kg_d": total_chem,
        "num_units_calculated": len(results),
    }
