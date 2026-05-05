"""计算编排器 —— 按工艺路线顺序执行各个构筑物的设计计算。"""
from typing import Dict, List, Optional, Any
from app.engine.calculators.base import CalculationInput, CalculationOutput
from app.engine.calculators.registry import CalculatorRegistry
from app.knowledge.loader import KnowledgeLoader


class CalculationOrchestrator:
    """
    按工艺路线顺序编排计算。

    每个构筑物的出水水质自动成为下一构筑物的进水。
    工程师可对指定单元的参数进行覆盖。
    """

    def __init__(self, kb: KnowledgeLoader, registry: CalculatorRegistry):
        self.kb = kb
        self.registry = registry

    def run_route(
        self,
        route_units: List[Dict[str, Any]],
        raw_water: Dict[str, float],
        flow_rate: float,
        flow_rate_peak: float,
        target_standard_limits: Dict[str, float],
        design_temp: float,
        parameter_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[CalculationOutput]:
        """
        按工艺路线顺序执行全部计算。

        Args:
            route_units: [{sequence, unit_code, unit_name_zh, is_mandatory}, ...]
            raw_water: 原水水质 {param_code: mg/L}
            flow_rate: 设计流量 m3/d
            flow_rate_peak: 峰值流量 m3/d
            target_standard_limits: 排放限值
            design_temp: 设计水温 °C
            parameter_overrides: {unit_code: {param_name: value}}

        Returns:
            List[CalculationOutput] 按工艺顺序排列
        """
        if parameter_overrides is None:
            parameter_overrides = {}

        results: List[CalculationOutput] = []
        current_effluent: Dict[str, float] = dict(raw_water)

        for unit in sorted(route_units, key=lambda u: u.get("sequence_order", u.get("sequence", 99))):
            unit_code = unit.get("unit_code", unit.get("code", ""))
            unit_name = unit.get("unit_name_zh", unit.get("name_zh", unit_code))

            if not self.registry.has(unit_code):
                continue

            try:
                calculator = self.registry.get(unit_code)
            except ValueError:
                results.append(CalculationOutput(
                    unit_code=unit_code,
                    unit_name_zh=unit_name,
                    warnings=[f"计算器 {unit_code} 尚未实现"],
                ))
                continue

            defaults = self.kb.get_calculator_defaults(unit_code)
            overrides = parameter_overrides.get(unit_code, {})
            merged_params = {**defaults, **overrides}

            calc_input = CalculationInput(
                flow_rate=flow_rate,
                flow_rate_peak=flow_rate_peak,
                influent=current_effluent,
                target_effluent=target_standard_limits,
                design_temp=design_temp,
                design_params=merged_params,
                previous_unit_effluent=results[-1].effluent_quality if results else None,
            )

            output = calculator.calculate(calc_input)
            output.unit_name_zh = unit_name
            results.append(output)

            current_effluent = {**current_effluent, **output.effluent_quality}

        return results

    def run_single_unit(
        self,
        unit_code: str,
        raw_water: Dict[str, float],
        flow_rate: float,
        target_standard_limits: Dict[str, float],
        design_temp: float,
        parameter_overrides: Optional[Dict[str, Any]] = None,
    ) -> CalculationOutput:
        """重新计算单个单元（工程师覆盖参数后调用）。"""
        calculator = self.registry.get(unit_code)
        defaults = self.kb.get_calculator_defaults(unit_code)
        merged_params = {**defaults, **(parameter_overrides or {})}

        calc_input = CalculationInput(
            flow_rate=flow_rate,
            flow_rate_peak=flow_rate * 1.3,
            influent=raw_water,
            target_effluent=target_standard_limits,
            design_temp=design_temp,
            design_params=merged_params,
        )

        return calculator.calculate(calc_input)
