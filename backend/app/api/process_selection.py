"""工艺选择 API。"""
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

    return result


@router.post("/{project_id}/confirm-route")
def confirm_route(project_id: str, req: ConfirmRouteRequest, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    project.status = "process_selected"
    db.query(models.ProjectProcessRoute).filter(
        models.ProjectProcessRoute.project_id == project_id
    ).update({"is_selected": False})

    route = db.query(models.ProjectProcessRoute).filter(
        models.ProjectProcessRoute.project_id == project_id,
        models.ProjectProcessRoute.route_id == req.route_id,
    ).first()

    if route:
        route.is_selected = True
    else:
        route = models.ProjectProcessRoute(
            project_id=project_id,
            route_id=req.route_id,
            route_name_zh=req.route_id,
            rank=1,
            total_score=100,
            is_selected=True,
        )
        db.add(route)

    db.commit()
    return {"message": f"已选择工艺路线: {req.route_id}", "status": project.status}


@router.get("/{project_id}/process-routes")
def get_process_routes(project_id: str, db: Session = Depends(get_db)):
    routes = db.query(models.ProjectProcessRoute).filter(
        models.ProjectProcessRoute.project_id == project_id
    ).order_by(models.ProjectProcessRoute.rank).all()
    return [{
        "route_id": r.route_id,
        "route_name_zh": r.route_name_zh,
        "rank": r.rank,
        "total_score": r.total_score,
        "is_selected": r.is_selected,
    } for r in routes]


@router.get("/{project_id}/selected-route")
def get_selected_route(project_id: str, db: Session = Depends(get_db)):
    route = db.query(models.ProjectProcessRoute).filter(
        models.ProjectProcessRoute.project_id == project_id,
        models.ProjectProcessRoute.is_selected == True,
    ).first()
    if not route:
        raise HTTPException(status_code=404, detail="未选择工艺路线")
    return {
        "route_id": route.route_id,
        "route_name_zh": route.route_name_zh,
        "total_score": route.total_score,
    }
