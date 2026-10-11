"""Add '· paul@ethicalpaul.com' after 'By Ethical Paul' on the silkscreen.
Text is rendered from Barlow Condensed SemiBold (the credit's face) and traced into Gerber regions.
usage: email.py IN_SILK OUT_SILK"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from skimage import measure

src, dst = sys.argv[1], sys.argv[2]
TEXT = 'paul@ethicalpaul.com'
FONT = __import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), '..', 'fab', 'fonts', 'BarlowCondensed-SemiBold.ttf')   # same face as 'By Ethical Paul'
S = 200.0                      # px per mm
BASE_Y = 68.35                 # second line of the left stack
CAP = 1.47                     # font size set by capital height (credit is 1.75)
X0 = 9.208                     # left edge of 'By Ethical Paul'

font = ImageFont.truetype(FONT, 100)
_t = Image.new('L', (400, 300), 0); ImageDraw.Draw(_t).text((50, 250), 'B', font=font, fill=255, anchor='ls')
_r = np.nonzero((np.array(_t) > 127).any(axis=1))[0]
size = int(round(100 * CAP * S / (_r[-1] - _r[0] + 1)))   # ink cap height at size 100
font = ImageFont.truetype(FONT, size)
pad = 40
w, h = font.getbbox(TEXT, anchor='ls')[2] + 2 * pad, int(size * 1.6) + 2 * pad
img = Image.new('L', (int(w), h), 0)
base_px = pad + int(size * 1.1)
ImageDraw.Draw(img).text((pad, base_px), TEXT, font=font, fill=255, anchor='ls')
a = np.array(img) > 127
first_col = np.nonzero(a.any(axis=0))[0][0]


contours = measure.find_contours(np.pad(a.astype(float), 1), 0.5)


def to_mm(c):
    c = measure.approximate_polygon(c, tolerance=0.6)
    return [(X0 + (px - 1 - first_col) / S, BASE_Y + (base_px - (py - 1)) / S) for py, px in c]


def area(p):
    return 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(p, p[1:] + p[:1]))


def inside(pt, poly):
    x, y = pt; n = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            n = not n
    return n


polys = [to_mm(c) for c in contours if len(c) > 4]
polys = [p for p in polys if abs(area(p)) > 0.0005]
depth = [sum(1 for j, q in enumerate(polys) if j != i and abs(area(q)) > abs(area(p)) and inside(p[0], q))
         for i, p in enumerate(polys)]
out = []
for d in range(max(depth) + 1):
    out.append('%LPD*%' if d % 2 == 0 else '%LPC*%')
    for p, dd in zip(polys, depth):
        if dd != d:
            continue
        out.append('G36*')
        for i, (x, y) in enumerate(p + [p[0]]):
            out.append('X%dY%dD0%d*' % (round(x * 1e6), round(y * 1e6), 2 if i == 0 else 1))
        out.append('G37*')
out.append('%LPD*%')
xs = [x for p in polys for x, y in p]; ys = [y for p in polys for x, y in p]
print('email text: x %.2f-%.2f  y %.2f-%.2f, %d contours, depths %s' % (min(xs), max(xs), min(ys), max(ys), len(polys), sorted(set(depth))))

lines = open(src).read().split('\n')
k = len(lines) - 1 - lines[::-1].index('M02*')
open(dst, 'w').write('\n'.join(lines[:k] + out + lines[k:]))
