"""Build Rev E.6 Gerbers from the Rev E.5 set.

Rev E.6 change: SW1's footprint pin map is turned 180 degrees so the Grayhill
94HBB16T is fitted with the 0 on its dial toward the TOP of the board.
Hole positions are unchanged; the four sound-bit tracks are swapped at the
resistor end:
  SW1 top-left hole     (44.39, 44.54) S1 -> S0   (front)
  SW1 bottom-right hole (52.01, 39.46) S0 -> S1   (back)
  SW1 bottom-left hole  (44.39, 39.46) S3 -> S2   (front)
  SW1 top-right hole    (52.01, 44.54) S2 -> S3   (back)
Silk: "0" replaces the top dial tick and "8" the bottom one; REV E.5 -> E.6.
Coordinates here are Gerber (Y up, mm).
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import routes

src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)


def sub1(text, old, new, label):
    n = text.count(old)
    if n < 1:
        raise SystemExit(f'{label}: pattern not found')
    return text.replace(old, new), n


def path(*pts):
    """Gerber D02 + D01 sequence through pts (mm)."""
    out = ['X%dY%dD02*' % (round(pts[0][0] * 1e6), round(pts[0][1] * 1e6)), 'G01*']
    for x, y in pts[1:]:
        out.append('X%dY%dD01*' % (round(x * 1e6), round(y * 1e6)))
    return '\n'.join(out)


# ---------------------------------------------------------------- copper
# Back: old S0 route started at the S0 node (29.7, 50); it now starts at the S1
# node (29.7, 54), drops down x = 31.6 between the resistor rows and rejoins y = 48.
OLD_B_S0 = ('X29700000Y50000000D02*\nG01*\nX31260660Y48439340D01*\nG03*\n'
            'X32321320Y48000000I1060660J1060660D01*\nG01*\nG01*\nX46700000Y48000000D01*')
NEW_B_S1 = routes.gerber('B_S1')
# Back: old S2 route from the S2 node (29.7, 30) now starts at the S3 node (29.7, 34).
OLD_B_S2 = ('X29700000Y30000000D02*\nG01*\nX31114214Y28585786D01*\nG03*\n'
            'X32528427Y28000000I1414214J1414214D01*\nG01*\nG01*\nX51800000Y28000000D01*')
NEW_B_S3 = routes.gerber('B_S3')
# Front: old S1 route from (29.7, 54) now starts at the S0 node (29.7, 50).
OLD_F_S1 = ('X29700000Y54000000D02*\nG01*\nX31114214Y52585786D01*\nG03*\n'
            'X32528427Y52000000I1414214J1414214D01*\nG01*\nG01*\nX40861573Y52000000D01*')
NEW_F_S0 = routes.gerber('F_S0')
# Front: old S3 route from (29.7, 34) now starts at the S2 node (29.7, 30).
OLD_F_S3 = ('X29700000Y34000000D02*\nG01*\nX31114214Y35414214D01*\nG02*\n'
            'X32528427Y36000000I1414214J-1414214D01*\nG01*\nG01*\nX40068298Y36000000D01*')
NEW_F_S2 = routes.gerber('F_S2')

# ---------------------------------------------------------------- silk glyphs
GLYPHS = {
    '0': ['.####.', '##..##', '##..##', '##..##', '##..##', '##..##', '.####.'],
    '8': ['.####.', '##..##', '##..##', '.####.', '##..##', '##..##', '.####.'],
    # REV-font 6, drawn on the same 0.2 mm grid as the E.5 "5" (7 x 7)
    '6': ['.#####.', '##.....', '######.', '##...##', '##...##', '##...##', '.#####.'],
}


def glyph_regions(ch, x0, ytop, px):
    """Merge each row's runs into rectangles; emit G36 regions."""
    out = []
    rows = GLYPHS[ch]
    for r, row in enumerate(rows):
        y1 = ytop - r * px
        y0 = y1 - px
        c = 0
        while c < len(row):
            if row[c] == '#':
                s = c
                while c < len(row) and row[c] == '#':
                    c += 1
                xa, xb = x0 + s * px, x0 + c * px
                pts = [(xa, y0), (xa, y1), (xb, y1), (xb, y0), (xa, y0)]
                out.append('G36*\n' + '\n'.join('X%dY%dD0%d*' % (round(x * 1e6), round(y * 1e6), 2 if i == 0 else 1)
                                                for i, (x, y) in enumerate(pts)) + '\nG37*')
            else:
                c += 1
    return out


