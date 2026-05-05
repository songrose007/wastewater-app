"""报告生成器 —— 组装计算数据生成 HTML 报告。"""
from typing import Dict, List, Any
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from app.config import settings


def generate_report_html(
    project_name: str,
    wastewater_type: str,
    flow_rate: float,
    target_standard: str,
    water_quality: Dict[str, float],
    process_route: Dict[str, Any],
    calculation_results: List[Dict[str, Any]],
    summary: Dict[str, Any],
    equipment_list: List[Dict[str, Any]] | None = None,
    cost_estimate: Dict[str, Any] | None = None,
) -> str:
    """生成设计报告 HTML。"""
    template_dir = Path(settings.REPORT_TEMPLATE_DIR)
    if not template_dir.exists():
        return _generate_basic_html(
            project_name, wastewater_type, flow_rate, target_standard,
            water_quality, process_route, calculation_results, summary,
            equipment_list, cost_estimate,
        )

    env = Environment(loader=FileSystemLoader(str(template_dir)))
    try:
        template = env.get_template("report_zh.html")
        return template.render(
            project_name=project_name,
            wastewater_type=wastewater_type,
            flow_rate=flow_rate,
            target_standard=target_standard,
            water_quality=water_quality,
            process_route=process_route,
            calculation_results=calculation_results,
            summary=summary,
            equipment_list=equipment_list,
            cost_estimate=cost_estimate,
        )
    except Exception:
        return _generate_basic_html(
            project_name, wastewater_type, flow_rate, target_standard,
            water_quality, process_route, calculation_results, summary,
            equipment_list, cost_estimate,
        )


