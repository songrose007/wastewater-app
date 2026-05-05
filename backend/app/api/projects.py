"""项目 CRUD API。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_db
from app.db import models
from app.models import ProjectCreate, ProjectResponse, ProjectStatusEnum

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    db_project = models.Project(
        name=project.name,
        description=project.description,
        wastewater_type=project.wastewater_type.value,
        status="draft",
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return _to_response(db_project)


@router.get("", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(models.Project).order_by(models.Project.updated_at.desc()).all()
    return [_to_response(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return _to_response(project)


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, update: ProjectCreate, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    project.name = update.name
    project.description = update.description
    project.wastewater_type = update.wastewater_type.value
    db.commit()
    db.refresh(project)
    return _to_response(project)


@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    db.delete(project)
    db.commit()
    return {"message": "项目已删除"}


def _to_response(p: models.Project) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "wastewater_type": p.wastewater_type,
        "flow_rate": p.flow_rate,
        "target_standard_id": p.target_standard_id,
        "status": p.status,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }
