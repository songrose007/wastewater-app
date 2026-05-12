"""报告生成 API。"""
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_kb
from app.db import models
from app.report.docx import generate_docx_from_snapshot
from app.report.generator import generate_report_html
from app.report.pdf import generate_pdf
from app.report.project_snapshot import build_project_report_snapshot
from app.knowledge.loader import KnowledgeLoader
from app.config import settings
from app.services.package_project import safe_artifact_id

router = APIRouter(prefix="/api/v1/projects", tags=["report"])


@router.post("/{project_id}/report")
def generate_report(
    project_id: str,
    format: str = Query("pdf", pattern="^(html|pdf|docx|all)$"),
    db: Session = Depends(get_db),
    kb: KnowledgeLoader = Depends(get_kb),
):
    try:
        artifact_id = safe_artifact_id(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    snapshot = build_project_report_snapshot(project_id, db)
    if not snapshot:
        raise HTTPException(status_code=404, detail="项目不存在")

    project = snapshot["project"]
    html_content = generate_report_html(
        project_name=snapshot["project_name"],
        wastewater_type=snapshot["wastewater_type"],
        flow_rate=snapshot["flow_rate"],
        target_standard=snapshot["target_standard"],
        water_quality=snapshot["water_quality"],
        process_route=snapshot["process_route"],
        calculation_results=snapshot["calculation_results"],
        summary=snapshot["summary"],
        equipment_list=snapshot["equipment_list"] or None,
        cost_estimate=snapshot["cost_estimate"],
    )

    output_dir = Path(settings.REPORT_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"report_{artifact_id}.pdf"
    docx_path = output_dir / f"report_{artifact_id}.docx"

    pdf_error = None
    if format in ("pdf", "all"):
        try:
            generate_pdf(html_content, str(pdf_path))
        except Exception as exc:
            if format == "pdf":
                raise HTTPException(status_code=500, detail=f"PDF报告生成失败: {exc}") from exc
            pdf_error = str(exc)

    if format in ("docx", "all"):
        generate_docx_from_snapshot(snapshot, str(docx_path))

    report = db.query(models.ProjectReport).filter(
        models.ProjectReport.project_id == project_id
    ).first()
    current_pdf_path = str(pdf_path) if pdf_path.exists() else None
    if report:
        report.html_content = html_content
        report.pdf_path = current_pdf_path
        report.generated_at = __import__('datetime').datetime.utcnow()
    else:
        report = models.ProjectReport(
            project_id=project_id,
            pdf_path=current_pdf_path,
            html_content=html_content,
        )
        db.add(report)

    project.status = "reported"
    db.commit()

    return {
        "status": "ready",
        "format": format,
        "pdf_exists": pdf_path.exists(),
        "docx_exists": docx_path.exists(),
        "pdf_error": pdf_error,
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
def download_report(
    project_id: str,
    format: str = Query("pdf", pattern="^(pdf|docx|html)$"),
    db: Session = Depends(get_db),
):
    try:
        artifact_id = safe_artifact_id(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    report = db.query(models.ProjectReport).filter(
        models.ProjectReport.project_id == project_id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    output_dir = Path(settings.REPORT_OUTPUT_DIR)
    if format == "docx":
        docx_path = output_dir / f"report_{artifact_id}.docx"
        if docx_path.exists():
            return FileResponse(
                str(docx_path),
                filename=f"设计方案_{artifact_id[:8]}.docx",
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        raise HTTPException(status_code=404, detail="DOCX报告不存在，请先生成DOCX报告")

    if format == "pdf":
        if report.pdf_path and os.path.exists(report.pdf_path):
            return FileResponse(
                report.pdf_path,
                filename=f"设计方案_{artifact_id[:8]}.pdf",
                media_type="application/pdf",
            )
        raise HTTPException(status_code=404, detail="PDF报告不存在，请先生成PDF报告")

    if format == "html":
        if report.html_content:
            html_path = output_dir / f"temp_{artifact_id}.html"
            html_path.write_text(report.html_content, encoding="utf-8")
            return FileResponse(
                str(html_path),
                filename=f"设计方案_{artifact_id[:8]}.html",
                media_type="text/html",
            )
        raise HTTPException(status_code=404, detail="HTML报告内容为空")

    raise HTTPException(status_code=404, detail="报告内容为空")
