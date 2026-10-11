"""Apply the Rev E.6 SW1 change to the KiCad PCB and schematic (KiCad coords, Y down)."""
import os, re, sys, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import routes

pcb_path, sch_path = sys.argv[1], sys.argv[2]
t = open(pcb_path).read()

t = t.replace('(rev "E.5")', '(rev "E.6")')

# SW1 pads: same holes, pin numbers turned 180 deg so the dial's 0 is at the top.
pad_map = {
    '(pad "2" thru_hole circle (at 0 -0) (size 1.7 1.7) (drill 1) (layers "*.Cu" "*.Mask") (net 18 "S1")':
    '(pad "1" thru_hole circle (at 0 -0) (size 1.7 1.7) (drill 1) (layers "*.Cu" "*.Mask") (net 17 "S0")',
    '(pad "8" thru_hole circle (at 0 5.08) (size 1.7 1.7) (drill 1) (layers "*.Cu" "*.Mask") (net 20 "S3")':
    '(pad "4" thru_hole circle (at 0 5.08) (size 1.7 1.7) (drill 1) (layers "*.Cu" "*.Mask") (net 19 "S2")',
    '(pad "4" thru_hole circle (at 7.62 -0) (size 1.7 1.7) (drill 1) (layers "*.Cu" "*.Mask") (net 19 "S2")':
    '(pad "8" thru_hole circle (at 7.62 -0) (size 1.7 1.7) (drill 1) (layers "*.Cu" "*.Mask") (net 20 "S3")',
    '(pad "1" thru_hole circle (at 7.62 5.08) (size 1.7 1.7) (drill 1) (layers "*.Cu" "*.Mask") (net 17 "S0")':
    '(pad "2" thru_hole circle (at 7.62 5.08) (size 1.7 1.7) (drill 1) (layers "*.Cu" "*.Mask") (net 18 "S1")',
}
for a, b in pad_map.items():
    assert t.count(a) == 1, a
    t = t.replace(a, b)

seg_re = re.compile(r'  \((segment|arc) \(start ([\d.-]+) ([\d.-]+)\)(?: \(mid [\d.-]+ [\d.-]+\))? \(end ([\d.-]+) ([\d.-]+)\) \(width ([\d.]+)\) \(layer "([^"]+)"\) \(net (\d+)\) \(uuid "[^"]+"\)\)\n')

# (layer, old net, starts to delete, new net, new polyline)
plan = [
    ('F.Cu', 18, {(29.7, 26.0), (31.1142, 27.4142), (32.5284, 28.0)}, 17,
     [(29.7, 30.0), (31.7, 28.0), (40.8616, 28.0)]),
    ('F.Cu', 20, {(29.7, 46.0), (31.1142, 44.5858), (32.5284, 44.0)}, 19,
     [(29.7, 50.0), (31.6, 48.1), (31.6, 44.9), (32.5, 44.0), (40.0683, 44.0)]),
    ('B.Cu', 17, {(29.7, 30.0), (31.2607, 31.5607), (32.3213, 32.0)}, 18,
     [(29.7, 26.0), (31.6, 27.9), (31.6, 31.1), (32.5, 32.0), (46.7, 32.0)]),
    ('B.Cu', 19, {(29.7, 50.0), (31.1142, 51.4142), (32.5284, 52.0)}, 20,
     [(29.7, 46.0), (31.6, 47.9), (31.6, 51.1), (32.5, 52.0), (51.8, 52.0)]),
]

out = []
pos = 0
deleted = {i: 0 for i in range(len(plan))}
renet = {i: 0 for i in range(len(plan))}
for m in seg_re.finditer(t):
    out.append(t[pos:m.start()])
    pos = m.end()
    kind, sx, sy, ex, ey, w, layer, net = m.groups()
    sx, sy, net = float(sx), float(sy), int(net)
    line = m.group(0)
    for i, (L, on, dels, nn, poly) in enumerate(plan):
        if layer == L and net == on and round(sx, 2) != 26.36:  # keep the RS-RPD links
            if (round(sx, 4), round(sy, 4)) in dels:
                deleted[i] += 1
                line = ''
            else:
                renet[i] += 1
                line = line.replace('(net %d)' % on, '(net %d)' % nn)
            break
    out.append(line)
out.append(t[pos:])
t = ''.join(out)
print('deleted', deleted, 'renetted', renet)
assert all(v == 3 for v in deleted.values())

new = []
for name, net in (('F_S0', 17), ('F_S2', 19), ('B_S1', 18), ('B_S3', 20)):
    new += routes.kicad(name, net, lambda: str(uuid.uuid4()))
k = t.find('  (zone ')
t = t[:k] + ''.join(new) + t[k:]
open(pcb_path, 'w').write(t)

# ---- schematic: SW1 symbol pins follow the footprint order (1, CL, 4, 8, CR, 2)
s = open(sch_path).read()
s = s.replace('(rev "E.5")', '(rev "E.6")').replace('Schematic_RevE5.pdf', 'Schematic_RevE6.pdf')
old_pins = ['"2"', '"CL"', '"8"', '"4"', '"CR"', '"1"']
new_pins = ['"1"', '"CL"', '"4"', '"8"', '"CR"', '"2"']
blk_a = s.find('(symbol "SW1_1_1"')
blk_b = s.find('\n    )', blk_a)
blk = s[blk_a:blk_b]
lines = blk.split('\n')
pin_lines = [i for i, l in enumerate(lines) if '(pin passive' in l]
assert len(pin_lines) == 6
for i, o, n in zip(pin_lines, old_pins, new_pins):
    l = lines[i]
    assert ('(name %s' % o) in l, l
    lines[i] = l.replace('(name %s' % o, '(name %s' % n).replace('(number %s' % o, '(number %s' % n)
s = s[:blk_a] + '\n'.join(lines) + s[blk_b:]
# net labels at the SW1 pins, top to bottom: S1,+5V,S3,S2,+5V,S0 -> S0,+5V,S2,S3,+5V,S1
lab = {'173.99': ('S1', 'S0'), '179.07': ('S3', 'S2'), '181.61': ('S2', 'S3'), '186.69': ('S0', 'S1')}
for y, (o, n) in lab.items():
    a = '(label "%s" (at 144.78 %s 0)' % (o, y)
    assert s.count(a) == 1, a
    s = s.replace(a, '(label "%s" (at 144.78 %s 0)' % (n, y))
open(sch_path, 'w').write(s)
print('ok')
