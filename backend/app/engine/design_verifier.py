"""设计校核引擎 — 对比图纸提取参数与计算结果，标注偏差和风险。"""
from typing import Dict, List, Any, Optional


class DesignVerifier:
    """交叉比对图纸参数与计算参数，生成校核报告。

    校核维度:
    1. 容积校核：图纸实际容积 vs 计算需求容积
    2. 尺寸校核：图纸各维度 vs 规范最小尺寸
    3. 设备校核：图纸标注设备 vs 选型推荐
    """

    def verify(
        self,
        calculation_results: List[Dict],
        design_params: Dict[str, Dict[str, float]],
        element_mappings: List[Dict],
        knowledge_defaults: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行设计校核。

        Args:
            calculation_results: 计算引擎输出的构筑物结果列表
            design_params: {unit_code: {param_name: value}} 图纸参数
            element_mappings: 元素到构筑物的映射列表
            knowledge_defaults: 计算参数默认值（含推荐范围）

        Returns:
            {items: [...], summary: {pass, warning, fail}}
        """
        items = []

        # Build calc index
        calc_by_unit = {}
        for cr in calculation_results:
            calc_by_unit[cr.get("calculator_code", "")] = cr

        # Build design params index from mappings
        drawing_params = self._build_drawing_params(element_mappings)

        for unit_code, params in drawing_params.items():
            calc = calc_by_unit.get(unit_code, {})
            calc_output = calc.get("output_parameters", {}) if isinstance(calc, dict) else {}

            unit_name = calc.get("unit_name_zh", unit_code) if isinstance(calc, dict) else unit_code
            unit_defaults = knowledge_defaults.get(unit_code, {}).get("parameters", {})
            if isinstance(unit_defaults, dict):
                unit_defaults = unit_defaults

            for param_name, drawing_val in params.items():
                calc_val = calc_output.get(param_name)
                ranges = self._get_param_ranges(unit_defaults, param_name)

                item = self._compare(
                    unit_code=unit_code,
                    unit_name=unit_name,
                    param_name=param_name,
                    drawing_value=drawing_val,
                    calculated_value=calc_val,
                    required_min=ranges.get("min"),
                    required_max=ranges.get("max"),
                )
                items.append(item)

        # Also check calculated values against defaults for units NOT in drawings
        for unit_code, calc in calc_by_unit.items():
            if unit_code in drawing_params:
                continue  # already checked above
            output = calc.get("output_parameters", {})
            unit_name = calc.get("unit_name_zh", unit_code)
            unit_defaults = knowledge_defaults.get(unit_code, {}).get("parameters", {})

            for param_name, calc_val in output.items():
                ranges = self._get_param_ranges(unit_defaults, param_name)
                item = self._compare(
                    unit_code=unit_code,
                    unit_name=unit_name,
                    param_name=param_name,
                    drawing_value=None,
                    calculated_value=calc_val,
                    required_min=ranges.get("min"),
                    required_max=ranges.get("max"),
                )
                items.append(item)

        # Summary
        summary = {"pass": 0, "warning": 0, "fail": 0}
        for item in items:
            summary[item["status"]] = summary.get(item["status"], 0) + 1

        return {"items": items, "summary": summary}

    def _compare(
        self,
        unit_code: str,
        unit_name: str,
        param_name: str,
        drawing_value: Optional[float],
        calculated_value: Optional[float],
        required_min: Optional[float],
        required_max: Optional[float],
    ) -> Dict:
        """单项参数校核。"""
        status = "pass"
        messages = []

        # Check drawing vs calculation
        if drawing_value is not None and calculated_value is not None and calculated_value > 0:
            ratio = drawing_value / calculated_value
            if ratio < 0.85:
                status = "warning"
                messages.append(f"图纸值 ({drawing_value}) 小于计算值 ({calculated_value}) 的85%")
            elif ratio > 1.3:
                status = "warning"
                messages.append(f"图纸值 ({drawing_value}) 超过计算值 ({calculated_value}) 的130%")
            else:
                messages.append(f"图纸值与计算值偏差 {(ratio-1)*100:.0f}%")

        # Check against required range
        if required_min is not None or required_max is not None:
            check_val = drawing_value if drawing_value is not None else calculated_value
            if check_val is not None:
                if required_min is not None and check_val < required_min:
                    status = "fail"
                    messages.append(f"低于规范最小值 {required_min}")
                elif required_max is not None and check_val > required_max:
                    status = "warning"
                    messages.append(f"超过规范最大值 {required_max}")

        return {
            "unit_code": unit_code,
            "unit_name_zh": unit_name,
            "param_name": param_name,
            "drawing_value": drawing_value,
            "calculated_value": calculated_value,
            "required_min": required_min,
            "required_max": required_max,
            "status": status,
            "message": "; ".join(messages) if messages else "校核通过",
        }

    def _build_drawing_params(self, mappings: List[Dict]) -> Dict[str, Dict[str, float]]:
        """从元素映射构建 {unit_code: {param_name: value}} 结构。"""
        params: Dict[str, Dict[str, float]] = {}
        for m in mappings:
            uc = m.get("unit_code")
            pn = m.get("param_name") or m.get("element_text", "")
            val = m.get("parsed_value")
            if uc and val is not None:
                if uc not in params:
                    params[uc] = {}
                params[uc][pn] = float(val)
        return params

    def _get_param_ranges(self, unit_defaults: Dict, param_name: str) -> Dict:
        """从知识库中提取参数的推荐范围。"""
        if isinstance(unit_defaults, dict):
            param_def = unit_defaults.get(param_name, {})
            if isinstance(param_def, dict):
                rng = param_def.get("range", [])
                if isinstance(rng, list) and len(rng) == 2:
                    return {"min": rng[0], "max": rng[1]}
        return {}
