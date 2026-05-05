"""设备选型引擎 — 根据计算结果自动匹配设备型号。"""
from typing import Dict, List, Any, Optional, Tuple
from app.knowledge.loader import KnowledgeLoader


# 构筑物代码到设备类别/类型的映射
# 每个构筑物可对应多个设备类型
_UNIT_TO_EQUIPMENT: Dict[str, List[Tuple[str, str]]] = {
    "coarse_screen": [("screens", "coarse_bar_screen")],
    "fine_screen": [("screens", "fine_bar_screen")],
    "fine_screen_1mm": [("screens", "fine_screen_1mm")],
    "grit_chamber": [("grit_removal", "aerated_grit")],
    "aeration_tank": [
        ("blowers_aerators", "roots_blower"),
        ("blowers_aerators", "fine_bubble_diffuser"),
    ],
    "anoxic_tank": [("mixers", "submersible_flow_pusher")],
    "anaerobic_tank": [("mixers", "submersible_mixer")],
    "oxidation_ditch": [
        ("blowers_aerators", "surface_aerator"),
        ("mixers", "submersible_flow_pusher"),
    ],
    "sbr_reactor": [
        ("pumps", "submersible_sewage"),
        ("blowers_aerators", "fine_bubble_diffuser"),
    ],
    "mbr_tank": [("mbr_membranes", "hollow_fiber")],
    "primary_clarifier": [("clarifier_mechanisms", "peripheral_drive")],
    "secondary_clarifier": [("clarifier_mechanisms", "suction")],
    "primary_enhanced": [
        ("clarifier_mechanisms", "peripheral_drive"),
        ("chemical_dosing", "pac_system"),
    ],
    "coagulation_tank": [
        ("mixers", "submersible_mixer"),
        ("chemical_dosing", "pac_system"),
    ],
    "coagulation_sedimentation": [
        ("clarifier_mechanisms", "peripheral_drive"),
        ("mixers", "submersible_mixer"),
    ],
    "coagulation_decolorization": [
        ("mixers", "submersible_mixer"),
        ("chemical_dosing", "pac_system"),
        ("chemical_dosing", "naoh_system"),
    ],
    "tube_settler": [("clarifier_mechanisms", "center_drive")],
    "disinfection": [
        ("uv_disinfection", "open_channel"),
        ("chemical_dosing", "disinfectant_system"),
    ],
    "sludge_thickening": [("clarifier_mechanisms", "center_drive")],
    "sludge_dewatering": [("sludge_handling", "belt_press")],
    "hydrolysis_acidification": [
        ("mixers", "submersible_flow_pusher"),
        ("pumps", "submersible_sewage"),
    ],
    "uasb": [("pumps", "submersible_sewage")],
    "advanced_oxidation": [
        ("chemical_dosing", "pac_system"),
        ("chemical_dosing", "naoh_system"),
        ("mixers", "submersible_mixer"),
    ],
    "equalization_tank": [
        ("mixers", "submersible_mixer"),
        ("pumps", "submersible_sewage"),
    ],
    "sand_filter": [("pumps", "clean_water")],
    "ion_exchange": [("chemical_dosing", "naoh_system")],

    # 工业预处理单元
    "chemical_precipitation": [
        ("mixers", "submersible_mixer"),
        ("chemical_dosing", "pac_system"),
        ("chemical_dosing", "naoh_system"),
    ],
    "chemical_p_removal": [
        ("mixers", "submersible_mixer"),
        ("chemical_dosing", "pac_system"),
    ],
    "chromium_reduction": [
        ("mixers", "submersible_mixer"),
        ("chemical_dosing", "naoh_system"),
        ("chemical_dosing", "pac_system"),
    ],
    "cyanide_oxidation": [
        ("mixers", "submersible_mixer"),
        ("chemical_dosing", "naoh_system"),
        ("chemical_dosing", "disinfectant_system"),
    ],
    "daf": [  # 溶气气浮
        ("pumps", "clean_water"),
        ("mixers", "submersible_mixer"),
    ],
    "fenton": [
        ("chemical_dosing", "pac_system"),
        ("chemical_dosing", "naoh_system"),
        ("mixers", "submersible_mixer"),
    ],
    "neutralization": [
        ("mixers", "submersible_mixer"),
        ("chemical_dosing", "naoh_system"),
    ],
    "oil_separator": [
        ("pumps", "submersible_sewage"),
    ],
    "contact_oxidation": [
        ("blowers_aerators", "roots_blower"),
        ("blowers_aerators", "fine_bubble_diffuser"),
        ("pumps", "submersible_sewage"),
    ],
    "filter_press": [
        ("sludge_handling", "filter_press"),
        ("pumps", "submersible_sludge"),
    ],

    # 辅助通用设备（自动为每个工艺单元追加）
    "_instruments": [
        ("instruments", "flow_meter"),
        ("instruments", "ph_probe"),
        ("instruments", "do_probe"),
        ("instruments", "mlss_probe"),
    ],
    "_electrical": [
        ("instruments", "plc_cabinet"),
    ],
}


