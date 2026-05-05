"""二沉池计算器。"""
from typing import List
from app.engine.calculators.base import BaseCalculator, CalculationInput, CalculationOutput
from app.engine.calculators.registry import CalculatorRegistry


class SecondaryClarifierCalculator(BaseCalculator):
    unit_code = "secondary_clarifier"
    unit_name_zh = "二沉池"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "SS"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        Q_p = input.flow_rate_peak
        dp = input.design_params

        slr_avg = dp.get("surface_loading_rate_avg", 0.8)
        slr_peak = dp.get("surface_loading_rate_peak", 1.5)
        sol_lr = dp.get("solid_loading_rate", 120)
        depth = dp.get("effective_depth", 3.5)
        hrt = dp.get("hrt", 3.0)
        weir_lr = dp.get("weir_loading_rate", 1.5)  # L/s-m

        Q_h_avg = Q / 24
        Q_h_peak = Q_p / 24

        area_avg = Q_h_avg / slr_avg
        area_peak = Q_h_peak / slr_peak

        MLSS_in = input.influent.get("MLSS", 3500)
        sludge_recycle = Q * dp.get("sludge_recycle_ratio", 0.8)
        Q_solid = Q + sludge_recycle
        solid_load = MLSS_in * Q_solid / 1000 / 24  # kg/h
        area_solid = solid_load / sol_lr

        area = max(area_avg, area_peak, area_solid) * 1.1

        n_tanks = max(1, int(area / 500) + 1)
        area_per_tank = area / n_tanks
        diameter = (area_per_tank * 4 / 3.14159) ** 0.5

        V = area * depth
        hrt_actual = V / (Q_solid / 24)

        weir_length_per_tank = 3.14159 * diameter * 0.85
        weir_load_actual = Q_h_peak / 3600 / (weir_length_per_tank * n_tanks) * 1000  # L/s-m

        effluent = dict(input.influent)
        effluent["SS"] = input.target_effluent.get("SS", 10)
        effluent["BOD5"] = input.influent.get("BOD5", 0) * 0.15

        warnings: List[str] = []
        self._check_param(warnings, "水力负荷-平均(m3/m2-h)", slr_avg, 0.6, 1.0, "水力负荷(平均)")
        self._check_param(warnings, "水力负荷-峰值(m3/m2-h)", Q_h_peak / area, 1.2, 2.0, "水力负荷(峰值)")
        self._check_param(warnings, "固体负荷(kg/m2-h)", solid_load / area, 3.0, 6.0, "固体负荷")
        self._check_param(warnings, "堰负荷(L/s-m)", weir_load_actual, 1.0, 2.0, "堰负荷")
        self._check_param(warnings, "有效水深(m)", depth, 3.0, 4.5, "有效水深")

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "num_tanks": n_tanks,
                "tank_diameter": round(diameter, 1),
                "area_per_tank": round(area_per_tank, 1),
                "total_area": round(area, 1),
                "effective_depth": depth,
                "effective_volume": round(V, 1),
                "hrt_h": round(hrt_actual, 2),
                "surface_loading_avg": round(Q_h_avg / area, 2),
                "surface_loading_peak": round(Q_h_peak / area, 2),
                "solid_loading": round(solid_load / area, 2),
                "weir_loading": round(weir_load_actual, 2),
            },
            effluent_quality=effluent,
            formulas={
                "area": "A = max(Q/slr_avg, Q_peak/slr_peak, M/sol_lr)",
                "diameter": "D = sqrt(4A/π/n)",
                "weir_load": "WL = Q_peak / (3600 * L_weir)",
            },
            warnings=warnings,
        )


CalculatorRegistry.register(SecondaryClarifierCalculator)
