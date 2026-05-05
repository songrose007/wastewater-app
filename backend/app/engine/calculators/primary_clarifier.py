"""初沉池计算器（含常规和强化）。"""
from typing import List
from app.engine.calculators.base import BaseCalculator, CalculationInput, CalculationOutput
from app.engine.calculators.registry import CalculatorRegistry


class PrimaryClarifierCalculator(BaseCalculator):
    unit_code = "primary_clarifier"
    unit_name_zh = "初沉池"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "SS", "BOD5"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        Q_p = input.flow_rate_peak
        dp = input.design_params

        slr = dp.get("surface_loading_rate", 1.5)           # m3/m2-h
        hrt = dp.get("hrt", 2.0)                           # h
        depth = dp.get("effective_depth", 3.0)              # m
        ss_eff = dp.get("ss_removal_efficiency", 0.55)
        bod_eff = dp.get("bod_removal_efficiency", 0.30)
        sludge_moisture = dp.get("sludge_moisture", 0.97)

        # 平均流量表面积
        Q_h_avg = Q / 24
        area_avg = Q_h_avg / slr

        # 峰值流量校核
        Q_h_peak = Q_p / 24
        area_peak = Q_h_peak / (slr * 1.5)
        area = max(area_avg, area_peak) * 1.1             # 10% safety

        # HRT 校核
        volume = Q_h_avg * hrt
        volume_check = area * depth
        area = max(area, volume_check / depth)

        # 直径 (圆形辐流式)
        n_tanks = max(1, int(area / 400) + 1)             # 单池最大~400m2
        area_per_tank = area / n_tanks
        diameter = (area_per_tank * 4 / 3.14159) ** 0.5

        # 有效容积
        V_actual = area * depth
        hrt_actual = V_actual / Q_h_avg

        # 污泥产量
        SS_in = input.influent.get("SS", 0)
        SS_removed = SS_in * ss_eff * Q / 1000            # kg/d
        BOD_in = input.influent.get("BOD5", 0)
        BOD_removed = BOD_in * bod_eff * Q / 1000         # kg/d
        sludge_wet = SS_removed / (1 - sludge_moisture) / 1000  # m3/d

        # 出水水质
        effluent = dict(input.influent)
        effluent["SS"] = SS_in * (1 - ss_eff)
        effluent["BOD5"] = BOD_in * (1 - bod_eff)
        effluent["COD"] = input.influent.get("COD", 0) * (1 - bod_eff * 0.8)

        warnings: List[str] = []
        self._check_param(warnings, "表面负荷(m3/m2-h)", slr, 1.0, 2.0, "表面负荷")
        self._check_param(warnings, "HRT(h)", hrt_actual, 1.5, 2.5, "HRT")
        self._check_param(warnings, "有效水深(m)", depth, 2.5, 4.0, "有效水深")

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "num_tanks": n_tanks,
                "tank_diameter": round(diameter, 1),
                "area_per_tank": round(area_per_tank, 1),
                "total_area": round(area, 1),
                "effective_depth": depth,
                "effective_volume": round(V_actual, 1),
                "hrt_h": round(hrt_actual, 2),
                "surface_loading_rate_avg": round(Q_h_avg / area, 2),
                "surface_loading_rate_peak": round(Q_h_peak / area, 2),
                "ss_removal_efficiency": ss_eff,
                "bod_removal_efficiency": bod_eff,
                "sludge_dry_kg_d": round(SS_removed, 1),
                "sludge_wet_m3_d": round(sludge_wet, 2),
            },
            effluent_quality=effluent,
            sludge_production=SS_removed,
            formulas={
                "area": "A = Q_h / SLR",
                "hrt": "HRT = V / Q_h",
                "diameter": "D = sqrt(4A / π)",
                "sludge": "Sludge = SS_in * η * Q / (1 - moisture)",
            },
            warnings=warnings,
        )


class PrimaryEnhancedCalculator(BaseCalculator):
    unit_code = "primary_enhanced"
    unit_name_zh = "强化初沉池(化学混凝)"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "SS", "BOD5"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        Q_p = input.flow_rate_peak
        dp = input.design_params

        slr = dp.get("surface_loading_rate", 1.2)
        hrt = dp.get("hrt", 2.5)
        depth = dp.get("effective_depth", 3.5)
        pac_dose = dp.get("pac_dosage", 30)
        ss_eff = dp.get("ss_removal_efficiency", 0.75)
        bod_eff = dp.get("bod_removal_efficiency", 0.40)
        tp_eff = dp.get("tp_removal_efficiency", 0.70)

        Q_h_avg = Q / 24
        area = Q_h_avg / slr * 1.1
        Q_h_peak = Q_p / 24
        area = max(area, Q_h_peak / (slr * 1.5))

        V = area * depth
        hrt_actual = V / Q_h_avg
        n_tanks = max(1, int(area / 300) + 1)
        area_per_tank = area / n_tanks
        diameter = (area_per_tank * 4 / 3.14159) ** 0.5

        SS_in = input.influent.get("SS", 0)
        SS_removed = SS_in * ss_eff * Q / 1000
        BOD_in = input.influent.get("BOD5", 0)
        BOD_removed = BOD_in * bod_eff * Q / 1000
        TP_in = input.influent.get("TP", 0)
        TP_removed = TP_in * tp_eff * Q / 1000
        pac_daily = pac_dose * Q / 1000                          # kg/d (as Al2O3)

        sludge_wet = SS_removed / (1 - 0.97) / 1000

        effluent = dict(input.influent)
        effluent["SS"] = SS_in * (1 - ss_eff)
        effluent["BOD5"] = BOD_in * (1 - bod_eff)
        effluent["COD"] = input.influent.get("COD", 0) * (1 - bod_eff * 0.8)
        effluent["TP"] = TP_in * (1 - tp_eff)

        warnings: List[str] = []
        self._check_param(warnings, "表面负荷(m3/m2-h)", slr, 0.8, 1.5, "表面负荷")
        self._check_param(warnings, "PAC投加量(mg/L)", pac_dose, 15, 50, "PAC")

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
                "pac_dosage": pac_dose,
                "pac_daily_kg": round(pac_daily, 1),
                "ss_removal_efficiency": ss_eff,
                "bod_removal_efficiency": bod_eff,
                "tp_removal_efficiency": tp_eff,
                "sludge_dry_kg_d": round(SS_removed + TP_removed, 1),
                "sludge_wet_m3_d": round(sludge_wet, 2),
            },
            effluent_quality=effluent,
            sludge_production=SS_removed,
            chemical_consumption={"PAC": pac_daily},
            formulas={
                "area": "A = Q_h / SLR",
                "PAC_daily": "PAC_daily = dose * Q / 1000",
                "sludge": "考虑化学污泥增量",
            },
            warnings=warnings,
        )


for cls in [PrimaryClarifierCalculator, PrimaryEnhancedCalculator]:
    CalculatorRegistry.register(cls)
