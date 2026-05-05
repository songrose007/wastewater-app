"""混凝反应池计算器（含普通混凝和脱色混凝）。"""
from typing import List
from app.engine.calculators.base import BaseCalculator, CalculationInput, CalculationOutput
from app.engine.calculators.registry import CalculatorRegistry


class CoagulationCalculator(BaseCalculator):
    unit_code = "coagulation_tank"
    unit_name_zh = "混凝反应池"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "SS", "COD"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        dp = input.design_params

        pac_dose = dp.get("pac_dosage", 30)
        pam_dose = dp.get("pam_dosage", 1.0)
        G_rapid = dp.get("rapid_mix_g", 500)
        t_rapid = dp.get("rapid_mix_t", 60)
        G_floc = dp.get("floc_g", 50)
        t_floc = dp.get("floc_t", 20)

        Q_h = Q / 24
        Q_s = Q / 86400

        # 快速混合池
        V_rapid = Q_s * t_rapid
        # 絮凝池
        V_floc = Q_h * t_floc / 60
        V_total = V_rapid + V_floc

        # 药剂
        pac_daily = pac_dose * Q / 1000
        pam_daily = pam_dose * Q / 1000

        # 混合搅拌功率
        P_rapid = G_rapid ** 2 * V_rapid * 1.0e-3 / 1000  # kW
        P_floc = G_floc ** 2 * V_floc * 1.0e-3 / 1000

        depth = 3.5
        area = V_total / depth

        warnings: List[str] = []
        self._check_param(warnings, "PAC(mg/L)", pac_dose, 10, 60, "PAC投加量")
        self._check_param(warnings, "快速混合G值(1/s)", G_rapid, 300, 800, "G值(快速)")
        self._check_param(warnings, "絮凝G值(1/s)", G_floc, 20, 70, "G值(絮凝)")

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "total_volume": round(V_total, 1),
                "rapid_mix_volume": round(V_rapid, 2),
                "floc_volume": round(V_floc, 1),
                "pac_dosage": pac_dose,
                "pac_daily_kg": round(pac_daily, 1),
                "pam_dosage": pam_dose,
                "pam_daily_kg": round(pam_daily, 1),
                "G_rapid": G_rapid,
                "G_floc": G_floc,
                "t_rapid_s": t_rapid,
                "t_floc_min": t_floc,
                "power_kw": round(P_rapid + P_floc, 2),
            },
            effluent_quality=input.influent,
            chemical_consumption={"PAC": pac_daily, "PAM": pam_daily},
            power_estimate=P_rapid + P_floc,
            formulas={
                "rapid_volume": "V = Q_s * t_rapid",
                "floc_volume": "V = Q_h * t_floc / 60",
                "power": "P = G^2 * V * μ",
            },
            warnings=warnings,
        )


class CoagulationDecolorizationCalculator(BaseCalculator):
    unit_code = "coagulation_decolorization"
    unit_name_zh = "混凝脱色池"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "color"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        dp = input.design_params

        pac_dose = dp.get("pac_dosage", 50)
        pam_dose = dp.get("pam_dosage", 2.0)
        color_removal = dp.get("color_removal", 0.70)

        pac_daily = pac_dose * Q / 1000
        pam_daily = pam_dose * Q / 1000

        Q_h = Q / 24
        t_rapid = 60
        t_floc = 20
        V_rapid = Q / 86400 * t_rapid
        V_floc = Q_h * t_floc / 60
        V_total = V_rapid + V_floc

        color_in = input.influent.get("color", 200)
        color_out = color_in * (1 - color_removal)

        effluent = dict(input.influent)
        effluent["color"] = color_out
        effluent["COD"] = input.influent.get("COD", 0) * 0.80
        effluent["SS"] = input.influent.get("SS", 0) * 0.50

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "total_volume": round(V_total, 1),
                "pac_dosage": pac_dose,
                "pac_daily_kg": round(pac_daily, 1),
                "pam_dosage": pam_dose,
                "pam_daily_kg": round(pam_daily, 1),
                "color_removal_efficiency": color_removal,
                "color_in_times": color_in,
                "color_out_times": round(color_out, 0),
            },
            effluent_quality=effluent,
            chemical_consumption={"PAC": pac_daily, "PAM": pam_daily},
            formulas={
                "color_removal": "Color_out = Color_in * (1 - η)",
                "pac": "PAC_daily = dose * Q / 1000",
            },
            warnings=[],
        )


for cls in [CoagulationCalculator, CoagulationDecolorizationCalculator]:
    CalculatorRegistry.register(cls)
