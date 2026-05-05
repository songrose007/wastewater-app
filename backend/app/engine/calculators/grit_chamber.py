"""沉砂池计算器。"""
from typing import List
import math
from app.engine.calculators.base import BaseCalculator, CalculationInput, CalculationOutput
from app.engine.calculators.registry import CalculatorRegistry


class GritChamberCalculator(BaseCalculator):
    unit_code = "grit_chamber"
    unit_name_zh = "沉砂池"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate       # m3/d
        Q_p = input.flow_rate_peak  # m3/d
        Q_h = Q / 24              # m3/h
        dp = input.design_params

        slr = dp.get("surface_loading_rate", 180)     # m3/m2-d
        hrt = dp.get("hrt", 30)                      # s
        v_h = dp.get("horizontal_velocity", 0.3)      # m/s
        depth = dp.get("effective_depth", 2.0)        # m

        # 表面积
        area = Q / slr                                 # m2
        # 按峰值流量校核水平流速
        area_check = Q_p / 86400 / v_h / depth
        area = max(area, area_check)

        # 停留时间校核
        hrt_actual = area * depth / (Q_p / 86400)      # s

        # 尺寸
        width = max(1.0, area ** 0.5 / 2)             # 分 2 格
        length = area / (2 * width)
        l_w_ratio = length / width

        # 沉砂量
        sand_rate = 0.03 / 1000                       # m3 沉砂 / m3 污水
        sand_daily = Q * sand_rate

        warnings: List[str] = []
        self._check_param(warnings, "表面负荷(m3/m2-d)", slr, 150, 200, "表面负荷")
        self._check_param(warnings, "停留时间(s)", hrt_actual, 20, 60, "停留时间(校核)")
        self._check_param(warnings, "水平流速(m/s)", Q_p / 86400 / (width * 2 * depth), 0.25, 0.35, "水平流速(校核)")
        if l_w_ratio < 3 or l_w_ratio > 8:
            warnings.append(f"长宽比={l_w_ratio:.1f}，建议在3~8之间")

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "total_area": round(area, 2),
                "num_channels": 2,
                "channel_width": round(width, 2),
                "channel_length": round(length, 2),
                "l_w_ratio": round(l_w_ratio, 1),
                "effective_depth": depth,
                "hrt_design_s": hrt,
                "hrt_actual_s": round(hrt_actual, 1),
                "surface_loading_rate": slr,
                "sand_daily_m3": round(sand_daily, 3),
            },
            effluent_quality={
                "SS": input.influent.get("SS", 0) * 0.95,
                "COD": input.influent.get("COD", 0) * 0.95,
                "BOD5": input.influent.get("BOD5", 0) * 0.95,
            },
            formulas={
                "area": "A = Q / SLR",
                "hrt": "HRT = V / Q_peak",
                "horizontal_velocity": "v = Q_peak / (n * B * H)",
            },
            warnings=warnings,
        )


CalculatorRegistry.register(GritChamberCalculator)
