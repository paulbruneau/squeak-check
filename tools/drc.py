"""Raster DRC + netlist check of a Squeak Check Gerber set against the KiCad pad nets.

usage: drc.py GERBER_DIR KICAD_PCB [ppm]
Checks: every pad's net (from KiCad) vs Gerber copper connectivity (F/B joined at
plated holes), copper islands, clearance between different nets, thin pour slivers,
silk over exposed pads, mask openings vs pads, drill vs pad alignment.
"""
import os, re, sys
import numpy as np
from scipy import ndimage as ndi
sys.path.insert(0, os.path.dirname(__file__))
from gerb import *

d, pcb = sys.argv[1], sys.argv[2]
ppm = int(sys.argv[3]) if len(sys.argv) > 3 else 25
MIN_CLR = 0.30
H = BOARD_H


def layer(suffix):
    f = [x for x in os.listdir(d) if x.endswith(suffix)][0]
    aps, prims = parse_gerber(open(os.path.join(d, f)).read())
    return np.array(render(aps, prims, ppm=ppm)) > 127


def drills(suffix):
    f = [x for x in os.listdir(d) if x.endswith(suffix)][0]
    return parse_drill(open(os.path.join(d, f)).read())


fcu, bcu = layer('F_Cu.gtl'), layer('B_Cu.gbl')
fmask, bmask, silk = layer('F_Mask.gts'), layer('B_Mask.gbs'), layer('F_SilkS.gto')
pth, npth = drills('-PTH.drl'), drills('-NPTH.drl')

# ---- pads from KiCad (absolute, Gerber Y-up)
t = open(pcb).read()
netname = {int(a): b for a, b in re.findall(r'^  \(net (\d+) "([^"]*)"\)', t, re.M)}
pads = []
for fm in re.finditer(r'\(footprint "SqueakCheck:([^"]+)" \(layer "F\.Cu"\) \(uuid "[^"]+"\) \(at ([\d.-]+) ([\d.-]+)\)(.*?)\n  \)', t, re.S):
    ref, fx, fy, body = fm.group(1), float(fm.group(2)), float(fm.group(3)), fm.group(4)
    for line in body.split('\n'):
        pm = re.search(r'\(pad "([^"]*)" (thru_hole|np_thru_hole) \w+ \(at ([\d.-]+) ([\d.-]+)\)', line)
        if not pm:
            continue
        dm = re.search(r'\(drill (?:oval )?([\d.]+)', line)
        nm = re.search(r'\(net \d+ "([^"]*)"\)', line)
        name, kind, px_, py_ = pm.groups()
        pads.append(dict(ref=ref, pad=name, x=fx + float(px_), y=H - (fy + float(py_)), drill=float(dm.group(1)),
                         plated=(kind == 'thru_hole'), net=nm.group(1) if nm else ''))
errors = []

# ---- drills line up with pads
def near(holes, x, y, tol=0.02):
    for h in holes:
        if abs(h[1] - x) < tol and abs(h[2] - y) < tol:
            return h
        if len(h) == 5 and abs((h[1] + h[3]) / 2 - x) < tol and abs((h[2] + h[4]) / 2 - y) < tol:
            return h
    return None

for p in pads:
    h = near(pth if p['plated'] else npth, p['x'], p['y'])
    if h is None:
        errors.append('no drill for %s.%s at (%.2f, %.2f)' % (p['ref'], p['pad'], p['x'], p['y']))
n_drill = len(pth) + len(npth)
if n_drill != len(pads):
    errors.append('drill count %d != pad count %d' % (n_drill, len(pads)))

# ---- connectivity
def px(x, y):
    return int(round((H - y) * ppm)), int(round(x * ppm))   # row, col

lf, nf = ndi.label(fcu, structure=np.ones((3, 3)))
lb, nb = ndi.label(bcu, structure=np.ones((3, 3)))
parent = {}
def find(a):
    while parent.setdefault(a, a) != a:
        parent[a] = parent[parent[a]]
        a = parent[a]
    return a
def union(a, b):
    parent[find(a)] = find(b)

pad_nodes = []
for p in pads:
    if not p['plated']:
        continue
    r, c = px(p['x'], p['y'])
    # sample the annular ring just outside the hole
    rr = int((p['drill'] / 2 + 0.12) * ppm)
    fs = {lf[r + dr, c + dc] for dr, dc in ((rr, 0), (-rr, 0), (0, rr), (0, -rr))} - {0}
    bs = {lb[r + dr, c + dc] for dr, dc in ((rr, 0), (-rr, 0), (0, rr), (0, -rr))} - {0}
    nodes = [('F', x) for x in fs] + [('B', x) for x in bs]
    if not nodes:
        errors.append('pad %s.%s has no copper' % (p['ref'], p['pad']))
        continue
    for a in nodes[1:]:
        union(nodes[0], a)
    pad_nodes.append((p, nodes[0]))

