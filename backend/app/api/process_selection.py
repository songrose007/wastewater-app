"""工艺选择 API。"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_kb
from app.db import models
from app.models import ConfirmRouteRequest
from app.engine.process_selector import ProcessSelector
from app.knowledge.loader import KnowledgeLoader

router = APIRouter(prefix="/api/v1/projects", tags=["process-selection"])


@router.post("/{project_id}/select-process")
def select_process(project_id: str, db: Session = Depends(get_db), kb: KnowledgeLoader = Depends(get_kb)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if not project.target_standard_id:
        raise HTTPException(status_code=400, detail="请先设置目标排放标准")

    wq_params = db.query(models.WaterQualityParameter).filter(
        models.WaterQualityParameter.project_id == project_id
    ).all()

    water_quality = {p.parameter_code: p.value for p in wq_params}

    selector = ProcessSelector(kb)
    result = selector.select(
        wastewater_type=project.wastewater_type,
        flow_rate=project.flow_rate or 0,
        design_temp_min=project.design_temp_min or 10,
        water_quality=water_quality,
        target_standard_id=project.target_standard_id,
    )
    recommendations = result.get("recommendations", [])
    _save_process_recommendations(project, db, recommendations)
    db.commit()

    return {
        **result,
        "project_id": project_id,
        "routes": recommendations,
    }


@router.post("/{project_id}/confirm-route")
def confirm_route(project_id: str, req: ConfirmRouteRequest, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    route = db.query(models.ProjectProcessRoute).filter(
        models.ProjectProcessRoute.project_id == project_id,
        models.ProjectProcessRoute.route_id == req.route_id,
    ).first()
    if not route:
        raise HTTPException(status_code=400, detail="请先运行工艺路线推荐")

    db.query(models.ProjectProcessRoute).filter(
        models.ProjectProcessRoute.project_id == project_id
    ).update({"is_selected": False})
    route.is_selected = True
    project.status = "process_selected"

    db.commit()
    db.refresh(route)
    return {
        **_serialize_selected_route(route),
        "message": f"已选择工艺路线: {req.route_id}",
        "status": project.status,
    }


@router.get("/{project_id}/process-routes")
def get_process_routes(project_id: str, db: Session = Depends(get_db)):
    routes = db.query(models.ProjectProcessRoute).filter(
        models.ProjectProcessRoute.project_id == project_id
    ).order_by(models.ProjectProcessRoute.rank).all()
    return [_serialize_route(route) for route in routes]


@router.get("/{project_id}/selected-route")
def get_selected_route(project_id: str, db: Session = Depends(get_db)):
    route = db.query(models.ProjectProcessRoute).filter(
        models.ProjectProcessRoute.project_id == project_id,
        models.ProjectProcessRoute.is_selected == True,
    ).first()
    if not route:
        raise HTTPException(status_code=404, detail="未选择工艺路线")
    return _serialize_selected_route(route)


def _save_process_recommendations(
    project: models.Project,
    db: Session,
    recommendations: list[dict[str, Any]],
) -> None:
    db.query(models.ProjectProcessRoute).filter(
        models.ProjectProcessRoute.project_id == project.id,
    ).delete(synchronize_session=False)

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


def _serialize_unit(unit: models.RouteUnit) -> dict[str, Any]:
    return {
        "sequence": unit.sequence_order,
        "order": unit.sequence_order,
        "unit_code": unit.unit_code,
        "unit_name_zh": unit.unit_name_zh,
        "is_mandatory": unit.is_mandatory,
        "mandatory": unit.is_mandatory,
    }


def _serialize_route(route: models.ProjectProcessRoute) -> dict[str, Any]:
    units = sorted(route.units or [], key=lambda unit: unit.sequence_order)
    return {
        "route_id": route.route_id,
        "id": route.route_id,
        "template_id": route.route_id,
        "route_name_zh": route.route_name_zh,
        "name_zh": route.route_name_zh,
        "name": route.route_id,
        "rank": route.rank,
        "total_score": route.total_score,
        "score": route.total_score,
        "is_selected": route.is_selected,
        "units": [_serialize_unit(unit) for unit in units],
        "suitability_reasons": [],
        "reasons": [],
        "risks": [],
    }


def _serialize_selected_route(route: models.ProjectProcessRoute) -> dict[str, Any]:
    return {
        **_serialize_route(route),
        "route_name": route.route_name_zh or route.route_id,
    }