def _generate_basic_html(
    project_name: str,
    wastewater_type: str,
    flow_rate: float,
    target_standard: str,
    water_quality: Dict[str, float],
    process_route: Dict[str, Any],
    calculation_results: List[Dict[str, Any]],
    summary: Dict[str, Any],
    equipment_list: List[Dict[str, Any]] | None = None,
    cost_estimate: Dict[str, Any] | None = None,
) -> str:
    """内置基础 HTML 报告模板（无需外部模板文件）。"""
    ww_type_names = {
        "domestic": "生活污水",
        "textile_dyeing": "印染废水",
        "electroplating": "电镀废水",
        "food_processing": "食品废水",
        "chemical": "化工废水",
    }

    param_names = {
        "COD": "化学需氧量(COD)", "BOD5": "五日生化需氧量(BOD5)",
        "NH3_N": "氨氮(NH3-N)", "TN": "总氮(TN)", "TP": "总磷(TP)",
        "SS": "悬浮物(SS)", "pH": "pH值", "color": "色度",
        "oil_grease": "动植物油", "Cr6plus": "六价铬", "cyanide": "氰化物",
    }

    wq_rows = ""
    for code, val in water_quality.items():
        name = param_names.get(code, code)
        wq_rows += f"<tr><td>{name}</td><td>{val}</td></tr>"

    calc_rows = ""
    for r in calculation_results:
        params = r.get("computed_parameters", {})
        params_html = ""
        for k, v in params.items():
            if isinstance(v, (int, float)):
                params_html += f"<tr><td style='padding-left:20px'>{k}</td><td>{v}</td></tr>"

        warnings = r.get("warnings", [])
        warn_html = ""
        if warnings:
            for w in warnings:
                warn_html += f"<li style='color:#d97706'>{w}</li>"

        calc_rows += f"""
        <tr>
            <td style='font-weight:bold;background:#f3f4f6'>{r.get('unit_name_zh', r.get('unit_code', ''))}</td>
            <td style='background:#f3f4f6'></td>
        </tr>
        {params_html}
        {"<tr><td colspan='2'><ul>" + warn_html + "</ul></td></tr>" if warn_html else ""}
        """

    # Build equipment table rows
    equip_rows = ""
    if equipment_list:
        for i, eq in enumerate(equipment_list, 1):
            specs_str = ", ".join(f"{k}={v}" for k, v in eq.get("specs", {}).items() if k not in ("model_id", "name_zh", "unit_price_cny", "manufacturer", "is_chinese"))
            equip_rows += f"""<tr>
                <td>{i}</td><td>{eq.get('category', '')}</td><td>{eq.get('model_name_zh', eq.get('model_id', ''))}</td>
                <td>{eq.get('model_id', '')}</td><td>{eq.get('quantity', 1)}</td>
                <td>{eq.get('unit_price_cny', 0):,.0f}</td><td>{eq.get('total_price_cny', 0):,.0f}</td>
                <td>{eq.get('manufacturer', '')}</td></tr>"""

    # Build cost tables
    cost_html = ""
    if cost_estimate:
        capex = cost_estimate.get("capex", {})
        opex = cost_estimate.get("opex", {})

        # CAPEX table
        cost_html += f"""<h2>7. 投资估算</h2>
        <h3>7.1 工程投资 (CAPEX)</h3>
        <table>
        <tr><th>费用类别</th><th>金额（万元）</th><th>占比</th></tr>
        <tr><td>土建工程费</td><td>{capex.get('civil_cost', 0):,.2f}</td><td>{capex.get('civil_cost', 0) / max(capex.get('total_capex', 1), 1) * 100:.1f}%</td></tr>
        <tr><td>设备购置费</td><td>{capex.get('equipment_cost', 0):,.2f}</td><td>{capex.get('equipment_cost', 0) / max(capex.get('total_capex', 1), 1) * 100:.1f}%</td></tr>
        <tr><td>安装工程费</td><td>{capex.get('installation_cost', 0):,.2f}</td><td>{capex.get('installation_cost', 0) / max(capex.get('total_capex', 1), 1) * 100:.1f}%</td></tr>
        <tr><td>设计费</td><td>{capex.get('engineering_cost', 0):,.2f}</td><td>{capex.get('engineering_cost', 0) / max(capex.get('total_capex', 1), 1) * 100:.1f}%</td></tr>
        <tr><td>不可预见费</td><td>{capex.get('contingency_cost', 0):,.2f}</td><td>{capex.get('contingency_cost', 0) / max(capex.get('total_capex', 1), 1) * 100:.1f}%</td></tr>
        <tr style="font-weight:bold;background:#e5e7eb"><td>合计</td><td>{capex.get('total_capex', 0):,.2f}</td><td>100%</td></tr>
        </table>"""

        # OPEX table
        cost_html += f"""<h3>7.2 年运行成本 (OPEX)</h3>
        <table>
        <tr><th>费用类别</th><th>金额（万元/年）</th><th>占比</th></tr>
        <tr><td>电费</td><td>{opex.get('energy_cost', 0):,.2f}</td><td>{opex.get('energy_cost', 0) / max(opex.get('total_annual_opex', 1), 1) * 100:.1f}%</td></tr>
        <tr><td>药剂费</td><td>{opex.get('chemical_cost', 0):,.2f}</td><td>{opex.get('chemical_cost', 0) / max(opex.get('total_annual_opex', 1), 1) * 100:.1f}%</td></tr>
        <tr><td>人工费</td><td>{opex.get('labor_cost', 0):,.2f}</td><td>{opex.get('labor_cost', 0) / max(opex.get('total_annual_opex', 1), 1) * 100:.1f}%</td></tr>
        <tr><td>维护费</td><td>{opex.get('maintenance_cost', 0):,.2f}</td><td>{opex.get('maintenance_cost', 0) / max(opex.get('total_annual_opex', 1), 1) * 100:.1f}%</td></tr>
        <tr><td>污泥处置费</td><td>{opex.get('sludge_disposal_cost', 0):,.2f}</td><td>{opex.get('sludge_disposal_cost', 0) / max(opex.get('total_annual_opex', 1), 1) * 100:.1f}%</td></tr>
        <tr><td>折旧</td><td>{opex.get('depreciation_cost', 0):,.2f}</td><td>{opex.get('depreciation_cost', 0) / max(opex.get('total_annual_opex', 1), 1) * 100:.1f}%</td></tr>
        <tr style="font-weight:bold;background:#e5e7eb"><td>合计</td><td>{opex.get('total_annual_opex', 0):,.2f}</td><td>100%</td></tr>
        </table>"""

        # Summary card
        cost_per_m3 = cost_estimate.get("cost_per_m3", 0)
        total_capex_val = capex.get("total_capex", 0)
        total_opex_val = opex.get("total_annual_opex", 0)
        cost_html += f"""<h3>7.3 经济指标汇总</h3>
        <div class="summary">
            <p><strong>工程总投资 (CAPEX):</strong> {total_capex_val:,.2f} 万元</p>
            <p><strong>年运行成本 (OPEX):</strong> {total_opex_val:,.2f} 万元/年</p>
            <p><strong>吨水处理成本:</strong> {cost_per_m3:,.2f} 元/m³</p>
            <p><strong>年处理水量:</strong> {flow_rate * 365:,.0f} m³/年</p>
        </div>"""

    # Build equipment section HTML
    equip_section_html = ""
    if equipment_list:
        equip_section_html = "<h2>6. 设备选型汇总</h2><table><tr><th>序号</th><th>类别</th><th>设备名称</th><th>型号</th><th>数量</th><th>单价(元)</th><th>总价(元)</th><th>制造商</th></tr>" + equip_rows + "</table>"
    else:
        equip_section_html = "<h2>6. 设备选型</h2><p>(尚未进行设备选型)</p>"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{project_name} - 设计方案</title>
