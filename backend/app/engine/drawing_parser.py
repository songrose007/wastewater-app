"""图纸解析引擎 — 从CAD导出的矢量PDF中提取文字标注和尺寸信息。"""
import re
import io
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import fitz  # PyMuPDF


# 尺寸标注正则模式
DIMENSION_PATTERNS = [
    # L×W×H 或 L×W 模式（池体/构筑物尺寸）
    (re.compile(r'(\d+\.?\d*)\s*[×xX]\s*(\d+\.?\d*)\s*[×xX]\s*(\d+\.?\d*)'), "LxWxH"),
    (re.compile(r'(\d+\.?\d*)\s*[×xX]\s*(\d+\.?\d*)'), "LxW"),
    # 直径标注
    (re.compile(r'[φΦDd]\s*(\d+\.?\d*)\s*(?:m|米)'), "diameter_m"),
    (re.compile(r'直径\s*(\d+\.?\d*)\s*(?:m|米)'), "diameter_m"),
    # 单值+单位
    (re.compile(r'(\d+\.?\d*)\s*(?:m|米)\s*[×xX高深]'), "length_m"),
    (re.compile(r'[高深Hh]\s*(\d+\.?\d*)\s*(?:m|米)'), "height_m"),
    # 面积
    (re.compile(r'面积\s*(\d+\.?\d*)\s*(?:m2|㎡|m²)'), "area_m2"),
    # 容积
    (re.compile(r'容积\s*(\d+\.?\d*)\s*(?:m3|m³)'), "volume_m3"),
]


# 构筑物关键词匹配（图纸标注 → 工艺单元代码）
UNIT_KEYWORDS: Dict[str, List[str]] = {
    "coarse_screen": ["粗格栅", "格栅", "粗格栅井", "格栅渠"],
    "fine_screen": ["细格栅", "转鼓格栅", "精细格栅"],
    "grit_chamber": ["沉砂池", "曝气沉砂池", "旋流沉砂", "沉砂"],
    "primary_clarifier": ["初沉池", "初次沉淀池", "辐流沉淀池"],
    "aeration_tank": ["曝气池", "好氧池", "生化池", "生物池", "活性污泥池"],
    "anoxic_tank": ["缺氧池", "反硝化池"],
    "anaerobic_tank": ["厌氧池", "厌氧区"],
    "secondary_clarifier": ["二沉池", "二次沉淀池", "终沉池"],
    "disinfection": ["消毒池", "消毒渠", "紫外消毒", "加氯消毒", "接触消毒池"],
    "sludge_thickening": ["污泥浓缩池", "浓缩池", "重力浓缩"],
    "sludge_dewatering": ["污泥脱水", "脱水机房", "脱水间", "压滤", "离心脱水"],
    "equalization_tank": ["调节池", "均质池", "调节"],
    "coagulation_tank": ["混凝池", "絮凝池", "混合絮凝"],
    "sbr_reactor": ["SBR", "序批式", "SBR池", "SBR反应器"],
    "mbr_tank": ["MBR", "膜池", "膜生物反应器"],
    "oxidation_ditch": ["氧化沟", "奥贝尔氧化沟", "卡鲁塞尔氧化沟"],
    "hydrolysis_acidification": ["水解酸化", "水解酸化池"],
    "uasb": ["UASB", "升流式厌氧"],
}


