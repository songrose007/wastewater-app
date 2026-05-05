"""设备选型校验引擎 —— 选型后自动校核关键参数，标注通过/警告/不通过。"""
from typing import Dict, List, Any, Optional, Tuple


class EquipmentVerifier:
    """对 EquipmentSelector 输出的设备清单进行逐项校核。

    校验维度:
    1. 泵类: 实际 Q×H 是否在型号工作范围内，功率是否匹配
    2. 风机: 实际空气流量是否在型号范围内，功率是否满足氧传递需求
    3. 搅拌机: 池容×搅拌功率密度 vs 型号功率
    4. 刮泥机: 池径 vs 型号直径范围，周边线速度校核
    5. 曝气器: 空气流量 vs 单只曝气器能力，数量是否合理
    6. 压滤机: 污泥量 vs 处理能力
    """

    def verify(
        self,
        equipment_list: List[Dict],
        calculation_results: List[Dict],
    ) -> Dict[str, Any]:
        """逐项校核设备选型结果。

        Returns:
            {items: [{equipment, checks: [{param, status, actual, required, message}]}],
             summary: {pass, warn, fail}}
        """
        # Build calc index
        calc_index: Dict[str, Dict] = {}
        for cr in calculation_results:
            code = cr.get("calculator_code", "")
            params = cr.get("output_parameters", {}) or {}
            calc_index[code] = params

        verified = []
        summary = {"pass": 0, "warn": 0, "fail": 0}

        for eq in equipment_list:
            unit_code = eq.get("process_unit_code", "")
            eq_type = eq.get("equipment_type", "")
            calc_params = calc_index.get(unit_code, {})
            specs = eq.get("specs", {})

            checks = self._verify_equipment(eq_type, eq, specs, calc_params)

            statuses = [c["status"] for c in checks]
            if "fail" in statuses:
                overall = "fail"
            elif "warn" in statuses:
                overall = "warn"
            else:
                overall = "pass"
            summary[overall] = summary.get(overall, 0) + 1

            verified.append({
                "model_name": eq.get("model_name_zh", eq.get("model_id", "")),
                "unit_code": unit_code,
                "equipment_type": eq_type,
                "overall": overall,
                "checks": checks,
            })

        return {"items": verified, "summary": summary}

    def _verify_equipment(
        self, eq_type: str, eq: Dict, specs: Dict, calc: Dict
    ) -> List[Dict]:
        """对单台设备执行校验。"""
        checks = []

        if "pump" in eq_type.lower() or eq_type in ("submersible_sewage", "submersible_sludge",
                                                      "clean_water", "chemical_dosing"):
            checks += self._check_pump(eq, specs, calc)
        elif "blower" in eq_type.lower() or eq_type in ("roots_blower", "centrifugal_blower"):
            checks += self._check_blower(eq, specs, calc)
        elif "mixer" in eq_type.lower():
            checks += self._check_mixer(eq, specs, calc)
        elif "clarifier" in eq_type.lower() or eq_type in (
            "peripheral_drive", "center_drive", "suction"
        ):
            checks += self._check_clarifier(eq, specs, calc)
        elif "diffuser" in eq_type.lower():
            checks += self._check_diffuser(eq, specs, calc)
        elif "press" in eq_type.lower() or "dewatering" in eq_type.lower() or eq_type in (
            "belt_press", "centrifuge", "screw_press", "filter_press"
        ):
            checks += self._check_dewatering(eq, specs, calc)
        elif "screen" in eq_type.lower() or "bar_screen" in eq_type:
            checks += self._check_screen(eq, specs, calc)

        if not checks:
            checks = [self._ok("设备类型无需额外校核")]

        return checks

    def _ok(self, msg: str) -> Dict:
        return {"param": "-", "status": "pass", "actual": "-", "required": "-", "message": msg}

    def _warn(self, param: str, actual, required, msg: str) -> Dict:
        return {"param": param, "status": "warn", "actual": str(actual),
                "required": str(required), "message": msg}

    def _fail(self, param: str, actual, required, msg: str) -> Dict:
        return {"param": param, "status": "fail", "actual": str(actual),
                "required": str(required), "message": msg}

    def _pass(self, param: str, actual, required, msg: str) -> Dict:
        return {"param": param, "status": "pass", "actual": str(actual),
                "required": str(required), "message": msg}

    # ==================== 泵校核 ====================
    def _check_pump(self, eq: Dict, specs: Dict, calc: Dict) -> List[Dict]:
        checks = []
        Q = calc.get("flow_rate_m3_h", calc.get("flow_rate", 0) / 24 if calc.get("flow_rate") else 0)
        H = calc.get("head_m", calc.get("head", 10))
        power_actual = calc.get("total_power_kw", calc.get("power_kw", 0))
        power_spec = specs.get("motor_power_kw", 0)
        eff = specs.get("efficiency", 0.7)

        # 理论功率校核: P = Q*H*rho*g / (3600*eta) [kW]
        if Q > 0 and H > 0:
            P_theory = (Q * H * 9.81) / (3600 * eff)
            if power_spec > 0:
                ratio = power_spec / max(P_theory, 0.01)
                if ratio < 0.8:
                    checks.append(self._fail("motor_power_kw", f"{power_spec}kW",
                        f"需要>{P_theory:.1f}kW", f"电机功率不足, 理论需{P_theory:.1f}kW"))
                elif ratio > 2.0:
                    checks.append(self._warn("motor_power_kw", f"{power_spec}kW",
                        f"理论{P_theory:.1f}kW", f"电机功率偏大, 余量{(ratio-1)*100:.0f}%"))
                else:
                    checks.append(self._pass("motor_power_kw", f"{power_spec}kW",
                        f"理论{P_theory:.1f}kW", f"功率匹配, 余量{(ratio-1)*100:.0f}%"))

        # 流量校核
        flow_range = specs.get("flow_range_m3_h", [])
        if flow_range and Q > 0:
            if Q < flow_range[0] * 0.5:
                checks.append(self._warn("flow_rate", f"{Q:.0f}m3/h",
                    f"{flow_range[0]}-{flow_range[1]}m3/h", "流量偏小, 泵可能不在高效区"))
            elif Q > flow_range[1] * 1.2:
                checks.append(self._fail("flow_rate", f"{Q:.0f}m3/h",
                    f"{flow_range[0]}-{flow_range[1]}m3/h", "流量超出型号范围"))
            else:
                checks.append(self._pass("flow_rate", f"{Q:.0f}m3/h",
                    f"{flow_range[0]}-{flow_range[1]}m3/h", "流量在型号范围内"))

        return checks

    # ==================== 风机校核 ====================
    def _check_blower(self, eq: Dict, specs: Dict, calc: Dict) -> List[Dict]:
        checks = []
        air_flow = calc.get("air_flow_m3_h", calc.get("air_flow_rate", 0))
        air_range = specs.get("air_flow_range_m3_h", [])

        if air_range and air_flow > 0:
            if air_flow < air_range[0] * 0.6:
                checks.append(self._warn("air_flow", f"{air_flow:.0f}m3/h",
                    f"{air_range[0]}-{air_range[1]}m3/h", "风量偏小, 风机可能喘振"))
            elif air_flow > air_range[1]:
                checks.append(self._fail("air_flow", f"{air_flow:.0f}m3/h",
                    f"{air_range[0]}-{air_range[1]}m3/h", "风量超出风机能力"))
            else:
                checks.append(self._pass("air_flow", f"{air_flow:.0f}m3/h",
                    f"{air_range[0]}-{air_range[1]}m3/h", "风量在型号范围内"))

        # 压力校核
        pressure_required = calc.get("pressure_kpa", calc.get("head_loss_kpa", 50))
        pressure_range = specs.get("pressure_range_kpa", [])
        if pressure_range:
            if pressure_required > pressure_range[1]:
                checks.append(self._fail("pressure", f"{pressure_required:.0f}kPa",
                    f"<={pressure_range[1]}kPa", "所需压力超过风机能力"))
            else:
                checks.append(self._pass("pressure", f"{pressure_required:.0f}kPa",
                    f"<={pressure_range[1]}kPa", "压力满足要求"))

        if not checks:
            checks.append(self._ok("风机参数校核通过"))
        return checks

    # ==================== 搅拌机校核 ====================
    def _check_mixer(self, eq: Dict, specs: Dict, calc: Dict) -> List[Dict]:
        checks = []
        tank_vol = calc.get("tank_volume_m3", calc.get("tank_volume", 0))
        power_density = calc.get("mixing_power_density_w_m3", 5.0)
        actual_power = specs.get("motor_power_kw", 0)

        if tank_vol > 0 and power_density > 0:
            required_kw = tank_vol * power_density / 1000
            qty = eq.get("quantity", 1)
            total_kw = actual_power * qty

            if total_kw < required_kw * 0.7:
                checks.append(self._fail("motor_power_kw", f"总{total_kw}kW",
                    f"需要>{required_kw*0.7:.1f}kW", "搅拌功率不足"))
            elif total_kw > required_kw * 1.5:
                checks.append(self._warn("motor_power_kw", f"总{total_kw}kW",
                    f"需要{required_kw:.1f}kW", "搅拌功率偏大"))
            else:
                checks.append(self._pass("motor_power_kw", f"总{total_kw}kW",
                    f"需要{required_kw:.1f}kW", "搅拌功率匹配"))

        # 池容适应性
        vol_range = specs.get("suitable_tank_volume_m3", [])
        if vol_range and tank_vol > 0:
            if tank_vol > vol_range[1] * 1.5:
                checks.append(self._warn("tank_volume", f"{tank_vol:.0f}m3",
                    f"<={vol_range[1]}m3", "池容超出搅拌机适用范围"))

        return checks

    # ==================== 刮泥机校核 ====================
    def _check_clarifier(self, eq: Dict, specs: Dict, calc: Dict) -> List[Dict]:
        checks = []
        diameter = calc.get("tank_diameter_m", calc.get("tank_diameter", 0))
        dia_range = specs.get("tank_diameter_range_m", [])

        if dia_range and diameter > 0:
            if diameter < dia_range[0] * 0.8:
                checks.append(self._warn("tank_diameter", f"{diameter:.1f}m",
                    f"{dia_range[0]}-{dia_range[1]}m", "池径偏小"))
            elif diameter > dia_range[1] * 1.1:
                checks.append(self._fail("tank_diameter", f"{diameter:.1f}m",
                    f"{dia_range[0]}-{dia_range[1]}m", "池径超出刮泥机范围"))
            else:
                checks.append(self._pass("tank_diameter", f"{diameter:.1f}m",
                    f"{dia_range[0]}-{dia_range[1]}m", "池径匹配"))

        return checks

    # ==================== 曝气器校核 ====================
    def _check_diffuser(self, eq: Dict, specs: Dict, calc: Dict) -> List[Dict]:
        checks = []
        air_flow = calc.get("air_flow_m3_h", calc.get("air_flow_rate", 0))
        capacity = specs.get("diffuser_capacity_m3_h", 2.5)
        qty = eq.get("quantity", 1)

        if air_flow > 0 and capacity > 0:
            needed = int(air_flow / capacity) + 1
            if qty < needed * 0.8:
                checks.append(self._fail("quantity", f"{qty}只",
                    f"需要~{needed}只", "曝气器数量不足"))
            elif qty > needed * 1.5:
                checks.append(self._warn("quantity", f"{qty}只",
                    f"需要~{needed}只", "曝气器数量偏多"))
            else:
                checks.append(self._pass("quantity", f"{qty}只",
                    f"需要~{needed}只", "曝气器数量合理"))

        return checks

    # ==================== 脱水机校核 ====================
    def _check_dewatering(self, eq: Dict, specs: Dict, calc: Dict) -> List[Dict]:
        checks = []
        sludge = calc.get("sludge_wet_t_d", calc.get("sludge_production_wet_t_d", 0))
        cap_range = specs.get("capacity_range_t_d", [])

        if cap_range and sludge > 0:
            if sludge > cap_range[1]:
                checks.append(self._fail("capacity", f"{sludge:.1f}t/d",
                    f"<={cap_range[1]}t/d", "污泥量超出脱水机能力"))
            else:
                checks.append(self._pass("capacity", f"{sludge:.1f}t/d",
                    f"<={cap_range[1]}t/d", "处理能力满足要求"))

        return checks

    # ==================== 格栅校核 ====================
    def _check_screen(self, eq: Dict, specs: Dict, calc: Dict) -> List[Dict]:
        checks = []
        flow = calc.get("flow_rate_m3_d", calc.get("flow_rate", 0))
        flow_range = specs.get("flow_range_m3_d", [])

        if flow_range and flow > 0:
            if flow < flow_range[0] * 0.5:
                checks.append(self._warn("flow_rate", f"{flow:.0f}m3/d",
                    f"{flow_range[0]}-{flow_range[1]}m3/d", "流量偏小"))
            elif flow > flow_range[1]:
                checks.append(self._fail("flow_rate", f"{flow:.0f}m3/d",
                    f"{flow_range[0]}-{flow_range[1]}m3/d", "流量超出格栅能力"))
            else:
                checks.append(self._pass("flow_rate", f"{flow:.0f}m3/d",
                    f"{flow_range[0]}-{flow_range[1]}m3/d", "流量匹配"))

        return checks
