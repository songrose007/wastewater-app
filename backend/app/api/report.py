"""报告生成 API。"""
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_kb
from app.db import models
from app.report.generator import generate_report_html
from app.report.pdf import generate_pdf
from app.knowledge.loader import KnowledgeLoader
from app.config import settings

router = APIRouter(prefix="/api/v1/projects", tags=["report"])


@router.post("/{project_id}/report")
def generate_report(project_id: str, db: Session = Depends(get_db), kb: KnowledgeLoader = Depends(get_kb)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    wq_params = db.query(models.WaterQualityParameter).filter(
        models.WaterQualityParameter.project_id == project_id
    ).all()
    water_quality = {p.parameter_code: p.value for p in wq_params}

    route = db.query(models.ProjectProcessRoute).filter(
        models.ProjectProcessRoute.project_id == project_id,
        models.ProjectProcessRoute.is_selected == True,
    ).first()
    process_route = {
        "route_id": route.route_id if route else "N/A",
        "route_name_zh": route.route_name_zh if route else "N/A",
        "total_score": route.total_score if route else 0,
    }

    calc_results_db = db.query(models.CalculationResult).filter(
        models.CalculationResult.project_id == project_id
    ).all()

    calculation_results = []
    total_volume = 0
    total_power = 0
    total_sludge = 0

    for r in calc_results_db:
        calc_dict = {
            "unit_code": r.calculator_code,
            "unit_name_zh": r.calculator_code,
            "computed_parameters": r.output_parameters or {},
            "warnings": r.warnings or [],
        }
        calculation_results.append(calc_dict)

        params = r.output_parameters or {}
        for k in ["tank_volume_total", "tank_volume", "total_volume", "effective_volume"]:
            v = params.get(k, 0)
            if v:
                total_volume += v
                break

    summary = {
        "total_tank_volume_m3": round(total_volume, 1),
        "total_power_kw": round(total_power, 1),
        "total_sludge_production_kg_d": round(total_sludge, 1),
    }

    # 获取设备选型结果
    equip_records = db.query(models.EquipmentSelection).filter(
        models.EquipmentSelection.project_id == project_id
    ).all()
    equipment_list = [
        {
            "category": e.category,
            "model_id": e.model_id,
            "model_name_zh": e.model_name_zh,
            "quantity": e.quantity,
            "unit_price_cny": e.unit_price_cny,
            "total_price_cny": e.total_price_cny,
            "specs": e.specs or {},
            "manufacturer": e.manufacturer,
        }
        for e in equip_records
    ] if equip_records else None

    # 获取造价估算结果
    cost_record = db.query(models.CostEstimate).filter(
        models.CostEstimate.project_id == project_id
    ).first()
    cost_estimate = None
    if cost_record:
        cost_estimate = {
            "capex": cost_record.capex_breakdown or {},
            "opex": cost_record.opex_breakdown or {},
            "total_capex": cost_record.total_capex,
            "total_annual_opex": cost_record.total_annual_opex,
            "cost_per_m3": cost_record.cost_per_m3 or 0,
            "assumptions": cost_record.assumptions or {},
        }

    html_content = generate_report_html(
        project_name=project.name,
        wastewater_type=project.wastewater_type,
        flow_rate=project.flow_rate or 0,
        target_standard=project.target_standard_id or "N/A",
        water_quality=water_quality,
        process_route=process_route,
        calculation_results=calculation_results,
        summary=summary,
        equipment_list=equipment_list,
        cost_estimate=cost_estimate,
    )

    # 保存报告
    output_dir = Path(settings.REPORT_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"report_{project_id}.pdf"

    try:
        generate_pdf(html_content, str(pdf_path))
    except Exception:
        pass

    report = db.query(models.ProjectReport).filter(
        models.ProjectReport.project_id == project_id
    ).first()
    if report:
        report.html_content = html_content
        report.pdf_path = str(pdf_path) if pdf_path.exists() else None
        report.generated_at = __import__('datetime').datetime.utcnow()
    else:
        report = models.ProjectReport(
            project_id=project_id,
            pdf_path=str(pdf_path) if pdf_path.exists() else None,
            html_content=html_content,
        )
        db.add(report)

    project.status = "reported"
    db.commit()

    return {
        "status": "ready",
        "pdf_exists": pdf_path.exists(),
        "message": "报告已生成",
    }


@router.get("/{project_id}/report/preview")
def preview_report(project_id: str, db: Session = Depends(get_db)):
    report = db.query(models.ProjectReport).filter(
        models.ProjectReport.project_id == project_id
    ).first()
    if not report or not report.html_content:
        raise HTTPException(status_code=404, detail="报告不存在，请先生成报告")
    return HTMLResponse(content=report.html_content)


@router.get("/{project_id}/report/download")
def download_report(project_id: str, db: Session = Depends(get_db)):
    report = db.query(models.ProjectReport).filter(
        models.ProjectReport.project_id == project_id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    if report.pdf_path and os.path.exists(report.pdf_path):
        return FileResponse(
            report.pdf_path,
            filename=f"设计方案_{project_id[:8]}.pdf",
            media_type="application/pdf",
        )

    if report.html_content:
        html_path = Path(settings.REPORT_OUTPUT_DIR) / f"temp_{project_id}.html"
        html_path.write_text(report.html_content, encoding="utf-8")
        return FileResponse(
            str(html_path),
            filename=f"设计方案_{project_id[:8]}.html",
            media_type="text/html",
        )

    raise HTTPException(status_code=404, detail="报告内容为空")
