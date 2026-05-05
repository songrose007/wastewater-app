"""造价估算 API。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_kb
from app.db import models
from app.models import CostEstimationResponse, CapexBreakdown, OpexBreakdown
from app.engine.cost_estimator import CostEstimator
from app.knowledge.loader import KnowledgeLoader

router = APIRouter(prefix="/api/v1/projects", tags=["cost"])


@router.post("/{project_id}/estimate-cost")
def estimate_cost(
    project_id: str,
    db: Session = Depends(get_db),
    kb: KnowledgeLoader = Depends(get_kb),
):
    """为项目估算投资和运行成本。"""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project.status not in ("equipment_selected", "cost_estimated"):
        raise HTTPException(status_code=400, detail="请先完成设备选型")

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

    # 获取设备清单
    equip_records = db.query(models.EquipmentSelection).filter(
        models.EquipmentSelection.project_id == project_id
    ).all()
    equipment_list = [
        {
            "category": e.category,
            "equipment_type": e.equipment_type,
            "model_id": e.model_id,
            "model_name_zh": e.model_name_zh,
            "quantity": e.quantity,
            "unit_price_cny": e.unit_price_cny,
            "total_price_cny": e.total_price_cny,
            "specs": e.specs or {},
            "manufacturer": e.manufacturer,
        }
        for e in equip_records
    ]

    # 运行造价估算
    estimator = CostEstimator(kb)
    result = estimator.estimate(
        flow_rate=project.flow_rate or 0,
        calculation_results=calcs,
        equipment_list=equipment_list,
    )

    capex = result["capex"]
    opex = result["opex"]
    assumptions = result["assumptions"]

    # 保存到数据库
    db.query(models.CostEstimate).filter(
        models.CostEstimate.project_id == project_id
    ).delete()

    db.add(models.CostEstimate(
        project_id=project_id,
        capex_breakdown=capex,
        opex_breakdown=opex,
        total_capex=result["total_capex"],
        total_annual_opex=result["total_annual_opex"],
        cost_per_m3=result["cost_per_m3"],
        assumptions=assumptions,
    ))

    project.status = "cost_estimated"
    db.commit()

    return CostEstimationResponse(
        project_id=project_id,
        capex=CapexBreakdown(
            civil_cost=capex["civil_cost"],
            equipment_cost=capex["equipment_cost"],
            installation_cost=capex["installation_cost"],
            engineering_cost=capex["engineering_cost"],
            contingency_cost=capex["contingency_cost"],
            total_capex=capex["total_capex"],
        ),
        opex=OpexBreakdown(
            energy_cost=opex["energy_cost"],
            chemical_cost=opex["chemical_cost"],
            labor_cost=opex["labor_cost"],
            maintenance_cost=opex["maintenance_cost"],
            sludge_disposal_cost=opex["sludge_disposal_cost"],
            depreciation_cost=opex["depreciation_cost"],
            total_annual_opex=opex["total_annual_opex"],
        ),
        cost_per_m3=result["cost_per_m3"],
        assumptions=assumptions,
    )


@router.get("/{project_id}/cost")
def get_cost(
    project_id: str,
    db: Session = Depends(get_db),
):
    """获取已保存的造价估算结果。"""
    estimate = db.query(models.CostEstimate).filter(
        models.CostEstimate.project_id == project_id
    ).first()
    if not estimate:
        raise HTTPException(status_code=404, detail="未找到造价估算，请先执行估算")

    capex = estimate.capex_breakdown or {}
    opex = estimate.opex_breakdown or {}

    return CostEstimationResponse(
        project_id=project_id,
        capex=CapexBreakdown(
            civil_cost=capex.get("civil_cost", 0),
            equipment_cost=capex.get("equipment_cost", 0),
            installation_cost=capex.get("installation_cost", 0),
            engineering_cost=capex.get("engineering_cost", 0),
            contingency_cost=capex.get("contingency_cost", 0),
            total_capex=capex.get("total_capex", 0),
        ),
        opex=OpexBreakdown(
            energy_cost=opex.get("energy_cost", 0),
            chemical_cost=opex.get("chemical_cost", 0),
            labor_cost=opex.get("labor_cost", 0),
            maintenance_cost=opex.get("maintenance_cost", 0),
            sludge_disposal_cost=opex.get("sludge_disposal_cost", 0),
            depreciation_cost=opex.get("depreciation_cost", 0),
            total_annual_opex=opex.get("total_annual_opex", 0),
        ),
        cost_per_m3=estimate.cost_per_m3 or 0,
        assumptions=estimate.assumptions or {},
    )
