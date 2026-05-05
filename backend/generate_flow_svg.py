"""Generate ProcessOn-style SVG flow diagram for uranium wastewater treatment."""
import math

# Canvas: 1400 x 750
W, H = 1400, 750

# Colors
BOX_BG = '#F5F5F5'
BOX_STROKE = '#595959'
TEXT_COLOR = '#333333'
ARROW_COLOR = '#595959'
CHEM_COLOR = '#666666'
RETURN_COLOR = '#999999'

# Box dimensions
BW, BH = 130, 38
RADIUS = 6

# Column centers
COL_LEFT = 220   # Bio treatment
COL_MID = 590    # Main process
COL_RIGHT = 950  # Concentrate treatment

# Y positions
def row_y(n): return 45 + n * 68

# Box data: (col_center, y, label)
boxes = [
    # Left column - Bio treatment
    (COL_LEFT, row_y(0), '水解酸化池'),
    (COL_LEFT, row_y(1), '缺氧池'),
    (COL_LEFT, row_y(2), '好氧池'),
    (COL_LEFT, row_y(3), 'MBR池'),
    (COL_LEFT, row_y(4), '芬顿氧化池'),
    (COL_LEFT, row_y(5), '排放池'),

    # Middle column - Main process
    (COL_MID, row_y(0), '原水'),
    (COL_MID, row_y(1), '絮凝沉淀池'),
    (COL_MID, row_y(2), '石英砂过滤'),
    (COL_MID, row_y(3), 'DTRO'),
    (COL_MID, row_y(4), 'RO-1'),
    (COL_MID, row_y(5), 'RO-2'),
    (COL_MID, row_y(6), '综合调节池'),

    # Right column - Concentrate
    (COL_RIGHT, row_y(0), '浓水池'),
    (COL_RIGHT, row_y(1), '铵盐反应池'),
    (COL_RIGHT, row_y(2), '压滤机'),
    (COL_RIGHT, row_y(3), '树脂吸附'),
    (COL_RIGHT, row_y(4), '除氟沉淀池'),
    (COL_RIGHT, row_y(5), '除硬沉淀池'),
    (COL_RIGHT, row_y(6), '脱氨塔'),
    (COL_RIGHT, row_y(7), 'MVR'),
]

