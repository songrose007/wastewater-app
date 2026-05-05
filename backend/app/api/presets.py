"""参数预设 CRUD API — 管理工程师的经验参数模板。"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.api.deps import get_db
from app.db import models
from app.models import PresetCreate, PresetUpdate, PresetResponse, PresetParamValue

router = APIRouter(prefix="/api/v1/presets", tags=["presets"])


@router.get("")
def list_presets(db: Session = Depends(get_db)):
    """列出所有参数预设。"""
    presets = db.query(models.ParameterPreset).order_by(
        models.ParameterPreset.is_default.desc(),
        models.ParameterPreset.updated_at.desc()
    ).all()
    return {
        "presets": [_preset_to_response(p) for p in presets],
    }


@router.post("")
def create_preset(data: PresetCreate, db: Session = Depends(get_db)):
    """创建新的参数预设。"""
    if data.is_default:
        _clear_defaults(db)

    preset = models.ParameterPreset(
        name=data.name,
        description=data.description,
        wastewater_type=data.wastewater_type,
    )
    db.add(preset)
    db.flush()

    for p in data.parameters:
        db.add(models.PresetParameter(
            preset_id=preset.id,
            unit_code=p.unit_code,
            param_name=p.param_name,
            param_value=p.param_value,
        ))

    db.commit()
    db.refresh(preset)
    return _preset_to_response(preset)


@router.get("/{preset_id}")
def get_preset(preset_id: int, db: Session = Depends(get_db)):
    """获取单个预设详情。"""
    preset = db.query(models.ParameterPreset).filter(
        models.ParameterPreset.id == preset_id
    ).first()
    if not preset:
        raise HTTPException(status_code=404, detail="预设不存在")
    return _preset_to_response(preset)


@router.put("/{preset_id}")
def update_preset(preset_id: int, data: PresetUpdate, db: Session = Depends(get_db)):
    """更新参数预设。"""
    preset = db.query(models.ParameterPreset).filter(
        models.ParameterPreset.id == preset_id
    ).first()
    if not preset:
        raise HTTPException(status_code=404, detail="预设不存在")

    if data.name is not None:
        preset.name = data.name
    if data.description is not None:
        preset.description = data.description
    if data.is_default is not None:
        if data.is_default:
            _clear_defaults(db)
        preset.is_default = data.is_default

    if data.parameters is not None:
        db.query(models.PresetParameter).filter(
            models.PresetParameter.preset_id == preset_id
        ).delete()
        for p in data.parameters:
            db.add(models.PresetParameter(
                preset_id=preset_id,
                unit_code=p.unit_code,
                param_name=p.param_name,
                param_value=p.param_value,
            ))

    preset.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(preset)
    return _preset_to_response(preset)


@router.delete("/{preset_id}")
def delete_preset(preset_id: int, db: Session = Depends(get_db)):
    """删除参数预设。"""
    preset = db.query(models.ParameterPreset).filter(
        models.ParameterPreset.id == preset_id
    ).first()
    if not preset:
        raise HTTPException(status_code=404, detail="预设不存在")
    db.delete(preset)
    db.commit()
    return {"status": "deleted"}


def _clear_defaults(db: Session):
    """清除所有其他预设的默认标记。"""
    db.query(models.ParameterPreset).filter(
        models.ParameterPreset.is_default == True
    ).update({"is_default": False})


def _preset_to_response(p: models.ParameterPreset) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "wastewater_type": p.wastewater_type,
        "is_default": p.is_default,
        "parameters": [
            {
                "unit_code": pp.unit_code,
                "param_name": pp.param_name,
                "param_value": pp.param_value,
            }
            for pp in p.parameters
        ],
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }
