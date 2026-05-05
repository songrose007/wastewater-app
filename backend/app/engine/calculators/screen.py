"""格栅计算器。"""
from typing import Dict, List
import math
from app.engine.calculators.base import BaseCalculator, CalculationInput, CalculationOutput
from app.engine.calculators.registry import CalculatorRegistry


class CoarseScreenCalculator(BaseCalculator):
    unit_code = "coarse_screen"
    unit_name_zh = "粗格栅"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate  # m3/d
        Q_s = Q / 86400      # m3/s
        dp = input.design_params

        bar_spacing = dp.get("bar_spacing", 20) / 1000    # mm -> m
        bar_width = dp.get("bar_width", 10) / 1000
        v_approach = dp.get("approach_velocity", 0.8)
        angle_deg = dp.get("installation_angle", 60)
        angle_rad = math.radians(angle_deg)

        n_bars = Q_s / (bar_spacing * v_approach * bar_spacing)  # approximation
        n_bars = max(3, int(n_bars * 2))  # ensure minimum

        # 栅槽宽度
        B = bar_spacing * (n_bars - 1) + bar_width * n_bars
        B = max(0.5, B)

        # 过栅水头损失
        beta = 2.42  # 矩形栅条
        h_loss = beta * (bar_width / bar_spacing) ** (4/3) * (v_approach ** 2) / (2 * 9.81) * math.sin(angle_rad)
        h_loss = round(h_loss * 1000, 1)  # mm

        # 栅后槽总高度
        h_upstream = 0.8
        h_total = h_upstream + h_loss / 1000 + 0.3  # 超高0.3m

        # 栅槽长度 (渐宽+渐缩)
        l1 = (B - 0.5) / (2 * math.tan(math.radians(20))) if B > 0.5 else 0.3
        l2 = l1 / 2
        l_total = l1 + l2 + 0.5 + 1.0 + h_total / math.tan(angle_rad)

        # 栅渣量 (每m3污水)
        slag_rate = 0.05 / 1000 if bar_spacing >= 0.02 else 0.1 / 1000  # m3/m3
        slag_daily = Q * slag_rate

        warnings: List[str] = []
        self._check_param(warnings, "过栅流速", v_approach, 0.6, 1.0, "过栅流速")
        self._check_param(warnings, "安装角度", angle_deg, 45, 75, "安装角度")
        self._check_param(warnings, "栅条间距(mm)", dp.get("bar_spacing", 20), 15, 40, "栅条间距")

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "channel_width": round(B, 2),
                "num_bars": n_bars,
                "head_loss_mm": h_loss,
                "total_height": round(h_total, 2),
                "total_length": round(l_total, 2),
                "slag_daily_m3": round(slag_daily, 3),
                "approach_velocity": v_approach,
            },
            effluent_quality=input.influent,
            formulas={
                "channel_width": "B = s*(n-1) + w*n",
                "head_loss": "h = β*(w/s)^(4/3) * v^2/(2g) * sin(α)",
            },
            warnings=warnings,
        )


class FineScreenCalculator(BaseCalculator):
    unit_code = "fine_screen"
    unit_name_zh = "细格栅"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        Q_s = Q / 86400
        dp = input.design_params

        bar_spacing = dp.get("bar_spacing", 5) / 1000
        bar_width = dp.get("bar_width", 6) / 1000
        v_approach = dp.get("approach_velocity", 0.8)
        angle_deg = dp.get("installation_angle", 60)
        angle_rad = math.radians(angle_deg)

        n_bars = max(5, int(Q_s / (bar_spacing * v_approach * 0.5) * 3))
        B = bar_spacing * (n_bars - 1) + bar_width * n_bars
        B = max(0.5, B)

        beta = 2.42
        h_loss = beta * (bar_width / bar_spacing) ** (4/3) * (v_approach ** 2) / (2 * 9.81) * math.sin(angle_rad)
        h_loss = round(h_loss * 1000, 1)

        h_total = 0.8 + h_loss / 1000 + 0.3
        l1 = (B - 0.5) / (2 * math.tan(math.radians(20))) if B > 0.5 else 0.3
        l2 = l1 / 2
        l_total = l1 + l2 + 0.5 + 1.0 + h_total / math.tan(angle_rad)

        slag_daily = Q * 0.1 / 1000

        warnings: List[str] = []
        self._check_param(warnings, "过栅流速", v_approach, 0.6, 1.0, "过栅流速")
        self._check_param(warnings, "栅条间距(mm)", dp.get("bar_spacing", 5), 3, 10, "栅条间距")

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "channel_width": round(B, 2),
                "num_bars": n_bars,
                "head_loss_mm": h_loss,
                "total_height": round(h_total, 2),
                "total_length": round(l_total, 2),
                "slag_daily_m3": round(slag_daily, 3),
            },
            effluent_quality=input.influent,
            formulas={
                "channel_width": "B = s*(n-1) + w*n",
                "head_loss": "h = β*(w/s)^(4/3) * v^2/(2g) * sin(α)",
            },
            warnings=warnings,
        )


class FineScreen1mmCalculator(BaseCalculator):
    unit_code = "fine_screen_1mm"
    unit_name_zh = "细格栅(1mm)"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        Q_s = Q / 86400
        dp = input.design_params

        bar_spacing = dp.get("bar_spacing", 1) / 1000
        bar_width = dp.get("bar_width", 3) / 1000
        v_approach = dp.get("approach_velocity", 0.6)
        angle_deg = dp.get("installation_angle", 60)
        angle_rad = math.radians(angle_deg)

        n_bars = max(10, int(Q_s / (bar_spacing * v_approach * 0.3) * 5))
        B = bar_spacing * (n_bars - 1) + bar_width * n_bars
        B = max(0.5, B)

        h_loss = 0.15  # m for fine screen
        h_total = 0.8 + h_loss + 0.3
        l_total = B * 1.5 + 2.0

        slag_daily = Q * 0.15 / 1000

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "channel_width": round(B, 2),
                "num_bars": n_bars,
                "head_loss_m": round(h_loss, 2),
                "total_height": round(h_total, 2),
                "total_length": round(l_total, 2),
                "slag_daily_m3": round(slag_daily, 3),
            },
            effluent_quality=input.influent,
            formulas={"channel_width": "B = s*(n-1) + w*n"},
            warnings=[],
        )


# 自注册
for cls in [CoarseScreenCalculator, FineScreenCalculator, FineScreen1mmCalculator]:
    CalculatorRegistry.register(cls)
