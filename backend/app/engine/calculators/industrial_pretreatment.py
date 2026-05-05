"""工业废水预处理计算器（破氰、铬还原、化学沉淀、气浮、隔油等）。"""
from typing import List
from app.engine.calculators.base import BaseCalculator, CalculationInput, CalculationOutput
from app.engine.calculators.registry import CalculatorRegistry


class CyanideOxidationCalculator(BaseCalculator):
    unit_code = "cyanide_oxidation"
    unit_name_zh = "破氰池"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "cyanide"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        dp = input.design_params

        HRT1 = dp.get("hrt_stage1", 1.0)
        ph = dp.get("ph_stage1", 10.5)
        naclo_ratio = dp.get("naclo_dosage_ratio", 7.0)

        CN_in = input.influent.get("cyanide", 0)

        Q_h = Q / 24
        V = Q_h * HRT1 * 2  # 两级破氰
        depth = 3.5
        area = V / depth

        naclo_daily = naclo_ratio * CN_in * Q / 1000 / 1000  # kg/d
        CN_out = input.target_effluent.get("cyanide", 0.3)

        effluent = dict(input.influent)
        effluent["cyanide"] = CN_out

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "tank_volume": round(V, 1),
                "hrt_stage1_h": HRT1,
                "hrt_stage2_h": HRT1,
                "ph_stage1": ph,
                "naclo_daily_kg": round(naclo_daily, 1),
                "naclo_ratio": naclo_ratio,
                "cn_removed_mg_l": round(CN_in - CN_out, 2),
            },
            effluent_quality=effluent,
            chemical_consumption={"NaClO": naclo_daily},
            formulas={
                "volume": "V = Q_h * (HRT1 + HRT2)",
                "naclo": "NaClO = 7 * CN_content",
            },
            warnings=[],
        )


class ChromiumReductionCalculator(BaseCalculator):
    unit_code = "chromium_reduction"
    unit_name_zh = "铬还原池"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "Cr6plus"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        dp = input.design_params

        HRT = dp.get("hrt", 1.0)
        ph = dp.get("ph_control", 2.5)
        na2s2o5_ratio = dp.get("na2s2o5_dosage_ratio", 4.0)

        Cr6_in = input.influent.get("Cr6plus", 0)

        Q_h = Q / 24
        V = Q_h * HRT

        na2s2o5_daily = na2s2o5_ratio * Cr6_in * Q / 1000 / 1000

        effluent = dict(input.influent)
        effluent["Cr6plus"] = input.target_effluent.get("Cr6plus", 0.2)

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "tank_volume": round(V, 1),
                "hrt_h": HRT,
                "ph_control": ph,
                "na2s2o5_daily_kg": round(na2s2o5_daily, 1),
                "na2s2o5_ratio": na2s2o5_ratio,
                "cr6_removed_mg_l": round(Cr6_in - input.target_effluent.get("Cr6plus", 0.2), 2),
            },
            effluent_quality=effluent,
            chemical_consumption={"Na2S2O5": na2s2o5_daily},
            formulas={
                "volume": "V = Q_h * HRT",
                "reductant": "Na2S2O5 = 4 * Cr6+",
            },
            warnings=[],
        )


class ChemicalPrecipitationCalculator(BaseCalculator):
    unit_code = "chemical_precipitation"
    unit_name_zh = "化学沉淀池"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "SS"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        Q_p = input.flow_rate_peak
        dp = input.design_params

        slr = dp.get("surface_loading_rate", 2.0)
        HRT = dp.get("hrt", 2.0)
        depth = dp.get("effective_depth", 3.5)
        naoh_dose = dp.get("naoh_dosage", 200)

        Q_h = Q / 24
        area = Q_h / slr
        V = area * depth
        hrt_actual = V / Q_h

        naoh_daily = naoh_dose * Q / 1000

        SS_in = input.influent.get("SS", 0)
        effluent = dict(input.influent)
        effluent["SS"] = SS_in * 0.15

        n_tanks = max(1, int(area / 300) + 1)
        area_per_tank = area / n_tanks
        diameter = (area_per_tank * 4 / 3.14159) ** 0.5

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "num_tanks": n_tanks,
                "tank_diameter": round(diameter, 1),
                "total_area": round(area, 1),
                "effective_depth": depth,
                "effective_volume": round(V, 1),
                "hrt_h": round(hrt_actual, 2),
                "surface_loading_rate": slr,
                "naoh_daily_kg": round(naoh_daily, 1),
            },
            effluent_quality=effluent,
            chemical_consumption={"NaOH": naoh_daily},
            formulas={
                "area": "A = Q_h / SLR",
                "diameter": "D = sqrt(4A/π/n)",
            },
            warnings=[],
        )


class DAFAirFlotationCalculator(BaseCalculator):
    unit_code = "daf"
    unit_name_zh = "溶气气浮(DAF)"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "oil_grease", "SS"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        dp = input.design_params

        slr = dp.get("surface_loading_rate", 5.0)
        HRT = dp.get("hrt", 0.5)
        recycle = dp.get("recycle_ratio", 0.3)
        air_solid = dp.get("air_solid_ratio", 0.03)
        pac_dose = dp.get("pac_dosage", 30)

        Q_h = Q / 24
        Q_recycle = Q_h * recycle
        Q_total = Q_h + Q_recycle

        area = Q_total / slr
        V = Q_h * HRT
        depth = max(2.0, V / area)
        V = area * depth
        hrt_actual = V / Q_h

        pac_daily = pac_dose * Q / 1000

        oil_in = input.influent.get("oil_grease", 0)
        SS_in = input.influent.get("SS", 0)

        effluent = dict(input.influent)
        effluent["oil_grease"] = oil_in * 0.15
        effluent["SS"] = SS_in * 0.30

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "effective_volume": round(V, 1),
                "surface_area": round(area, 1),
                "hrt_h": round(hrt_actual, 2),
                "surface_loading_rate": slr,
                "recycle_ratio": recycle,
                "recycle_flow": round(Q_recycle, 1),
                "air_solid_ratio": air_solid,
                "pac_daily_kg": round(pac_daily, 1),
                "oil_removal": "~85%",
            },
            effluent_quality=effluent,
            chemical_consumption={"PAC": pac_daily},
            formulas={
                "area": "A = (Q_h + Q_recycle) / SLR",
                "volume": "V = Q_h * HRT",
            },
            warnings=[],
        )


class OilSeparatorCalculator(BaseCalculator):
    unit_code = "oil_separator"
    unit_name_zh = "隔油池"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "oil_grease"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        dp = input.design_params

        slr = dp.get("surface_loading_rate", 2.0)
        HRT = dp.get("hrt", 1.5)
        depth = dp.get("effective_depth", 2.5)

        Q_h = Q / 24
        area = Q_h / slr
        V = Q_h * HRT
        depth = max(depth, V / area)
        V = area * depth
        hrt_actual = V / Q_h

        oil_in = input.influent.get("oil_grease", 0)
        effluent = dict(input.influent)
        effluent["oil_grease"] = oil_in * 0.40

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "effective_volume": round(V, 1),
                "surface_area": round(area, 1),
                "hrt_h": round(hrt_actual, 2),
                "effective_depth": round(depth, 2),
                "oil_removal": "~60%",
            },
            effluent_quality=effluent,
            formulas={
                "area": "A = Q_h / SLR",
                "volume": "V = Q_h * HRT",
            },
            warnings=[],
        )


