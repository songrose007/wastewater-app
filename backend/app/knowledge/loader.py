"""知识库 YAML 加载器。启动时加载全部 KB 到内存，支持热重载。"""
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from app.config import settings


class KnowledgeLoader:
    """加载并缓存所有知识库 YAML 文件。"""

    def __init__(self, kb_dir: Optional[str] = None):
        self._kb_dir = Path(kb_dir or settings.KNOWLEDGE_BASE_DIR)
        self._cache: Dict[str, Any] = {}
        self.load_all()

    def load_all(self):
        """加载所有 KB 文件到缓存。"""
        for yaml_file in self._kb_dir.glob("*.yaml"):
            with open(yaml_file, "r", encoding="utf-8") as f:
                self._cache[yaml_file.stem] = yaml.safe_load(f)

    def reload(self):
        """热重载所有 KB 文件。"""
        self._cache.clear()
        self.load_all()

    @property
    def standards(self) -> List[Dict]:
        """排放标准列表。"""
        return self._cache.get("discharge_standards", {}).get("standards", [])

    @property
    def rules(self) -> List[Dict]:
        """工艺选择规则列表。"""
        return self._cache.get("process_rules", {}).get("rules", [])

    @property
    def templates(self) -> List[Dict]:
        """工艺模板列表。"""
        return self._cache.get("process_templates", {}).get("templates", [])

    @property
    def defaults(self) -> Dict[str, Any]:
        """计算参数默认值，key 为 unit_code。"""
        calcs = self._cache.get("calculation_defaults", {}).get("calculators", {})
        return calcs

    def get_standard(self, standard_id: str) -> Optional[Dict]:
        """获取指定排放标准。"""
        for s in self.standards:
            if s["id"] == standard_id:
                return s
        return None

    @property
    def equipment_catalog(self) -> Dict[str, Any]:
        """设备选型目录。Returns {category_key: category_data}."""
        return self._cache.get("equipment_catalog", {}).get("categories", {})

    @property
    def cost_factors(self) -> Dict[str, Any]:
        """造价估算系数。"""
        return self._cache.get("cost_factors", {})

    def get_equipment_models(self, category: str, equipment_type: str) -> List[Dict]:
        """获取指定设备类别/类型的型号列表。"""
        cat = self.equipment_catalog.get(category, {})
        et = cat.get("equipment_types", {}).get(equipment_type, {})
        return et.get("models", [])

    def get_equipment_type_config(self, category: str, equipment_type: str) -> Dict:
        """获取指定设备类型的配置（匹配参数、公式、冗余系数等）。"""
        cat = self.equipment_catalog.get(category, {})
        return cat.get("equipment_types", {}).get(equipment_type, {})

    def get_cost_factor(self, *path: str) -> Any:
        """按路径获取造价系数。如 ('opex', 'energy', 'electricity_price_cny_per_kwh')。"""
        result = self.cost_factors
        for key in path:
            result = result.get(key, {}) if isinstance(result, dict) else result
        return result

    def get_standard_grade(self, standard_id: str, grade: str) -> Optional[Dict]:
        """获取指定标准和等级的限值。"""
        std = self.get_standard(standard_id)
        if std:
            for cat in std.get("categories", []):
                if cat["grade"] == grade:
                    return cat
        return None

    def get_templates_for_type(self, wastewater_type: str) -> List[Dict]:
        """获取适用于指定污水类型的工艺模板。"""
        result = []
        for t in self.templates:
            applies = t.get("applies_to", [])
            if "all" in applies or wastewater_type in applies:
                result.append(t)
        return result

    def get_calculator_defaults(self, unit_code: str) -> Dict[str, Any]:
        """获取指定构筑物的设计参数默认值。"""
        calc_data = self.defaults.get(unit_code, {})
        params = calc_data.get("parameters", {})
        return {k: v["value"] for k, v in params.items()}

    def get_calculator_param_ranges(self, unit_code: str) -> Dict[str, tuple]:
        """获取指定构筑物参数推荐范围。"""
        calc_data = self.defaults.get(unit_code, {})
        params = calc_data.get("parameters", {})
        return {k: tuple(v.get("range", [None, None])) for k, v in params.items()}

    def resolve_standard_limits(self, standard_id: str) -> Dict[str, float]:
        """
        将排放标准 ID（如 'GB18918-2002-1A'）解析为限值字典。
        返回 {param_code: limit_value}。
        """
        parts = standard_id.rsplit("-", 1)
        if len(parts) == 2:
            std_id, grade = parts
        else:
            std_id = standard_id
            grade = "1"

        std = self.get_standard(std_id)
        if not std:
            return {}

        for cat in std.get("categories", []):
            if cat["grade"] == grade:
                limits = {}
                for code, info in cat.get("limits", {}).items():
                    if code.endswith("_min") or code.endswith("_max"):
                        continue
                    limits[code] = info["value"]
                return limits
        return {}
