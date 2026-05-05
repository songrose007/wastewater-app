"""设计参数查询 API — 获取工艺路线中所有构筑物的默认参数和推荐范围。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_kb
from app.db import models
from app.models import DesignParamsResponse, ParamDef
from app.knowledge.loader import KnowledgeLoader

router = APIRouter(prefix="/api/v1/projects", tags=["design-params"])


@router.get("/{project_id}/design-params")
def get_design_params(
    project_id: str,
    db: Session = Depends(get_db),
    kb: KnowledgeLoader = Depends(get_kb),
):
    """获取项目已选工艺路线中所有构筑物的设计参数默认值及推荐范围。"""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    route = db.query(models.ProjectProcessRoute).filter(
        models.ProjectProcessRoute.project_id == project_id,
        models.ProjectProcessRoute.is_selected == True,
    ).first()
    if not route:
        raise HTTPException(status_code=400, detail="请先选择工艺路线")

    route_units = db.query(models.RouteUnit).filter(
        models.RouteUnit.route_id == route.id
    ).order_by(models.RouteUnit.sequence_order).all()

    units_data = []
    for u in route_units:
        # Get default values
        defaults = kb.get_calculator_defaults(u.unit_code)
        # Get ranges
        ranges = kb.get_calculator_param_ranges(u.unit_code)
        # Get the calculator unit name
        calc_info = kb.defaults.get(u.unit_code, {})
        unit_name = calc_info.get("name_zh", u.unit_name_zh)

        params_list = []
        for param_name, default_val in defaults.items():
            range_vals = ranges.get(param_name, (None, None))
            params_list.append({
                "param_name": param_name,
                "param_name_zh": param_name,
                "value": default_val,
                "unit": _get_param_unit(calc_info, param_name),
                "range_min": range_vals[0],
                "range_max": range_vals[1],
            })

        units_data.append({
            "unit_code": u.unit_code,
            "unit_name_zh": unit_name,
            "parameters": params_list,
        })

    return {
        "project_id": project_id,
        "route_name": route.route_name_zh or route.route_id,
        "units": units_data,
    }


def _get_param_unit(calc_info: dict, param_name: str) -> str:
    """从 calculator 的 YAML 配置中提取参数单位。"""
    params = calc_info.get("parameters", {})
    param = params.get(param_name, {})
    if isinstance(param, dict):
        return param.get("unit", "")
    return ""