def find_region_block(text, first_vertex):
    i = text.find(first_vertex)
    if i < 0:
        raise SystemExit('region not found: ' + first_vertex)
    a = text.rfind('G36*', 0, i)
    b = text.find('G37*', i) + len('G37*')
    return a, b


for f in sorted(os.listdir(src)):
    t = open(os.path.join(src, f)).read()
    nf = f.replace('RevE5', 'RevE6')
    t = re.sub(r'(G04 [^*]*Squeak Check) Rev E\*', r'\1 Rev E.6*', t)
    t = t.replace('; Squeak Check Rev E -', '; Squeak Check Rev E.6 -')
    if f.endswith('B_Cu.gbl'):
        t, n = sub1(t, OLD_B_S0, NEW_B_S1, 'B S0'); assert n == 2, n   # clearance + track
        t, n = sub1(t, OLD_B_S2, NEW_B_S3, 'B S2'); assert n == 2, n
        # pour keep-out: the strip between the SIRQ track (x 28.03) and the new S1
        # track (x 31.6) would be an unconnected island; clear it.
        k = t.rfind('%LPD*%')
        j = t.rfind('G37*', 0, k) + len('G37*')
        # plus two small ones that would otherwise leave thin pour slivers
        keeps = [(28.5, 50.3, 31.15, 53.3), (31.8, 46.95, 32.75, 47.9), (30.55, 28.9, 31.3, 31.3)]
        reg = ''
        for xa, ya, xb, yb in keeps:
            keep = [(xa, ya), (xa, yb), (xb, yb), (xb, ya), (xa, ya)]
            reg += 'G36*\n' + '\n'.join('X%dY%dD0%d*' % (round(x * 1e6), round(y * 1e6), 2 if i == 0 else 1)
                                          for i, (x, y) in enumerate(keep)) + '\nG37*\n'
        reg = reg.rstrip('\n')
        t = t[:j] + '\n' + reg + t[j:]
    if f.endswith('F_Cu.gtl'):
        t, n = sub1(t, OLD_F_S1, NEW_F_S0, 'F S1'); assert n == 1, n
        t, n = sub1(t, OLD_F_S3, NEW_F_S2, 'F S3'); assert n == 1, n
    if f.endswith('F_SilkS.gto'):
        # REV E.5 -> E.6: drop the "5" region (first vertex 18.2, 21.6), add a "6"
        a, b = find_region_block(t, 'X18200000Y21600000D02*')
        t = t[:a] + t[b:]
        # top and bottom dial ticks become "0" and "8"
        t, n = sub1(t, 'D13*\nX48200000Y48200000D02*\nG01*\nX48200000Y49500000D01*\n', 'D13*\n', 'top tick'); assert n == 1
        t, n = sub1(t, 'X48200000Y35800000D02*\nG01*\nX48200000Y34500000D01*\n', '', 'bottom tick'); assert n == 1
        add = ['%LPD*%']
        add += glyph_regions('6', 18.0, 23.0, 0.2)
        px = 0.24
        add += glyph_regions('0', 48.2 - 3 * px, 48.05 + 7 * px, px)
        add += glyph_regions('8', 48.2 - 3 * px, 34.32 + 7 * px, px)
        k = t.rfind('M02*')
        t = t[:k] + '\n'.join(add) + '\n' + t[k:]
    open(os.path.join(dst, nf), 'w').write(t)
    print('wrote', nf)
