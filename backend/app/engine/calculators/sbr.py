"""SBR反应池计算器。"""
from typing import List
from app.engine.calculators.base import BaseCalculator, CalculationInput, CalculationOutput
from app.engine.calculators.registry import CalculatorRegistry


class SBRCalculator(BaseCalculator):
    unit_code = "sbr_reactor"
    unit_name_zh = "SBR反应池"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "BOD5", "NH3_N", "TN", "TP"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        T = input.design_temp
        dp = input.design_params

        MLSS = dp.get("mlss", 3500)
        MLVSS_ratio = dp.get("mlvss_ratio", 0.7)
        MLVSS = MLSS * MLVSS_ratio
        cycle_time = dp.get("cycle_time", 6)            # h
        fill_ratio = dp.get("fill_ratio", 0.3)
        cycles_per_day = dp.get("cycles_per_day", 4)
        decant_depth = dp.get("decant_depth", 1.5)
        depth = dp.get("effective_depth", 5.0)

        Y = dp.get("sludge_yield", 0.6)
        Kd = dp.get("endogenous_decay", 0.05)
        SRT = dp.get("srt", 20)

        BOD_in = input.influent.get("BOD5", 0)
        BOD_out = input.target_effluent.get("BOD5", 10)

        Q_per_cycle = Q / cycles_per_day                     # m3/cycle
        V_fill_min = Q_per_cycle / fill_ratio                # 最小容积
        BOD_removed = (BOD_in - BOD_out) * Q / 1000          # kg/d

        F_M = dp.get("f_m_ratio", 0.10)
        # 按设计负荷
        V_bod = BOD_removed * 1000 / (F_M * MLVSS)
        V_design = max(V_fill_min, V_bod)

        HRT_total = V_design / Q * 24
        HRT_effective = HRT_total * fill_ratio

        # 污泥产量
        Y_obs = Y / (1 + Kd * SRT)
        Px_vss = Y_obs * BOD_removed
        Px_tss = Px_vss / 0.8

        # 需氧量
        O2_bod = 1.47 * BOD_removed
        NH3_in = input.influent.get("NH3_N", 0)
        NH3_out = input.target_effluent.get("NH3_N", 5)
        N_oxidized = max(0, NH3_in - NH3_out - BOD_removed * 0.05) * Q / 1000
        if N_oxidized < 0:
            N_oxidized = max(0, NH3_in - NH3_out) * Q / 1000
        O2_nit = 4.57 * N_oxidized
        O2_total = (O2_bod + O2_nit) * 1.3 * 1.2

        OTE = dp.get("oxygen_transfer_efficiency", 0.20)
        submergence = dp.get("diffuser_submergence", 4.5)
        Cs_20 = 9.08
        Cs_T = Cs_20 / (1 + 0.02 * (T - 20))
        Csm = Cs_T * (1 + submergence / 20.6)
        alpha, beta, C_do = 0.85, 0.95, 2.0
        SOTR = O2_total * Cs_20 / (24 * alpha * (beta * Csm - C_do) * 1.024 ** (T - 20))
        air_flow = SOTR / (0.28 * OTE)

        n_trains = max(2, int(V_design / 2000) + 1)
        V_per_train = V_design / n_trains
        area_per_train = V_per_train / depth
        width = (area_per_train / 3) ** 0.5
        length = area_per_train / width if width > 0 else 20

        warnings: List[str] = []
        self._check_param(warnings, "HRT-总(h)", HRT_total, 12, 30, "HRT(总)")
        self._check_param(warnings, "充水比", fill_ratio, 0.2, 0.4, "充水比")
        self._check_param(warnings, "MLSS(mg/L)", MLSS, 2500, 4500, "MLSS")

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "tank_volume_total": round(V_design, 1),
                "volume_per_train": round(V_per_train, 1),
                "num_trains": n_trains,
                "hrt_total_h": round(HRT_total, 2),
                "hrt_effective_h": round(HRT_effective, 2),
                "cycle_time_h": cycle_time,
                "cycles_per_day": cycles_per_day,
                "fill_ratio": fill_ratio,
                "decant_depth": decant_depth,
                "mlss": MLSS,
                "effective_depth": depth,
                "tank_length": round(length, 1),
                "tank_width": round(width, 1),
                "sludge_production_tss_kg_d": round(Px_tss, 1),
                "oxygen_demand_kg_d": round(O2_total, 1),
                "air_flow_rate_m3_h": round(air_flow, 0),
            },
            effluent_quality={
                "BOD5": BOD_out,
                "NH3_N": max(NH3_out, input.target_effluent.get("NH3_N", 5)),
            },
            sludge_production=Px_tss,
            power_estimate=round(air_flow * 0.006, 1),
            formulas={
                "volume": "V = max(Q_cycle/fill_ratio, BOD_load/(F/M*MLVSS))",
                "HRT": "HRT_total = V/Q*24; HRT_eff = HRT_total * fill_ratio",
                "oxygen": "O2 = 1.47*BOD_removed + 4.57*N_oxidized",
            },
            warnings=warnings,
        )


CalculatorRegistry.register(SBRCalculator)
