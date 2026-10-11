"""Rev E.6 silkscreen: bring all text under 1.1 mm cap height up to 1.1 mm.

usage: bigtext.py IN_SILK OUT_SILK
Each entry: name, selection box (x0, x1, y0, y1), polarities, current cap height,
anchor point (stays fixed), extra move (dx, dy). Gerber coords, mm, Y up.
"""
import sys, json
from silkedit import Silk, bbox_of

T = 1.1
DC = ('D', 'C')
SPEC = [
    # top right: power header notes
    ('INSERT', (62.3, 70.0, 75.6, 77.0), DC, None, (62.45, 76.26), (0, 0), (1.1, 1.1 / 0.92)),
    ('POWER', (62.3, 70.0, 73.7, 75.2), DC, None, (62.45, 74.37), (0, 0), (1.1, 1.1 / 0.92)),
    ('KK-396', (62.3, 65.7, 71.3, 72.5), DC, 0.85, (62.48, 71.90), (0, 0)),
    ('KK-396 bolt', (65.9, 67.1, 70.9, 72.9), DC, None, None, (0.9, 0)),
    ('5V 1A', (62.3, 64.4, 69.3, 70.3), DC, 0.70, (62.46, 69.45), (0, 0.05)),
    ('12V 0.5A', (64.9, 68.1, 69.3, 70.3), DC, 0.70, (64.96, 69.45), (-2.5, -1.55)),
    # power pin tags: pill grows a little, text grows to 1.1
    ('+5V tag text', (47.2, 49.2, 66.9, 68.2), DC, None, (48.20, 67.55), (0, 0), (1.12, 1.25)),
    ('GND tag text', (51.2, 53.2, 66.9, 68.2), DC, None, (52.16, 67.55), (0, 0), (1.12, 1.25)),
    ('GND2 tag text', (55.1, 57.2, 66.9, 68.2), DC, None, (56.12, 67.55), (0, 0), (1.12, 1.25)),
    ('+12V tag text', (58.9, 61.3, 66.9, 68.2), DC, None, (60.08, 67.55), (0, 0), (1.12, 1.25)),
    ('F1', (43.5, 46.0, 66.5, 68.0), DC, 0.77, (44.65, 66.86), (0, 0)),
    # how-to panel
    ('step 1', (62.9, 63.8, 59.0, 60.2), DC, 0.91, (63.35, 59.60), (0, 0)),
    ('step 2', (62.9, 63.8, 55.9, 57.1), DC, 0.91, (63.35, 56.50), (0, 0)),
    ('step 3', (62.9, 63.8, 52.8, 54.0), DC, 0.91, (63.35, 53.40), (0, 0)),
    ('step 4', (62.9, 63.8, 49.7, 50.9), DC, 0.91, (63.35, 50.30), (0, 0)),
    ('LINE LEVEL', (62.3, 75.0, 46.5, 47.8), DC, 0.84, (62.45, 46.78), (0, 0)),
    ('NOT A BARE', (62.3, 72.0, 45.0, 46.2), DC, 0.84, (62.45, 45.18), (0, 0)),
    ('SOUND BD LED', (62.3, 70.0, 41.3, 42.5), DC, 0.95, (62.44, 41.42), (0, 0)),
    ('6 FLASHES', (62.3, 70.5, 39.4, 40.4), DC, 0.81, (62.44, 39.49), (0, 0)),
    ('1-4 ROM', (62.3, 71.4, 37.6, 38.6), DC, 0.78, (62.41, 37.71), (0, 0)),
    ('STOPS', (62.3, 71.0, 35.8, 36.8), DC, 0.78, (62.43, 35.91), (0, 0)),
    # J3 side
    ('J3 22 AWG', (74.6, 75.9, 28.2, 32.2), DC, 0.92, (75.72, 30.2), (0, 0)),
    ('LOUDER', (78.1, 79.4, 19.0, 23.0), DC, 0.95, (78.75, 21.03), (0, 0.35)),
    ('VOLUME text', (78.2, 79.3, 11.6, 15.6), ('C', 'D'), 0.95, (78.75, 13.625), (0, 0)),
    ('VOLUME pill', (77.8, 79.7, 11.0, 16.3), ('D',), None, (78.75, 13.625), (0, 0), 1.12),
    ('RRST 10K', (69.6, 71.5, 18.9, 20.1), DC, 0.91, (70.575, 19.5), (0, 0)),
    ('5V', (50.6, 52.0, 49.8, 51.1), DC, 0.78, (51.305, 50.45), (0, 0)),
    ('12V', (55.7, 57.5, 49.8, 51.1), DC, 0.78, (56.59, 50.45), (0, 0)),
    ('F2', (59.4, 60.8, 57.2, 58.4), DC, 0.78, (60.095, 57.80), (0, 0)),
    # left side
    ('J1 22 AWG', (12.3, 16.1, 64.6, 65.8), DC, 0.92, (12.47, 65.20), (0, 0)),
    ('1K SERIES', (19.1, 23.5, 60.3, 61.4), DC, 0.84, (21.275, 60.48), (0, 0)),
    ('10K PULL-DOWN', (30.2, 39.4, 60.3, 61.4), DC, 0.84, (34.775, 60.48), (0, 0)),
    ('TRIGGER', (21.9, 28.7, 38.9, 40.1), DC, 0.88, (25.32, 40.04), (0, 0)),
    ('1uF', (33.1, 34.8, 45.4, 46.8), DC, 0.84, (33.94, 46.20), (0, 0.1)),
    ('18 AWG', (7.2, 10.8, 10.5, 11.7), DC, 0.92, (7.36, 11.10), (0, 0)),
    ('98 x 80', (8.3, 20.8, 19.0, 20.2), DC, 0.84, (8.42, 19.18), (0, 0)),
    ('MOUNT', (8.3, 23.7, 16.8, 17.8), DC, 0.74, (8.44, 16.93), (0, 0)),
    ('J2 tag text', (6.4, 17.2, 13.3, 14.7), DC, 1.03, (11.78, 14.00), (0, 0)),
]
# resistor values in the boxes
for y in (58.0, 54.0, 50.0, 34.0, 30.0):
    SPEC.append(('1K @%g' % y, (19.6, 23.0, y - 0.6, y + 0.6), DC, 0.91, (21.28, y), (0, 0)))
    SPEC.append(('10K @%g' % y, (33.0, 36.6, y - 0.6, y + 0.6), DC, 0.91, (34.775, y), (0, 0)))
