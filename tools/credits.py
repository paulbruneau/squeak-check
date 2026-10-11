"""Rearrange the header block under the title into two stacks:
  left:  By Ethical Paul / paul@ethicalpaul.com
  right: CHEAP SQUEAK DELUXE / SOUNDS GOOD / TURBO CHEAP SQUEAK  (bigger, left-aligned)
Starts from the silkscreen that still has the original one-line subtitle.
usage: credits.py IN_SILK OUT_SILK  (the email is added afterwards by add_email.py)"""
import sys
from silkedit import Silk

src, dst = sys.argv[1], sys.argv[2]
s = Silk(open(src).read())

# --- layout (Gerber mm, Y up)
LIST_CAP = 1.30
LIST_RIGHT = 43.80          # widest line ends here (clear of the F1 label at x 44.16)
LIST_BASES = (71.15, 69.20, 67.25)
CREDIT_BASE = 71.15         # "By Ethical Paul" baseline (cap tops line up with the list)

# --- the original subtitle glyphs
ps = s.select((9.0, 46.0, 70.2, 72.0), pols=('D', 'C'))
D = sorted([p for p in ps if p['pol'] == 'D'], key=lambda p: p['bbox'][0])
C = [p for p in ps if p['pol'] == 'C']
assert len(D) == 40, len(D)
SRC_BASE, SRC_CAP = 70.603, 0.994


def counters(g):
    b = g['bbox']
    return [c for c in C if b[0] <= c['bbox'][0] and c['bbox'][1] <= b[1] and b[2] <= c['bbox'][2] and c['bbox'][3] <= b[3]]


def pts(p):
    return [s.xy(i)[:2] for i in p['idx']]


k = LIST_CAP / SRC_CAP
words = {'CHEAP': D[0:5], 'SQUEAK': D[5:11], 'DELUXE': D[11:17], 'SOUNDS': D[18:24], 'GOOD': D[24:28],
         'TURBO': [D[34], D[7], D[39], D[29], D[19]]}
LETTER_GAP, WORD_GAP = 0.18, 0.52      # at the original size


def word_layout(name):
    """[(glyph, x offset of its left edge from the word start)] at original size, and width."""
    gs = words[name]
    if name == 'TURBO':                # letters taken from different words: space them evenly
        out, x = [], 0.0
        for g in gs:
            out.append((g, x)); x += g['bbox'][1] - g['bbox'][0] + LETTER_GAP
        return out, x - LETTER_GAP
    x0 = gs[0]['bbox'][0]
    return [(g, g['bbox'][0] - x0) for g in gs], gs[-1]['bbox'][1] - x0


lines = [['CHEAP', 'SQUEAK', 'DELUXE'], ['SOUNDS', 'GOOD'], ['TURBO', 'CHEAP', 'SQUEAK']]
widths = []
for ln in lines:
    widths.append(sum(word_layout(w)[1] for w in ln) + WORD_GAP * (len(ln) - 1))
X_LEFT = LIST_RIGHT - max(widths) * k

out = []


def emit(points, pol, f):
    out.append('%LP' + pol + '*%')
    out.append('G36*')
    for i, (x, y) in enumerate(points):
        nx, ny = f(x, y)
        out.append('X%dY%dD0%d*' % (round(nx * 1e6), round(ny * 1e6), 2 if i == 0 else 1))
    out.append('G37*')


for ln, base in zip(lines, LIST_BASES):
    cur = 0.0                                  # original-size offset along the line
    for w in ln:
        lay, wd = word_layout(w)
        for g, off in lay:
            gx0 = g['bbox'][0]
            f = lambda x, y, gx0=gx0, off=off, cur=cur, base=base: (X_LEFT + (cur + off + (x - gx0)) * k,
                                                                    base + (y - SRC_BASE) * k)
            emit(pts(g), 'D', f)
            for c in counters(g):
                emit(pts(c), 'C', f)
            out.append('%LPD*%')
        cur += wd + WORD_GAP
print('list: x %.2f-%.2f, line widths %s' % (X_LEFT, X_LEFT + max(widths) * k, ['%.2f' % (w * k) for w in widths]))

# delete the old subtitle
dead = set()
for g in D:
    for p in [g] + counters(g):
        dead.update(range(p['start'], p['end'] + 1))

# move "By Ethical Paul" up to the list's first baseline
cred = s.select((9.0, 19.6, 66.8, 69.3), pols=('D', 'C'))
assert len(cred) == 19, len(cred)
dy = CREDIT_BASE - 67.60
s.transform(cred, lambda x, y: (x, y + dy))

L = [l for i, l in enumerate(s.lines) if i not in dead and l is not None]
j = len(L) - 1 - L[::-1].index('M02*')
open(dst, 'w').write('\n'.join(L[:j] + out + L[j:]))
