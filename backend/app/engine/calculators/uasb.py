"""UASB厌氧反应器计算器。"""
from typing import List
from app.engine.calculators.base import BaseCalculator, CalculationInput, CalculationOutput
from app.engine.calculators.registry import CalculatorRegistry


class UASBCalculator(BaseCalculator):
    unit_code = "uasb"
    unit_name_zh = "UASB厌氧反应器"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "COD"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        dp = input.design_params

        cod_vol_loading = dp.get("cod_vol_loading", 5.0)  # kgCOD/m3-d
        upflow_v = dp.get("upflow_velocity", 0.5)          # m/h
        HRT = dp.get("hrt", 12)                            # h
        depth = dp.get("effective_depth", 6.0)
        cod_eff = dp.get("cod_removal_efficiency", 0.70)
        biogas_yield = dp.get("biogas_yield", 0.4)         # m3/kgCOD_removed

        COD_in = input.influent.get("COD", 0)
        COD_removed_daily = COD_in * cod_eff * Q / 1000    # kg/d

        # 按容积负荷
        V_load = COD_removed_daily / cod_vol_loading
        # 按HRT
        V_hrt = Q / 24 * HRT
        # 按上升流速
        Q_h = Q / 24
        area_v = Q_h / upflow_v
        V_v = area_v * depth

        V = max(V_load, V_hrt, V_v)
        area = V / depth

        # 实际值校核
        upflow_actual = Q_h / area
        HRT_actual = V / Q_h
        cod_load_actual = COD_removed_daily / V

        # 沼气产量
        biogas = COD_removed_daily * biogas_yield      # m3/d
        methane = biogas * 0.65                         # m3 CH4/d

        # 出水
        effluent = dict(input.influent)
        effluent["COD"] = COD_in * (1 - cod_eff)
        effluent["BOD5"] = input.influent.get("BOD5", 0) * (1 - cod_eff * 1.1)

        n_tanks = max(1, int(V / 1000) + 1)
        V_per_tank = V / n_tanks
        diameter = (V_per_tank / depth * 4 / 3.14159) ** 0.5

        warnings: List[str] = []
        self._check_param(warnings, "COD容积负荷(kgCOD/m3-d)", cod_load_actual, 3.0, 8.0, "COD容积负荷")
        self._check_param(warnings, "上升流速(m/h)", upflow_actual, 0.3, 0.8, "上升流速")
        self._check_param(warnings, "HRT(h)", HRT_actual, 8, 24, "HRT")

        if COD_in < 1000:
            warnings.append(f"进水COD={COD_in}mg/L偏低，UASB更适合COD>=1000mg/L的废水")

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "tank_volume_total": round(V, 1),
                "volume_per_tank": round(V_per_tank, 1),
                "num_tanks": n_tanks,
                "tank_diameter": round(diameter, 1),
                "effective_depth": depth,
                "surface_area": round(area, 1),
                "hrt_h": round(HRT_actual, 2),
                "upflow_velocity_m_h": round(upflow_actual, 2),
                "cod_vol_loading_design": cod_vol_loading,
                "cod_vol_loading_actual": round(cod_load_actual, 2),
                "cod_removal_efficiency": cod_eff,
                "cod_removed_kg_d": round(COD_removed_daily, 1),
                "biogas_m3_d": round(biogas, 1),
                "methane_m3_d": round(methane, 1),
            },
            effluent_quality=effluent,
            formulas={
                "volume": "V = max(COD_load/Nv, Q_h*HRT, Q_h/v_up * H)",
                "upflow": "v_up = Q_h / A",
                "biogas": "V_biogas = COD_removed * Y_biogas",
            },
            warnings=warnings,
            notes=["UASB可回收沼气用于能源利用", "出水需进一步好氧处理"],
        )


CalculatorRegistry.register(UASBCalculator)
