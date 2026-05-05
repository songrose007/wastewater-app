"""设备选型 API。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.api.deps import get_db, get_kb
from app.db import models
from app.models import EquipmentSelectionResponse, EquipmentListResponse, EquipmentItem, EquipmentCategoryGroup
from app.engine.equipment_selector import EquipmentSelector
from app.knowledge.loader import KnowledgeLoader

router = APIRouter(prefix="/api/v1/projects", tags=["equipment"])

CATEGORY_NAMES_ZH = {
    "screens": "格栅",
    "grit_removal": "沉砂池设备",
    "pumps": "泵类",
    "blowers_aerators": "曝气设备",
    "mixers": "搅拌/推流设备",
    "clarifier_mechanisms": "沉淀池刮吸泥机",
    "sludge_handling": "污泥处理设备",
    "chemical_dosing": "加药系统",
    "mbr_membranes": "MBR膜组件",
    "uv_disinfection": "紫外消毒设备",
    "instruments": "仪表与自控",
}


@router.post("/{project_id}/select-equipment")
def select_equipment(
    project_id: str,
    db: Session = Depends(get_db),
    kb: KnowledgeLoader = Depends(get_kb),
):
    """根据计算结果自动匹配设备。"""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project.status not in ("calculated", "equipment_selected"):
        raise HTTPException(status_code=400, detail="请先完成设计计算")

    # 获取选中的工艺路线和单元
    route = db.query(models.ProjectProcessRoute).filter(
        models.ProjectProcessRoute.project_id == project_id,
        models.ProjectProcessRoute.is_selected == True,
    ).first()
    if not route:
        raise HTTPException(status_code=400, detail="未找到已选工艺路线")

    route_units = db.query(models.RouteUnit).filter(
        models.RouteUnit.route_id == route.id
    ).order_by(models.RouteUnit.sequence_order).all()

    # 获取计算结果
    calc_results = db.query(models.CalculationResult).filter(
        models.CalculationResult.project_id == project_id
    ).all()
    calcs = [
        {
            "calculator_code": r.calculator_code,
            "output_parameters": r.output_parameters,
        }
        for r in calc_results
    ]

    # 运行设备选型
    selector = EquipmentSelector(kb)
    units_dicts = [{"unit_code": u.unit_code, "unit_name_zh": u.unit_name_zh} for u in route_units]
    result = selector.select(
        route_units=units_dicts,
        calculation_results=calcs,
        flow_rate=project.flow_rate or 0,
    )

    equipment_list = result["equipment_list"]

    # 保存到数据库
    db.query(models.EquipmentSelection).filter(
        models.EquipmentSelection.project_id == project_id
    ).delete()

    for item in equipment_list:
        db.add(models.EquipmentSelection(
            project_id=project_id,
            category=item["category"],
            process_unit_code=item["process_unit_code"],
            equipment_type=item["equipment_type"],
            model_id=item["model_id"],
            model_name_zh=item["model_name_zh"],
            quantity=item["quantity"],
            unit_price_cny=item["unit_price_cny"],
            total_price_cny=item["total_price_cny"],
            specs=item.get("specs", {}),
            manufacturer=item.get("manufacturer"),
            is_chinese=item.get("is_chinese", True),
            selection_rationale=item.get("selection_rationale"),
        ))

    project.status = "equipment_selected"
    db.commit()

    items = [
        EquipmentItem(
            category=it["category"],
            process_unit_code=it["process_unit_code"],
            equipment_type=it["equipment_type"],
            model_id=it["model_id"],
            model_name_zh=it["model_name_zh"],
            quantity=it["quantity"],
            unit_price_cny=it["unit_price_cny"],
            total_price_cny=it["total_price_cny"],
            specs=it.get("specs", {}),
            manufacturer=it.get("manufacturer"),
            is_chinese=it.get("is_chinese", True),
            selection_rationale=it.get("selection_rationale"),
        )
        for it in equipment_list
    ]

    return EquipmentSelectionResponse(
        project_id=project_id,
        equipment_list=items,
        summary=result["summary"],
    )


@router.get("/{project_id}/equipment")
def get_equipment(
    project_id: str,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """获取已保存的设备选型结果。"""
    query = db.query(models.EquipmentSelection).filter(
        models.EquipmentSelection.project_id == project_id
    )
    if category:
        query = query.filter(models.EquipmentSelection.category == category)

    records = query.all()

    # 按类别分组
    groups: dict[str, list] = {}
    for r in records:
        if r.category not in groups:
            groups[r.category] = []
        groups[r.category].append(EquipmentItem(
            category=r.category,
            process_unit_code=r.process_unit_code,
            equipment_type=r.equipment_type,
            model_id=r.model_id,
            model_name_zh=r.model_name_zh,
            quantity=r.quantity,
            unit_price_cny=r.unit_price_cny,
            total_price_cny=r.total_price_cny,
            specs=r.specs or {},
            manufacturer=r.manufacturer,
            is_chinese=r.is_chinese,
            selection_rationale=r.selection_rationale,
        ))

    categories = [
        EquipmentCategoryGroup(
            category=cat,
            name_zh=CATEGORY_NAMES_ZH.get(cat, cat),
            items=items,
        )
        for cat, items in groups.items()
    ]

    total = sum(
        r.total_price_cny
        for r in records
    )

    return EquipmentListResponse(
        project_id=project_id,
        categories=categories,
        total_equipment_cost=total,
    )
