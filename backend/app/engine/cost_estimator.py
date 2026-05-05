"""造价估算引擎 — CAPEX + OPEX 完整计算。"""
from typing import Dict, List, Any, Tuple
from app.knowledge.loader import KnowledgeLoader


class CostEstimator:
    """污水处理项目投资估算和运行成本计算引擎。

    CAPEX = 土建费 + 设备费 + 安装费 + 设计费 + 不可预见费
    OPEX = 电费 + 药剂费 + 人工费 + 维护费 + 污泥处置费 + 折旧
    吨水成本 = (折旧 + 年运营费) / (Q × 365)
    """

    def __init__(self, kb: KnowledgeLoader):
        self.kb = kb

    def estimate(
        self,
        flow_rate: float,             # m3/d
        calculation_results: List[Dict],
        equipment_list: List[Dict],
    ) -> Dict[str, Any]:
        """主入口：返回完整的造价估算。

        Returns:
            {capex: {...}, opex: {...}, total_capex, total_annual_opex, cost_per_m3, assumptions: {...}}
        """
        cf = self.kb.cost_factors
        capex_factors = cf.get("capex", {})
        opex_factors = cf.get("opex", {})

        # CAPEX
        civil_cost, civil_breakdown = self._calc_civil_cost(calculation_results, capex_factors)
        equipment_cost = self._calc_equipment_cost(equipment_list)
        installation_cost, install_breakdown = self._calc_installation(equipment_cost, capex_factors)
        engineering_cost = round(
            (civil_cost + equipment_cost + installation_cost)
            * capex_factors.get("engineering", {}).get("ratio_of_direct_cost", 0.08),
            2,
        )
        subtotal = civil_cost + equipment_cost + installation_cost + engineering_cost
        contingency_cost = round(
            subtotal * capex_factors.get("contingency", {}).get("ratio_of_subtotal", 0.10),
            2,
        )
        total_capex = round(subtotal + contingency_cost, 2)

        # OPEX
        energy_cost = self._calc_opex_energy(calculation_results, equipment_list, opex_factors)
        chemical_cost, chemical_breakdown = self._calc_opex_chemical(calculation_results, opex_factors)
        labor_cost = self._calc_opex_labor(opex_factors)
        maintenance_cost = round(
            equipment_cost * opex_factors.get("maintenance", {}).get("rate_of_equipment_cost", 0.025),
            2,
        )
        sludge_cost = self._calc_opex_sludge(calculation_results, opex_factors)

        # 折旧
        civil_life = opex_factors.get("depreciation", {}).get("civil_design_life_years", 30)
        equip_life = opex_factors.get("depreciation", {}).get("equipment_design_life_years", 15)
        depreciation_cost = round(civil_cost / civil_life + equipment_cost / equip_life, 2)

        total_opex = round(
            energy_cost + chemical_cost + labor_cost + maintenance_cost + sludge_cost + depreciation_cost,
            2,
        )

        # 吨水成本
        annual_volume = flow_rate * 365
        cost_per_m3 = round((depreciation_cost + total_opex - depreciation_cost) * 10000 / annual_volume, 2) if annual_volume > 0 else 0
        # Correct formula: cost_per_m3 = (total_annual_opex * 10000) / (Q * 365)
        cost_per_m3_correct = round(total_opex * 10000 / annual_volume, 2) if annual_volume > 0 else 0

        return {
            "capex": {
                "civil_cost": civil_cost,
                "civil_breakdown": civil_breakdown,
                "equipment_cost": equipment_cost,
                "installation_cost": installation_cost,
                "install_breakdown": install_breakdown,
                "engineering_cost": engineering_cost,
                "contingency_cost": contingency_cost,
                "total_capex": total_capex,
            },
            "opex": {
                "energy_cost": energy_cost,
                "chemical_cost": chemical_cost,
                "chemical_breakdown": chemical_breakdown,
                "labor_cost": labor_cost,
                "maintenance_cost": maintenance_cost,
                "sludge_disposal_cost": sludge_cost,
                "depreciation_cost": depreciation_cost,
                "total_annual_opex": total_opex,
            },
            "total_capex": total_capex,
            "total_annual_opex": total_opex,
            "cost_per_m3": cost_per_m3_correct,
            "assumptions": {
                "design_flow_rate_m3_d": flow_rate,
                "annual_treatment_volume_m3": annual_volume,
                "electricity_price_cny_per_kwh": opex_factors.get("energy", {}).get("electricity_price_cny_per_kwh", 0.80),
                "operating_hours_per_year": opex_factors.get("energy", {}).get("operating_hours_per_year", 8760),
                "civil_life_years": civil_life,
                "equipment_life_years": equip_life,
            },
        }

    def _calc_civil_cost(self, calc_results: List[Dict], factors: Dict) -> Tuple[float, Dict]:
        """计算土建费用：各池容 × 单价系数 × 深度系数。"""
        unit_costs = factors.get("civil", {}).get("unit_costs_cny_per_m3", {})
        default_cost = unit_costs.get("default", 800)
        depth_threshold = factors.get("civil", {}).get("excavation_depth_factor", {}).get("threshold_depth_m", 5.0)
        depth_factor_per_m = factors.get("civil", {}).get("excavation_depth_factor", {}).get("factor_per_m", 0.05)

        total = 0.0
        breakdown: Dict[str, Dict[str, float]] = {}

        for cr in calc_results:
            unit_code = cr.get("calculator_code", "")
            output = cr.get("output_parameters", {}) or {}

            # 提取池容
            volume = 0
            for vk in ("tank_volume", "total_volume", "effective_volume", "volume_total", "tank_volume_total"):
                if vk in output:
                    volume = float(output[vk])
                    break
            if volume <= 0:
                continue

            # 提取池深
            depth = 0
            for dk in ("water_depth", "effective_depth", "tank_depth", "depth", "side_water_depth"):
                if dk in output:
                    depth = float(output[dk])
                    break

            unit_price = unit_costs.get(unit_code, default_cost)

            # 深基坑加价
            if depth > depth_threshold:
                extra = (depth - depth_threshold) * depth_factor_per_m
                unit_price = unit_price * (1 + extra)

            cost = round(volume * unit_price / 10000, 2)  # 转换为万元
            total += cost
            breakdown[unit_code] = {
                "volume_m3": round(volume, 2),
                "unit_cost_cny_per_m3": unit_price,
                "depth_m": depth,
                "total_cost_wan_cny": cost,
            }

        return round(total, 2), breakdown

    def _calc_equipment_cost(self, equipment_list: List[Dict]) -> float:
        """设备购置费 = 所有设备总价之和（转万元）。"""
        total = sum(
            e.get("total_price_cny", e.get("unit_price_cny", 0) * e.get("quantity", 1))
            for e in equipment_list
        )
        return round(total / 10000, 2)  # 转换为万元

    def _calc_installation(self, equipment_cost: float, factors: Dict) -> Tuple[float, Dict]:
        """安装费 = 设备费 × (管道% + 电气% + 自控%)。"""
        install = factors.get("installation", {})
        piping = equipment_cost * install.get("piping", 0.30)
        electrical = equipment_cost * install.get("electrical", 0.15)
        automation = equipment_cost * install.get("automation", 0.10)
        total = round(piping + electrical + automation, 2)
        return total, {
            "piping": round(piping, 2),
            "electrical": round(electrical, 2),
            "automation": round(automation, 2),
        }

    def _calc_opex_energy(
        self, calc_results: List[Dict], equipment_list: List[Dict], factors: Dict
    ) -> float:
        """电费 = 总功率(kW) × 电价 × 年运行小时 / 10000 (万元)。"""
        energy_factors = factors.get("energy", {})
        price = energy_factors.get("electricity_price_cny_per_kwh", 0.80)
        hours = energy_factors.get("operating_hours_per_year", 8760)

        total_power = 0.0
        for cr in calc_results:
            output = cr.get("output_parameters", {}) or {}
            for pk in ("total_power", "total_power_kw", "power_kw", "motor_power_kw"):
                if pk in output:
                    total_power += float(output[pk])
                    break

        # Also sum equipment motor powers
        for eq in equipment_list:
            specs = eq.get("specs", {})
            motor_kw = specs.get("motor_power_kw", 0)
            if motor_kw:
                total_power += motor_kw * eq.get("quantity", 1) * 0.7  # 70% load factor

        annual_cost = total_power * price * hours
        return round(annual_cost / 10000, 2)  # 万元

    def _calc_opex_chemical(
        self, calc_results: List[Dict], factors: Dict
    ) -> Tuple[float, Dict]:
        """药剂费 = 日消耗量(kg/d) × 单价(元/kg) × 365 / 10000 (万元)。"""
        chem_factors = factors.get("chemical", {})
        unit_prices = chem_factors.get("unit_prices_cny_per_kg", {})

        total = 0.0
        breakdown: Dict[str, Dict[str, float]] = {}

        for cr in calc_results:
            output = cr.get("output_parameters", {}) or {}

            # 查找药剂消耗
            chem_consumption = output.get("chemical_consumption", output.get("chemical_daily", output.get("dosage", {})))
            if isinstance(chem_consumption, dict):
                for chem_name, daily_kg in chem_consumption.items():
                    chem_name_upper = chem_name.upper()
                    # Map to known chemical keys
                    matched_key = None
                    for known in unit_prices:
                        if known.upper() in chem_name_upper or chem_name_upper in known.upper():
                            matched_key = known
                            break
                    if not matched_key:
                        continue
                    price = unit_prices.get(matched_key, 0)
                    daily_val = float(daily_kg) if not isinstance(daily_kg, (int, float)) else daily_kg
                    annual_val = daily_val * 365 * price / 10000
                    total += annual_val
                    breakdown[chem_name] = {
                        "daily_kg": round(daily_val, 2),
                        "unit_price_cny_per_kg": price,
                        "annual_cost_wan_cny": round(annual_val, 2),
                    }

        return round(total, 2), breakdown

    def _calc_opex_labor(self, factors: Dict) -> float:
        """人工费 = 操作员数 × 年工资 / 10000 (万元)。"""
        labor_factors = factors.get("labor", {})
        operators = labor_factors.get("operators_per_shift", 2)
        shifts = labor_factors.get("shifts_per_day", 3)
        salary = labor_factors.get("annual_salary_cny", 80000)
        return round(operators * shifts * salary / 10000, 2)

    def _calc_opex_sludge(self, calc_results: List[Dict], factors: Dict) -> float:
        """污泥处置费 = 日产泥量(t/d) × 处置费(元/t) × 365 / 10000 (万元)。"""
        sludge_factors = factors.get("sludge_disposal", {})
        disposal_cost = sludge_factors.get("disposal_cost_cny_per_ton", 250)

        daily_sludge = 0.0
        for cr in calc_results:
            output = cr.get("output_parameters", {}) or {}
            for sk in ("sludge_production_wet_t_d", "sludge_wet_tons_day", "sludge_wet_t_d", "sludge_production_t_d"):
                if sk in output:
                    daily_sludge += float(output[sk])
                    break

        return round(daily_sludge * disposal_cost * 365 / 10000, 2)