# 从计算结果中提取设备匹配所需参数
def _extract_design_params(calc_result: Dict) -> Dict[str, float]:
    """从 CalculationResult JSON 中提取关键设计参数。"""
    output = calc_result.get("output_parameters", {}) or {}
    params: Dict[str, float] = {}

    # 流量相关
    for key in ("flow_rate", "flow_rate_m3_d", "flow_rate_m3_h", "Q_avg", "Q_design", "q_design"):
        if key in output:
            v = output[key]
            params["flow_rate_m3_d"] = float(v) if "m3_d" in key or key in ("flow_rate", "Q_avg", "Q_design") else float(v) * 24
            break

    # 小时流量
    if "flow_rate_m3_h" not in params:
        daily = params.get("flow_rate_m3_d", 0)
        if daily > 0:
            params["flow_rate_m3_h"] = daily / 24

    # 空气流量
    for key in ("air_flow_rate", "air_flow", "air_flow_total", "Q_air", "air_flow_m3_h"):
        if key in output:
            params["air_flow_m3_h"] = float(output[key])
            break

    # 扬程
    for key in ("head_m", "head", "total_head", "pump_head"):
        if key in output:
            params["head_m"] = float(output[key])
            break
    if "head_m" not in params:
        params["head_m"] = 10.0  # default pump head

    # 池容
    for key in ("tank_volume", "total_volume", "effective_volume", "volume_total", "tank_volume_total"):
        if key in output:
            params["tank_volume_m3"] = float(output[key])
            break

    # 池径
    for key in ("tank_diameter", "diameter", "clarifier_diameter"):
        if key in output:
            params["tank_diameter_m"] = float(output[key])
            break

    # SOTR (kg O2/h)
    for key in ("sotr", "SOTR", "oxygen_transfer_rate", "aor"):
        if key in output:
            params["sotr_kg_h"] = float(output[key])
            break

    # 膜面积
    for key in ("membrane_area", "total_membrane_area"):
        if key in output:
            params["membrane_area_m2"] = float(output[key])
            break

    # 搅拌功率密度
    for key in ("mixing_power_density", "mixing_power_density_w_m3", "mixing_intensity"):
        if key in output:
            params["mixing_power_density_w_m3"] = float(output[key])
            break
    if "mixing_power_density_w_m3" not in params:
        params["mixing_power_density_w_m3"] = 5.0  # default W/m3

    # 加药量 (kg/h)
    for key in ("daily_consumption_kg", "dosage_rate_kg_d", "chemical_daily"):
        if key in output:
            params["dosage_rate_kg_h"] = float(output[key]) / 24
            break
    if "dosage_rate_kg_h" in output:
        params["dosage_rate_kg_h"] = float(output["dosage_rate_kg_h"])

    # 污泥产量 (t/d 湿泥)
    for key in ("sludge_production_wet_t_d", "sludge_wet_tons_day", "sludge_wet_t_d"):
        if key in output:
            params["sludge_wet_t_d"] = float(output[key])
            break

    # 管径
    for key in ("pipe_diameter", "pipe_dn", "diameter_mm"):
        if key in output:
            params["pipe_diameter_mm"] = float(output[key])
            break
    if "pipe_diameter_mm" not in params:
        daily_flow = params.get("flow_rate_m3_d", 10000)
        # rough estimate: DN = sqrt(Q_day * 4 / (pi * v * 86400)) * 1000
        vel = 1.5  # m/s
        area = daily_flow / (vel * 86400)
        dia_mm = (area * 4 / 3.1416) ** 0.5 * 1000
        params["pipe_diameter_mm"] = round(dia_mm / 50) * 50

    # 泵功率密度 (W/m3)
    for key in ("total_power", "power_kw", "total_power_kw"):
        if key in output:
            params["total_power_kw"] = float(output[key])
            break

    return params


