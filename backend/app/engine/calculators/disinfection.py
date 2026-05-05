"""消毒池计算器。"""
from typing import List
from app.engine.calculators.base import BaseCalculator, CalculationInput, CalculationOutput
from app.engine.calculators.registry import CalculatorRegistry


class DisinfectionCalculator(BaseCalculator):
    unit_code = "disinfection"
    unit_name_zh = "消毒池"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        Q_p = input.flow_rate_peak
        dp = input.design_params

        hrt = dp.get("hrt", 30)                          # min
        uv_dosage = dp.get("uv_dosage", 20)              # mJ/cm2
        cl_dose = dp.get("chlorine_dosage", 8)           # mg/L
        depth = dp.get("effective_depth", 3.0)

        Q_h_peak = Q_p / 24                               # m3/h
        V = Q_h_peak * hrt / 60                           # m3
        area = V / depth

        # 廊道设计
        n_channels = max(1, int(area ** 0.5 / 3) + 1)
        channel_width = 3.0                               # 标准廊宽
        length = area / (n_channels * channel_width)

        # 折流设计，实际总长
        L_total = length

        # 氯投加量
        cl_daily = cl_dose * Q / 1000                     # kg/d

        # UV 功率估算
        uv_power = Q_h_peak * uv_dosage / 3600 * 0.06     # kW (rough)

        warnings: List[str] = []
        self._check_param(warnings, "HRT(min)", hrt, 20, 45, "HRT")
        self._check_param(warnings, "UV剂量(mJ/cm2)", uv_dosage if uv_power > 0 else 20, 15, 30, "UV剂量")

        if Q > 50000 and uv_power > 0:
            warnings.append("大规模污水处理厂建议采用次氯酸钠消毒替代UV，降低运行成本")

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "tank_volume": round(V, 1),
                "hrt_min": hrt,
                "num_channels": n_channels,
                "channel_width": channel_width,
                "tank_length": round(L_total, 1),
                "effective_depth": depth,
                "surface_area": round(area, 1),
                "chlorine_dosage": cl_dose,
                "chlorine_daily_kg": round(cl_daily, 1),
                "uv_dosage": uv_dosage,
                "uv_power_kw": round(uv_power, 2),
            },
            effluent_quality={
                "fecal_coliform": input.target_effluent.get("fecal_coliform", 1000),
            },
            chemical_consumption={"NaClO": cl_daily},
            power_estimate=uv_power,
            formulas={
                "volume": "V = Q_peak * HRT / 60",
                "chlorine": "Cl_daily = dose * Q / 1000",
            },
            warnings=warnings,
        )


CalculatorRegistry.register(DisinfectionCalculator)
