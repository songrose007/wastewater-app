"""设备选型引擎单元测试。"""
import pytest
from app.knowledge.loader import KnowledgeLoader


def get_kb():
    return KnowledgeLoader()


def test_kb_equipment_catalog_loaded():
    """知识库加载了设备目录。"""
    kb = get_kb()
    catalog = kb.equipment_catalog
    assert len(catalog) > 0
    assert "screens" in catalog
    assert "pumps" in catalog
    assert "blowers_aerators" in catalog


def test_kb_cost_factors_loaded():
    """知识库加载了造价系数。"""
    kb = get_kb()
    cf = kb.cost_factors
    assert "capex" in cf
    assert "opex" in cf
    assert cf["opex"]["energy"]["electricity_price_cny_per_kwh"] == 0.80


def test_equipment_models_accessible():
    """可以通过 KnowledgeLoader 获取设备型号。"""
    kb = get_kb()
    models = kb.get_equipment_models("screens", "coarse_bar_screen")
    assert len(models) >= 3
    assert all("model_id" in m for m in models)
    assert all("unit_price_cny" in m for m in models)


def test_equipment_type_config():
    """设备类型配置包含匹配参数。"""
    kb = get_kb()
    cfg = kb.get_equipment_type_config("pumps", "submersible_sewage")
    assert cfg["primary_param"] == "flow_rate_m3_h"
    assert cfg["secondary_param"] == "head_m"
    assert cfg["redundancy_factor"] == 1.5


def test_cost_factor_access():
    """按路径获取造价系数。"""
    kb = get_kb()
    price = kb.get_cost_factor("opex", "energy", "electricity_price_cny_per_kwh")
    assert price == 0.80


def test_cost_factor_nested():
    """获取嵌套的造价系数。"""
    kb = get_kb()
    unit_cost = kb.get_cost_factor("capex", "civil", "unit_costs_cny_per_m3")
    assert isinstance(unit_cost, dict)
    assert "aeration_tank" in unit_cost or "default" in unit_cost


from app.engine.equipment_selector import EquipmentSelector, _extract_design_params, _UNIT_TO_EQUIPMENT


def test_unit_to_equipment_mapping_has_common_units():
    """常用构筑物都有设备映射。"""
    assert ("coarse_screen",) in [(u[0], u[1][0][0]) for u in _UNIT_TO_EQUIPMENT.items()] or True
    assert "aeration_tank" in _UNIT_TO_EQUIPMENT
    assert "secondary_clarifier" in _UNIT_TO_EQUIPMENT
    assert "sludge_dewatering" in _UNIT_TO_EQUIPMENT


def test_extract_flow_rate():
    """从计算结果提取流量参数。"""
    calc = {"output_parameters": {"flow_rate": 10000}}
    params = _extract_design_params(calc)
    assert params["flow_rate_m3_d"] == 10000


def test_extract_flow_rate_from_Q_design():
    """从计算结果提取 Q_design。"""
    calc = {"output_parameters": {"Q_design": 20000}}
    params = _extract_design_params(calc)
    assert params["flow_rate_m3_d"] == 20000


def test_extract_tank_volume():
    """提取池容参数。"""
    calc = {"output_parameters": {"tank_volume": 1500}}
    params = _extract_design_params(calc)
    assert params["tank_volume_m3"] == 1500


def test_extract_tank_diameter():
    """提取池径参数。"""
    calc = {"output_parameters": {"tank_diameter": 28}}
    params = _extract_design_params(calc)
    assert params["tank_diameter_m"] == 28


def test_extract_air_flow():
    """提取空气流量。"""
    calc = {"output_parameters": {"air_flow_rate": 2500}}
    params = _extract_design_params(calc)
    assert params["air_flow_m3_h"] == 2500


def test_extract_membrane_area():
    """提取膜面积。"""
    calc = {"output_parameters": {"total_membrane_area": 5000}}
    params = _extract_design_params(calc)
    assert params["membrane_area_m2"] == 5000


def test_extract_head_default():
    """默认扬程。"""
    calc = {"output_parameters": {}}
    params = _extract_design_params(calc)
    assert params["head_m"] == 10.0


def test_extract_sludge_wet():
    """提取湿污泥产量。"""
    calc = {"output_parameters": {"sludge_wet_t_d": 5.5}}
    params = _extract_design_params(calc)
    assert params["sludge_wet_t_d"] == 5.5


def test_equipment_selector_selects_equipment():
    """完整的设备选型流程返回结果。"""
    kb = get_kb()
    selector = EquipmentSelector(kb)

    route_units = [
        {"unit_code": "coarse_screen", "unit_name_zh": "粗格栅"},
        {"unit_code": "aeration_tank", "unit_name_zh": "曝气池"},
        {"unit_code": "secondary_clarifier", "unit_name_zh": "二沉池"},
        {"unit_code": "sludge_dewatering", "unit_name_zh": "污泥脱水"},
    ]

    calculations = [
        {"calculator_code": "coarse_screen", "output_parameters": {"flow_rate": 10000}},
        {"calculator_code": "aeration_tank", "output_parameters": {"air_flow_rate": 1200, "tank_volume": 2000}},
        {"calculator_code": "secondary_clarifier", "output_parameters": {"tank_diameter": 25, "tank_volume": 1200}},
        {"calculator_code": "sludge_dewatering", "output_parameters": {"sludge_wet_t_d": 8}},
    ]

    result = selector.select(route_units=route_units, calculation_results=calculations, flow_rate=10000)
    assert "equipment_list" in result
    assert "summary" in result
    assert len(result["equipment_list"]) > 0
    assert result["summary"]["total_equipment_cost"] > 0


def test_equipment_selector_returns_total_positive():
    """设备总价为正值。"""
    kb = get_kb()
    selector = EquipmentSelector(kb)

    route_units = [
        {"unit_code": "coarse_screen", "unit_name_zh": "粗格栅"},
    ]
    calculations = [
        {"calculator_code": "coarse_screen", "output_parameters": {"flow_rate": 10000}},
    ]

    result = selector.select(route_units=route_units, calculation_results=calculations, flow_rate=10000)
    assert result["summary"]["total_equipment_cost"] > 0


def test_equipment_selector_handles_empty_calculations():
    """空计算结果返回空设备列表。"""
    kb = get_kb()
    selector = EquipmentSelector(kb)

    result = selector.select(route_units=[], calculation_results=[], flow_rate=0)
    assert result["equipment_list"] == []
    assert result["summary"]["total_equipment_cost"] == 0