class FentonCalculator(BaseCalculator):
    unit_code = "fenton"
    unit_name_zh = "Fenton高级氧化"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "COD"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        dp = input.design_params

        h2o2_dose = dp.get("h2o2_dosage", 300)
        fe2_dose = dp.get("fe2_dosage", 200)
        HRT = dp.get("hrt", 2)
        ph = dp.get("ph", 3.5)
        cod_eff = dp.get("cod_removal_efficiency", 0.50)

        Q_h = Q / 24
        V = Q_h * HRT

        h2o2_daily = h2o2_dose * Q / 1000
        fe2_daily = fe2_dose * Q / 1000

        COD_in = input.influent.get("COD", 0)
        COD_out = COD_in * (1 - cod_eff)

        effluent = dict(input.influent)
        effluent["COD"] = COD_out
        effluent["BOD5"] = COD_out * 0.3

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "tank_volume": round(V, 1),
                "hrt_h": HRT,
                "ph_operating": ph,
                "h2o2_daily_kg": round(h2o2_daily, 1),
                "fe2_daily_kg": round(fe2_daily, 1),
                "cod_removal_efficiency": cod_eff,
            },
            effluent_quality=effluent,
            chemical_consumption={"H2O2_30%": h2o2_daily, "FeSO4": fe2_daily},
            formulas={"volume": "V = Q_h * HRT"},
            warnings=[],
        )


class NeutralizationCalculator(BaseCalculator):
    unit_code = "neutralization"
    unit_name_zh = "中和沉淀池"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        dp = input.design_params

        HRT = dp.get("hrt", 1.0)
        depth = dp.get("effective_depth", 3.5)
        ph_target = dp.get("ph_target", 7.0)

        Q_h = Q / 24
        V = Q_h * HRT
        area = V / depth

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "tank_volume": round(V, 1),
                "hrt_h": HRT,
                "effective_depth": depth,
                "surface_area": round(area, 1),
                "ph_target": ph_target,
            },
            effluent_quality=input.influent,
            formulas={"volume": "V = Q_h * HRT"},
            warnings=[],
        )


class TubeSettlerCalculator(BaseCalculator):
    unit_code = "tube_settler"
    unit_name_zh = "斜管沉淀池"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "SS"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        dp = input.design_params

        slr = dp.get("surface_loading_rate", 3.0)
        HRT = dp.get("hrt", 0.5)
        depth = dp.get("effective_depth", 3.5)

        Q_h = Q / 24
        area = Q_h / slr
        V = Q_h * HRT
        depth = max(depth, V / area * 1.5)
        V = area * depth

        n_tanks = max(1, int(area / 100) + 1)
        area_per_tank = area / n_tanks

        SS_in = input.influent.get("SS", 0)
        effluent = dict(input.influent)
        effluent["SS"] = SS_in * 0.15

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "num_tanks": n_tanks,
                "area_per_tank": round(area_per_tank, 1),
                "total_area": round(area, 1),
                "effective_depth": round(depth, 2),
                "effective_volume": round(V, 1),
                "hrt_h": round(HRT, 2),
                "surface_loading_rate": slr,
            },
            effluent_quality=effluent,
            formulas={"area": "A = Q_h / SLR"},
            warnings=[],
        )


class SandFilterCalculator(BaseCalculator):
    unit_code = "sand_filter"
    unit_name_zh = "砂滤池"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "SS"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        dp = input.design_params

        filtration_rate = dp.get("filtration_rate", 8)
        filter_depth = dp.get("filter_depth", 1.2)

        Q_h = Q / 24
        area = Q_h / filtration_rate
        n_filters = max(2, int(area / 30) + 1)
        area_per_filter = area / n_filters

        SS_in = input.influent.get("SS", 0)
        effluent = dict(input.influent)
        effluent["SS"] = max(5, SS_in * 0.20)

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "num_filters": n_filters,
                "area_per_filter": round(area_per_filter, 1),
                "total_area": round(area, 1),
                "filtration_rate": filtration_rate,
                "filter_depth": filter_depth,
            },
            effluent_quality=effluent,
            formulas={"area": "A = Q_h / v_f"},
            warnings=[],
        )


