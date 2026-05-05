"""Draw ProcessOn-style flow diagram using Pillow and embed in DOCX."""
from PIL import Image, ImageDraw, ImageFont
import datetime

W, H = 1400, 780
img = Image.new('RGB', (W, H), 'white')
draw = ImageDraw.Draw(img)

# Try to load Chinese font
font_paths = [
    'C:/Windows/Fonts/msyh.ttc',
    'C:/Windows/Fonts/simhei.ttf',
    'C:/Windows/Fonts/simsun.ttc',
]
font = None
font_small = None
for fp in font_paths:
    try:
        font = ImageFont.truetype(fp, 18)
        font_small = ImageFont.truetype(fp, 15)
        font_tiny = ImageFont.truetype(fp, 13)
        font_header = ImageFont.truetype(fp, 20)
        break
    except:
        continue

if font is None:
    font = ImageFont.load_default()
    font_small = font
    font_tiny = font
    font_header = font

# Colors
BOX_BG = '#F0F0F0'
BOX_LINE = '#666666'
ARROW_C = '#666666'
CHEM_C = '#555555'
RET_C = '#999999'
HEADER_C = '#2E75B6'

BW, BH = 130, 40
R = 6

def draw_rbox(x, y, label, color=BOX_LINE, bg=BOX_BG, w=BW, h=BH):
    """Draw rounded rectangle with text."""
    draw.rounded_rectangle([x-w//2, y-h//2, x+w//2, y+h//2], radius=R, outline=color, fill=bg, width=2)
    bbox = draw.textbbox((0, 0), label, font=font_small)
    tw = bbox[2] - bbox[0]
    draw.text((x - tw//2, y - 9), label, fill='#333333', font=font_small)

def arrow(x1, y1, x2, y2, color=ARROW_C, width=2):
    """Draw line with arrowhead."""
    import math
    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    angle = math.atan2(y2 - y1, x2 - x1)
    hl = 9
    ax = x2 - hl * math.cos(angle - 0.45)
    ay = y2 - hl * math.sin(angle - 0.45)
    bx = x2 - hl * math.cos(angle + 0.45)
    by = y2 - hl * math.sin(angle + 0.45)
    draw.polygon([(x2, y2), (ax, ay), (bx, by)], fill=color)

def dashed_arrow(x1, y1, x2, y2):
    """Draw dashed line with arrowhead."""
    import math
    # Draw dashed segments
    dx, dy = x2 - x1, y2 - y1
    dist = (dx*dx + dy*dy) ** 0.5
    if dist == 0: return
    ux, uy = dx/dist, dy/dist
    seg = 8
    pos = 0
    while pos < dist - 5:
        ex = x1 + ux * min(pos + seg//2, dist)
        ey = y1 + uy * min(pos + seg//2, dist)
        draw.line([(x1 + ux*pos, y1 + uy*pos), (ex, ey)], fill=RET_C, width=2)
        pos += seg
    # Arrowhead
    angle = math.atan2(dy, dx)
    hl = 9
    ax = x2 - hl * math.cos(angle - 0.45)
    ay = y2 - hl * math.sin(angle - 0.45)
    bx = x2 - hl * math.cos(angle + 0.45)
    by = y2 - hl * math.sin(angle + 0.45)
    draw.polygon([(x2, y2), (ax, ay), (bx, by)], fill=RET_C)

def draw_text(x, y, text, font=font_tiny, color=CHEM_C):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text((x - tw//2, y - 8), text, fill=color, font=font)

# Column positions
CL = 220   # Bio
CM = 600   # Main
CR = 980   # Concentrate

# Row function
def ry(n): return 55 + n * 70

# Column headers
draw_text(CL, 25, '生化处理', font_header, HEADER_C)
draw_text(CM, 25, '主流工艺', font_header, '#1F4E79')
draw_text(CR, 25, '浓水/深度处理', font_header, '#C55A11')

# ---- Left Column (Bio) ----
for i, name in enumerate(['水解酸化池', '缺氧池', '好氧池', 'MBR池', '芬顿氧化池', '排放池']):
    draw_rbox(CL, ry(i), name)
    if i < 5:
        arrow(CL, ry(i)+BH//2, CL, ry(i+1)-BH//2)

# ---- Middle Column (Main) ----
for i, name in enumerate(['原水', '絮凝沉淀池', '石英砂过滤', 'DTRO', 'RO-1', 'RO-2', '综合调节池']):
    draw_rbox(CM, ry(i), name)
    if i < 6:
        arrow(CM, ry(i)+BH//2, CM, ry(i+1)-BH//2)

# ---- Right Column (Concentrate) ----
for i, name in enumerate(['浓水池', '铵盐反应池', '压滤机', '树脂吸附', '除氟沉淀池', '除硬沉淀池', '脱氨塔', 'MVR']):
    draw_rbox(CR, ry(i), name)
    if i < 7:
        arrow(CR, ry(i)+BH//2, CR, ry(i+1)-BH//2)

# ---- Cross-column connections ----
# DTRO → 浓水池
dtro_y = ry(3); nong_y = ry(0)
mid_x = CM + BW//2 + 40
draw.line([(CM+BW//2, dtro_y), (mid_x, dtro_y)], fill=ARROW_C, width=2)
draw.line([(mid_x, dtro_y), (mid_x, nong_y)], fill=ARROW_C, width=2)
arrow(mid_x, dtro_y, mid_x, nong_y)

# DTRO → RO (permeate)
ro1_y = ry(4)
perm_x = CM + BW//2 + 80
draw.line([(CM+BW//2, dtro_y), (perm_x, dtro_y)], fill=ARROW_C, width=2)
draw.line([(perm_x, dtro_y), (perm_x, ro1_y)], fill=ARROW_C, width=2)
draw.line([(perm_x, ro1_y), (CM+BW//2, ro1_y)], fill=ARROW_C, width=2)
arrow(perm_x, ro1_y, CM+BW//2, ro1_y)

# RO-2 → 综合调节池 (horizontal)
ro2_y = ry(5); zh_y = ry(6)
draw.line([(CM+BW//2, ro2_y), (CR-10, ro2_y)], fill=ARROW_C, width=2)
draw.line([(CR-10, ro2_y), (CR-10, zh_y)], fill=ARROW_C, width=2)
arrow(CM+BW//2, ro2_y+15, CM-10, zh_y-10)  # simplified

# 综合调节池 → 水解酸化池 (return flow)
draw.line([(CM-BW//2, zh_y), (CL+BW//2, zh_y)], fill=RET_C, width=2)
dashed_arrow(CL+BW//2, zh_y, CL+BW//2, ry(0)-BH//2)

# MBR → 缺氧池 (return flow)
mbr_y = ry(3); que_y = ry(1)
ret_x = CL - BW//2 - 20
draw.line([(ret_x, mbr_y), (ret_x, que_y)], fill=RET_C, width=2)
dashed_arrow(ret_x, mbr_y, ret_x, que_y)

# MVR → 综合调节池 (condensate return)
mvr_y = ry(7)
draw.line([(CR-BW//2, mvr_y), (CR-BW//2, mvr_y+30)], fill=ARROW_C, width=2)
draw.line([(CR-BW//2, mvr_y+30), (CM+BW//2+20, mvr_y+30)], fill=ARROW_C, width=2)
draw.line([(CM+BW//2+20, mvr_y+30), (CM+BW//2+20, zh_y)], fill=ARROW_C, width=2)
arrow(CM+BW//2+20, mvr_y+30, CM+BW//2+20, zh_y)

# ---- Chemical labels ----
draw_text(CR + 85, ry(1) + BH//2 - 5, '氨水', font_tiny, '#555')
draw_text(CR + 85, ry(1) + BH//2 + 15, '硝酸', font_tiny, '#555')
draw_text(CR + 85, ry(4) + BH//2, '石灰', font_tiny, '#555')
draw_text(CR + 85, ry(5) + BH//2, '碳酸钠', font_tiny, '#555')
draw_text(CR + 85, ry(6) + BH//2, '氨水', font_tiny, '#555')
draw_text(CM - 90, ry(2) + BH//2, '鼓风曝气', font_tiny, '#555')
draw_text(CL + 80, ry(4) - 5, '芬顿试剂', font_tiny, '#555')
draw_text(CL - 60, ry(1) - 5, '回流', font_tiny, RET_C)
draw_text(CR, ry(7) + BH + 2, '残渣', font_tiny, '#555')

# Save
png_path = r'E:\claude\wastewater-app\backend\reports\flow_diagram.png'
img.save(png_path, 'PNG')
print(f'PNG saved: {png_path} ({W}x{H})')
