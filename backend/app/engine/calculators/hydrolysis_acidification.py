"""水解酸化池计算器。"""
from typing import List
from app.engine.calculators.base import BaseCalculator, CalculationInput, CalculationOutput
from app.engine.calculators.registry import CalculatorRegistry


class HydrolysisAcidificationCalculator(BaseCalculator):
    unit_code = "hydrolysis_acidification"
    unit_name_zh = "水解酸化池"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "COD", "BOD5"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        dp = input.design_params

        HRT = dp.get("hrt", 6)
        depth = dp.get("effective_depth", 6.0)
        bod_increase = dp.get("bod5_cod_increase", 0.15)

        Q_h = Q / 24
        V = Q_h * HRT
        area = V / depth

        n_trains = max(1, int(area / 500) + 1)
        area_per_train = area / n_trains
        L_W = 2
        width = (area_per_train / L_W) ** 0.5
        length = width * L_W

        # 上升流速
        upflow_velocity = Q_h / area

        COD_in = input.influent.get("COD", 0)
        BOD5_in = input.influent.get("BOD5", 0)
        COD_removal = COD_in * 0.15
        BOD5_increase = COD_in * bod_increase

        effluent = dict(input.influent)
        effluent["COD"] = COD_in * 0.85
        effluent["BOD5"] = min(BOD5_in * 0.95 + BOD5_increase, COD_in * 0.85 * 0.5)
        effluent["BOD5_COD"] = effluent["BOD5"] / effluent["COD"] if effluent["COD"] > 0 else 0.4

        warnings: List[str] = []
        self._check_param(warnings, "HRT(h)", HRT, 4, 10, "HRT")
        self._check_param(warnings, "上升流速(m/h)", upflow_velocity, 0.5, 1.5, "上升流速")

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "tank_volume": round(V, 1),
                "hrt_h": HRT,
                "effective_depth": depth,
                "surface_area": round(area, 1),
                "num_trains": n_trains,
                "tank_length": round(length, 1),
                "tank_width": round(width, 1),
                "upflow_velocity_m_h": round(upflow_velocity, 2),
                "cod_removal_ratio": 0.15,
                "bod5_cod_increase": bod_increase,
            },
            effluent_quality=effluent,
            formulas={
                "volume": "V = Q_h * HRT",
                "upflow": "v_up = Q_h / A",
            },
            warnings=warnings,
            notes=["水解酸化可提高B/C比0.10~0.20，改善可生化性"],
        )


class ContactOxidationCalculator(BaseCalculator):
    unit_code = "contact_oxidation"
    unit_name_zh = "接触氧化池"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "BOD5", "COD"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        dp = input.design_params

        bod_vol_loading = dp.get("bod_vol_loading", 1.0)
        HRT_check = dp.get("hrt", 6)
        depth = dp.get("effective_depth", 4.5)
        O2_util = dp.get("oxygen_utilization", 0.15)

        BOD_in = input.influent.get("BOD5", 0)
        BOD_out = input.target_effluent.get("BOD5", 20)
        BOD_removed = (BOD_in - BOD_out) * Q / 1000

        # 按容积负荷
        V_load = BOD_removed / bod_vol_loading
        # 按HRT
        V_hrt = Q / 24 * HRT_check
        V = max(V_load, V_hrt)
        HRT_actual = V / Q * 24

        area = V / depth
        COD_removed = BOD_removed * 1.5

        # 曝气量
        O2_needed = BOD_removed * 1.2
        air_flow = O2_needed / (0.28 * O2_util * 24)

        warnings: List[str] = []
        self._check_param(warnings, "BOD容积负荷(kgBOD/m3-d)", bod_vol_loading, 0.5, 1.5, "容积负荷")
        self._check_param(warnings, "HRT(h)", HRT_actual, 4, 8, "HRT")

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "tank_volume": round(V, 1),
                "hrt_h": round(HRT_actual, 2),
                "bod_vol_loading": round(bod_vol_loading, 2),
                "effective_depth": depth,
                "surface_area": round(area, 1),
                "oxygen_demand_kg_d": round(O2_needed, 1),
                "air_flow_rate_m3_h": round(air_flow, 0),
            },
            effluent_quality={
                "BOD5": BOD_out,
                "COD": input.influent.get("COD", 0) * 0.30,
            },
            power_estimate=round(air_flow * 0.005, 1),
            formulas={
                "volume": "V = BOD_load / Nv",
                "air_flow": "Q_air = O2_demand / (0.28 * O2_util * 24)",
            },
            warnings=warnings,
        )


for cls in [HydrolysisAcidificationCalculator, ContactOxidationCalculator]:
    CalculatorRegistry.register(cls)