class IonExchangeCalculator(BaseCalculator):
    unit_code = "ion_exchange"
    unit_name_zh = "离子交换"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        dp = input.design_params

        exchange_v = dp.get("exchange_velocity", 20)
        bed_depth = dp.get("bed_depth", 1.5)

        Q_h = Q / 24
        area = Q_h / exchange_v
        diameter = (area * 4 / 3.14159) ** 0.5
        n_columns = max(1, int(area / 5) + 1)

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "num_columns": n_columns,
                "column_diameter": round(diameter / n_columns ** 0.5, 2),
                "bed_depth": bed_depth,
                "exchange_velocity": exchange_v,
            },
            effluent_quality=input.influent,
            formulas={"area": "A = Q_h / v"},
            warnings=[],
        )


class FilterPressCalculator(BaseCalculator):
    unit_code = "filter_press"
    unit_name_zh = "板框压滤机"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        dp = input.design_params

        pressure = dp.get("filtration_pressure", 1.0)
        cycle_time = dp.get("cycle_time", 4)
        cake_thickness = dp.get("cake_thickness", 30)
        cake_moisture = dp.get("cake_moisture", 0.70)

        sludge_dry = input.influent.get("sludge_tss", 300)
        if sludge_dry <= 0:
            sludge_dry = 300

        inlet_wet = sludge_dry / (1 - 0.975) / 1000  # assuming 97.5% inlet moisture
        cake_wet = sludge_dry / (1 - cake_moisture) / 1000
        batches_per_day = 24 / cycle_time
        vol_per_batch = inlet_wet / batches_per_day

        n_machines = max(1, int(vol_per_batch / 2) + 1)

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "num_machines": n_machines,
                "filtration_pressure": pressure,
                "cycle_time_h": cycle_time,
                "cake_thickness_mm": cake_thickness,
                "cake_moisture": cake_moisture,
                "batches_per_day": round(batches_per_day, 1),
                "volume_per_batch_m3": round(vol_per_batch, 2),
                "cake_wet_m3_d": round(cake_wet, 2),
            },
            effluent_quality={},
            sludge_production=sludge_dry,
            formulas={
                "cycles": "n = 24 / t_cycle",
                "batch_volume": "V_batch = Q / n",
            },
            warnings=[],
        )


class ChemicalPRemovalCalculator(BaseCalculator):
    unit_code = "chemical_p_removal"
    unit_name_zh = "化学除磷"

    def get_required_inputs(self) -> List[str]:
        return ["flow_rate", "TP"]

    def calculate(self, input: CalculationInput) -> CalculationOutput:
        Q = input.flow_rate
        dp = input.design_params

        pac_dose = dp.get("pac_dosage", 20)
        tp_eff = dp.get("tp_removal_efficiency", 0.80)

        TP_in = input.influent.get("TP", 0)
        TP_out = TP_in * (1 - tp_eff)

        pac_daily = pac_dose * Q / 1000

        effluent = dict(input.influent)
        effluent["TP"] = min(TP_out, input.target_effluent.get("TP", 0.5))

        return CalculationOutput(
            unit_code=self.unit_code,
            unit_name_zh=self.unit_name_zh,
            computed_params={
                "pac_dosage": pac_dose,
                "pac_daily_kg": round(pac_daily, 1),
                "tp_removal_efficiency": tp_eff,
            },
            effluent_quality=effluent,
            chemical_consumption={"PAC": pac_daily},
            formulas={"TP_removal": "化学沉淀同步除磷"},
            warnings=[],
        )


# 注册所有工业预处理计算器
for cls in [
    CyanideOxidationCalculator,
    ChromiumReductionCalculator,
    ChemicalPrecipitationCalculator,
    DAFAirFlotationCalculator,
    OilSeparatorCalculator,
    FentonCalculator,
    NeutralizationCalculator,
    TubeSettlerCalculator,
    SandFilterCalculator,
    IonExchangeCalculator,
    FilterPressCalculator,
    ChemicalPRemovalCalculator,
]:
    CalculatorRegistry.register(cls)
