"""工艺选择引擎 —— 基于规则评分推荐最优工艺路线。"""
import math
from typing import Dict, List, Any, Optional, Tuple
from app.knowledge.loader import KnowledgeLoader


class ProcessSelector:
    """
    基于加权评分 + 过滤规则的工艺选择引擎。

    算法流程：
    1. 加载适用该污水类型的所有工艺模板
    2. 计算衍生参数（BOD5/COD比、各污染物去除需求）
    3. 遍历所有规则，匹配条件后执行动作（加分/减分/强制要求/强制排除）
    4. 过滤掉不满足强制能力要求的模板
    5. 按总分排序，返回推荐工艺路线列表
    """

    def __init__(self, kb: KnowledgeLoader):
        self.kb = kb

    def select(self, wastewater_type: str, flow_rate: float,
               design_temp_min: float, water_quality: Dict[str, float],
               target_standard_id: str) -> Dict[str, Any]:
        """
        执行工艺选择。

        Args:
            wastewater_type: 污水类型 (domestic, textile_dyeing, electroplating, ...)
            flow_rate: 设计流量 m3/d
            design_temp_min: 最低设计水温
            water_quality: 进水水质 {param_code: mg/L}
            target_standard_id: 目标排放标准 ID (如 GB18918-2002-1A)

        Returns:
            {recommendations: [...], applied_rules: [...]}
        """
        target_limits = self.kb.resolve_standard_limits(target_standard_id)
        derived = self._derive_params(water_quality, target_limits, flow_rate, design_temp_min)
        all_params = {**water_quality, **derived, "flow_rate": flow_rate,
                      "design_temp_min": design_temp_min}

        templates = self.kb.get_templates_for_type(wastewater_type)
        if not templates:
            return {"recommendations": [], "applied_rules": [],
                    "message": f"未找到适用于 {wastewater_type} 的工艺模板"}

        scores = {t["id"]: 50.0 for t in templates}  # 基础分
        breakdown = {t["id"]: {} for t in templates}
        reasons: Dict[str, List[str]] = {t["id"]: [] for t in templates}
        risks: Dict[str, List[str]] = {t["id"]: [] for t in templates}
        mandatory_units: Dict[str, List[Dict]] = {t["id"]: [] for t in templates}
        forbidden_templates: set = set()
        required_capabilities: Dict[str, List[str]] = {}

        applied_rules = []

        for rule in self.kb.rules:
            applies_to = rule.get("applies_to", [])
            if "all" not in applies_to and wastewater_type not in applies_to:
                continue

            matched = self._eval_condition(rule.get("condition", {}), all_params)
            if not matched:
                applied_rules.append({"rule_id": rule["id"], "matched": False})
                continue

            applied_rules.append({
                "rule_id": rule["id"],
                "matched": True,
                "description_zh": rule.get("description_zh", ""),
            })

            for action in rule.get("actions", []):
                action_type = action.get("type")
                target_unit = action.get("unit_code", "")
                capability = action.get("capability", "")
                mandatory = action.get("mandatory", False)
                score_add = action.get("score_add", 0)
                reason = action.get("reason_zh", "")

                if action_type == "require_capability":
                    if mandatory:
                        for tid in list(scores.keys()):
                            if tid not in forbidden_templates:
                                caps = self._get_template_capabilities(tid, templates)
                                if capability not in caps:
                                    forbidden_templates.add(tid)

                elif action_type == "require_unit":
                    for tid in list(scores.keys()):
                        if tid not in forbidden_templates:
                            mandatory_units[tid].append({
                                "unit_code": target_unit,
                                "reason": reason,
                                "mandatory": True,
                            })

                elif action_type == "recommend_unit":
                    for tid in list(scores.keys()):
                        if tid not in forbidden_templates:
                            mandatory_units[tid].append({
                                "unit_code": target_unit,
                                "reason": reason,
                                "mandatory": mandatory,
                            })
                            if score_add:
                                scores[tid] = scores.get(tid, 50) + score_add

                elif action_type == "score_adjust":
                    if target_unit in scores and target_unit not in forbidden_templates:
                        scores[target_unit] += score_add
                        if score_add > 0 and reason:
                            reasons[target_unit].append(reason)
                        elif score_add < 0 and reason:
                            risks[target_unit].append(reason)

        for tid in sorted(breakdown.keys()):
            breakdown[tid] = {
                "base": 50.0,
                "rules_adjustment": scores[tid] - 50.0,
            }

        ranked = []
        for tid in sorted(scores.keys(), key=lambda t: scores[t], reverse=True):
            if tid in forbidden_templates:
                continue
            template = next(t for t in templates if t["id"] == tid)
            units = list(template.get("units", []))
            for extra in mandatory_units.get(tid, []):
                if not any(u.get("unit_code") == extra["unit_code"] for u in units):
                    units.append({
                        "code": extra["unit_code"],
                        "name_zh": extra.get("unit_code", ""),
                        "mandatory": extra.get("mandatory", False),
                        "note": extra.get("reason", ""),
                    })

            ranked.append({
                "route_id": tid,
                "route_name_zh": template.get("name_zh", tid),
                "total_score": round(scores[tid], 1),
                "breakdown": breakdown[tid],
                "units": [
                    {
                        "sequence": i + 1,
                        "unit_code": u["code"],
                        "unit_name_zh": u.get("name_zh", u["code"]),
                        "is_mandatory": u.get("mandatory", True),
                        "purpose_zh": u.get("note", ""),
                    }
                    for i, u in enumerate(units)
                ],
                "suitability_reasons": reasons.get(tid, []),
                "risks": risks.get(tid, []),
            })

        return {
            "wastewater_type": wastewater_type,
            "recommendations": ranked,
            "applied_rules": applied_rules,
        }

    def _derive_params(self, wq: Dict[str, float], limits: Dict[str, float],
                       flow_rate: float, temp_min: float) -> Dict[str, float]:
        """计算衍生参数。"""
        derived = {}

        cod = wq.get("COD", 0)
        bod5 = wq.get("BOD5", 0)
        if cod > 0:
            derived["BOD5_COD_ratio"] = round(bod5 / cod, 3)
        else:
            derived["BOD5_COD_ratio"] = 0.4

        nh3_in = wq.get("NH3_N", 0)
        nh3_limit = limits.get("NH3_N", 999)
        derived["NH3_N_removal_required"] = max(0, nh3_in - nh3_limit)

        tn_in = wq.get("TN", nh3_in * 1.2)
        tn_limit = limits.get("TN", 999)
        derived["TN_removal_required"] = max(0, tn_in - tn_limit)

        tp_in = wq.get("TP", 0)
        tp_limit = limits.get("TP", 999)
        derived["TP_removal_required"] = max(0, tp_in - tp_limit)

        return derived

    def _eval_condition(self, condition: Dict, params: Dict[str, float]) -> bool:
        """递归求值条件树（支持 all / any 嵌套）。"""
        if "all" in condition:
            return all(self._eval_single(c, params) for c in condition["all"])
        if "any" in condition:
            return any(self._eval_single(c, params) for c in condition["any"])
        return True

    def _eval_single(self, cond: Dict, params: Dict[str, float]) -> bool:
        """求值单个条件。"""
        param = cond["parameter"]
        operator = cond["operator"]
        threshold = cond["value"]

        actual = params.get(param)
        if actual is None:
            return False

        if operator == ">":
            return actual > threshold
        elif operator == ">=":
            return actual >= threshold
        elif operator == "<":
            return actual < threshold
        elif operator == "<=":
            return actual <= threshold
        elif operator == "==":
            return math.isclose(actual, threshold)
        elif operator == "!=":
            return not math.isclose(actual, threshold)
        return False

    def _get_template_capabilities(self, tid: str, templates: List[Dict]) -> List[str]:
        """获取指定模板的能力列表。"""
        for t in templates:
            if t["id"] == tid:
                return t.get("capabilities", [])
        return []
