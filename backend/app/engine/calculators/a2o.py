"""A2O工艺相关构筑物计算器：厌氧池、缺氧池。"""
from typing import List
from app.engine.calculators.base import BaseCalculator, CalculationInput, CalculationOutput
from app.engine.calculators.registry import CalculatorRegistry


class AnaerobicTankCalculator(BaseCalculator):
    unit_code = "anaerobic_tank"
    unit_name_zh = "厌氧池 (A2O)"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "TP", "BOD5"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        sludge_recycle = Q * input.design_params.get("sludge_recycle_ratio", 0.8)
        Q_total = Q + sludge_recycle
        dp = input.design_params

        HRT = dp.get("hrt", 1.5)
        depth = dp.get("effective_depth", 5.5)
        MLSS = dp.get("mlss", 3500)

        V = Q_total * HRT / 24
        area = V / depth

        n_trains = 2
        area_per_train = area / n_trains
        width = area_per_train ** 0.5 / 3
        length = area_per_train / width if width > 0 else 10

        TP_in = input.influent.get("TP", 0)
        TP_release = TP_in * 1.5

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
                "mlss": MLSS,
            },
            effluent_quality={
                "TP": TP_release,
            },
            formulas={
                "volume": "V = (Q + Q_recycle) * HRT / 24",
            },
            warnings=[],
        )


class AnoxicTankCalculator(BaseCalculator):
    unit_code = "anoxic_tank"
    unit_name_zh = "缺氧池 (A2O)"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "TN", "BOD5"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        dp = input.design_params

        HRT = dp.get("hrt", 3.0)
        depth = dp.get("effective_depth", 5.5)
        MLSS = dp.get("mlss", 3500)
        MLVSS_ratio = dp.get("mlvss_ratio", 0.7)
        MLVSS = MLSS * MLVSS_ratio
        denit_rate = dp.get("denitrification_rate", 0.04)
        internal_recycle = dp.get("internal_recycle_ratio", 2.5)
        sludge_recycle_ratio = dp.get("sludge_recycle_ratio", 0.8)

        Q_total = Q * (1 + internal_recycle + sludge_recycle_ratio)
        V = Q_total * HRT / 24

        TN_in = input.influent.get("TN", 0)
        TN_out = input.target_effluent.get("TN", 15)
        TN_to_remove = (TN_in - TN_out) * Q / 1000

        # 核算反硝化能力
        V_denit = TN_to_remove / (denit_rate * MLVSS / 1000)
        V = max(V, V_denit)
        HRT_actual = V / Q_total * 24

        area = V / depth
        n_trains = 2
        area_per_train = area / n_trains
        width = area_per_train ** 0.5 / 4
        length = area_per_train / width if width > 0 else 15

        warnings: List[str] = []
        self._check_param(warnings, "HRT(h)", HRT_actual, 2.0, 4.0, "HRT")
        if TN_to_remove <= 0:
            warnings.append("进水TN已达标，缺氧池可按最小HRT设计")

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "tank_volume": round(V, 1),
                "hrt_h": round(HRT_actual, 2),
                "effective_depth": depth,
                "surface_area": round(area, 1),
                "num_trains": n_trains,
                "tank_length": round(length, 1),
                "tank_width": round(width, 1),
                "mlss": MLSS,
                "internal_recycle_ratio": internal_recycle,
                "internal_recycle_flow": round(Q * internal_recycle, 0),
                "sludge_recycle_ratio": sludge_recycle_ratio,
                "denitrification_rate": denit_rate,
                "tn_removed_kg_d": round(TN_to_remove, 1),
            },
            effluent_quality={
                "TN": max(TN_out, input.influent.get("TN", 0) * 0.3),
                "NO3_N": max(TN_out * 0.7, 0),
            },
            formulas={
                "volume_HRT": "V = Q_total * HRT / 24",
                "volume_denit": "V = TN_to_remove / (r_denit * MLVSS / 1000)",
                "total_flow": "Q_total = Q * (1 + R_internal + R_sludge)",
            },
            warnings=warnings,
        )


for cls in [AnaerobicTankCalculator, AnoxicTankCalculator]:
    CalculatorRegistry.register(cls)
