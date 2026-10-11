"""Parse the Squeak Check silkscreen Gerber into primitives that can be moved/scaled in place."""
import re

COORD = re.compile(r'^X(-?\d+)Y(-?\d+)D0([123])\*$')


class Silk:
    def __init__(self, text):
        self.lines = text.split('\n')
        self.prims = []          # dict(kind, pol, idx=[line indices of coords], bbox)
        pol = 'D'
        region = None
        cur_line = None
        for i, l in enumerate(self.lines):
            s = l.strip()
            if s.startswith('%LP'):
                pol = s[3]
                continue
            if s == 'G36*':
                region = dict(kind='region', pol=pol, idx=[], start=i)
                continue
            if s == 'G37*':
                region['end'] = i
                self._add(region)
                region = None
                continue
            m = COORD.match(s)
            if not m:
                if re.match(r'^D\d\d+\*$', s):
                    cur_line = None
                continue
            d = m.group(3)
            if region is not None:
                region['idx'].append(i)
            elif d == '3':
                self._add(dict(kind='flash', pol=pol, idx=[i]))
                cur_line = None
            elif d == '2':
                cur_line = dict(kind='line', pol=pol, idx=[i])
                self._add(cur_line)
            else:
                cur_line['idx'].append(i)
        for p in self.prims:
            self._bbox(p)

    def _add(self, p):
        self.prims.append(p)

    def xy(self, i):
        m = COORD.match(self.lines[i].strip())
        return int(m.group(1)) / 1e6, int(m.group(2)) / 1e6, m.group(3)

    def _bbox(self, p):
        pts = [self.xy(i)[:2] for i in p['idx']]
        xs = [a for a, b in pts]; ys = [b for a, b in pts]
        p['bbox'] = (min(xs), max(xs), min(ys), max(ys))

    def select(self, box, kinds=('region',), pols=('D', 'C')):
        x0, x1, y0, y1 = box
        return [p for p in self.prims if p['kind'] in kinds and p['pol'] in pols
                and x0 <= p['bbox'][0] and p['bbox'][1] <= x1 and y0 <= p['bbox'][2] and p['bbox'][3] <= y1]

    def transform(self, prims, f):
        """f(x, y) -> (x, y) applied to every coordinate of the given primitives."""
        done = set()
        for p in prims:
            for i in p['idx']:
                if i in done:
                    continue
                done.add(i)
                x, y, d = self.xy(i)
                nx, ny = f(x, y)
                self.lines[i] = 'X%dY%dD0%s*' % (round(nx * 1e6), round(ny * 1e6), d)
            self._bbox(p)

    def text(self):
        return '\n'.join(self.lines)


def bbox_of(prims):
    return (min(p['bbox'][0] for p in prims), max(p['bbox'][1] for p in prims),
            min(p['bbox'][2] for p in prims), max(p['bbox'][3] for p in prims))