# pills of the four power tags grow 1.19x about their centres
for nm, cx in (('+5V', 48.20), ('GND', 52.16), ('GND2', 56.12), ('+12V', 60.08)):
    SPEC.append((nm + ' tag pill', (cx - 1.7, cx + 1.7, 66.6, 68.5), ('D',), None, (cx, 67.55), (0, 0), (1.17, 0.94)))
REMOVE = [('5V 1A dot', (64.5, 64.8, 69.6, 69.9), ('D',))]


def run(src, dst, report=None):
    s = Silk(open(src).read())
    groups = {}
    taken = set()
    for e in SPEC:
        name, box, pols, h, anchor, (dx, dy) = e[:6]
        k = e[6] if len(e) > 6 else (T / h if h else 1.0)
        ps = [p for p in s.select(box, pols=pols) if id(p) not in taken]
        assert ps, name
        for p in ps:
            taken.add(id(p))
        ax, ay = anchor if anchor else (0, 0)
        kx, ky = k if isinstance(k, tuple) else (k, k)
        s.transform(ps, lambda x, y, kx=kx, ky=ky, ax=ax, ay=ay, dx=dx, dy=dy: (ax + (x - ax) * kx + dx, ay + (y - ay) * ky + dy))
        groups[name] = ps
    # curved "PICK A SOUND": each letter grows about its own centre (1.04 -> 1.1 mm)
    # and moves out from the dial centre so its inner edge stays put
    import math
    arc = [p for p in s.select((55.0, 58.5, 35.0, 49.5), pols=('D', 'C')) if id(p) not in taken]
    letters = [p for p in arc if p['pol'] == 'D']
    k = 1.06
    for L in letters:
        bx = L['bbox']
        members = [L] + [c for c in arc if c['pol'] == 'C' and bx[0] <= c['bbox'][0] and c['bbox'][1] <= bx[1]
                         and bx[2] <= c['bbox'][2] and c['bbox'][3] <= bx[3]]
        cx, cy = (bx[0] + bx[1]) / 2, (bx[2] + bx[3]) / 2
        a = math.atan2(cy - 42.0, cx - 48.2)
        push = (k - 1) * 1.04 / 2
        s.transform(members, lambda x, y, cx=cx, cy=cy, a=a: (cx + (x - cx) * k + push * math.cos(a),
                                                                 cy + (y - cy) * k + push * math.sin(a)))
    groups['PICK A SOUND'] = letters + [c for c in arc if c['pol'] == 'C']
    removed = []
    for name, box, pols in REMOVE:
        ps = s.select(box, pols=pols)
        assert len(ps) == 1, (name, len(ps))
        p = ps[0]
        for i in range(p['start'], p['end'] + 1):
            s.lines[i] = None
        removed.append(name)
    open(dst, 'w').write('\n'.join(l for l in s.lines if l is not None))
    return s, groups


if __name__ == '__main__':
    s, g = run(sys.argv[1], sys.argv[2])
    for k, v in g.items():
        v = [p['bbox'] for p in v]
        b = (min(a[0] for a in v), max(a[1] for a in v), min(a[2] for a in v), max(a[3] for a in v))
        print('%-16s %3d prims  x %.2f-%.2f  y %.2f-%.2f' % (k, len(v), *b))
