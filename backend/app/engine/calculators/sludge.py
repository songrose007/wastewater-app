"""污泥处理计算器（浓缩 + 脱水）。"""
from typing import List
from app.engine.calculators.base import BaseCalculator, CalculationInput, CalculationOutput
from app.engine.calculators.registry import CalculatorRegistry


class SludgeThickeningCalculator(BaseCalculator):
    unit_code = "sludge_thickening"
    unit_name_zh = "污泥浓缩池"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        dp = input.design_params

        solid_lr = dp.get("solid_loading_rate", 30)
        target_moisture = dp.get("thickened_sludge_moisture", 0.97)
        hrt = dp.get("hrt", 12)
        depth = dp.get("effective_depth", 4.0)

        # 收集上游污泥产量
        prev_sludge = input.previous_unit_effluent or {}
        sludge_dry = prev_sludge.get("_sludge_total_kg_d", input.influent.get("sludge_tss", 500))
        if sludge_dry <= 0:
            sludge_dry = 500  # default estimate

        area = sludge_dry / solid_lr
        n_tanks = max(1, int(area / 200) + 1)
        area_per_tank = area / n_tanks
        diameter = (area_per_tank * 4 / 3.14159) ** 0.5

        V = area * depth
        Q_sludge = sludge_dry / (1 - 0.995) / 1000  # rough wet sludge flow at 99.5% from secondary
        hrt_actual = V / (Q_sludge / 24) if Q_sludge > 0 else hrt

        thickened_conc = 1 - target_moisture
        thickened_wet = sludge_dry / thickened_conc / 1000  # m3/d

        warnings: List[str] = []
        self._check_param(warnings, "固体负荷(kg/m2-d)", solid_lr, 20, 50, "固体负荷")
        if hrt_actual < 10:
            warnings.append(f"HRT={hrt_actual:.1f}h 偏低，建议增大池容")

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
                "solid_loading_rate": solid_lr,
                "hrt_h": round(hrt_actual, 1),
                "inlet_sludge_dry_kg_d": round(sludge_dry, 1),
                "inlet_moisture": 0.995,
                "thickened_moisture": target_moisture,
                "thickened_sludge_m3_d": round(thickened_wet, 2),
            },
            effluent_quality={},
            sludge_production=sludge_dry,
            formulas={
                "area": "A = M_dry / SLR",
                "thickened": "Q_thickened = M_dry / (1 - moisture) / 1000",
            },
            warnings=warnings,
        )


class SludgeDewateringCalculator(BaseCalculator):
    unit_code = "sludge_dewatering"
    unit_name_zh = "污泥脱水间"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        dp = input.design_params

        inlet_moisture = dp.get("inlet_moisture", 0.97)
        cake_moisture = dp.get("cake_moisture", 0.80)
        working_hours = dp.get("working_hours", 16)

        sludge_dry = input.influent.get("sludge_tss", 500)
        if sludge_dry <= 0:
            sludge_dry = 500

        inlet_wet = sludge_dry / (1 - inlet_moisture) / 1000  # m3/d
        cake_wet = sludge_dry / (1 - cake_moisture) / 1000     # m3/d
        filtrate_flow = inlet_wet - cake_wet                    # m3/d

        inlet_rate = inlet_wet / working_hours                  # m3/h
        n_machines = max(1, int(inlet_rate / 15) + 1)           # 15 m3/h per machine

        pam_dose = 3.0                                          # kg/t dry solids
        pam_daily = pam_dose * sludge_dry / 1000                # kg/d

        power = n_machines * 15                                 # kW per machine estimate

        warnings: List[str] = []
        if cake_moisture > 0.85:
            warnings.append(f"泥饼含水率={cake_moisture*100}% 偏高，建议调整脱水机参数")

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "num_machines": n_machines,
                "working_hours_per_day": working_hours,
                "inlet_sludge_m3_d": round(inlet_wet, 2),
                "cake_m3_d": round(cake_wet, 2),
                "cake_t_d": round(cake_wet * 1.2, 2),
                "filtrate_m3_d": round(filtrate_flow, 2),
                "inlet_moisture": inlet_moisture,
                "cake_moisture": cake_moisture,
                "pam_daily_kg": round(pam_daily, 1),
                "power_kw": power,
            },
            effluent_quality={},
            sludge_production=sludge_dry,
            chemical_consumption={"PAM": pam_daily},
            power_estimate=power,
            formulas={
                "cake": "Q_cake = M_dry / (1 - ω_cake) / 1000",
                "filtrate": "Q_filtrate = Q_in - Q_cake",
            },
            warnings=warnings,
        )


for cls in [SludgeThickeningCalculator, SludgeDewateringCalculator]:
    CalculatorRegistry.register(cls)
