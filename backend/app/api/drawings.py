"""图纸上传与解析 API。"""
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from app.api.deps import get_db, get_kb
from app.db import models
from app.models import (
    DrawingResponse, DrawingElementListResponse, ExtractedElementSchema,
    ElementMappingRequest, BatchMappingRequest,
)
from app.engine.drawing_parser import DrawingParser
from app.knowledge.loader import KnowledgeLoader
from app.config import settings

router = APIRouter(prefix="/api/v1/projects", tags=["drawings"])

UPLOAD_DIR = Path(settings.REPORT_OUTPUT_DIR).parent / "uploads" / "drawings"


@router.post("/{project_id}/drawings/upload")
def upload_drawing(
    project_id: str,
    file: UploadFile = File(...),
    name: str = Form(""),
    drawing_type: str = Form("plan"),
    db: Session = Depends(get_db),
):
    """上传PDF图纸并自动解析。"""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="仅支持PDF格式图纸")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"{project_id}_{file.filename}"
    file_path = UPLOAD_DIR / safe_name

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Parse PDF
    parser = DrawingParser()
    parse_result = parser.parse(str(file_path))

    # Save drawing record
    display_name = name or file.filename.rsplit('.', 1)[0]
    drawing = models.Drawing(
        project_id=project_id,
        name=display_name,
        drawing_type=drawing_type,
        file_path=str(file_path),
        original_filename=file.filename,
        page_count=parse_result["page_count"],
        processed=True,
    )
    db.add(drawing)
    db.flush()

    # Save extracted elements
    for elem in parse_result["elements"]:
        db.add(models.ExtractedElement(
            drawing_id=drawing.id,
            text=elem["text"],
            element_type=elem.get("element_type", "text"),
            page_num=elem.get("page_num", 1),
            x0=elem.get("x0"),
            y0=elem.get("y0"),
            x1=elem.get("x1"),
            y1=elem.get("y1"),
            parsed_value=elem.get("parsed_value"),
            parsed_unit=elem.get("parsed_unit"),
            parsed_dimensions=elem.get("parsed_dimensions"),
        ))

    project.status = "drawings_uploaded"
    db.commit()
    db.refresh(drawing)

    return {
        "id": drawing.id,
        "name": drawing.name,
        "drawing_type": drawing_type,
        "original_filename": file.filename,
        "page_count": parse_result["page_count"],
        "element_count": len(parse_result["elements"]),
        "processed": True,
        "created_at": drawing.created_at.isoformat() if drawing.created_at else None,
    }


@router.get("/{project_id}/drawings")
def list_drawings(project_id: str, db: Session = Depends(get_db)):
    """获取项目所有已上传图纸。"""
    drawings = db.query(models.Drawing).filter(
        models.Drawing.project_id == project_id
    ).all()

    result = []
    for d in drawings:
        elem_count = db.query(models.ExtractedElement).filter(
            models.ExtractedElement.drawing_id == d.id
        ).count()
        result.append({
            "id": d.id,
            "name": d.name,
            "drawing_type": d.drawing_type,
            "original_filename": d.original_filename,
            "page_count": d.page_count,
            "processed": d.processed,
            "element_count": elem_count,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        })
    return {"drawings": result}


@router.get("/{project_id}/drawings/{drawing_id}/elements")
def get_drawing_elements(drawing_id: int, db: Session = Depends(get_db)):
    """获取图纸解析出的文字元素列表。"""
    elements = db.query(models.ExtractedElement).filter(
        models.ExtractedElement.drawing_id == drawing_id
    ).order_by(models.ExtractedElement.page_num, models.ExtractedElement.y0).all()

    return {
        "drawing_id": drawing_id,
        "elements": [
            {
                "id": e.id,
                "text": e.text,
                "element_type": e.element_type,
                "page_num": e.page_num,
                "x0": e.x0,
                "y0": e.y0,
                "x1": e.x1,
                "y1": e.y1,
                "parsed_value": e.parsed_value,
                "parsed_unit": e.parsed_unit,
                "parsed_dimensions": e.parsed_dimensions,
            }
            for e in elements
        ],
    }


@router.get("/{project_id}/drawings/suggest-mappings")
def suggest_mappings(
    project_id: str,
    drawing_id: Optional[int] = None,
    db: Session = Depends(get_db),
    kb: KnowledgeLoader = Depends(get_kb),
):
    """自动建议元素到构筑物的映射。"""
    route = db.query(models.ProjectProcessRoute).filter(
        models.ProjectProcessRoute.project_id == project_id,
        models.ProjectProcessRoute.is_selected == True,
    ).first()
    if not route:
        raise HTTPException(status_code=400, detail="请先选择工艺路线")

    route_units = db.query(models.RouteUnit).filter(
        models.RouteUnit.route_id == route.id
    ).all()

    query = db.query(models.ExtractedElement)
    if drawing_id:
        query = query.filter(models.ExtractedElement.drawing_id == drawing_id)
    else:
        # All drawings for this project
        drawing_ids = [
            d.id for d in db.query(models.Drawing).filter(
                models.Drawing.project_id == project_id
            ).all()
        ]
        query = query.filter(models.ExtractedElement.drawing_id.in_(drawing_ids))

    elements = query.all()

    parser = DrawingParser()
    elements_dicts = [
        {
            "id": e.id,
            "text": e.text,
            "element_type": e.element_type,
            "parsed_value": e.parsed_value,
            "parsed_unit": e.parsed_unit,
            "parsed_dimensions": e.parsed_dimensions,
        }
        for e in elements
    ]
    route_dicts = [{"unit_code": u.unit_code, "unit_name_zh": u.unit_name_zh} for u in route_units]

    suggestions = parser.suggest_mappings(elements_dicts, route_dicts)
    return {"suggestions": suggestions}


@router.post("/{project_id}/drawings/map")
def save_mappings(
    project_id: str,
    data: BatchMappingRequest,
    db: Session = Depends(get_db),
):
    """保存元素到构筑物的映射关系。"""
    db.query(models.ElementMapping).filter(
        models.ElementMapping.project_id == project_id
    ).delete()

    for m in data.mappings:
        db.add(models.ElementMapping(
            project_id=project_id,
            element_id=m.element_id,
            unit_code=m.unit_code,
            param_name=m.param_name,
        ))

    db.commit()
    return {"status": "saved", "count": len(data.mappings)}


@router.get("/{project_id}/drawings/mapping")
def get_mappings(project_id: str, db: Session = Depends(get_db)):
    """获取已保存的映射关系。"""
    mappings = db.query(models.ElementMapping).filter(
        models.ElementMapping.project_id == project_id
    ).all()

    mapped_elements = []
    for m in mappings:
        elem = db.query(models.ExtractedElement).filter(
            models.ExtractedElement.id == m.element_id
        ).first()
        mapped_elements.append({
            "element_id": m.element_id,
            "element_text": elem.text if elem else "",
            "parsed_value": elem.parsed_value if elem else None,
            "parsed_unit": elem.parsed_unit if elem else None,
            "parsed_dimensions": elem.parsed_dimensions if elem else None,
            "unit_code": m.unit_code,
            "param_name": m.param_name,
        })

    return {"mappings": mapped_elements}
