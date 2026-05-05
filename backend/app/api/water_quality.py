"""水质参数 API。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_db
from app.db import models
from app.models import WaterQualityInput, ParameterValue

router = APIRouter(prefix="/api/v1/projects", tags=["water-quality"])


@router.post("/{project_id}/water-quality")
def save_water_quality(project_id: str, data: dict, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # Extract meta fields from flat dict
    flow_rate = data.pop("flow_rate", None)
    target_standard_id = data.pop("target_standard_id", None)
    data.pop("flow_rate_peak_factor", None)
    data.pop("design_temp_min", None)
    data.pop("design_temp_max", None)
    data.pop("wastewater_type", None)

    if flow_rate is not None:
        project.flow_rate = float(flow_rate)
    if target_standard_id is not None:
        project.target_standard_id = str(target_standard_id)
    project.status = "input_done"

    db.query(models.WaterQualityParameter).filter(
        models.WaterQualityParameter.project_id == project_id
    ).delete()

    # Accept parameters as flat key-value dict
    # Handle both: {"ph": 7, "cod": 350} and {"parameters": [{...}]}
    params_data = data.pop("parameters", None)
    if params_data and isinstance(params_data, list):
        # Structured format
        for param in params_data:
            if isinstance(param, dict):
                code = param.get("parameter_code", "")
                val = param.get("value", 0)
                unit = param.get("unit", "mg/L")
                db.add(models.WaterQualityParameter(
                    project_id=project_id,
                    parameter_code=code,
                    parameter_name_zh=PARAM_NAMES.get(code, code),
                    value=float(val),
                    unit=unit,
                    category=_get_category(code),
                ))
    else:
        # Flat format: {ph: 7, cod: 350, bod5: 180, ...}
        for code, val in data.items():
            if isinstance(code, str) and code.strip():
                try:
                    num_val = float(val) if val is not None else 0
                except (ValueError, TypeError):
                    continue
                db.add(models.WaterQualityParameter(
                    project_id=project_id,
                    parameter_code=code,
                    parameter_name_zh=PARAM_NAMES.get(code, code),
                    value=num_val,
                    unit="mg/L" if code not in ("ph", "temperature", "color") else "",
                    category=_get_category(code),
                ))

    db.commit()
    return {"message": "水质参数已保存", "status": project.status}


@router.get("/{project_id}/water-quality")
def get_water_quality(project_id: str, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    params = db.query(models.WaterQualityParameter).filter(
        models.WaterQualityParameter.project_id == project_id
    ).all()

    return {
        "project_id": project_id,
        "wastewater_type": project.wastewater_type,
        "flow_rate": project.flow_rate,
        "flow_rate_peak_factor": project.flow_rate_peak_factor,
        "design_temp_min": project.design_temp_min,
        "design_temp_max": project.design_temp_max,
        "target_standard_id": project.target_standard_id,
        "parameters": [
            {
                "parameter_code": p.parameter_code,
                "parameter_name_zh": p.parameter_name_zh,
                "value": p.value,
                "unit": p.unit,
                "category": p.category,
            }
            for p in params
        ],
    }


PARAM_NAMES = {
    "COD": "化学需氧量",
    "BOD5": "五日生化需氧量",
    "NH3_N": "氨氮",
    "TN": "总氮",
    "TP": "总磷",
    "SS": "悬浮物",
    "pH": "pH值",
    "color": "色度",
    "oil_grease": "动植物油",
    "conductivity": "电导率",
    "chloride": "氯化物",
    "Cr6plus": "六价铬",
    "total_cr": "总铬",
    "total_cu": "总铜",
    "total_zn": "总锌",
    "total_ni": "总镍",
    "cyanide": "氰化物",
    "fecal_coliform": "粪大肠菌群",
    "temperature": "温度",
}


def _get_category(code: str) -> str:
    organic = {"COD", "BOD5"}
    nutrient = {"NH3_N", "TN", "TP"}
    solid = {"SS"}
    metal = {"Cr6plus", "total_cr", "total_cu", "total_zn", "total_ni", "cyanide"}
    physical = {"pH", "color", "temperature", "conductivity", "chloride"}
    if code in organic:
        return "organic"
    if code in nutrient:
        return "nutrient"
    if code in solid:
        return "solid"
    if code in metal:
        return "metal"
    if code in physical:
        return "physical"
    return "other"
