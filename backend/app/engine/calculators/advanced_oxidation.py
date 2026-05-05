"""高级氧化计算器 (Fenton/类Fenton)。"""
from typing import List
from app.engine.calculators.base import BaseCalculator, CalculationInput, CalculationOutput
from app.engine.calculators.registry import CalculatorRegistry


class AdvancedOxidationCalculator(BaseCalculator):
    unit_code = "advanced_oxidation"
    unit_name_zh = "高级氧化"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "COD"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        dp = input.design_params

        h2o2_dose = dp.get("fenton_h2o2_dosage", 300)
        fe2_dose = dp.get("fenton_fe2_dosage", 200)
        HRT = dp.get("fenton_hrt", 2)
        ph = dp.get("fenton_ph", 3.5)
        cod_eff = dp.get("cod_removal_efficiency", 0.50)

        Q_h = Q / 24
        V = Q_h * HRT
        depth = 4.0
        area = V / depth

        n_trains = max(1, int(area / 200) + 1)
        area_per_train = area / n_trains

        L_W = 3
        width = (area_per_train / L_W) ** 0.5
        length = width * L_W

        h2o2_daily = h2o2_dose * Q / 1000
        fe2_daily = fe2_dose * Q / 1000

        COD_in = input.influent.get("COD", 0)
        COD_out = COD_in * (1 - cod_eff)

        BOD5_in = input.influent.get("BOD5", 0)
        BOD5_COD_in = BOD5_in / COD_in if COD_in > 0 else 0.3
        BOD5_COD_out = min(BOD5_COD_in * 1.5, 0.6)

        effluent = dict(input.influent)
        effluent["COD"] = COD_out
        effluent["BOD5"] = COD_out * BOD5_COD_out

        warnings: List[str] = []
        if ph < 3.0 or ph > 4.0:
            warnings.append(f"Fenton最佳pH=3.0~4.0，当前设计pH={ph}")
        self._check_param(warnings, "H2O2投加量(mg/L)", h2o2_dose, 100, 500, "H2O2")
        self._check_param(warnings, "Fe2+投加量(mg/L)", fe2_dose, 50, 400, "Fe2+")

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "tank_volume": round(V, 1),
                "hrt_h": HRT,
                "ph_operating": ph,
                "h2o2_dosage": h2o2_dose,
                "h2o2_daily_kg": round(h2o2_daily, 1),
                "fe2_dosage": fe2_dose,
                "fe2_daily_kg": round(fe2_daily, 1),
                "cod_removal_efficiency": cod_eff,
                "surface_area": round(area, 1),
                "num_trains": n_trains,
                "tank_length": round(length, 1),
                "tank_width": round(width, 1),
            },
            effluent_quality=effluent,
            chemical_consumption={"H2O2_30%": h2o2_daily, "FeSO4": fe2_daily},
            formulas={
                "volume": "V = Q_h * HRT",
                "cod_removal": "COD_out = COD_in * (1 - η)",
                "bod_improvement": "Fenton提高B/C比",
            },
            warnings=warnings,
        )


CalculatorRegistry.register(AdvancedOxidationCalculator)
