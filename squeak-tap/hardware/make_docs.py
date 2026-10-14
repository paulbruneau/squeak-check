#!/usr/bin/env python3
"""Schematic PDF, BOM and ribbon pin map for Squeak Tap Rev A, from the panel netlist.

The schematic is drawn label-style: every pin carries its net name, so it reads
straight against the KiCad netlist (checked: every pad listed here exists with
this net in out/KiCad/SqueakTap.kicad_pcb).
"""
import csv, os, re, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.backends.backend_pdf import PdfPages

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
FP = FontProperties(fname=os.path.join(HERE, 'fonts', 'BarlowCondensed-SemiBold.ttf'))

# ---- netlist from the KiCad file (source of truth for pin -> net)
pcb = open(os.path.join(OUT, 'KiCad', 'SqueakTap.kicad_pcb')).read()
NET = {}
for fm in re.finditer(r'\(footprint "SqueakTap:([^"]+)".*?\n  \)', pcb, re.S):
    for line in fm.group(0).split('\n'):
        pm = re.search(r'\(pad "([^"]*)" thru_hole ', line)
        if pm:
            nm = re.search(r'\(net \d+ "([^"]*)"\)', line)
            NET[(fm.group(1), pm.group(1))] = nm.group(1) if nm else ''


def net(ref, pin):
    n = NET[(ref, str(pin))]
    return n if n else 'NC'


INK, QUIET, ACC = '#1d1d1b', '#6b6a64', '#1f5fa8'


def part(ax, x, y, ref, title, left, right, w=7.0, pitch=1.0):
    """Box with pins. left/right: lists of (pin, name) top to bottom; None = gap."""
    n = max(len(left), len(right))
    h = n * pitch + 0.8
    ax.add_patch(plt.Rectangle((x, y - h), w, h, fill=False, lw=1.2, ec=INK))
    ax.text(x + w / 2, y + 0.45, ref, ha='center', va='bottom', fontproperties=FP, fontsize=11, color=INK)
    ax.text(x + w / 2, y - h - 0.35, title, ha='center', va='top', fontproperties=FP, fontsize=8, color=QUIET)
    for side, pins in (('L', left), ('R', right)):
        for i, pn in enumerate(pins):
            if pn is None:
                continue
            pin, name = pn
            py = y - 0.9 - i * pitch
            if side == 'L':
                ax.plot([x - 1.2, x], [py, py], color=INK, lw=1)
                ax.text(x + 0.25, py, name, ha='left', va='center', fontproperties=FP, fontsize=7.5, color=INK)
                ax.text(x - 0.15, py + 0.12, str(pin), ha='right', va='bottom', fontproperties=FP, fontsize=6, color=QUIET)
                lab = net(ref, pin)
                ax.text(x - 1.35, py, lab, ha='right', va='center', fontproperties=FP, fontsize=7.5,
                        color=QUIET if lab == 'NC' else ACC)
            else:
                ax.plot([x + w, x + w + 1.2], [py, py], color=INK, lw=1)
                ax.text(x + w - 0.25, py, name, ha='right', va='center', fontproperties=FP, fontsize=7.5, color=INK)
                ax.text(x + w + 0.15, py + 0.12, str(pin), ha='left', va='bottom', fontproperties=FP, fontsize=6, color=QUIET)
                lab = net(ref, pin)
                ax.text(x + w + 1.35, py, lab, ha='left', va='center', fontproperties=FP, fontsize=7.5,
                        color=QUIET if lab == 'NC' else ACC)


def sheet(pdf, title, draw):
    fig = plt.figure(figsize=(16.54, 11.69))          # A3 landscape
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 84)
    ax.set_ylim(0, 59.4)
    ax.axis('off')
    ax.add_patch(plt.Rectangle((1, 1), 82, 57.4, fill=False, lw=1, ec=INK))
    ax.text(2.2, 56.6, title, fontproperties=FP, fontsize=17, color=INK, va='top')
    ax.text(81.8, 2.0, 'Squeak Tap  REV A  ·  By Ethical Paul  ·  2026-10-14', ha='right', fontproperties=FP, fontsize=10, color=QUIET)
    ax.text(2.2, 2.0, 'Net names in blue. Labels with the same name are connected. Drawn from the board netlist.',
            fontproperties=FP, fontsize=9, color=QUIET)
    draw(ax)
    pdf.savefig(fig)
    plt.close(fig)


DAC = {1: 'OUT1 (REF)', 2: 'OUT2', 3: 'GND', 4: 'BIT1 MSB', 5: 'BIT2', 6: 'BIT3', 7: 'BIT4', 8: 'BIT5', 9: 'BIT6',
       10: 'BIT7', 11: 'BIT8', 12: 'BIT9', 13: 'BIT10 LSB', 14: 'VDD +12V', 15: 'VREF (AUDIO)', 16: 'RFB'}


