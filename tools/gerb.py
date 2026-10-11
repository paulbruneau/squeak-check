"""Minimal Gerber (RS-274X) + Excellon reader/renderer for the Squeak Check fab files.

Supports what the generator emits: C/R/O apertures, G01/G02/G03 (G75), D01/D02/D03,
G36/G37 regions, %LPD/%LPC polarity. Coordinates are mm (FSLAX46Y46, MOMM).
"""
import math, re
from PIL import Image, ImageDraw

BOARD_W, BOARD_H = 98.0, 80.0


def arc_points(x0, y0, x1, y1, cx, cy, cw, seg_mm=0.05):
    r = math.hypot(x0 - cx, y0 - cy)
    a0 = math.atan2(y0 - cy, x0 - cx)
    a1 = math.atan2(y1 - cy, x1 - cx)
    if cw:
        while a1 >= a0:
            a1 -= 2 * math.pi
    else:
        while a1 <= a0:
            a1 += 2 * math.pi
    if abs(x0 - x1) < 1e-9 and abs(y0 - y1) < 1e-9:
        a1 = a0 - 2 * math.pi if cw else a0 + 2 * math.pi
    n = max(4, int(abs(a1 - a0) * r / seg_mm))
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(1, n + 1)]


def parse_gerber(text):
    """Return list of primitives: ('flash', ap, x, y, pol), ('line', ap, pts, pol), ('region', pts, pol)."""
    aps = {}
    prims = []
    cur_ap = None
    x = y = 0.0
    mode = 'G01'
    pol = 'D'
    region = None
    for m in re.finditer(r'%([^%]*)%|([^*%]*)\*', text):
        if m.group(1) is not None:
            for blk in m.group(1).split('*'):
                blk = blk.strip()
                if blk.startswith('AD'):
                    mm = re.match(r'ADD(\d+)([CRO]),([\d.]+)(?:X([\d.]+))?', blk)
                    aps[int(mm.group(1))] = (mm.group(2), float(mm.group(3)), float(mm.group(4)) if mm.group(4) else None)
                elif blk.startswith('LP'):
                    pol = blk[2]
            continue
        s = m.group(2).strip()
        if not s or s.startswith('G04'):
            continue
        if s in ('G36',):
            region = []
            continue
        if s == 'G37':
            if region and len(region) > 2:
                prims.append(('region', region, pol))
            region = None
            continue
        if s in ('G01', 'G02', 'G03'):
            mode = s
            continue
        if s in ('G75', 'G74', 'M02'):
            continue
        mm = re.match(r'^(?:G0([123]))?(?:X(-?\d+))?(?:Y(-?\d+))?(?:I(-?\d+))?(?:J(-?\d+))?(?:D0?([123]))?$', s)
        if mm and (mm.group(2) or mm.group(3) or mm.group(6)) and not re.match(r'^D(\d\d+)$', s):
            if mm.group(1):
                mode = 'G0' + mm.group(1)
            nx = int(mm.group(2)) / 1e6 if mm.group(2) else x
            ny = int(mm.group(3)) / 1e6 if mm.group(3) else y
            i = int(mm.group(4)) / 1e6 if mm.group(4) else 0.0
            j = int(mm.group(5)) / 1e6 if mm.group(5) else 0.0
            d = mm.group(6) or '1'
            if d == '2':
                if region is not None:
                    if len(region) > 2:
                        prims.append(('region', region, pol))
                    region = [(nx, ny)]
                x, y = nx, ny
                continue
            if d == '3':
                prims.append(('flash', cur_ap, nx, ny, pol))
                x, y = nx, ny
                continue
            if mode == 'G01':
                seg = [(nx, ny)]
            else:
                seg = arc_points(x, y, nx, ny, x + i, y + j, mode == 'G02')
            if region is not None:
                if not region:
                    region = [(x, y)]
                region.extend(seg)
            else:
                prims.append(('line', cur_ap, [(x, y)] + seg, pol))
            x, y = nx, ny
            continue
        mm = re.match(r'^(?:G54)?D(\d+)$', s)
        if mm:
            cur_ap = int(mm.group(1))
            continue
    return aps, prims


def render(aps, prims, ppm=20, w=BOARD_W, h=BOARD_H, img=None, fill=255):
    W, H = int(round(w * ppm)), int(round(h * ppm))
    if img is None:
        img = Image.new('L', (W, H), 0)
    dr = ImageDraw.Draw(img)

    def P(px, py):
        return (px * ppm, (h - py) * ppm)

    for p in prims:
        if p[0] == 'region':
            col = fill if p[2] == 'D' else 0
            dr.polygon([P(*q) for q in p[1]], fill=col)
            continue
        col = fill if p[-1] == 'D' else 0
        if p[0] == 'flash':
            t, a, b = aps[p[1]]
            cx, cy = P(p[2], p[3])
            if t == 'C':
                r = a / 2 * ppm
                dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
            elif t == 'R':
                dr.rectangle([cx - a / 2 * ppm, cy - b / 2 * ppm, cx + a / 2 * ppm, cy + b / 2 * ppm], fill=col)
            elif t == 'O':
                rr = min(a, b) / 2 * ppm
                dr.rounded_rectangle([cx - a / 2 * ppm, cy - b / 2 * ppm, cx + a / 2 * ppm, cy + b / 2 * ppm], radius=rr, fill=col)
        elif p[0] == 'line':
            t, a, b = aps[p[1]]
            wd = a * ppm
            pts = [P(*q) for q in p[2]]
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                dr.line([(x0, y0), (x1, y1)], fill=col, width=max(1, int(round(wd))))
                r = wd / 2
                dr.ellipse([x1 - r, y1 - r, x1 + r, y1 + r], fill=col)
            r = wd / 2
            x0, y0 = pts[0]
            dr.ellipse([x0 - r, y0 - r, x0 + r, y0 + r], fill=col)
    return img


def parse_drill(text):
    tools = {}
    holes = []
    cur = None
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r'^T(\d+)C([\d.]+)$', line)
        if m:
            tools[int(m.group(1))] = float(m.group(2))
            continue
        m = re.match(r'^T(\d+)$', line)
        if m:
            cur = int(m.group(1))
            continue
        m = re.match(r'^X(-?[\d.]+)Y(-?[\d.]+)(?:G85X(-?[\d.]+)Y(-?[\d.]+))?$', line)
        if m:
            if m.group(3):
                holes.append((tools[cur], float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))))
            else:
                holes.append((tools[cur], float(m.group(1)), float(m.group(2))))
    return holes
