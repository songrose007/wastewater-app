"""调节池计算器。"""
from typing import List
from app.engine.calculators.base import BaseCalculator, CalculationInput, CalculationOutput
from app.engine.calculators.registry import CalculatorRegistry


class EqualizationTankCalculator(BaseCalculator):
    unit_code = "equalization_tank"
    unit_name_zh = "调节池"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        dp = input.design_params

        HRT = dp.get("hrt", 8)
        depth = dp.get("effective_depth", 5.0)

        Q_h = Q / 24
        V = Q_h * HRT
        area = V / depth

        n_tanks = max(1, int(area / 500) + 1)
        area_per_tank = area / n_tanks
        L_W = 2
        width = (area_per_tank / L_W) ** 0.5
        length = width * L_W

        # 潜水搅拌机功率
        mixing_power = V * 5 / 1000  # 5 W/m3
        n_mixers = max(2, int(V / 500) + 1)
        mixer_power_each = mixing_power / n_mixers

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "tank_volume": round(V, 1),
                "hrt_h": HRT,
                "effective_depth": depth,
                "surface_area": round(area, 1),
                "num_tanks": n_tanks,
                "tank_length": round(length, 1),
                "tank_width": round(width, 1),
                "mixing_power_kw": round(mixing_power, 1),
                "num_mixers": n_mixers,
                "mixer_power_each_kw": round(mixer_power_each, 1),
            },
            effluent_quality=input.influent,
            formulas={
                "volume": "V = Q_h * HRT",
                "mixing_power": "P = V * 5 W/m3",
            },
            warnings=[],
        )


CalculatorRegistry.register(EqualizationTankCalculator)
