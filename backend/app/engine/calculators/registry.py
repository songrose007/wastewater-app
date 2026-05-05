"""Calculator 注册表——自动发现并注册所有计算器。"""
from typing import Dict, Type, List
from app.engine.calculators.base import BaseCalculator


class CalculatorRegistry:
    _calculators: Dict[str, Type[BaseCalculator]] = {}
    _instances: Dict[str, BaseCalculator] = {}
    _discovered: bool = False

    @classmethod
    def discover(cls):
        """扫描 calculators/ 目录，自动注册所有 BaseCalculator 子类。"""
        if cls._discovered:
            return

        from app.engine.calculators import screen, grit_chamber, primary_clarifier
        from app.engine.calculators import activated_sludge, secondary_clarifier
        from app.engine.calculators import disinfection, coagulation
        from app.engine.calculators import a2o, sbr, oxidation_ditch, mbr
        from app.engine.calculators import advanced_oxidation, hydrolysis_acidification
        from app.engine.calculators import equalization, uasb, sludge
        from app.engine.calculators import industrial_pretreatment

        cls._discovered = True

    @classmethod
    def register(cls, calc_class: Type[BaseCalculator]):
        """手动注册一个计算器类。"""
        inst = calc_class()
        cls._calculators[inst.unit_code] = calc_class
        cls._instances[inst.unit_code] = inst

    @classmethod
    def get(cls, unit_code: str) -> BaseCalculator:
        """获取计算器实例。首次调用自动触发发现。"""
        if not cls._discovered:
            cls.discover()
        if unit_code not in cls._instances:
            raise ValueError(f"未找到计算器: {unit_code}")
        return cls._instances[unit_code]

    @classmethod
    def list_all(cls) -> List[str]:
        """列出所有已注册的计算器单元代码。"""
        if not cls._discovered:
            cls.discover()
        return sorted(cls._calculators.keys())

    @classmethod
    def has(cls, unit_code: str) -> bool:
        if not cls._discovered:
            cls.discover()
        return unit_code in cls._calculators