<style>
    body {{ font-family: 'SimSun', 'Microsoft YaHei', serif; font-size: 12pt; line-height: 1.8; max-width: 210mm; margin: 0 auto; padding: 20px; color: #1a1a1a; }}
    h1 {{ text-align: center; font-size: 18pt; border-bottom: 2px solid #1a1a1a; padding-bottom: 10px; }}
    h2 {{ font-size: 14pt; border-bottom: 1px solid #9ca3af; padding-bottom: 5px; margin-top: 30px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
    th, td {{ border: 1px solid #d1d5db; padding: 6px 10px; text-align: left; }}
    th {{ background: #e5e7eb; }}
    .summary {{ background: #f0fdf4; padding: 15px; border-radius: 4px; margin: 15px 0; }}
    .footer {{ text-align: center; margin-top: 40px; color: #9ca3af; font-size: 9pt; }}
</style>
</head>
<body>
<h1>污水处理工程设计方案</h1>

<h2>1. 项目概况</h2>
<table>
    <tr><th style="width:150px">项目名称</th><td>{project_name}</td></tr>
    <tr><th>污水类型</th><td>{ww_type_names.get(wastewater_type, wastewater_type)}</td></tr>
    <tr><th>设计流量</th><td>{flow_rate} m³/d</td></tr>
    <tr><th>排放标准</th><td>{target_standard}</td></tr>
</table>

<h2>2. 进水水质</h2>
<table><tr><th>参数</th><th>数值 (mg/L)</th></tr>{wq_rows}</table>

<h2>3. 推荐工艺路线</h2>
<p>工艺路线: <strong>{process_route.get('route_name_zh', process_route.get('route_id', 'N/A'))}</strong></p>
<p>综合评分: {process_route.get('total_score', 'N/A')}</p>

<h2>4. 构筑物设计计算</h2>
<table><tr><th>构筑物</th><th>计算参数</th></tr>{calc_rows}</table>

<h2>5. 设计汇总</h2>
<div class="summary">
    <p><strong>总池容:</strong> {summary.get('total_tank_volume_m3', '-')} m³</p>
    <p><strong>估算总功率:</strong> {summary.get('total_power_kw', '-')} kW</p>
    <p><strong>污泥产量:</strong> {summary.get('total_sludge_production_kg_d', '-')} kg/d (干重)</p>
</div>

{equip_section_html}
{cost_html}

<div class="footer">
    <p>本报告由「污水处理工艺自动化设计平台」自动生成</p>
    <p>仅供参考，正式设计需由注册环保工程师审核确认</p>
</div>
</body>
</html>"""
    return html
