"""计算器抽象基类。每个处理构筑物都是一个独立 Calculator。"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class CalculationInput:
    """单个构筑物计算器的输入。"""
    flow_rate: float                                    # m3/d
    flow_rate_peak: float                               # 峰值流量 m3/d
    influent: Dict[str, float]                          # {parameter_code: value_mg/L}
    target_effluent: Dict[str, float]                   # 目标出水 {parameter_code: value_mg/L}
    design_temp: float                                  # 设计水温 °C
    design_params: Dict[str, Any] = field(default_factory=dict)  # 设计参数覆盖
    previous_unit_effluent: Optional[Dict[str, float]] = None


@dataclass
class CalculationOutput:
    """单个构筑物计算器的输出。"""
    unit_code: str
    unit_name_zh: str
    computed_params: Dict[str, Any] = field(default_factory=dict)
    effluent_quality: Dict[str, float] = field(default_factory=dict)
    sludge_production: Optional[float] = None           # kg TSS/d
    chemical_consumption: Dict[str, float] = field(default_factory=dict)  # kg/d
    power_estimate: Optional[float] = None              # kW
    formulas: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


class BaseCalculator(ABC):
    """
    处理构筑物计算器抽象基类。

    每个子类代表一个处理单元（格栅、曝气池、二沉池...）。
    计算器是无状态的——输入 CalculationInput，输出 CalculationOutput。
    """

    unit_code: str = ""
    unit_name_zh: str = ""

    @abstractmethod
    def calculate(self, input: CalculationInput) -> CalculationOutput:
        """执行该构筑物的设计计算。"""
        ...

    @abstractmethod
    def get_required_inputs(self) -> List[str]:
        """返回必需的水质参数代码列表。"""
        ...

    def validate(self, input: CalculationInput) -> List[str]:
        """检查必需输入是否齐备，返回缺失项列表。"""
        missing = []
        for p in self.get_required_inputs():
            if p in ("flow_rate", "temperature"):
                continue
            if p not in input.influent or input.influent.get(p, 0) <= 0:
                missing.append(p)
        return missing

    def _check_range(self, param_name: str, value: float,
                     low: Optional[float], high: Optional[float]) -> Optional[str]:
        """检查值是否在推荐范围内，超出则返回警告字符串。"""
        if low is not None and value < low:
            return f"{param_name}={value:.2f} 低于推荐下限 {low}"
        if high is not None and value > high:
            return f"{param_name}={value:.2f} 高于推荐上限 {high}"
        return None

    def _check_param(self, warnings: List[str], label: str, value: float,
                     low: Optional[float], high: Optional[float], prefix: str = ""):
        """检查参数范围并追加警告。"""
        msg = self._check_range(label, value, low, high)
        if msg:
            full = f"{prefix}：{msg}" if prefix else msg
            warnings.append(full)
