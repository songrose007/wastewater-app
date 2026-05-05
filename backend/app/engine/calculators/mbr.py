"""MBR好氧池计算器。"""
from typing import List
from app.engine.calculators.base import BaseCalculator, CalculationInput, CalculationOutput
from app.engine.calculators.registry import CalculatorRegistry


class MBRCalculator(BaseCalculator):
    unit_code = "mbr_tank"
    unit_name_zh = "MBR好氧池"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "BOD5", "NH3_N", "TN"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        T = input.design_temp
        dp = input.design_params

        MLSS = dp.get("mlss", 8000)
        MLVSS_ratio = dp.get("mlvss_ratio", 0.6)
        MLVSS = MLSS * MLVSS_ratio
        F_M = dp.get("f_m_ratio", 0.10)
        SRT = dp.get("srt", 25)
        Y = dp.get("sludge_yield", 0.5)
        Kd = dp.get("endogenous_decay", 0.04)
        depth = dp.get("effective_depth", 4.5)
        membrane_flux = dp.get("membrane_flux", 15)  # L/m2-h

        BOD_in = input.influent.get("BOD5", 0)
        BOD_out = input.target_effluent.get("BOD5", 10)
        BOD_removed = (BOD_in - BOD_out) * Q / 1000

        # 生物池容积
        V_fm = BOD_removed * 1000 / (F_M * MLVSS)
        V_srt = (SRT * Y * Q * (BOD_in - BOD_out)) / (1000 * MLVSS * (1 + Kd * SRT))
        V_bio = max(V_fm, V_srt)

        # 膜面积
        membrane_area = Q * 1000 / (24 * membrane_flux)   # m2
        n_membrane_racks = max(1, int(membrane_area / 1500) + 1)

        # 膜池：浸没式MBR，膜组件在好氧池内或分置
        V_membrane = n_membrane_racks * 50                # m3 per rack
        V_total = V_bio + V_membrane
        HRT = V_total / Q * 24

        # 污泥产量 (MBR产泥量较低)
        Y_obs = Y / (1 + Kd * SRT)
        Px_tss = Y_obs * BOD_removed / 0.8 * 0.85

        # 需氧量 (MBR需氧量更高，膜擦洗)
        NH3_in = input.influent.get("NH3_N", 0)
        NH3_out = input.target_effluent.get("NH3_N", 5)
        N_oxidized = max(0, NH3_in - NH3_out) * Q / 1000
        O2_bio = 1.47 * BOD_removed + 4.57 * N_oxidized
        O2_scour = membrane_area * 0.3 / 24                     # membrane scouring air
        O2_total = (O2_bio + O2_scour) * 1.2

        air_flow = O2_total / (24 * 0.28 * dp.get("oxygen_transfer_efficiency", 0.20))

        area = V_total / depth
        n_trains = max(1, int(area / 500) + 1)
        area_per_train = area / n_trains
        L_W = 3
        width = (area_per_train / L_W) ** 0.5
        length = width * L_W

        warnings: List[str] = []
        self._check_param(warnings, "HRT(h)", HRT, 4, 12, "HRT")
        self._check_param(warnings, "膜通量(L/m2-h)", membrane_flux, 10, 25, "膜通量")
        self._check_param(warnings, "MLSS(mg/L)", MLSS, 6000, 12000, "MLSS")

        if SRT < 20:
            warnings.append(f"SRT={SRT}d 偏低，建议MBR膜污泥龄>=20d")

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "bio_tank_volume": round(V_bio, 1),
                "membrane_tank_volume": round(V_membrane, 1),
                "total_volume": round(V_total, 1),
                "hrt_h": round(HRT, 2),
                "srt_d": SRT,
                "mlss": MLSS,
                "f_m_ratio": round(F_M, 3),
                "membrane_area": round(membrane_area, 0),
                "membrane_racks": n_membrane_racks,
                "membrane_flux": membrane_flux,
                "effective_depth": depth,
                "num_trains": n_trains,
                "tank_length": round(length, 1),
                "tank_width": round(width, 1),
                "surface_area": round(area, 1),
                "sludge_production_tss_kg_d": round(Px_tss, 1),
                "oxygen_demand_kg_d": round(O2_total, 1),
                "air_flow_rate_m3_h": round(air_flow, 0),
            },
            effluent_quality={
                "BOD5": min(BOD_out, 5),
                "SS": 5,
                "NH3_N": max(min(NH3_out, 2), 1),
                "TN": input.target_effluent.get("TN", 15),
            },
            sludge_production=Px_tss,
            power_estimate=round(air_flow * 0.006 + membrane_area * 0.0003, 1),
            formulas={
                "bio_volume": "V_bio = BOD_load / (F/M * MLVSS)",
                "membrane_area": "A_mem = Q * 1000 / (24 * J)",
                "HRT": "HRT = V_total / Q * 24",
            },
            warnings=warnings,
            notes=["MBR出水水质优，SS<5mg/L，浊度<1NTU"],
        )


CalculatorRegistry.register(MBRCalculator)