by_comp = {}
for p, n in pad_nodes:
    by_comp.setdefault(find(n), []).append(p)
net_comps = {}
for comp, ps in by_comp.items():
    nets = {p['net'] for p in ps}
    named = nets - {''}
    if len(named) > 1:
        errors.append('SHORT: %s joined: %s' % (sorted(named), ', '.join('%s.%s' % (p['ref'], p['pad']) for p in ps)))
    if '' in nets and len(ps) > 1:
        errors.append('unconnected-net pad joined to others: ' + ', '.join('%s.%s' % (p['ref'], p['pad']) for p in ps))
    for n in named:
        net_comps.setdefault(n, set()).add(comp)
for n, comps in net_comps.items():
    if len(comps) > 1:
        groups = [sorted('%s.%s' % (p['ref'], p['pad']) for p in by_comp[c]) for c in comps]
        errors.append('OPEN: net %s split into %d pieces: %s' % (n, len(comps), groups))

# islands: copper components touching no pad
used = {find(n) for _, n in pad_nodes}
for L, lab, cnt in (('F', lf, nf), ('B', lb, nb)):
    sizes = ndi.sum(np.ones_like(lab), lab, range(1, cnt + 1))
    for i in range(1, cnt + 1):
        if ('%s' % L, i) in parent and find((L, i)) in used:
            continue
        if (L, i) not in parent:
            ys, xs = np.nonzero(lab == i)
            errors.append('ISLAND on %s: %.2f mm2 near (%.2f, %.2f)' % (L, sizes[i - 1] / ppm ** 2, xs.mean() / ppm, H - ys.mean() / ppm))

# ---- clearance between different nets, per layer
comp_net = {}
for comp, ps in by_comp.items():
    for p in ps:
        if p['net']:
            comp_net[comp] = p['net']
min_gap = {}
for L, lab in (('F', lf), ('B', lb)):
    netimg = np.zeros(lab.shape, np.int32)
    names = {}
    for i in range(1, lab.max() + 1):
        key = (L, i)
        nm = comp_net.get(find(key)) if key in parent else None
        nm = nm or 'island%s%d' % (L, i)
        names.setdefault(nm, len(names) + 1)
        netimg[lab == i] = names[nm]
    dist, (ir, ic) = ndi.distance_transform_edt(netimg == 0, return_indices=True)
    near_net = netimg[ir, ic]
    inv = {v: k for k, v in names.items()}
    worst = []
    for axis in (0, 1):
        a = near_net
        b = np.roll(near_net, 1, axis=axis)
        da, db = dist, np.roll(dist, 1, axis=axis)
        m = (a != b) & (a > 0) & (b > 0)
        gap = (da + db + 1) / ppm
        gap[~m] = 99
        idx = np.argwhere(gap < MIN_CLR)
        for r, c in idx[:2000]:
            pair = tuple(sorted((inv[a[r, c]], inv[b[r, c]])))
            g = gap[r, c]
            if pair not in min_gap or g < min_gap[pair][0]:
                min_gap[pair] = (g, L, c / ppm, H - r / ppm)
        mg = gap.min()
        worst.append(mg)
    print('layer %s: min clearance between nets %.3f mm' % (L, min(worst)))
for pair, (g, L, x, y) in sorted(min_gap.items(), key=lambda kv: kv[1][0]):
    errors.append('CLEARANCE %.3f mm on %s between %s and %s near (%.2f, %.2f)' % (g, L, pair[0], pair[1], x, y))

# ---- thin copper (pour slivers): features narrower than 0.25 mm
for L, cu in (('F', fcu), ('B', bcu)):
    r = int(round(0.125 * ppm))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disk = (xx ** 2 + yy ** 2) <= r * r
    opened = ndi.binary_opening(cu, structure=disk)
    thin = cu & ~opened
    lab, n = ndi.label(thin)
    if n:
        sizes = ndi.sum(thin, lab, range(1, n + 1))
        for i, s in enumerate(sizes, 1):
            if s / ppm ** 2 > 0.05:
                ys, xs = np.nonzero(lab == i)
                errors.append('THIN copper on %s: %.3f mm2 near (%.2f, %.2f)' % (L, s / ppm ** 2, xs.mean() / ppm, H - ys.mean() / ppm))

# ---- silk on exposed copper (mask openings)
bad = silk & fmask
if bad.sum() / ppm ** 2 > 0.01:
    lab, n = ndi.label(bad)
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        if len(ys) / ppm ** 2 > 0.005:
            errors.append('SILK over mask opening near (%.2f, %.2f) %.3f mm2' % (xs.mean() / ppm, H - ys.mean() / ppm, len(ys) / ppm ** 2))

print('pads', len(pads), 'drills', n_drill, 'nets', len(net_comps))
print('\n'.join(errors) if errors else 'NO ERRORS')
