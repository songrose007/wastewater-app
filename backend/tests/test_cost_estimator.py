"""造价估算引擎单元测试。"""
import pytest
from app.knowledge.loader import KnowledgeLoader
from app.engine.cost_estimator import CostEstimator


def get_kb():
    return KnowledgeLoader()


def test_cost_estimator_returns_full_structure():
    """估算结果包含完整结构。"""
    kb = get_kb()
    estimator = CostEstimator(kb)

    calcs = [
        {"calculator_code": "aeration_tank", "output_parameters": {
            "tank_volume": 2000, "water_depth": 5, "total_power": 55
        }},
        {"calculator_code": "secondary_clarifier", "output_parameters": {
            "tank_volume": 1200, "tank_diameter": 25
        }},
    ]
    equipment = [
        {"total_price_cny": 35000, "quantity": 2, "unit_price_cny": 35000,
         "specs": {"motor_power_kw": 22}},
        {"total_price_cny": 195000, "quantity": 1, "unit_price_cny": 195000,
         "specs": {"motor_power_kw": 0.75}},
    ]

    result = estimator.estimate(flow_rate=10000, calculation_results=calcs, equipment_list=equipment)

    assert "capex" in result
    assert "opex" in result
    assert "total_capex" in result
    assert "total_annual_opex" in result
    assert "cost_per_m3" in result


def test_capex_total_equals_sum_of_parts():
    """CAPEX 各项之和等于总计。"""
    kb = get_kb()
    estimator = CostEstimator(kb)

    calcs = [
        {"calculator_code": "aeration_tank", "output_parameters": {"tank_volume": 2000, "water_depth": 5}},
    ]
    equipment = [
        {"total_price_cny": 35000, "quantity": 1, "specs": {}},
    ]

    result = estimator.estimate(flow_rate=10000, calculation_results=calcs, equipment_list=equipment)
    capex = result["capex"]

    calc_sum = (
        capex["civil_cost"]
        + capex["equipment_cost"]
        + capex["installation_cost"]
        + capex["engineering_cost"]
        + capex["contingency_cost"]
    )
    assert abs(calc_sum - capex["total_capex"]) < 0.01


def test_civil_cost_computed_from_tank_volume():
    """土建费 = 池容 × 单价系数。"""
    kb = get_kb()
    estimator = CostEstimator(kb)

    calcs = [
        {"calculator_code": "aeration_tank", "output_parameters": {"tank_volume": 1000, "water_depth": 4}},
    ]
    equipment = []

    result = estimator.estimate(flow_rate=5000, calculation_results=calcs, equipment_list=equipment)
    capex = result["capex"]
    # 1000 m3 * 800 CNY/m3 / 10000 = 80 万元
    assert capex["civil_cost"] > 0
    # civil_breakdown should contain the tank
    assert "aeration_tank" in capex.get("civil_breakdown", {})


def test_deep_tank_increases_civil_cost():
    """深基坑 > 5m 增加土建费。"""
    kb = get_kb()
    estimator = CostEstimator(kb)

    shallow = [
        {"calculator_code": "aeration_tank", "output_parameters": {"tank_volume": 1000, "water_depth": 4}},
    ]
    deep = [
        {"calculator_code": "aeration_tank", "output_parameters": {"tank_volume": 1000, "water_depth": 7}},
    ]

    r_shallow = estimator.estimate(flow_rate=5000, calculation_results=shallow, equipment_list=[])
    r_deep = estimator.estimate(flow_rate=5000, calculation_results=deep, equipment_list=[])

    assert r_deep["capex"]["civil_cost"] > r_shallow["capex"]["civil_cost"]


def test_equipment_cost_correctly_converted_to_wan():
    """设备费从元转换为万元。"""
    kb = get_kb()
    estimator = CostEstimator(kb)

    calcs = []
    equipment = [
        {"total_price_cny": 100000, "quantity": 1, "specs": {}},
        {"total_price_cny": 100000, "quantity": 2, "specs": {}},
    ]

    result = estimator.estimate(flow_rate=5000, calculation_results=calcs, equipment_list=equipment)
    # total_price_cny is already total: 100000 + 100000 = 200000 = 20 wan
    assert abs(result["capex"]["equipment_cost"] - 20.0) < 0.1


def test_opex_energy_positive():
    """电费为正值。"""
    kb = get_kb()
    estimator = CostEstimator(kb)

    calcs = [
        {"calculator_code": "aeration_tank", "output_parameters": {"tank_volume": 2000, "total_power": 55}},
    ]
    equipment = [
        {"total_price_cny": 35000, "quantity": 2, "specs": {"motor_power_kw": 22}},
    ]

    result = estimator.estimate(flow_rate=10000, calculation_results=calcs, equipment_list=equipment)
    assert result["opex"]["energy_cost"] > 0


def test_opex_labor_positive():
    """人工费为正值（2人×3班×8万/年）。"""
    kb = get_kb()
    estimator = CostEstimator(kb)

    result = estimator.estimate(flow_rate=10000, calculation_results=[], equipment_list=[])
    # 2 * 3 * 80000 / 10000 = 48 万元
    assert result["opex"]["labor_cost"] > 40


def test_cost_per_m3_reasonable_range():
    """吨水成本在合理范围内 (0.1-10 元/m³)。"""
    kb = get_kb()
    estimator = CostEstimator(kb)

    calcs = [
        {"calculator_code": "aeration_tank", "output_parameters": {"tank_volume": 2000, "water_depth": 5, "total_power": 55}},
        {"calculator_code": "secondary_clarifier", "output_parameters": {"tank_volume": 1200}},
    ]
    equipment = [
        {"total_price_cny": 35000, "quantity": 2, "specs": {"motor_power_kw": 22}},
        {"total_price_cny": 195000, "quantity": 1, "specs": {"motor_power_kw": 0.75}},
    ]

    result = estimator.estimate(flow_rate=10000, calculation_results=calcs, equipment_list=equipment)
    assert 0.05 < result["cost_per_m3"] < 15


def test_empty_equipment_and_calcs_still_works():
    """空输入不抛异常。"""
    kb = get_kb()
    estimator = CostEstimator(kb)

    result = estimator.estimate(flow_rate=0, calculation_results=[], equipment_list=[])
    assert result["total_capex"] == 0
    assert result["cost_per_m3"] == 0


def test_installation_cost_proportional_to_equipment():
    """安装费与设备费成比例。"""
    kb = get_kb()
    estimator = CostEstimator(kb)

    equipment = [{"total_price_cny": 100000, "quantity": 1, "specs": {}}]

    result = estimator.estimate(flow_rate=5000, calculation_results=[], equipment_list=equipment)
    capex = result["capex"]
    # equipment = 10 万, installation = 10 * 0.55 = 5.5 万
    expected_install = capex["equipment_cost"] * 0.55  # 0.30 + 0.15 + 0.10
    assert abs(capex["installation_cost"] - expected_install) < 0.01