class DrawingParser:
    """PDF图纸解析器 — 从CAD导出的矢量PDF中提取文字和尺寸。"""

    def parse(self, file_path: str) -> Dict[str, Any]:
        """解析PDF文件，返回提取的元素列表和汇总信息。

        Returns:
            {elements: [{text, type, page, x0, y0, x1, y1, parsed_value, parsed_unit, parsed_dimensions}, ...],
             page_count: int}
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"图纸文件不存在: {file_path}")

        doc = fitz.open(str(path))
        elements = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("blocks")

            for block in blocks:
                if len(block) < 5:
                    continue
                x0, y0, x1, y1 = block[0], block[1], block[2], block[3]
                text = block[4] if isinstance(block[4], str) else ""

                if not text.strip():
                    continue

                text = text.strip()
                elem = self._analyze_text(text, x0, y0, x1, y1, page_num + 1)
                if elem:
                    elements.append(elem)

        doc.close()

        return {
            "elements": elements,
            "page_count": len(doc),
        }

    def _analyze_text(
        self, text: str, x0: float, y0: float, x1: float, y1: float, page: int
    ) -> Optional[Dict]:
        """分析单条文字，判断类型并提取数值。"""
        elem: Dict[str, Any] = {
            "text": text,
            "element_type": "text",
            "page_num": page,
            "x0": round(x0, 1),
            "y0": round(y0, 1),
            "x1": round(x1, 1),
            "y1": round(y1, 1),
        }

        # Try dimension patterns
        for pattern, dim_type in DIMENSION_PATTERNS:
            match = pattern.search(text)
            if match:
                elem["element_type"] = "dimension"
                groups = match.groups()

                if dim_type == "LxWxH" and len(groups) == 3:
                    elem["parsed_dimensions"] = {
                        "length_m": float(groups[0]),
                        "width_m": float(groups[1]),
                        "height_m": float(groups[2]),
                    }
                    elem["parsed_value"] = (
                        float(groups[0]) * float(groups[1]) * float(groups[2])
                    )
                    elem["parsed_unit"] = "m3"
                elif dim_type == "LxW" and len(groups) == 2:
                    elem["parsed_dimensions"] = {
                        "length_m": float(groups[0]),
                        "width_m": float(groups[1]),
                    }
                    elem["parsed_value"] = float(groups[0]) * float(groups[1])
                    elem["parsed_unit"] = "m2"
                elif dim_type in ("diameter_m", "height_m", "length_m"):
                    elem["parsed_value"] = float(groups[0])
                    elem["parsed_unit"] = "m"
                elif dim_type == "area_m2":
                    elem["parsed_value"] = float(groups[0])
                    elem["parsed_unit"] = "m2"
                elif dim_type == "volume_m3":
                    elem["parsed_value"] = float(groups[0])
                    elem["parsed_unit"] = "m3"
                break

        # Try simple numeric extraction
        if elem["element_type"] == "text":
            num_match = re.search(r'(\d+\.?\d*)\s*(m3|m²|m2|㎡|m|mm|kW|L/s|m³)', text)
            if num_match:
                elem["parsed_value"] = float(num_match.group(1))
                elem["parsed_unit"] = num_match.group(2)
                elem["element_type"] = "dimension"

        # Check if it's an equipment tag (e.g., numbers or codes)
        if re.match(r'^[A-Z]{2,4}[\-\d]+', text):
            elem["element_type"] = "equipment_tag"

        return elem

    def suggest_mappings(
        self, elements: List[Dict], route_units: List[Dict]
    ) -> List[Dict]:
        """自动建议元素到构筑物的映射。

        基于关键词匹配：如果元素的文字中包含构筑物关键词，则自动建议映射。
        也尝试从坐标关系推断：同一区域（相近y坐标）的元素归为同一构筑物。
        """
        # Build keyword index
        keyword_to_unit: Dict[str, str] = {}
        for unit_code, keywords in UNIT_KEYWORDS.items():
            for kw in keywords:
                keyword_to_unit[kw] = unit_code

        mappings = []
        for elem in elements:
            text = elem.get("text", "")
            best_match = None
            best_len = 0

            # Longest keyword match
            for keyword, unit_code in keyword_to_unit.items():
                if keyword in text and len(keyword) > best_len:
                    best_match = unit_code
                    best_len = len(keyword)

            # Only map if unit exists in route
            if best_match and any(
                u.get("unit_code") == best_match for u in route_units
            ):
                mappings.append({
                    "element_id": elem.get("id") or elem.get("text"),
                    "element_text": text,
                    "unit_code": best_match,
                    "param_name": self._suggest_param_name(elem),
                    "is_auto_mapped": True,
                    "confidence": 0.8,
                })

        return mappings

    def _suggest_param_name(self, elem: Dict) -> Optional[str]:
        """根据提取的数值类型建议参数名。"""
        unit = elem.get("parsed_unit", "")
        dims = elem.get("parsed_dimensions")

        if dims and "length_m" in dims and "width_m" in dims and "height_m" in dims:
            return "tank_volume_total"
        elif dims and "length_m" in dims:
            return "tank_length"
        elif unit == "m":
            return "effective_depth"
        elif unit in ("m2", "m²", "㎡"):
            return "surface_area"
        elif unit in ("m3", "m³"):
            return "tank_volume"
        elif unit == "kW":
            return "total_power"
        return None
