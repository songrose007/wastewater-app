"""从数据库项目构造报告生成快照。"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db import models


VOLUME_KEYS = ("tank_volume_total", "tank_volume", "total_volume", "effective_volume")


def build_project_report_snapshot(project_id: str, db: Session) -> dict[str, Any] | None:
    """读取项目数据库记录，返回 HTML/PDF/DOCX 共用的报告快照。"""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        return None

    water_quality = _load_water_quality(project_id, db)
    route = _load_selected_route(project_id, db)
    calculation_results = _load_calculations(project_id, db)
    equipment_list = _load_equipment(project_id, db)
    cost_estimate = _load_cost(project_id, db)

    return {
        "project": project,
        "project_name": project.name,
        "wastewater_type": project.wastewater_type,
        "flow_rate": project.flow_rate or 0,
        "target_standard": project.target_standard_id or "N/A",
        "water_quality": water_quality,
        "process_route": route,
        "calculation_results": calculation_results,
        "summary": _build_summary(calculation_results),
        "equipment_list": equipment_list,
        "cost_estimate": cost_estimate,
    }


def _load_water_quality(project_id: str, db: Session) -> dict[str, float]:
    records = db.query(models.WaterQualityParameter).filter(
        models.WaterQualityParameter.project_id == project_id
    ).all()
    return {record.parameter_code: record.value for record in records}


def _load_selected_route(project_id: str, db: Session) -> dict[str, Any]:
    route = db.query(models.ProjectProcessRoute).filter(
        models.ProjectProcessRoute.project_id == project_id,
        models.ProjectProcessRoute.is_selected == True,  # noqa: E712
    ).first()
    if not route:
        return {"route_id": "N/A", "route_name_zh": "N/A", "total_score": 0}

    return {
        "route_id": route.route_id,
        "route_name_zh": route.route_name_zh,
        "total_score": route.total_score,
    }


def _load_calculations(project_id: str, db: Session) -> list[dict[str, Any]]:
    records = db.query(models.CalculationResult).filter(
        models.CalculationResult.project_id == project_id
    ).all()
    return [
        {
            "unit_code": record.calculator_code,
            "unit_name_zh": record.calculator_code,
            "computed_parameters": record.output_parameters or {},
            "warnings": record.warnings or [],
            "formulas": record.formulas_applied or [],
        }
        for record in records
    ]


def _load_equipment(project_id: str, db: Session) -> list[dict[str, Any]]:
    records = db.query(models.EquipmentSelection).filter(
        models.EquipmentSelection.project_id == project_id
    ).all()
    return [
        {
            "category": record.category,
            "model_id": record.model_id,
            "model_name_zh": record.model_name_zh,
            "quantity": record.quantity,
            "unit_price_cny": record.unit_price_cny,
            "total_price_cny": record.total_price_cny,
            "specs": record.specs or {},
            "manufacturer": record.manufacturer,
            "equipment_type": record.equipment_type,
            "process_unit_code": record.process_unit_code,
        }
        for record in records
    ]


def _load_cost(project_id: str, db: Session) -> dict[str, Any] | None:
    record = db.query(models.CostEstimate).filter(models.CostEstimate.project_id == project_id).first()
    if not record:
        return None
    return {
        "capex": record.capex_breakdown or {},
        "opex": record.opex_breakdown or {},
        "total_capex": record.total_capex,
        "total_annual_opex": record.total_annual_opex,
        "cost_per_m3": record.cost_per_m3 or 0,
        "assumptions": record.assumptions or {},
    }


def _build_summary(calculation_results: list[dict[str, Any]]) -> dict[str, Any]:
    total_volume = 0.0
    for result in calculation_results:
        params = result.get("computed_parameters", {})
        for key in VOLUME_KEYS:
            value = params.get(key)
            if isinstance(value, (int, float)):
                total_volume += value
                break

    return {
        "total_tank_volume_m3": round(total_volume, 1),
        "total_power_kw": 0,
        "total_sludge_production_kg_d": 0,
        "num_units_calculated": len(calculation_results),
    }