# Chemical labels
chems = [
    (COL_RIGHT + 100, row_y(1) + BH//2, '氨水'),
    (COL_RIGHT + 170, row_y(1) + BH//2, '硝酸'),
    (COL_RIGHT + 100, row_y(4) + BH//2, '石灰'),
    (COL_RIGHT + 100, row_y(5) + BH//2, '碳酸钠'),
    (COL_RIGHT + 100, row_y(6) + BH//2, '氨水'),
    (COL_MID - 100, row_y(2) + BH//2, '鼓风曝气'),
    (COL_LEFT + 100, row_y(4) + BH//2 - 5, '芬顿试剂'),
    (COL_RIGHT, row_y(7) + BH + 15, '残渣'),
    (COL_LEFT, row_y(1) - 10, '回流'),
]

def draw_box(x, y, label):
    """Round rect box"""
    x0, y0 = x - BW//2, y - BH//2
    return f'''<rect x="{x0}" y="{y0}" width="{BW}" height="{BH}" rx="{RADIUS}" ry="{RADIUS}"
          fill="{BOX_BG}" stroke="{BOX_STROKE}" stroke-width="1.5"/>
  <text x="{x}" y="{y+5}" text-anchor="middle" font-family="Microsoft YaHei, SimHei, sans-serif"
        font-size="13" fill="{TEXT_COLOR}">{label}</text>'''

def draw_arrow(x1, y1, x2, y2, dashed=False):
    """Draw arrow between two points"""
    dash = ' stroke-dasharray="6,4"' if dashed else ''
    # Calculate arrowhead
    angle = math.atan2(y2-y1, x2-x1)
    head_len = 8
    ax1 = x2 - head_len * math.cos(angle - 0.4)
    ay1 = y2 - head_len * math.sin(angle - 0.4)
    ax2 = x2 - head_len * math.cos(angle + 0.4)
    ay2 = y2 - head_len * math.sin(angle + 0.4)
    # Shorten line from box edges
    return f'''<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"
          stroke="{RETURN_COLOR if dashed else ARROW_COLOR}" stroke-width="1.5"{dash}/>
  <polygon points="{x2},{y2} {ax1},{ay1} {ax2},{ay2}" fill="{RETURN_COLOR if dashed else ARROW_COLOR}"/>'''

def draw_hline(x1, x2, y):
    """Horizontal line"""
    return f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{ARROW_COLOR}" stroke-width="1.5"/>'

svg_parts = []
svg_parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
svg_parts.append(f'<rect width="{W}" height="{H}" fill="white"/>')

# Draw boxes
for cx, cy, label in boxes:
    svg_parts.append(draw_box(cx, cy, label))

# Vertical arrows - Left column
for i in range(5):  # 0-4
    svg_parts.append(draw_arrow(COL_LEFT, row_y(i)+BH//2, COL_LEFT, row_y(i+1)-BH//2))

# Vertical arrows - Middle column
for i in range(6):  # 0-5
    svg_parts.append(draw_arrow(COL_MID, row_y(i)+BH//2, COL_MID, row_y(i+1)-BH//2))

# Vertical arrows - Right column
for i in range(7):  # 0-6
    svg_parts.append(draw_arrow(COL_RIGHT, row_y(i)+BH//2, COL_RIGHT, row_y(i+1)-BH//2))

# DTRO → 浓水池 (cross-column, angled)
sv_parts = []
# From DTRO top-right to 浓水池 left
dtro_y = row_y(3)
nong_y = row_y(0)
# Horizontal out from DTRO right, then up to 浓水池
mid_x = (COL_MID + COL_RIGHT) // 2
sv_parts.append(draw_hline(COL_MID + BW//2, mid_x, dtro_y))
sv_parts.append(f'<line x1="{mid_x}" y1="{dtro_y}" x2="{mid_x}" y2="{nong_y}" stroke="{ARROW_COLOR}" stroke-width="1.5"/>')
# Arrowhead
sv_parts.append(f'<polygon points="{mid_x},{nong_y} {mid_x-5},{nong_y+10} {mid_x+5},{nong_y+10}" fill="{ARROW_COLOR}"/>')

# RO-2 → 综合调节池 (cross-column)
ro2_y = row_y(5)
zonghe_y = row_y(6)
sv_parts.append(draw_arrow(COL_MID + BW//2 + 60, zonghe_y - BH//2, COL_MID, zonghe_y - BH//2))

# 综合调节池 → 水解酸化池 (return flow, dashed)
sv_parts.append(draw_hline(COL_MID - BW//2, COL_LEFT + BW//2, zonghe_y))
sv_parts.append(draw_arrow(COL_LEFT + BW//2, zonghe_y, COL_LEFT + BW//2, row_y(0) - BH//2, dashed=True))

# MBR → 缺氧池 (return flow, dashed)
mbr_y = row_y(3)
que_y = row_y(1)
ret_x = COL_LEFT - BW//2 - 15
sv_parts.append(f'<line x1="{ret_x}" y1="{mbr_y}" x2="{ret_x}" y2="{que_y}" stroke="{RETURN_COLOR}" stroke-width="1.5" stroke-dasharray="6,4"/>')
sv_parts.append(f'<polygon points="{ret_x},{que_y} {ret_x-5},{que_y+10} {ret_x+5},{que_y+10}" fill="{RETURN_COLOR}"/>')

# MVR → 综合调节池 (冷凝水回流)
mvr_y = row_y(7)
sv_parts.append(f'<line x1="{COL_RIGHT - BW//2}" y1="{mvr_y}" x2="{COL_RIGHT - BW//2}" y2="{mvr_y + 30}" stroke="{ARROW_COLOR}" stroke-width="1.5"/>')
sv_parts.append(f'<line x1="{COL_RIGHT - BW//2}" y1="{mvr_y + 30}" x2="{COL_MID + BW//2 + 50}" y2="{mvr_y + 30}" stroke="{ARROW_COLOR}" stroke-width="1.5"/>')
sv_parts.append(f'<line x1="{COL_MID + BW//2 + 50}" y1="{mvr_y + 30}" x2="{COL_MID + BW//2 + 50}" y2="{zonghe_y}" stroke="{ARROW_COLOR}" stroke-width="1.5"/>')
sv_parts.append(f'<polygon points="{COL_MID+BW//2+50},{zonghe_y} {COL_MID+BW//2+45},{zonghe_y+10} {COL_MID+BW//2+55},{zonghe_y+10}" fill="{ARROW_COLOR}"/>')

# DTRO → RO (permeate line): DTRO bottom-right → RO-1 left side
# Actually: DTRO right side → horizontal to between columns → split to RO-1 and RO-2
ro1_y = row_y(4)
dtro_rx = COL_MID + BW//2
split_x = COL_MID + BW//2 + 25

sv_parts.append(f'<line x1="{dtro_rx}" y1="{dtro_y}" x2="{split_x}" y2="{dtro_y}" stroke="{ARROW_COLOR}" stroke-width="1.5"/>')
sv_parts.append(f'<line x1="{split_x}" y1="{dtro_y}" x2="{split_x}" y2="{ro1_y}" stroke="{ARROW_COLOR}" stroke-width="1.5"/>')
sv_parts.append(f'<line x1="{split_x}" y1="{ro1_y}" x2="{COL_MID + BW//2}" y2="{ro1_y}" stroke="{ARROW_COLOR}" stroke-width="1.5"/>')
# Arrow into RO-1
sv_parts.append(f'<polygon points="{COL_MID+BW//2},{ro1_y} {COL_MID+BW//2-8},{ro1_y-5} {COL_MID+BW//2-8},{ro1_y+5}" fill="{ARROW_COLOR}"/>')

# Chemical labels
for cx, cy, text in chems:
    sv_parts.append(f'<text x="{cx}" y="{cy}" text-anchor="middle" font-family="Microsoft YaHei, SimHei, sans-serif" font-size="12" fill="{CHEM_COLOR}">{text}</text>')

# Column headers
header_y = 28
col_colors = ['#2E75B6', '#1F4E79', '#C55A11']
col_names = ['生化处理', '主流工艺', '浓水/深度处理']
col_x = [COL_LEFT, COL_MID, COL_RIGHT]
for i in range(3):
    svg_parts.append(f'<text x="{col_x[i]}" y="{header_y}" text-anchor="middle" font-family="Microsoft YaHei, SimHei, sans-serif" font-size="14" font-weight="bold" fill="{col_colors[i]}">{col_names[i]}</text>')

svg_parts.append('</svg>')

svg_content = '\n'.join(svg_parts)

with open(r'E:\claude\wastewater-app\backend\reports\flow_diagram.svg', 'w', encoding='utf-8') as f:
    f.write(svg_content)

print(f'SVG saved: {len(svg_content)} chars')
