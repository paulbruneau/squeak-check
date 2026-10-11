import re, sys, os, math
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
sys.path.insert(0, os.path.dirname(__file__))
from gerb import *
d, pcb = sys.argv[1], sys.argv[2]
ppm = 25; H = 80.0
t = open(pcb).read()
def P(x, y): return (x * ppm, y * ppm)   # KiCad Y down == image Y down
imgs = {L: Image.new('L', (int(98 * ppm), int(80 * ppm)), 0) for L in ('F.Cu', 'B.Cu')}
drs = {L: ImageDraw.Draw(im) for L, im in imgs.items()}
def stroke(dr, pts, w):
    r = w / 2 * ppm
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        dr.line([P(x0, y0), P(x1, y1)], fill=255, width=max(1, int(round(w * ppm))))
    for x, y in pts:
        dr.ellipse([x * ppm - r, y * ppm - r, x * ppm + r, y * ppm + r], fill=255)
for m in re.finditer(r'\(segment \(start ([\d.-]+) ([\d.-]+)\) \(end ([\d.-]+) ([\d.-]+)\) \(width ([\d.]+)\) \(layer "([^"]+)"\)', t):
    x0, y0, x1, y1, w = map(float, m.groups()[:5]); stroke(drs[m.group(6)], [(x0, y0), (x1, y1)], w)
for m in re.finditer(r'\(arc \(start ([\d.-]+) ([\d.-]+)\) \(mid ([\d.-]+) ([\d.-]+)\) \(end ([\d.-]+) ([\d.-]+)\) \(width ([\d.]+)\) \(layer "([^"]+)"\)', t):
    x0, y0, xm, ym, x1, y1, w = map(float, m.groups()[:7])
    # circle through 3 points
    ax, ay, bx, by, cx, cy = x0, y0, xm, ym, x1, y1
    dd = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    ux = ((ax*ax+ay*ay)*(by-cy)+(bx*bx+by*by)*(cy-ay)+(cx*cx+cy*cy)*(ay-by))/dd
    uy = ((ax*ax+ay*ay)*(cx-bx)+(bx*bx+by*by)*(ax-cx)+(cx*cx+cy*cy)*(bx-ax))/dd
    r = math.hypot(ax-ux, ay-uy)
    a0, am, a1 = [math.atan2(y-uy, x-ux) for x, y in ((ax, ay), (bx, by), (cx, cy))]
    def norm(a): 
        while a < 0: a += 2*math.pi
        return a
    s = norm(a1 - a0); mm = norm(am - a0)
    if mm > s: s = s - 2*math.pi
    pts = [(ux + r*math.cos(a0 + s*i/40), uy + r*math.sin(a0 + s*i/40)) for i in range(41)]
    stroke(drs[m.group(8)], pts, w)
for fm in re.finditer(r'\(footprint "SqueakCheck:([^"]+)" \(layer "F\.Cu"\) \(uuid "[^"]+"\) \(at ([\d.-]+) ([\d.-]+)\)(.*?)\n  \)', t, re.S):
    fx, fy = float(fm.group(2)), float(fm.group(3))
    for line in fm.group(4).split('\n'):
        pm = re.search(r'\(pad "[^"]*" thru_hole (\w+) \(at ([\d.-]+) ([\d.-]+)\) \(size ([\d.]+) ([\d.]+)\)', line)
        if not pm: continue
        shp, px, py, sx, sy = pm.group(1), *map(float, pm.groups()[1:])
        x, y = fx + px, fy + py
        for dr in drs.values():
            box = [P(x - sx/2, y - sy/2), P(x + sx/2, y + sy/2)]
            if shp == 'circle': dr.ellipse(box, fill=255)
            elif shp == 'rect': dr.rectangle(box, fill=255)
            else: dr.rounded_rectangle(box, radius=min(sx, sy)/2*ppm, fill=255)
k = {L: np.array(im) > 127 for L, im in imgs.items()}
def L(suffix):
    f = [x for x in os.listdir(d) if x.endswith(suffix)][0]
    return np.array(render(*parse_gerber(open(os.path.join(d, f)).read()), ppm=ppm)) > 127
g = {'F.Cu': L('F_Cu.gtl'), 'B.Cu': L('B_Cu.gbl')}
er = np.ones((3, 3), bool)
for Ly in ('F.Cu', 'B.Cu'):
    miss = ndi.binary_erosion(k[Ly] & ~g[Ly], er)    # KiCad copper absent in Gerber
    extra = ndi.binary_erosion(g[Ly] & ~k[Ly], er)  # Gerber copper absent in KiCad (expected on B: pour)
    print(Ly, 'kicad-not-in-gerber px:', int(miss.sum()), ' gerber-not-in-kicad px:', int(extra.sum()) if Ly == 'F.Cu' else '(pour)')
    if miss.sum():
        ys, xs = np.nonzero(miss); print('   e.g. near', xs.mean()/ppm, ys.mean()/ppm)
