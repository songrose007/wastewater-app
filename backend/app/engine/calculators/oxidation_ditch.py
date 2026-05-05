"""氧化沟计算器。"""
from typing import List
from app.engine.calculators.base import BaseCalculator, CalculationInput, CalculationOutput
from app.engine.calculators.registry import CalculatorRegistry


class OxidationDitchCalculator(BaseCalculator):
    unit_code = "oxidation_ditch"
    unit_name_zh = "氧化沟"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "BOD5", "NH3_N", "TN"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        T = input.design_temp
        dp = input.design_params

        MLSS = dp.get("mlss", 4000)
        MLVSS_ratio = dp.get("mlvss_ratio", 0.65)
        MLVSS = MLSS * MLVSS_ratio
        F_M = dp.get("f_m_ratio", 0.08)
        SRT = dp.get("srt", 20)
        Y = dp.get("sludge_yield", 0.5)
        Kd = dp.get("endogenous_decay", 0.04)
        depth = dp.get("effective_depth", 4.0)
        v_channel = dp.get("channel_velocity", 0.3)

        BOD_in = input.influent.get("BOD5", 0)
        BOD_out = input.target_effluent.get("BOD5", 10)
        BOD_removed = (BOD_in - BOD_out) * Q / 1000

        # 容积
        V_fm = BOD_removed * 1000 / (F_M * MLVSS)
        V_srt = (SRT * Y * Q * (BOD_in - BOD_out)) / (1000 * MLVSS * (1 + Kd * SRT))
        V_design = max(V_fm, V_srt)
        HRT = V_design / Q * 24

        # 污泥产量
        Y_obs = Y / (1 + Kd * SRT)
        Px_tss = Y_obs * BOD_removed / 0.8

        # 需氧量
        NH3_in = input.influent.get("NH3_N", 0)
        NH3_out = input.target_effluent.get("NH3_N", 5)
        N_oxidized = max(0, NH3_in - NH3_out) * Q / 1000
        O2_total = (1.47 * BOD_removed + 4.57 * N_oxidized) * 1.3 * 1.2

        OTE = dp.get("oxygen_transfer_efficiency", 0.22)
        air_flow = O2_total / (24 * 0.28 * OTE)

        # 沟道尺寸
        area = V_design / depth
        n_trains = max(1, int(area / 1000) + 1)
        area_per_train = area / n_trains

        # 氧化沟近似：总面积 = 2*(L*W_curve + straight_sections)
        # 简化计算：假设椭圆形沟道
        channel_W = area_per_train ** 0.5 / 5
        channel_L = area_per_train / channel_W if channel_W > 0 else 60

        warnings: List[str] = []
        self._check_param(warnings, "F/M(kgBOD/kgMLVSS-d)", F_M, 0.05, 0.15, "F/M")
        self._check_param(warnings, "HRT(h)", HRT, 12, 30, "HRT")
        self._check_param(warnings, "沟道流速(m/s)", v_channel, 0.25, 0.35, "沟道流速")

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "tank_volume_total": round(V_design, 1),
                "hrt_h": round(HRT, 2),
                "srt_d": SRT,
                "mlss": MLSS,
                "f_m_ratio": round(F_M, 3),
                "effective_depth": depth,
                "num_trains": n_trains,
                "channel_length": round(channel_L, 1),
                "channel_width": round(channel_W, 1),
                "surface_area": round(area, 1),
                "channel_velocity": v_channel,
                "sludge_production_tss_kg_d": round(Px_tss, 1),
                "oxygen_demand_kg_d": round(O2_total, 1),
                "air_flow_rate_m3_h": round(air_flow, 0),
            },
            effluent_quality={
                "BOD5": BOD_out,
                "NH3_N": max(NH3_out, input.target_effluent.get("NH3_N", 5)),
                "TN": input.target_effluent.get("TN", 15),
            },
            sludge_production=Px_tss,
            power_estimate=round(air_flow * 0.005 + V_design * 0.002, 1),
            formulas={
                "volume": "V = BOD_load / (F/M * MLVSS)",
                "HRT": "HRT = V / Q * 24",
                "SRT": "典型SRT=20d",
            },
            warnings=warnings,
        )


CalculatorRegistry.register(OxidationDitchCalculator)
