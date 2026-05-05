"""排放标准查询 API。"""
from fastapi import APIRouter, Depends
from app.api.deps import get_kb
from app.knowledge.loader import KnowledgeLoader

router = APIRouter(prefix="/api/v1", tags=["standards"])


@router.get("/standards")
def list_standards(kb: KnowledgeLoader = Depends(get_kb)):
    return [
        {
            "id": s["id"],
            "name_zh": s["name_zh"],
            "grades": [c["grade"] for c in s.get("categories", [])],
        }
        for s in kb.standards
    ]


@router.get("/standards/{standard_id}")
def get_standard(standard_id: str, kb: KnowledgeLoader = Depends(get_kb)):
    for s in kb.standards:
        if s["id"] == standard_id:
            return s
    return {"error": "标准不存在"}


@router.get("/wastewater-types")
def list_wastewater_types():
    return {
        "types": [
            {"id": "domestic", "name_zh": "生活污水"},
            {"id": "textile_dyeing", "name_zh": "印染废水"},
            {"id": "electroplating", "name_zh": "电镀废水"},
            {"id": "food_processing", "name_zh": "食品废水"},
            {"id": "chemical", "name_zh": "化工废水"},
        ],
    }


@router.get("/parameters")
def list_parameters():
    return {
        "parameters": [
            {"code": "COD", "name_zh": "化学需氧量", "unit": "mg/L", "category": "organic"},
            {"code": "BOD5", "name_zh": "五日生化需氧量", "unit": "mg/L", "category": "organic"},
            {"code": "NH3_N", "name_zh": "氨氮", "unit": "mg/L", "category": "nutrient"},
            {"code": "TN", "name_zh": "总氮", "unit": "mg/L", "category": "nutrient"},
            {"code": "TP", "name_zh": "总磷", "unit": "mg/L", "category": "nutrient"},
            {"code": "SS", "name_zh": "悬浮物", "unit": "mg/L", "category": "solid"},
            {"code": "pH", "name_zh": "pH值", "unit": "--", "category": "physical"},
            {"code": "color", "name_zh": "色度", "unit": "times", "category": "physical"},
            {"code": "oil_grease", "name_zh": "动植物油", "unit": "mg/L", "category": "organic"},
            {"code": "conductivity", "name_zh": "电导率", "unit": "us/cm", "category": "physical"},
            {"code": "chloride", "name_zh": "氯化物", "unit": "mg/L", "category": "physical"},
            {"code": "Cr6plus", "name_zh": "六价铬", "unit": "mg/L", "category": "metal"},
            {"code": "total_cr", "name_zh": "总铬", "unit": "mg/L", "category": "metal"},
            {"code": "total_cu", "name_zh": "总铜", "unit": "mg/L", "category": "metal"},
            {"code": "total_zn", "name_zh": "总锌", "unit": "mg/L", "category": "metal"},
            {"code": "total_ni", "name_zh": "总镍", "unit": "mg/L", "category": "metal"},
            {"code": "cyanide", "name_zh": "氰化物", "unit": "mg/L", "category": "metal"},
            {"code": "fecal_coliform", "name_zh": "粪大肠菌群", "unit": "个/L", "category": "biological"},
            {"code": "temperature", "name_zh": "温度", "unit": "°C", "category": "physical"},
        ],
    }


@router.get("/process-templates")
def list_process_templates(kb: KnowledgeLoader = Depends(get_kb)):
    return [
        {
            "id": t["id"],
            "name_zh": t["name_zh"],
            "applies_to": t.get("applies_to", []),
            "units_count": len(t.get("units", [])),
        }
        for t in kb.templates
    ]