def board1(ax):
    left = [(n, DAC[n]) for n in range(1, 9)]
    right = [(n, DAC[n]) for n in range(16, 8, -1)]
    part(ax, 12, 48, 'P1', 'pin strips, plug into CSD U10 socket', left, right, w=8.5, pitch=1.6)
    part(ax, 40, 48, 'X1', 'socket, original AD7533 fits here', left, right, w=8.5, pitch=1.6)
    j2l = [(p, 'pin %d' % p) for p in range(1, 17, 2)]
    j2r = [(p, 'pin %d' % p) for p in range(2, 17, 2)]
    part(ax, 64, 48, 'J2', '2x8 box header, ribbon to capture board', j2l, j2r, w=5, pitch=1.6)
    notes = ['P1 pin n and X1 pin n are joined for all 16 pins: the adapter passes the DAC straight through.',
             'Taps: the 10 data bits (U10 pins 4-13) and ground go to J2. Nothing else is taken from the CSD; no power is used.',
             'CSD U10 wiring (from the A080-91671 schematic): BIT1-BIT8 = PIA U9 PA7-PA0, BIT9 = PB7, BIT10 = PB6.',
             'Midway runs the AD7533 in voltage mode: about 1.7 V from Q2 into OUT1, audio out of VREF (pin 15).']
    for i, s in enumerate(notes):
        ax.text(3, 26 - i * 1.6, s, fontproperties=FP, fontsize=10, color=INK)


def board2(ax):
    j1l = [(p, 'pin %d' % p) for p in range(1, 17, 2)]
    j1r = [(p, 'pin %d' % p) for p in range(2, 17, 2)]
    part(ax, 4, 52.5, 'J1', '2x8 box header, ribbon from adapter', j1l, j1r, w=5, pitch=1.4)
    rn = [(1, 'COMMON')] + [(p, 'R%d' % (p - 1)) for p in range(2, 12)]
    part(ax, 4, 31, 'RN1', '100k x10 bussed SIP (pull-downs)', rn, [], w=5, pitch=1.4)
    u = [(1, 'DIR'), (2, 'A1'), (3, 'A2'), (4, 'A3'), (5, 'A4'), (6, 'A5'), (7, 'A6'), (8, 'A7'), (9, 'A8'), (10, 'GND')]
    ur = [(20, 'VCC'), (19, '/OE'), (18, 'B1'), (17, 'B2'), (16, 'B3'), (15, 'B4'), (14, 'B5'), (13, 'B6'), (12, 'B7'), (11, 'B8')]
    part(ax, 27, 52.5, 'U1', '74LVC245, 5 V in, 3.3 V out', u, ur, w=6, pitch=1.4)
    part(ax, 27, 34.5, 'U2', '74LVC245, 5 V in, 3.3 V out', u, ur, w=6, pitch=1.4)
    pl = [(n, nm) for n, nm in ((1, 'GP0'), (2, 'GP1'), (3, 'GND'), (4, 'GP2'), (5, 'GP3'), (6, 'GP4'), (7, 'GP5'),
                                (8, 'GND'), (9, 'GP6'), (10, 'GP7'), (11, 'GP8'), (12, 'GP9'), (13, 'GND'), (14, 'GP10'),
                                (15, 'GP11'), (16, 'GP12'), (17, 'GP13'), (18, 'GND'), (19, 'GP14'), (20, 'GP15'))]
    pr = [(n, nm) for n, nm in ((40, 'VBUS'), (39, 'VSYS'), (38, 'GND'), (37, '3V3_EN'), (36, '3V3(OUT)'), (35, 'ADC_VREF'),
                                (34, 'GP28'), (33, 'AGND'), (32, 'GP27'), (31, 'GP26'), (30, 'RUN'), (29, 'GP22'), (28, 'GND'),
                                (27, 'GP21'), (26, 'GP20'), (25, 'GP19'), (24, 'GP18'), (23, 'GND'), (22, 'GP17'), (21, 'GP16'))]
    part(ax, 55, 52.5, 'A1', 'Raspberry Pi Pico 2 (or Pico), on headers', pl, pr, w=8, pitch=1.4)
    part(ax, 55, 21, 'C1', '100 nF, at U1', [(1, '+')], [(2, '')], w=3, pitch=1.4)
    part(ax, 55, 16, 'C2', '100 nF, at U2', [(1, '+')], [(2, '')], w=3, pitch=1.4)
    part(ax, 70, 21, 'SW1', 'MARK button, 6 mm tactile', [(1, ''), (3, '')], [(2, ''), (4, '')], w=3, pitch=1.4)
    notes = ['Ribbon bit order: U1 A1-A8 = D5-D9, D0-D2; U2 A1-A2 = D3, D4. Firmware rotates GP2-GP11 back to D0-D9.',
             'MARK: SW1 diagonal pads 1 and 4, so the button works whichever way it is fitted. GP12 uses the Pico pull-up.',
             'U2 A3-A8 tied to GND, B3-B8 unused. Both /OE to GND and DIR to 3V3 (A to B).']
    for i, s in enumerate(notes):
        ax.text(3, 8.2 - i * 1.5, s, fontproperties=FP, fontsize=10, color=INK)


