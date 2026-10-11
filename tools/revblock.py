"""Scale the REV / size / mounting block up and centre it in the open area
between the SOUND2 row and the J2 labels.  usage: revblock.py IN_SILK OUT_SILK"""
import sys
from silkedit import Silk, bbox_of

K = 1.6
AREA = (1.5, 51.5, 16.2, 28.6)      # free area: board edge .. RESET pads, J2 labels .. SOUND2 row
src, dst = sys.argv[1], sys.argv[2]
s = Silk(open(src).read())
ps = s.select((8.0, 32.0, 16.5, 23.3), kinds=('region', 'line', 'flash'), pols=('D', 'C'))
x0, x1, y0, y1 = bbox_of(ps)
cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
tx, ty = (AREA[0] + AREA[1]) / 2, (AREA[2] + AREA[3]) / 2
s.transform(ps, lambda x, y: (tx + (x - cx) * K, ty + (y - cy) * K))
# the note's stem is a 0.2 mm stroke: draw it with the 0.3 mm aperture so it scales with the rest
stem = [p for p in ps if p['kind'] == 'line']
assert len(stem) == 1
a, b = stem[0]['idx'][0], stem[0]['idx'][-1]
s.lines[a] = 'D13*\n' + s.lines[a]
s.lines[b] = s.lines[b] + '\nD12*'
print('block now x %.2f-%.2f y %.2f-%.2f' % bbox_of(ps))
open(dst, 'w').write('\n'.join(l for l in s.lines if l is not None))
