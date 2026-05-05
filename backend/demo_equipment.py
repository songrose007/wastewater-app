"""演示: 给定水质水量 → 自动生成设备清单（完整链路）"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.knowledge.loader import KnowledgeLoader
from app.engine.orchestration import CalculationOrchestrator
from app.engine.calculators.registry import CalculatorRegistry
from app.engine.equipment_selector import EquipmentSelector
from app.engine.equipment_verifier import EquipmentVerifier
from app.engine.cost_estimator import CostEstimator

kb = KnowledgeLoader()
registry = CalculatorRegistry()

# ---- 模拟输入：生活污水 200m3/d ----
FLOW = 200
STANDARD = "GB18918-2002-1A"
WATER = {
    "pH": 7.2, "COD": 350, "BOD5": 180, "SS": 200,
    "NH3_N": 35, "TN": 45, "TP": 4, "temperature": 20,
}

print("=" * 80)
print(f"  输入: 生活污水 {FLOW} m3/d | COD={WATER['COD']} BOD5={WATER['BOD5']} NH3-N={WATER['NH3_N']}")
print(f"  标准: {STANDARD}")
print("=" * 80)

# ---- Step 1: 选工艺模板 ----
template = None
for t in kb.templates:
    if t['id'] == 'conventional_as':
        template = t
        break

route_units = template['units']
print(f"\n[1] 工艺路线: {template['name_zh']}")
print(f"    单元: {' -> '.join(u['name_zh'] for u in route_units)}")

# ---- Step 2: 设计计算 ----
print(f"\n[2] 设计计算中...")
limits = kb.resolve_standard_limits(STANDARD)
orch = CalculationOrchestrator(kb, registry)

calc_inputs = [{'unit_code': u['code'], 'unit_name_zh': u['name_zh'],
                'sequence_order': i+1, 'is_mandatory': u.get('mandatory', True)}
               for i, u in enumerate(route_units)]
results = orch.run_route(calc_inputs, WATER, FLOW, FLOW*1.3, limits, 12)

calc_data = []
for r in results:
    w = len(r.warnings)
    mark = ' [!]' if w > 0 else ''
    print(f"    {r.unit_name_zh}: {len(r.computed_params)} params, {w} warnings{mark}")
    calc_data.append({'calculator_code': r.unit_code, 'output_parameters': r.computed_params})

# ---- Step 3: 设备选型 ----
print(f"\n[3] 设备选型中...")
eq = EquipmentSelector(kb)
eq_result = eq.select(
    route_units=[{'unit_code': u['code'], 'unit_name_zh': u['name_zh']} for u in route_units],
    calculation_results=calc_data,
    flow_rate=FLOW,
)
equipment = eq_result['equipment_list']

# ---- 输出设备清单（用户格式）----
print(f"\n{'='*90}")
print(f"  设备清单（共 {len(equipment)} 项）")
print(f"{'='*90}")
print(f"{'序号':<4} {'设备名称':<22} {'规格型号':<28} {'数量':<5} {'单价(元)':<10} {'金额(元)':<10} {'制造商'}")
print("-" * 90)

total = 0
for i, e in enumerate(equipment, 1):
    specs = e.get('specs', {})
    # Extract key specs
    key_parts = []
    if 'motor_power_kw' in specs: key_parts.append(f"N={specs['motor_power_kw']}kW")
    if 'channel_width_mm' in specs: key_parts.append(f"B={specs['channel_width_mm']}mm")
    if 'bar_spacing_mm' in specs: key_parts.append(f"b={specs['bar_spacing_mm']}mm")
    if 'diffuser_capacity_m3_h' in specs: key_parts.append(f"Q={specs['diffuser_capacity_m3_h']}m3/h")
    if 'tank_diameter_range_m' in specs:
        d = specs['tank_diameter_range_m']
        if isinstance(d, list) and len(d)==2: key_parts.append(f"D={d[0]}-{d[1]}m")
    spec_str = ', '.join(key_parts[:3]) if key_parts else e.get('model_id', '')
    qty = e['quantity']
    price = e['unit_price_cny']
    subtotal = e['total_price_cny']
    total += subtotal
    mfr = (e.get('manufacturer', '') or '')[:10]
    print(f"{i:<4} {e['model_name_zh'][:20]:<22} {spec_str[:26]:<28} {qty:<5} {price:<10,.0f} {subtotal:<10,.0f} {mfr}")

print("-" * 90)
print(f"{'':>4} {'合计':>22} {'':>28} {'':>5} {'':>10} {total:>10,.0f}")
print(f"\n  设备总价: {total:,.0f} 元 ({total/10000:.2f} 万元)  |  吨水设备投资: {total/FLOW:,.0f} 元/m3.d")

# ---- Step 3.5: 设备校核 ----
print(f"\n[3.5] 设备校核中...")
verifier = EquipmentVerifier()
verify_result = verifier.verify(equipment, calc_data)
vsum = verify_result['summary']
print(f"  通过: {vsum.get('pass',0)} | 警告: {vsum.get('warn',0)} | 不通过: {vsum.get('fail',0)}")
for item in verify_result['items']:
    if item['overall'] != 'pass':
        icon = '[FAIL]' if item['overall'] == 'fail' else '[WARN]'
        print(f"  {icon} {item['model_name'][:25]}:")
        for c in item['checks']:
            if c['status'] != 'pass':
                print(f"      {c['status'].upper()}: {c['message']}")

# ---- Step 4: 造价估算 ----
print(f"\n[4] 造价估算中...")
estimator = CostEstimator(kb)
cost = estimator.estimate(FLOW, calc_data, equipment)
capex = cost['capex']
opex = cost['opex']
print(f"    CAPEX: {capex['total_capex']:,.2f} 万元")
print(f"    其中 土建{capex['civil_cost']:,.1f} + 设备{capex['equipment_cost']:,.1f} + 安装{capex['installation_cost']:,.1f}")
print(f"    OPEX:  {opex['total_annual_opex']:,.2f} 万元/年")
print(f"    吨水成本: {cost['cost_per_m3']:.2f} 元/m3")

# ---- Step 5: 覆盖度 ----
print(f"\n[5] 设备库覆盖度:")
from app.engine.equipment_selector import _UNIT_TO_EQUIPMENT
all_units = set()
for mappings in _UNIT_TO_EQUIPMENT.values():
    for cat, etype in mappings:
        all_units.add(f"{cat}/{etype}")
route_codes = set(u['code'] for u in route_units)
mapped = route_codes & set(_UNIT_TO_EQUIPMENT.keys())
unmapped = route_codes - mapped
print(f"    工艺 {len(route_codes)} 个单元: 已匹配 {len(mapped)} 个, 未匹配 {len(unmapped)} 个")
if unmapped:
    print(f"    未匹配: {sorted(unmapped)}")
    print(f"    (这些单元可能不需要独立设备，或需补充设备库)")
print(f"    设备库共支持 {len(all_units)} 种设备类型")

# ---- 输出对比 ----
print(f"\n{'='*80}")
print(f"  总结: 给定 {FLOW} m3/d 生活污水 → 自动生成 {len(equipment)} 项设备清单")
print(f"  总投资: {capex['total_capex']:,.2f}万 | 运行: {cost['cost_per_m3']:.2f}元/m3 | 吨水设备: {total/FLOW:,.0f}元")
print(f"{'='*80}")
