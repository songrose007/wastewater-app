"""设计校核 API。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_kb
from app.db import models
from app.models import VerificationResponse, VerificationItem
from app.engine.design_verifier import DesignVerifier
from app.knowledge.loader import KnowledgeLoader

router = APIRouter(prefix="/api/v1/projects", tags=["verification"])


@router.post("/{project_id}/verify-design")
def run_verification(
    project_id: str,
    db: Session = Depends(get_db),
    kb: KnowledgeLoader = Depends(get_kb),
):
    """执行设计校核：图纸参数 vs 计算结果 vs 规范要求。"""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # Get calculation results
    calc_results = db.query(models.CalculationResult).filter(
        models.CalculationResult.project_id == project_id
    ).all()
    if not calc_results:
        raise HTTPException(status_code=400, detail="请先完成设计计算")

    calcs = [
        {
            "calculator_code": r.calculator_code,
            "output_parameters": r.output_parameters,
        }
        for r in calc_results
    ]

    # Get element mappings
    mappings = db.query(models.ElementMapping).filter(
        models.ElementMapping.project_id == project_id
    ).all()
    mapping_dicts = []
    for m in mappings:
        elem = db.query(models.ExtractedElement).filter(
            models.ExtractedElement.id == m.element_id
        ).first()
        mapping_dicts.append({
            "unit_code": m.unit_code,
            "param_name": m.param_name,
            "element_text": elem.text if elem else "",
            "parsed_value": elem.parsed_value if elem else None,
        })

    # Run verification
    verifier = DesignVerifier()
    result = verifier.verify(
        calculation_results=calcs,
        design_params={},
        element_mappings=mapping_dicts,
        knowledge_defaults=kb.defaults,
    )

    items = [
        VerificationItem(
            unit_code=it["unit_code"],
            unit_name_zh=it["unit_name_zh"],
            param_name=it["param_name"],
            drawing_value=it.get("drawing_value"),
            calculated_value=it.get("calculated_value"),
            required_min=it.get("required_min"),
            required_max=it.get("required_max"),
            status=it["status"],
            message=it["message"],
        )
        for it in result["items"]
    ]

    return VerificationResponse(
        project_id=project_id,
        items=items,
        summary=result["summary"],
    )