def bom():
    rows = [
        ['Ref', 'Qty', 'Description', 'Manufacturer', 'Mfr Part #', 'Mouser #', 'Notes'],
        ['--- BOARD 1: DAC ADAPTER ---', '', '', '', '', '', ''],
        ['X1', '1', '16-pin machined DIP socket, 0.300" rows', 'Mill-Max', '110-43-316-41-001000', '',
         'Top side. The original AD7533 moves here; notch toward the silk notch'],
        ['P1', '2', '1x8 machined male pin strip, 0.025" PCB end, 0.018" plug end', 'Mill-Max', '350-10-108-00-006000', '',
         'Bottom side, solder from the top. The thin ends plug into the CSD U10 socket. Or cut 8-pin lengths from 350-10-164-00-001000'],
        ['J2', '1', '2x8 shrouded box header, 2.54 mm, vertical', 'Wurth Elektronik', '61201621621', '',
         'Key slot toward the silk notch (the DIP side)'],
        ['--- BOARD 2: CAPTURE BOARD ---', '', '', '', '', '', ''],
        ['J1', '1', '2x8 shrouded box header, 2.54 mm, vertical', 'Wurth Elektronik', '61201621621', '',
         'Key slot toward the silk notch (the RN1 side)'],
        ['RN1', '1', '100 k x10 bussed resistor network, SIP-11', 'Bourns', '4611X-101-104LF', '',
         'Pin 1 (common, dot) toward the top of the board'],
        ['U1, U2', '2', 'Octal bus transceiver, 3.3 V, 5 V tolerant inputs, PDIP-20', 'Texas Instruments', 'SN74LVC245AN',
         '595-SN74LVC245AN', ''],
        ['(U1, U2)', '2', '20-pin DIP socket, 0.300" (optional)', 'any', '', '', ''],
        ['C1, C2', '2', '100 nF X7R ceramic, 2.54 mm leads', 'KEMET', 'C320C104K5R5TA', '', ''],
        ['A1', '1', 'Raspberry Pi Pico 2 (original Pico also works)', 'Raspberry Pi', 'SC1631', '',
         'Mount on headers so C1/C2 fit underneath. Pico 2 H comes with headers'],
        ['(A1)', '2', '1x20 female header, 2.54 mm (Pico socket)', 'any', '', '', 'Plus 2x 1x20 male header if the Pico has none'],
        ['SW1', '1', '6x6 mm THT tactile switch (MARK)', 'Omron', 'B3F-1000', '653-B3F-1000', 'Same switch as Squeak Check'],
        ['H1, H2', '2', 'M3 standoff or rubber foot (optional)', 'any', '', '', ''],
        ['--- CABLE ---', '', '', '', '', '', ''],
        ['', '2', '16-way IDC socket, 2.54 mm, with strain relief', 'any', '', '', 'Crimp both the same way round: pin 1 to pin 1'],
        ['', '1', '16-way 1.27 mm flat ribbon, about 15 cm', 'any', '', '', 'Or one ready-made 16-pin IDC cable'],
    ]
    with open(os.path.join(OUT, 'BOM.csv'), 'w', newline='') as f:
        csv.writer(f).writerows(rows)


def pinmap():
    data = {'D0': 'U10 pin 13 (BIT10, PIA PB6)', 'D1': 'U10 pin 12 (BIT9, PIA PB7)', 'D2': 'U10 pin 11 (BIT8, PIA PA0)',
            'D3': 'U10 pin 10 (BIT7, PIA PA1)', 'D4': 'U10 pin 9 (BIT6, PIA PA2)', 'D5': 'U10 pin 8 (BIT5, PIA PA3)',
            'D6': 'U10 pin 7 (BIT4, PIA PA4)', 'D7': 'U10 pin 6 (BIT3, PIA PA5)', 'D8': 'U10 pin 5 (BIT2, PIA PA6)',
            'D9': 'U10 pin 4 (BIT1, PIA PA7)'}
    gp = {}
    for (ref, pin), n in NET.items():
        if ref == 'A1' and n.startswith('GP'):
            pass
    rows = [['Ribbon pin', 'Signal', 'CSD source', 'Capture board input', 'Pico GPIO']]
    buf = {}
    for (ref, pin), n in NET.items():
        if ref in ('U1', 'U2') and n.startswith('D'):
            out_pin = 20 - int(pin)                  # A(n) pin p -> B(n) pin 20 - p
            buf[n] = (ref, int(pin), NET[(ref, str(out_pin))])
    for p in range(1, 17):
        n = NET[('J1', str(p))]
        if n == 'GND':
            rows.append([p, 'GND', 'U10 pin 3', 'GND', ''])
        else:
            ref, pin, g = buf[n]
            rows.append([p, n, data[n], '%s pin %d' % (ref, pin), g])
    with open(os.path.join(OUT, 'Ribbon_Pin_Map.csv'), 'w', newline='') as f:
        csv.writer(f).writerows(rows)
    return rows


def main():
    with PdfPages(os.path.join(OUT, 'Schematic_RevA.pdf')) as pdf:
        sheet(pdf, 'Squeak Tap  ·  Board 1: DAC adapter', board1)
        sheet(pdf, 'Squeak Tap  ·  Board 2: capture board', board2)
    bom()
    for r in pinmap():
        print(r)


if __name__ == '__main__':
    main()