class EquipmentSelector:
    """根据计算结果自动匹配设备型号的规则引擎。"""

    def __init__(self, kb: KnowledgeLoader):
        self.kb = kb

    def select(
        self,
        route_units: List[Dict],
        calculation_results: List[Dict],
        flow_rate: float,
    ) -> Dict[str, Any]:
        """主入口：返回设备清单和汇总。

        Args:
            route_units: RouteUnit 字典列表，含 unit_code, unit_name_zh
            calculation_results: CalculationResult 字典列表，含 calculator_code, output_parameters
            flow_rate: 设计流量 m3/d

        Returns:
            {equipment_list: [...], summary: {total_equipment_cost, by_category: {...}}}
        """
        calc_by_unit: Dict[str, Dict] = {}
        for cr in calculation_results:
            code = cr.get("calculator_code", "")
            calc_by_unit[code] = cr

        equipment_list: List[Dict] = []
        for unit in route_units:
            unit_code = unit.get("unit_code", "")
            unit_name = unit.get("unit_name_zh", unit_code)
            calc = calc_by_unit.get(unit_code, {})
            if not calc:
                continue

            design_params = _extract_design_params(calc)
            design_params["flow_rate_m3_d"] = design_params.get("flow_rate_m3_d", flow_rate)

            pairs = _UNIT_TO_EQUIPMENT.get(unit_code, [])
            for category, equipment_type in pairs:
                cfg = self.kb.get_equipment_type_config(category, equipment_type)
                if not cfg:
                    continue
                models = self._match_equipment(category, equipment_type, design_params)
                if not models:
                    continue
                best = models[0]
                qty = self._compute_quantity(cfg, best, design_params)
                total_price = qty * best.get("unit_price_cny", 0)

                equipment_list.append({
                    "category": category,
                    "process_unit_code": unit_code,
                    "equipment_type": equipment_type,
                    "model_id": best["model_id"],
                    "model_name_zh": best["name_zh"],
                    "quantity": qty,
                    "unit_price_cny": best["unit_price_cny"],
                    "total_price_cny": total_price,
                    "specs": {k: v for k, v in best.items() if k not in (
                        "model_id", "name_zh", "unit_price_cny", "manufacturer", "is_chinese"
                    )},
                    "manufacturer": best.get("manufacturer"),
                    "is_chinese": best.get("is_chinese", True),
                    "selection_rationale": f"根据{unit_name}设计参数自动匹配",
                })

        # ---- 自动追加仪表和电控（每个项目标配）----
        for aux_key in ("_instruments", "_electrical"):
            aux_pairs = _UNIT_TO_EQUIPMENT.get(aux_key, [])
            for category, equipment_type in aux_pairs:
                cfg = self.kb.get_equipment_type_config(category, equipment_type)
                if not cfg:
                    continue
                models = self._match_equipment(category, equipment_type, {"flow_rate_m3_d": flow_rate})
                if not models:
                    continue
                best = models[0]
                qty = 1
                total_price = qty * best.get("unit_price_cny", 0)
                equipment_list.append({
                    "category": category,
                    "process_unit_code": aux_key,
                    "equipment_type": equipment_type,
                    "model_id": best["model_id"],
                    "model_name_zh": best["name_zh"],
                    "quantity": qty,
                    "unit_price_cny": best["unit_price_cny"],
                    "total_price_cny": total_price,
                    "specs": {k: v for k, v in best.items() if k not in (
                        "model_id", "name_zh", "unit_price_cny", "manufacturer", "is_chinese"
                    )},
                    "manufacturer": best.get("manufacturer"),
                    "is_chinese": best.get("is_chinese", True),
                    "selection_rationale": "项目标配仪表及自控系统",
                })

        total = sum(e["total_price_cny"] for e in equipment_list)
        by_cat: Dict[str, float] = {}
        for e in equipment_list:
            cat = e["category"]
            by_cat[cat] = by_cat.get(cat, 0) + e["total_price_cny"]

        return {
            "equipment_list": equipment_list,
            "summary": {
                "total_equipment_cost": round(total, 2),
                "by_category": by_cat,
                "total_items": len(equipment_list),
            },
        }

    def _match_equipment(
        self, category: str, equipment_type: str, params: Dict[str, float]
    ) -> List[Dict]:
        """在指定类别中匹配设备型号，返回排序后的候选列表。"""
        cfg = self.kb.get_equipment_type_config(category, equipment_type)
        models = cfg.get("models", [])
        if not models:
            return []

        primary_param = cfg.get("primary_param", "")
        secondary_param = cfg.get("secondary_param", "")

        design_val = params.get(primary_param)
        if design_val is None:
            # try to find the param key in params directly
            design_val = params.get(primary_param.replace("_m3_d", "").replace("_m3_h", ""), 0)

        # Find range keys
        range_keys = self._find_range_keys(primary_param, models[0] if models else {})

        # Filter models whose design range contains the parameter value
        candidates = []
        for m in models:
            in_range = self._check_range(m, range_keys, design_val)
            if secondary_param:
                sec_val = params.get(secondary_param, 0)
                sec_range_keys = self._find_range_keys(secondary_param, m)
                in_range = in_range and self._check_range(m, sec_range_keys, sec_val)
            if in_range:
                candidates.append(m)

        if not candidates:
            # Return the closest model by range midpoint
            return self._find_closest(models, range_keys, design_val)

        # Score and sort
        priority = cfg.get("match_priority", ["in_range", "power_efficiency", "chinese_mfg", "low_price"])
        for m in candidates:
            score = 0
            if m.get("is_chinese", True):
                score += 10
            power = m.get("motor_power_kw", 0)
            if power > 0:
                score += 5  # prefer models with power data
            score -= m.get("unit_price_cny", 0) / 100000  # slight price bias
            m["_score"] = score

        candidates.sort(key=lambda m: m.get("_score", 0), reverse=True)
        return candidates

    def _check_range(self, model: Dict, range_keys: List[str], design_val: float) -> bool:
        """检查设计值是否在型号的设计范围内。"""
        if not range_keys:
            return True
        for rk in range_keys:
            range_vals = model.get(rk)
            if range_vals and len(range_vals) == 2:
                if range_vals[0] <= design_val <= range_vals[1]:
                    return True
        return False

    def _find_range_keys(self, param_name: str, model: Dict) -> List[str]:
        """在型号字典中找到包含 range 的键名。"""
        candidates = []
        for key in model:
            if "range" in key:
                # e.g. flow_range_m3_d matches flow_rate_m3_d
                base = param_name.replace("_rate_", "_").replace("_m3_d", "").replace("_m3_h", "")
                if base[:4] in key or key[:10] in base[:10] or param_name[:6].replace("_", "") in key[:6].replace("_", ""):
                    candidates.append(key)
        # fallback: any key with "range" that has a numeric list
        if not candidates:
            for key, val in model.items():
                if "range" in key and isinstance(val, list) and len(val) == 2:
                    candidates.append(key)
        return candidates

    def _find_closest(self, models: List[Dict], range_keys: List[str], design_val: float) -> List[Dict]:
        """当没有精确匹配时，找到最接近的型号。"""
        best_model = None
        best_distance = float("inf")
        for m in models:
            for rk in range_keys:
                range_vals = m.get(rk, [0, float("inf")])
                if len(range_vals) == 2:
                    mid = (range_vals[0] + range_vals[1]) / 2
                    dist = abs(design_val - mid)
                    if dist < best_distance:
                        best_distance = dist
                        best_model = m
        if best_model:
            best_model["_score"] = -100
            return [best_model]
        return [models[0]] if models else []

    def _compute_quantity(
        self, type_config: Dict, model: Dict, params: Dict[str, float]
    ) -> int:
        """计算所需数量（含冗余系数）。"""
        formula = type_config.get("sizing_formula", "")

        if "diffuser" in type_config.get("name_zh", "").lower() or "diffuser" in type_config.get("equipment_type", ""):
            air_flow = params.get("air_flow_m3_h", 0)
            cap = model.get("diffuser_capacity_m3_h", 2.5)
            if air_flow > 0:
                qty = max(1, int(air_flow / cap + 0.5))
            else:
                qty = 1
        elif "membrane" in type_config.get("equipment_type", ""):
            total_area = params.get("membrane_area_m2", 0)
            module_area = model.get("module_area_m2", 25)
            if total_area > 0 and module_area > 0:
                qty = max(1, int(total_area / module_area + 0.5))
            else:
                qty = 1
        elif "pump" in type_config.get("equipment_type", "").lower():
            redundancy = type_config.get("redundancy_factor", 1.5)
            qty = max(2, int(redundancy + 0.5))  # at least 2 for duty+standby
        elif formula and "tank_volume" in formula:
            vol = params.get("tank_volume_m3", 100)
            power_density = params.get("mixing_power_density_w_m3", 5)
            required_kw = vol * power_density / 1000
            unit_kw = model.get("motor_power_kw", 4)
            qty = max(1, int(required_kw / unit_kw + 0.5))
        else:
            redundancy = type_config.get("redundancy_factor", 1.0)
            qty = max(1, int(redundancy + 0.5))

        return qty
