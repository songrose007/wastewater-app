"""曝气池（活性污泥法）计算器。"""
from typing import List
from app.engine.calculators.base import BaseCalculator, CalculationInput, CalculationOutput
from app.engine.calculators.registry import CalculatorRegistry


class ActivatedSludgeCalculator(BaseCalculator):
    unit_code = "aeration_tank"
    unit_name_zh = "曝气池（活性污泥法）"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "BOD5", "NH3_N", "TN"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        Q_p = input.flow_rate_peak
        T = input.design_temp
        dp = input.design_params

        MLSS = dp.get("mlss", 3000)
        MLVSS_ratio = dp.get("mlvss_ratio", 0.7)
        MLVSS = MLSS * MLVSS_ratio
        F_M = dp.get("f_m_ratio", 0.15)
        SRT = dp.get("srt", 15)
        Y = dp.get("sludge_yield", 0.6)
        Kd = dp.get("endogenous_decay", 0.05)
        depth = dp.get("effective_depth", 5.5)
        n_trains = dp.get("n_trains", 2)

        BOD_in = input.influent.get("BOD5", 0)
        BOD_out = input.target_effluent.get("BOD5", 10)
        BOD_removed_daily = (BOD_in - BOD_out) * Q / 1000  # kg/d

        # ---- 1. 按 F/M 计算池容 ----
        V_fm = (BOD_removed_daily * 1000) / (F_M * MLVSS)

        # ---- 2. 按 SRT 计算池容 ----
        V_srt = (SRT * Y * Q * (BOD_in - BOD_out)) / (1000 * MLVSS * (1 + Kd * SRT))

        V_design = max(V_fm, V_srt)
        HRT_design = V_design / Q * 24

        # ---- 3. 污泥产量 ----
        Y_obs = Y / (1 + Kd * SRT)
        Px_vss = Y_obs * BOD_removed_daily          # kg VSS/d
        Px_tss = Px_vss / 0.8                        # kg TSS/d

        # ---- 4. 需氧量 ----
        a_prime = dp.get("oxygen_per_kg_bod", 1.47)
        b_prime = dp.get("oxygen_per_kg_mlvss", 0.12)
        O2_bod = a_prime * BOD_removed_daily
        O2_endo = b_prime * MLVSS / 1000 * V_design

        NH3_in = input.influent.get("NH3_N", 0)
        NH3_out = input.target_effluent.get("NH3_N", 5)
        N_oxidized = max(0, NH3_in - NH3_out - BOD_removed_daily * 0.05) * Q / 1000  # net oxidized
        if N_oxidized < 0:
            N_oxidized = max(0, NH3_in - NH3_out) * Q / 1000
        O2_nit = 4.57 * N_oxidized

        O2_total = (O2_bod + O2_endo + O2_nit) * dp.get("safety_factor", 1.2)

        # ---- 5. 曝气量计算 ----
        OTE = dp.get("oxygen_transfer_efficiency", 0.20)
        submergence = dp.get("diffuser_submergence", 5.0)

        alpha = dp.get("alpha_factor", 0.85)
        beta = dp.get("beta_factor", 0.95)
        C_do = dp.get("design_do", 2.0)

        Cs_20 = 9.08
        Cs_T = Cs_20 / (1 + 0.02 * (T - 20))
        Csm = Cs_T * (1 + submergence / 20.6)

        SOTR = O2_total * Cs_20 / (24 * alpha * (beta * Csm - C_do) * 1.024 ** (T - 20))
        air_flow = SOTR / (0.28 * OTE)               # m3/h

        # ---- 6. 池体尺寸 ----
        area_total = V_design / depth
        area_per_train = area_total / n_trains
        L_W = dp.get("l_w_ratio", 5)
        width = (area_per_train / L_W) ** 0.5
        length = width * L_W

        # ---- 7. 校核值 ----
        F_M_actual = (Q * BOD_in) / (V_design * MLVSS)
        BOD_vol_loading = (Q * BOD_in) / (1000 * V_design)
        sludge_recycle = Q * dp.get("sludge_recycle_ratio", 0.8)

        warnings: List[str] = []
        self._check_param(warnings, "F/M(kgBOD/kgMLVSS-d)", F_M_actual, 0.1, 0.25, "F/M")
        self._check_param(warnings, "HRT(h)", HRT_design, 4, 12, "HRT")
        self._check_param(warnings, "SRT(d)", SRT, 10, 25, "污泥龄")
        self._check_param(warnings, "BOD容积负荷(kgBOD/m3-d)", BOD_vol_loading, 0.3, 1.0, "BOD容积负荷")
        self._check_param(warnings, "MLSS(mg/L)", MLSS, 2000, 4000, "MLSS")

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "tank_volume_total": round(V_design, 1),
                "hrt": round(HRT_design, 2),
                "srt": SRT,
                "mlss": MLSS,
                "mlvss": round(MLVSS, 0),
                "f_m_ratio": round(F_M_actual, 3),
                "f_m_ratio_design": F_M,
                "bod_vol_loading": round(BOD_vol_loading, 3),
                "bod_removed_daily_kg": round(BOD_removed_daily, 1),
                "oxygen_demand_kg_d": round(O2_total, 1),
                "sotr_kg_h": round(SOTR, 1),
                "air_flow_rate_m3_h": round(air_flow, 0),
                "diffuser_submergence": submergence,
                "oxygen_transfer_efficiency": OTE,
                "sludge_production_tss_kg_d": round(Px_tss, 1),
                "sludge_production_vss_kg_d": round(Px_vss, 1),
                "observed_yield": round(Y_obs, 3),
                "sludge_recycle_m3_d": round(sludge_recycle, 0),
                "effective_depth": depth,
                "num_trains": n_trains,
                "tank_length": round(length, 1),
                "tank_width": round(width, 1),
                "area_per_train": round(area_per_train, 1),
                "total_area": round(area_total, 1),
            },
            effluent_quality={
                "BOD5": BOD_out,
                "NH3_N": max(NH3_out, input.target_effluent.get("NH3_N", 5)),
                "TN": input.influent.get("TN", 0) * 0.3,
            },
            sludge_production=Px_tss,
            chemical_consumption={},
            power_estimate=round(air_flow * 0.005, 1),
            formulas={
                "tank_volume": "V = Q*(S0-Se) / (F/M * MLVSS)",
                "srt_volume": "V = SRT*Y*Q*(S0-Se) / (MLVSS*(1+Kd*SRT))",
                "oxygen_demand": "O2 = a'*BOD_removed + b'*MLVSS*V + 4.57*N_oxidized",
                "sludge_production": "Y_obs = Y/(1+Kd*SRT); Px = Y_obs*BOD_removed/0.8",
                "air_flow": "Q_air = SOTR / (0.28 * OTE)",
            },
            warnings=warnings,
            notes=[
                f"设计水温: {T}°C",
                f"曝气器安装深度: {submergence}m",
                f"氧转移效率: {OTE*100}%",
            ],
        )


CalculatorRegistry.register(ActivatedSludgeCalculator)
