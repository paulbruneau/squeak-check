"""Check resized silk groups: distance to other silk, to mask openings, to board edge;
for knocked-out text, the margin inside its pill/circle."""
import sys, re
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import numpy as np
from scipy import ndimage as ndi
from gerb import parse_gerber, render
from bigtext import run
ppm = 40
src, dst, mask_f, edge_f = sys.argv[1:5]
s, groups = run(src, dst)
full = s.lines
def text_of(sel=None, force_dark=None, drop=None):
    """sel: set of line idx to keep (None = all); force_dark: idx whose polarity is forced D; drop: idx removed."""
    out = []; pol = '%LPD*%'; cur = None
    for i, l in enumerate(full):
        if l is None: continue
        if l.startswith('%LP'):
            pol = l; continue
        in_sel = sel is None or i in sel or not (l == 'G36*' or l == 'G37*' or re.match(r'^X-?\d+Y', l))
        if drop and i in drop: continue
        if not in_sel: continue
        want = '%LPD*%' if (force_dark and i in force_dark) else pol
        if want != cur and (l == 'G36*' or re.match(r'^X-?\d+Y', l)):
            out.append(want); cur = want
        out.append(l)
    return '\n'.join(out)
def idxs(ps):
    k = set()
    for p in ps:
        if p['kind'] == 'region': k.update(range(p['start'], p['end'] + 1))
        else: k.update(p['idx'])
    return k
def R(t): return np.array(render(*parse_gerber(t), ppm=ppm)) > 127
newsilk = R(text_of())
mask = R(open(mask_f).read()); edge = R(open(edge_f).read())
board = ndi.binary_fill_holes(edge)
dm = ndi.distance_transform_edt(~mask) / ppm
de = ndi.distance_transform_edt(board & ~edge) / ppm
for name, ps in groups.items():
    K = idxs(ps)
    allC = all(p['pol'] == 'C' for p in ps) or name in ('VOLUME text', 'J2 tag text') or 'tag text' in name or name.startswith('step')
    g = R(text_of(sel=K, force_dark=K))
    if allC:
        solid = R(text_of(drop={i for p in ps if p['pol'] == 'C' for i in idxs([p])}))
        bg = ~solid
        db = ndi.distance_transform_edt(~bg) / ppm
        m = db[g].min()
        print('%-16s knocked-out text margin inside its pill/circle %.2f%s' % (name, m, '  <-- CHECK' if m < 0.15 else ''))
        continue
    others = newsilk & ~ndi.binary_dilation(g, iterations=2)
    do = ndi.distance_transform_edt(~others) / ppm
    gi = g & ~ndi.binary_erosion(g)
    a, b, c = do[gi].min(), dm[gi].min(), de[gi].min()
    flag = '  <-- CHECK' if a < 0.2 or b < 0.15 or c < 0.3 else ''
    print('%-16s to other silk %.2f  to pads %.2f  to edge %.2f%s' % (name, a, b, c, flag))
