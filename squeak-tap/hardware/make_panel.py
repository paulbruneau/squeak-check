#!/usr/bin/env python3
"""Squeak Tap Rev A panel generator: DAC adapter + capture board, one order.

By Ethical Paul. Writes Gerbers, Excellon drills, a KiCad 8 PCB and pad data to
out/. Coordinates are panel millimetres, KiCad style (origin top-left, Y down);
Gerbers use Y up (gerber_y = PANEL_H - y).

Board 1 (DAC adapter) sits at the left, Board 2 (capture board) at the right,
with a 2 mm routed gap between them bridged by three mouse-bite tabs, laid out to
JLCPCB's mouse-bite guide (0.6 mm holes, 0.36 mm webs, 6 holes per tab edge).
"""
import math, os, uuid, zipfile
import numpy as np
from PIL import Image, ImageDraw
import cv2
from scipy import ndimage as ndi
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
FONT = os.path.join(HERE, 'fonts', 'BarlowCondensed-SemiBold.ttf')
NAME = 'SqueakTap_RevA'

P = 2.54
W1, H1 = 34.0, 37.0            # Board 1, DAC adapter
GAP = 2.0                      # routed gap between the boards (JLCPCB: 1.6-2 mm)
B2X = W1 + GAP                 # Board 2 x offset
W2, H2 = 55.0, 60.0            # Board 2, capture board
PANEL_W, PANEL_H = B2X + W2, max(H1, H2)
PERF_D = 0.6                   # mouse-bite hole diameter (non-plated)
PERF_PITCH = 0.96              # hole centre spacing: 0.36 mm webs (JLCPCB: 0.35-0.4 mm)
PERF_N = 6                     # holes per tab edge (JLCPCB: 5-8)
TAB_W = 6.0                    # tab width along the edge
TABS = [(3.0, 3.0 + TAB_W), (15.5, 15.5 + TAB_W), (28.0, 28.0 + TAB_W)]   # tab y ranges

pads, tracks, silk_f, silk_b, texts = [], [], [], [], []


def pad(ref, num, x, y, net, drill=1.0, size=1.7, shape='circle', plated=True):
    pads.append(dict(ref=ref, num=str(num), x=round(x, 4), y=round(y, 4), net=net, drill=drill,
                     size=size, shape=shape, plated=plated))


def trk(layer, net, pts, w=0.25):
    tracks.append(dict(layer=layer, net=net, w=w, pts=[(round(a, 4), round(b, 4)) for a, b in pts]))


def sline(pts, w=0.15, layer='F'):
    (silk_f if layer == 'F' else silk_b).append(('line', w, pts))


def srect(x0, y0, x1, y1, w=0.15, layer='F'):
    sline([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], w, layer)


def stext(s, x, y, h, anchor='c', layer='F', rot=0):
    texts.append(dict(s=s, x=x, y=y, h=h, anchor=anchor, layer=layer, rot=rot))


# ============================================================ Board 1 ==
# DAC adapter. P1 = pin strips into the CSD U10 socket (bottom side),
# X1 = machined socket for the AD7533 (top side), J2 = ribbon header.
yr = [4.5 + i * P for i in range(8)]          # DIP rows, pin 1/16 at yr[0]
P1L, P1R = 6.84, 6.84 + 7.62
X1L, X1R = P1L + 12.7, P1R + 12.7
JA, JB = 29.5, 29.5 + P                       # J2 rows (odd, even)
JC = [8.11 + i * P for i in range(8)]         # J2 columns

U10 = {1: 'ADP_REF', 2: 'ADP_OUT2', 3: 'ADP_GND', 4: 'ADP_D9', 5: 'ADP_D8', 6: 'ADP_D7', 7: 'ADP_D6',
       8: 'ADP_D5', 9: 'ADP_D4', 10: 'ADP_D3', 11: 'ADP_D2', 12: 'ADP_D1', 13: 'ADP_D0', 14: 'ADP_12V',
       15: 'ADP_VOUT', 16: 'ADP_RFB'}


def dip16_xy(n, xl, xr):
    return (xl, yr[n - 1]) if n <= 8 else (xr, yr[16 - n])


for n in range(1, 17):
    x, y = dip16_xy(n, P1L, P1R)
    pad('P1', n, x, y, U10[n], drill=1.0, size=1.6, shape='rect' if n == 1 else 'circle')
    x, y = dip16_xy(n, X1L, X1R)
    pad('X1', n, x, y, U10[n], drill=0.8, size=1.6, shape='rect' if n == 1 else 'circle')

J2NET = {1: 'ADP_D6', 2: 'ADP_D5', 3: 'ADP_D7', 5: 'ADP_D8', 7: 'ADP_D9', 9: 'ADP_D0', 11: 'ADP_D1',
         13: 'ADP_D2', 15: 'ADP_D3', 16: 'ADP_D4'}
for c in range(8):
    for row, num in ((JA, 2 * c + 1), (JB, 2 * c + 2)):
        pad('J2', num, JC[c], row, J2NET.get(num, 'ADP_GND'), drill=1.0, size=1.7,
            shape='rect' if num == 1 else 'circle')

# Pass-through, pins 1-8 on F (thread between P1's right-row pads),
# pins 9-16 on B (thread between X1's left-row pads).
for n in range(1, 9):
    y = yr[n - 1]
    trk('F', U10[n], [(P1L, y), (11.4, y), (12.67, y - 1.27), (16.25, y - 1.27), (17.52, y), (X1L, y)])
for k in range(8):
    y = yr[k]
    trk('B', U10[16 - k], [(P1R, y), (16.25, y), (17.52, y - 1.27), (21.56, y - 1.27), (22.83, y), (X1R, y)])

# Data taps. D5-D9 from P1's left row on B, D0-D4 from X1's right row on F.
trk('B', 'ADP_D5', [(P1L, yr[7]), (P1L, 23.3), (6.7, 23.44), (6.7, JB), (JC[0], JB)])
trk('B', 'ADP_D6', [(P1L, yr[6]), (8.6, yr[6]), (8.6, 26.0), (JC[0], 26.49), (JC[0], JA)])
trk('B', 'ADP_D7', [(P1L, yr[5]), (9.4, yr[5]), (9.4, 25.6), (JC[1], 26.85), (JC[1], JA)])
trk('B', 'ADP_D8', [(P1L, yr[4]), (10.2, yr[4]), (10.2, 24.8), (JC[2], 27.79), (JC[2], JA)])
trk('B', 'ADP_D9', [(P1L, yr[3]), (11.0, yr[3]), (11.0, 24.0), (JC[3], 28.73), (JC[3], JA)])
trk('F', 'ADP_D0', [(X1R, yr[3]), (23.0, yr[3]), (23.0, 24.0), (JC[4], 28.73), (JC[4], JA)])
trk('F', 'ADP_D1', [(X1R, yr[4]), (23.8, yr[4]), (23.8, 24.8), (JC[5], 27.79), (JC[5], JA)])
trk('F', 'ADP_D2', [(X1R, yr[5]), (24.6, yr[5]), (24.6, 25.6), (JC[6], 26.85), (JC[6], JA)])
trk('F', 'ADP_D3', [(X1R, yr[6]), (25.4, yr[6]), (25.4, 26.0), (JC[7], 26.49), (JC[7], JA)])
trk('F', 'ADP_D4', [(X1R, yr[7]), (X1R, 23.3), (27.3, 23.44), (27.3, JB), (JC[7], JB)])
# Ground: P1 pin 3 to the six J2 ground pins.
trk('B', 'ADP_GND', [(P1L, yr[2]), (4.5, yr[2]), (4.5, 33.7), (JC[6], 33.7)], w=0.5)
for c in range(1, 7):
    trk('B', 'ADP_GND', [(JC[c], 33.7), (JC[c], JB)], w=0.5)

# Board 1 silkscreen
stext('SQUEAK TAP  DAC ADAPTER', W1 / 2, 1.75, 1.2)
srect(X1L - 1.35, yr[0] - 1.6, X1R + 1.35, yr[7] + 1.6)               # X1 socket
sline([(X1L + 2.3, yr[0] - 1.6), (X1L + 3.81, yr[0] - 0.6), (X1R - 2.3, yr[0] - 1.6)])   # notch
stext('X1', (X1L + X1R) / 2, yr[2] + 0.1, 1.2)
stext('DAC', (X1L + X1R) / 2, yr[3] + 0.6, 1.2)
stext('AD7533', (X1L + X1R) / 2, yr[4] + 1.1, 1.0)
stext('P1', (P1L + P1R) / 2, yr[0] + 0.1, 1.2)
srect(3.03, (JA + JB) / 2 - 4.43, 30.97, (JA + JB) / 2 + 4.43)         # J2 shroud
sline([(14.0, (JA + JB) / 2 - 4.43), (14.0, (JA + JB) / 2 - 3.4), (20.0, (JA + JB) / 2 - 3.4), (20.0, (JA + JB) / 2 - 4.43)])
for x, y in ((P1L - 1.55, yr[0] - 1.5), (X1L - 1.55, yr[0] - 1.5), (JC[0] - 1.9, JA - 1.3)):
    sline([(x, y), (x + 0.9, y), (x, y + 0.9), (x, y)], w=0.2)        # pin-1 triangles
# bottom side (text is mirrored at output)
srect(P1L - 1.3, yr[0] - 1.6, P1R + 1.3, yr[7] + 1.6, layer='B')
stext('P1', (P1L + P1R) / 2, yr[3], 1.4, layer='B')
stext('TO CSD', (P1L + P1R) / 2, yr[4] + 0.4, 1.0, layer='B')
stext('U10', (P1L + P1R) / 2, yr[5] + 0.4, 1.0, layer='B')
stext('SQUEAK TAP  DAC ADAPTER', 32.0, 13.4, 1.2, layer='B', rot=90)
stext('By Ethical Paul  REV A', 29.9, 13.4, 1.2, layer='B', rot=90)
stext('J2  TO CAPTURE BOARD', W1 / 2, 25.0, 1.0, layer='B')

# ============================================================ Board 2 ==
ox = B2X
s = lambda k: 6.45 + k * P                    # signal row k
J1I, J1O = ox + 7.54, ox + 5.0                # J1 odd (inner) / even (outer) columns
RNX = ox + 14.0
U1L, U1R = ox + 20.0, ox + 27.62
CX = ox + 30.6
PL, PR = ox + 34.0, ox + 51.78

J1NET = {1: 'D6', 2: 'D5', 3: 'D7', 5: 'D8', 7: 'D9', 9: 'D0', 11: 'D1', 13: 'D2', 15: 'D3', 16: 'D4'}
for r in range(1, 9):
    for num, x in ((2 * r - 1, J1I), (2 * r, J1O)):
        pad('J1', num, x, s(r), J1NET.get(num, 'GND'), drill=1.0, size=1.7,
            shape='rect' if num == 1 else 'circle')

RNNET = ['GND', 'D5', 'D6', 'D7', 'D8', 'D9', 'D0', 'D1', 'D2', 'D3', 'D4']
for p_ in range(1, 12):
    pad('RN1', p_, RNX, s(p_ - 2), RNNET[p_ - 1], drill=0.8, size=1.6, shape='rect' if p_ == 1 else 'circle')

U1NET = {1: '+3V3', 2: 'D5', 3: 'D6', 4: 'D7', 5: 'D8', 6: 'D9', 7: 'D0', 8: 'D1', 9: 'D2', 10: 'GND',
         11: 'GP9', 12: 'GP8', 13: 'GP7', 14: 'GP6', 15: 'GP5', 16: 'GP4', 17: 'GP3', 18: 'GP2', 19: 'GND', 20: '+3V3'}
U2NET = {1: '+3V3', 2: 'D3', 3: 'D4', 4: 'GND', 5: 'GND', 6: 'GND', 7: 'GND', 8: 'GND', 9: 'GND', 10: 'GND',
         11: '', 12: '', 13: '', 14: '', 15: '', 16: '', 17: 'GP11', 18: 'GP10', 19: 'GND', 20: '+3V3'}
for ref, top, nets in (('U1', -1, U1NET), ('U2', 10, U2NET)):
    for n in range(1, 21):
        x, y = (U1L, s(top + n - 1)) if n <= 10 else (U1R, s(top + 20 - n))
        pad(ref, n, x, y, nets[n], drill=0.8, size=1.6, shape='rect' if n == 1 else 'circle')

pad('C1', 1, CX, s(-1), '+3V3', drill=0.8, size=1.6, shape='rect')
pad('C1', 2, CX, s(0), 'GND', drill=0.8, size=1.6)
pad('C2', 1, CX, s(10), '+3V3', drill=0.8, size=1.6, shape='rect')
pad('C2', 2, CX, s(9), 'GND', drill=0.8, size=1.6)

PICO = {3: 'GND', 4: 'GP2', 5: 'GP3', 6: 'GP4', 7: 'GP5', 8: 'GND', 9: 'GP6', 10: 'GP7', 11: 'GP8', 12: 'GP9',
        13: 'GND', 14: 'GP10', 15: 'GP11', 16: 'MARK', 18: 'GND', 23: 'GND', 28: 'GND', 36: '+3V3', 38: 'GND'}
for n in range(1, 41):
    x, y = (PL, s(n - 3)) if n <= 20 else (PR, s(38 - n))
    pad('A1', n, x, y, PICO.get(n, ''), drill=1.0, size=1.7, shape='rect' if n == 1 else 'circle')

SWX, SWY = ox + 39.75, 53.25
pad('SW1', 1, SWX, SWY, 'MARK', drill=1.1, size=2.0)
pad('SW1', 2, SWX + 6.5, SWY, '', drill=1.1, size=2.0)
pad('SW1', 3, SWX, SWY + 4.5, '', drill=1.1, size=2.0)
pad('SW1', 4, SWX + 6.5, SWY + 4.5, 'GND', drill=1.1, size=2.0)

for i, (hx, hy) in enumerate(((ox + 3.5, 56.5), (ox + 51.5, 56.5))):
    pad('H%d' % (i + 1), '', hx, hy, '', drill=3.2, size=3.2, plated=False)

# Board 2 signal routing, all on F except the 3V3 feed and MARK (B).
trk('F', 'D5', [(J1O, s(1)), (J1O, s(0) + 1.27), (J1O + 1.27, s(0)), (U1L, s(0))])
for num, k in ((1, 1), (3, 2), (5, 3), (7, 4), (9, 5), (11, 6), (13, 7)):
    trk('F', J1NET[num], [(J1I, s(k)), (U1L, s(k))])
trk('F', 'D3', [(J1I, s(8)), (ox + 17.0, s(8)), (ox + 17.0, s(11)), (U1L, s(11))])
trk('F', 'D4', [(J1O, s(8)), (J1O, s(9) - 1.27), (J1O + 1.27, s(9)), (ox + 16.2, s(9)), (ox + 16.2, s(12)), (U1L, s(12))])
for k, gp in ((1, 'GP2'), (2, 'GP3'), (3, 'GP4'), (4, 'GP5')):
    trk('F', gp, [(U1R, s(k)), (PL, s(k))])
for k, gp in ((5, 'GP6'), (6, 'GP7'), (7, 'GP8'), (8, 'GP9')):
    trk('F', gp, [(U1R, s(k)), (ox + 29.8, s(k)), (ox + 32.34, s(k + 1)), (PL, s(k + 1))])
for k, gp in ((12, 'GP10'), (13, 'GP11')):
    trk('F', gp, [(U1R, s(k)), (ox + 29.8, s(k)), (ox + 32.34, s(k - 1)), (PL, s(k - 1))])
# 3V3: Pico pin 36 -> C1 -> U1 pins 20 and 1; -> C2 -> U2 pins 20 and 1.
trk('B', '+3V3', [(PR, s(2)), (ox + 40.0, s(2)), (ox + 40.0, s(-1)), (ox + 38.73, s(-1) - 1.27),
                  (ox + 31.87, s(-1) - 1.27), (CX, s(-1))], w=0.3)
trk('B', '+3V3', [(ox + 40.0, s(2)), (ox + 40.0, s(9)), (ox + 38.73, s(9) + 1.27),
                  (ox + 31.87, s(9) + 1.27), (CX, s(10))], w=0.3)
trk('F', '+3V3', [(CX, s(-1)), (U1L, s(-1))], w=0.3)
trk('F', '+3V3', [(CX, s(10)), (U1L, s(10))], w=0.3)
trk('B', 'MARK', [(PL, s(13)), (ox + 38.0, s(13)), (ox + 38.0, 51.5), (SWX, SWY)])

# Board 2 silkscreen
srect(J1O - 3.16, (s(1) + s(8)) / 2 - 13.97, J1I + 3.16, (s(1) + s(8)) / 2 + 13.97)   # J1 shroud
sline([(J1I + 3.16, (s(1) + s(8)) / 2 - 3.0), (J1I + 2.1, (s(1) + s(8)) / 2 - 3.0),
       (J1I + 2.1, (s(1) + s(8)) / 2 + 3.0), (J1I + 3.16, (s(1) + s(8)) / 2 + 3.0)])        # key
stext('J1', ox + 3.2, 1.75, 1.2)
stext('FROM ADAPTER', ox + 9.0, 1.75, 1.0, anchor='l')
srect(RNX - 1.3, s(-1) - 1.4, RNX + 1.3, s(9) + 1.4)
stext('RN1 100K', RNX, s(9) + 2.6, 1.0)
for ref, top in (('U1', -1), ('U2', 10)):
    y0, y1 = s(top) - 1.6, s(top + 9) + 1.6
    srect(U1L - 1.35, y0, U1R + 1.35, y1)
    sline([(U1L + 2.3, y0), (U1L + 3.81, y0 + 1.0), (U1R - 2.3, y0)])
    stext(ref, (U1L + U1R) / 2, s(top + 3), 1.4)
    stext('74LVC245', (U1L + U1R) / 2, s(top + 5), 1.0)
stext('C1', CX, 1.3, 1.0)
stext('C2', CX, s(10) + 2.1, 1.0)
srect(PL - 1.61, 0.15, PR + 1.61, 51.0)                                 # Pico outline
stext('PICO 2', (PL + PR) / 2, 20.0, 2.2)
stext('USB', (PL + PR) / 2, 4.2, 1.4)
sline([((PL + PR) / 2 - 1.2, 2.7), ((PL + PR) / 2, 1.5), ((PL + PR) / 2 + 1.2, 2.7)], w=0.2)
stext('ON HEADERS', (PL + PR) / 2, 24.0, 1.1)
sline([(SWX + 1.4, SWY - 0.75), (SWX + 5.1, SWY - 0.75)])
sline([(SWX + 1.4, SWY + 5.25), (SWX + 5.1, SWY + 5.25)])
sline([(SWX + 3.25 + 1.6 * math.cos(a / 24 * 2 * math.pi), SWY + 2.25 + 1.6 * math.sin(a / 24 * 2 * math.pi)) for a in range(25)])
stext('MARK', ox + 34.5, SWY + 2.25, 1.5)
for x, y in ((J1I + 1.3, s(1) - 1.5), (RNX - 2.6, s(-1) - 0.45), (U1L - 1.55, s(-1) - 1.5),
             (U1L - 1.55, s(10) - 1.5), (PL - 1.0, s(-2) + 1.2)):
    sline([(x, y), (x + 0.9, y), (x, y + 0.9), (x, y)], w=0.2)
stext('SQUEAK TAP', ox + 8.4, 37.5, 2.0)
stext('CAPTURE BOARD', ox + 8.4, 40.3, 1.15)
stext('By Ethical Paul', ox + 8.4, 44.0, 1.5)
stext('REV A', ox + 8.4, 46.8, 1.1)
stext('BITS: D5-D9 D0-D4', ox + 8.4, 49.6, 0.9)
stext('SQUEAK TAP  CAPTURE BOARD', ox + 9.6, 37.5, 1.2, layer='B')
stext('By Ethical Paul', ox + 9.6, 40.3, 1.3, layer='B')
stext('REV A', ox + 9.6, 42.9, 1.0, layer='B')

# ================================================================ outline ==
outer = [(0, 0), (W1, 0), (W1, TABS[0][0]), (B2X, TABS[0][0]), (B2X, 0), (PANEL_W, 0), (PANEL_W, H2),
         (B2X, H2), (B2X, TABS[-1][1]), (W1, TABS[-1][1]), (W1, H1), (0, H1), (0, 0)]
slots = [[(W1, a[1]), (B2X, a[1]), (B2X, b[0]), (W1, b[0]), (W1, a[1])] for a, b in zip(TABS, TABS[1:])]
# Each tab: a row of holes along each board's edge, centred 0.15 mm inside the
# board so the snapped nubs stay within the outline.
bites = []
for y0, y1 in TABS:
    first = (y0 + y1) / 2 - (PERF_N - 1) * PERF_PITCH / 2
    for i in range(PERF_N):
        bites += [(W1 - 0.15, first + i * PERF_PITCH), (B2X + 0.15, first + i * PERF_PITCH)]

# ============================================================== copper pour ==
PPM = 40
PW, PH = int(PANEL_W * PPM), int(PANEL_H * PPM)


def blank():
    return Image.new('1', (PW, PH), 0)


def draw_pad(dr, p, grow=0.0, fill=1):
    x, y = p['x'] * PPM, p['y'] * PPM
    r = (p['size'] / 2 + grow) * PPM
    if p['shape'] == 'rect':
        dr.rectangle([x - r, y - r, x + r, y + r], fill=fill)
    else:
        dr.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def draw_trk(dr, t, grow=0.0, fill=1):
    w = (t['w'] + 2 * grow) * PPM
    pts = [(a * PPM, b * PPM) for a, b in t['pts']]
    dr.line(pts, fill=fill, width=max(1, int(round(w))))
    for x, y in pts:
        dr.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=fill)


CLR, TGAP, SPOKE, EDGE = 0.35, 0.35, 0.5, 0.5
EDGE_L = 1.0                   # pour keeps further back from the perforated edge
allowed = blank()
ImageDraw.Draw(allowed).rectangle([(B2X + EDGE_L) * PPM, EDGE * PPM, (PANEL_W - EDGE) * PPM, (H2 - EDGE) * PPM], fill=1)
keep_other, keep_all, spokes, gnd_cu = blank(), blank(), blank(), blank()
d_o, d_a, d_s, d_g = (ImageDraw.Draw(i) for i in (keep_other, keep_all, spokes, gnd_cu))
for p in pads:
    if p['x'] < B2X:
        continue
    if not p['plated']:
        r = (p['drill'] / 2 + 0.5) * PPM
        for d in (d_o, d_a):
            d.ellipse([p['x'] * PPM - r, p['y'] * PPM - r, p['x'] * PPM + r, p['y'] * PPM + r], fill=1)
        continue
    if p['net'] == 'GND':
        draw_pad(d_a, p, TGAP)
        draw_pad(d_g, p)
        L = (p['size'] / 2 + TGAP + 0.6) * PPM
        x, y, h = p['x'] * PPM, p['y'] * PPM, SPOKE / 2 * PPM
        d_s.rectangle([x - L, y - h, x + L, y + h], fill=1)
        d_s.rectangle([x - h, y - L, x + h, y + L], fill=1)
    else:
        draw_pad(d_o, p, CLR)
        draw_pad(d_a, p, CLR)
for t in tracks:
    if t['layer'] == 'B' and t['pts'][0][0] > B2X and t['net'] != 'GND':
        draw_trk(d_o, t, CLR)
        draw_trk(d_a, t, CLR)
A, KO, KA, SP, G = (np.array(i, bool) for i in (allowed, keep_other, keep_all, spokes, gnd_cu))
pour = A & ~KA | (SP & A & ~KO)
r = int(round(0.22 * PPM))
yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
pour = ndi.binary_opening(pour, structure=(xx ** 2 + yy ** 2) <= r * r)
lab, n = ndi.label(pour | G, structure=np.ones((3, 3)))
keep_ids = set(np.unique(lab[G])) - {0}
pour = pour & np.isin(lab, list(keep_ids))
contours, hier = cv2.findContours(pour.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
pour_regions = []          # (is_hole, [(x, y) mm])
for c, h in zip(contours, hier[0]):
    c = cv2.approxPolyDP(c, 0.6, True)
    if len(c) < 3:
        continue
    pts = [((pt[0][0] + 0.5) / PPM, (pt[0][1] + 0.5) / PPM) for pt in c]
    pour_regions.append((h[3] != -1, pts))
pour_outline = [(B2X + EDGE_L, EDGE), (PANEL_W - EDGE, EDGE), (PANEL_W - EDGE, H2 - EDGE), (B2X + EDGE_L, H2 - EDGE)]

# =============================================================== text ==
FP = FontProperties(fname=FONT)


def text_rings(t):
    tp = TextPath((0, 0), t['s'], size=1.0, prop=FP)
    sc = t['h'] / 0.7                                   # Barlow cap height = 0.7 em
    ext = tp.get_extents()
    wd = (ext.x1 - ext.x0) * sc
    x0 = {'c': t['x'] - wd / 2, 'l': t['x'], 'r': t['x'] - wd}[t['anchor']] - ext.x0 * sc
    rings = []
    for poly in tp.to_polygons(closed_only=True):
        pts = [(x0 + px * sc, t['y'] + t['h'] / 2 - py * sc) for px, py in poly]
        if t['layer'] == 'B':                           # mirror about the text centre
            cx = x0 + (ext.x0 + ext.x1) / 2 * sc
            pts = [(2 * cx - a, b) for a, b in pts]
        if t.get('rot'):                                # rotate about (x, y); 90 = reads bottom to top from the viewing side
            a = math.radians(t['rot'] if t['layer'] == 'F' else -t['rot'])
            ca, sa = math.cos(a), math.sin(a)
            pts = [(t['x'] + (px - t['x']) * ca + (py - t['y']) * sa, t['y'] - (px - t['x']) * sa + (py - t['y']) * ca) for px, py in pts]
        rings.append(pts)
    # classify holes by nesting depth
    out = []
    for i, rg in enumerate(rings):
        pt = rg[0]
        depth = sum(1 for j, o in enumerate(rings) if j != i and point_in(pt, o))
        out.append((depth % 2 == 1, rg))
    return out


def point_in(pt, poly):
    x, y = pt
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1:
            inside = not inside
    return inside


# ============================================================== gerbers ==
def fmt(v):
    return '%d' % round(v * 1e6)


class Gerber:
    def __init__(self, func):
        self.aps, self.body, self.func = {}, [], func

    def ap(self, kind, a, b=None):
        key = (kind, round(a, 4), round(b, 4) if b else None)
        if key not in self.aps:
            self.aps[key] = 10 + len(self.aps)
        return self.aps[key]

    def use(self, d):
        self.body.append('D%d*' % d)

    def flash(self, d, x, y):
        self.use(d)
        self.body.append('X%sY%sD03*' % (fmt(x), fmt(PANEL_H - y)))

    def path(self, d, pts):
        self.use(d)
        self.body.append('X%sY%sD02*' % (fmt(pts[0][0]), fmt(PANEL_H - pts[0][1])))
        for x, y in pts[1:]:
            self.body.append('X%sY%sD01*' % (fmt(x), fmt(PANEL_H - y)))

    def region(self, pts, clear=False):
        if clear:
            self.body.append('%LPC*%')
        self.body.append('G36*')
        self.body.append('X%sY%sD02*' % (fmt(pts[0][0]), fmt(PANEL_H - pts[0][1])))
        for x, y in pts[1:] + pts[:1]:
            self.body.append('X%sY%sD01*' % (fmt(x), fmt(PANEL_H - y)))
        self.body.append('G37*')
        if clear:
            self.body.append('%LPD*%')

    def text(self):
        h = ['G04 Squeak Tap Rev A, by Ethical Paul*', '%%TF.FileFunction,%s*%%' % self.func,
             '%FSLAX46Y46*%', '%MOMM*%', '%LPD*%', 'G01*', 'G75*']
        for (kind, a, b), d in sorted(self.aps.items(), key=lambda kv: kv[1]):
            h.append('%%ADD%d%s,%s%s*%%' % (d, kind, ('%.4f' % a).rstrip('0').rstrip('.'),
                                            ('X%.4f' % b).rstrip('0').rstrip('.') if b else ''))
        return '\n'.join(h + self.body + ['M02*']) + '\n'


def pad_ap(g, p, grow=0.0):
    sz = p['size'] + 2 * grow
    return g.ap('R', sz, sz) if p['shape'] == 'rect' else g.ap('C', sz)


def copper(layer):
    g = Gerber('Copper,L%d,%s' % ((1, 'Top') if layer == 'F' else (2, 'Bot')))
    if layer == 'B':
        for hole, pts in pour_regions:
            if not hole:
                g.region(pts)
        for hole, pts in pour_regions:
            if hole:
                g.region(pts, clear=True)
    for t in tracks:
        if t['layer'] == layer:
            g.path(g.ap('C', t['w']), t['pts'])
    for p in pads:
        if p['plated']:
            g.flash(pad_ap(g, p), p['x'], p['y'])
    return g.text()


def mask(layer):
    g = Gerber('Soldermask,%s' % ('Top' if layer == 'F' else 'Bot'))
    for p in pads:
        if p['plated']:
            g.flash(pad_ap(g, p, 0.05), p['x'], p['y'])
        else:
            g.flash(g.ap('C', p['drill'] + 0.1), p['x'], p['y'])
    for x, y in bites:
        g.flash(g.ap('C', PERF_D + 0.1), x, y)
    return g.text()


def silk(layer):
    g = Gerber('Legend,%s' % ('Top' if layer == 'F' else 'Bot'))
    for kind, w, pts in (silk_f if layer == 'F' else silk_b):
        g.path(g.ap('C', w), pts)
    rings = [r for t in texts if t['layer'] == layer for r in text_rings(t)]
    for hole, pts in rings:
        if not hole:
            g.region(pts)
    for hole, pts in rings:
        if hole:
            g.region(pts, clear=True)
    return g.text()


def edges():
    g = Gerber('Profile,NP')
    d = g.ap('C', 0.1)
    g.path(d, outer)
    for sl in slots:
        g.path(d, sl)
    return g.text()


def drill(plated):
    holes = [(p['drill'], p['x'], p['y']) for p in pads if p['plated'] == plated]
    if not plated:
        holes += [(PERF_D, x, y) for x, y in bites]
    tools = sorted({h[0] for h in holes})
    out = ['M48', '; Squeak Tap Rev A %s' % ('PTH' if plated else 'NPTH'), 'METRIC']
    out += ['T%dC%.3f' % (i + 1, d) for i, d in enumerate(tools)]
    out += ['%', 'G90', 'G05']
    for i, d in enumerate(tools):
        out.append('T%d' % (i + 1))
        out += ['X%.3fY%.3f' % (x, PANEL_H - y) for dd, x, y in holes if dd == d]
    out.append('M30')
    return '\n'.join(out) + '\n'


# ================================================================ kicad ==
def U():
    return str(uuid.uuid4())


def kicad():
    nets = sorted({p['net'] for p in pads if p['net']} | {t['net'] for t in tracks})
    nid = {n: i + 1 for i, n in enumerate(nets)}
    L = ['(kicad_pcb (version 20240108) (generator "squeak_tap_py") (generator_version "8.0")',
         '  (general (thickness 1.6) (legacy_teardrops no))', '  (paper "A4")',
         '  (title_block (title "Squeak Tap") (rev "A") (company "Ethical Paul"))',
         '  (layers', '    (0 "F.Cu" signal) (31 "B.Cu" signal)',
         '    (32 "B.Adhes" user "B.Adhesive") (33 "F.Adhes" user "F.Adhesive")',
         '    (34 "B.Paste" user) (35 "F.Paste" user) (36 "B.SilkS" user "B.Silkscreen") (37 "F.SilkS" user "F.Silkscreen")',
         '    (38 "B.Mask" user) (39 "F.Mask" user) (40 "Dwgs.User" user "User.Drawings") (41 "Cmts.User" user "User.Comments")',
         '    (44 "Edge.Cuts" user) (45 "Margin" user) (46 "B.CrtYd" user "B.Courtyard") (47 "F.CrtYd" user "F.Courtyard")',
         '    (48 "B.Fab" user) (49 "F.Fab" user))',
         '  (setup (pad_to_mask_clearance 0.05) (pcbplotparams (layerselection 0x00010fc_ffffffff) (outputdirectory "gerbers/")))',
         '  (net 0 "")']
    L += ['  (net %d "%s")' % (nid[n], n) for n in nets]
    refs = []
    for p in pads:
        if p['ref'] not in refs:
            refs.append(p['ref'])
    VAL = {'P1': 'CSD U10 plug (pin strips)', 'X1': 'AD7533 socket', 'J2': 'Ribbon to capture board',
           'J1': 'Ribbon from DAC adapter', 'RN1': '100k bussed x10', 'U1': '74LVC245', 'U2': '74LVC245',
           'C1': '100nF', 'C2': '100nF', 'A1': 'Raspberry Pi Pico 2', 'SW1': 'MARK', 'H1': 'M3', 'H2': 'M3'}
    for ref in refs:
        ps = [p for p in pads if p['ref'] == ref]
        fx, fy = ps[0]['x'], ps[0]['y']
        L.append('  (footprint "SqueakTap:%s" (layer "F.Cu") (uuid "%s") (at %g %g)' % (ref, U(), fx, fy))
        L.append('    (property "Reference" "%s" (at 0 -3 0) (layer "F.Fab") (uuid "%s") (effects (font (size 1 1) (thickness 0.15))))' % (ref, U()))
        L.append('    (property "Value" "%s" (at 0 3 0) (layer "F.Fab") (uuid "%s") (effects (font (size 1 1) (thickness 0.15))))' % (VAL.get(ref, ref), U()))
        L.append('    (attr through_hole)')
        for p in ps:
            dx, dy = round(p['x'] - fx, 4), round(p['y'] - fy, 4)
            if p['plated']:
                net = ' (net %d "%s")' % (nid[p['net']], p['net']) if p['net'] else ''
                L.append('    (pad "%s" thru_hole %s (at %g %g) (size %g %g) (drill %g) (layers "*.Cu" "*.Mask")%s (uuid "%s"))'
                         % (p['num'], p['shape'], dx, dy, p['size'], p['size'], p['drill'], net, U()))
            else:
                L.append('    (pad "" np_thru_hole circle (at %g %g) (size %g %g) (drill %g) (layers "*.Cu" "*.Mask") (uuid "%s"))'
                         % (dx, dy, p['drill'], p['drill'], p['drill'], U()))
        L.append('  )')
    for i, (y0, y1) in enumerate(TABS):
        cx, cy = (W1 + B2X) / 2, (y0 + y1) / 2
        L.append('  (footprint "SqueakTap:TAB%d" (layer "F.Cu") (uuid "%s") (at %g %g)' % (i + 1, U(), cx, cy))
        L.append('    (property "Reference" "TAB%d" (at 0 -4 0) (layer "F.Fab") (uuid "%s") (effects (font (size 1 1) (thickness 0.15))))' % (i + 1, U()))
        L.append('    (property "Value" "mouse bites" (at 0 4 0) (layer "F.Fab") (uuid "%s") (effects (font (size 1 1) (thickness 0.15))))' % U())
        L.append('    (attr exclude_from_pos_files exclude_from_bom)')
        for x, y in bites:
            if y0 <= y <= y1:
                L.append('    (pad "" np_thru_hole circle (at %g %g) (size %g %g) (drill %g) (layers "*.Cu" "*.Mask") (uuid "%s"))'
                         % (round(x - cx, 4), round(y - cy, 4), PERF_D, PERF_D, PERF_D, U()))
        L.append('  )')
    for t in tracks:
        for (x0, y0), (x1, y1) in zip(t['pts'], t['pts'][1:]):
            L.append('  (segment (start %g %g) (end %g %g) (width %g) (layer "%s.Cu") (net %d) (uuid "%s"))'
                     % (x0, y0, x1, y1, t['w'], t['layer'], nid[t['net']], U()))
    for poly in [outer] + slots:
        for (x0, y0), (x1, y1) in zip(poly, poly[1:]):
            L.append('  (gr_line (start %g %g) (end %g %g) (stroke (width 0.1) (type default)) (layer "Edge.Cuts") (uuid "%s"))'
                     % (x0, y0, x1, y1, U()))
    pts = ' '.join('(xy %g %g)' % q for q in pour_outline)
    L.append('  (zone (net %d) (net_name "GND") (layer "B.Cu") (uuid "%s") (hatch edge 0.5) (connect_pads (clearance %g)) '
             '(min_thickness 0.25) (filled_areas_thickness no) (fill yes (thermal_gap %g) (thermal_bridge_width %g)) (polygon (pts %s)))'
             % (nid['GND'], U(), CLR, TGAP, SPOKE, pts))
    L.append('  (gr_text "Silkscreen artwork is in the Gerbers; this file carries copper, drills, outline and nets. Refill the zone (B) after opening." '
             '(at %g %g 0) (layer "Cmts.User") (uuid "%s") (effects (font (size 1.2 1.2) (thickness 0.15))))' % (PANEL_W / 2, PANEL_H + 4, U()))
    L.append(')')
    return '\n'.join(L) + '\n'


# ================================================================ write ==
def main():
    gdir = os.path.join(OUT, 'Gerbers')
    os.makedirs(gdir, exist_ok=True)
    files = {
        '-F_Cu.gtl': copper('F'), '-B_Cu.gbl': copper('B'),
        '-F_Mask.gts': mask('F'), '-B_Mask.gbs': mask('B'),
        '-F_SilkS.gto': silk('F'), '-B_SilkS.gbo': silk('B'),
        '-Edge_Cuts.gm1': edges(), '-PTH.drl': drill(True), '-NPTH.drl': drill(False),
    }
    for f in os.listdir(gdir):
        os.remove(os.path.join(gdir, f))
    for suf, txt in files.items():
        open(os.path.join(gdir, NAME + suf), 'w').write(txt)
    with zipfile.ZipFile(os.path.join(OUT, NAME + '_Gerbers.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        for suf in files:
            z.write(os.path.join(gdir, NAME + suf), NAME + suf)
    kdir = os.path.join(OUT, 'KiCad')
    os.makedirs(kdir, exist_ok=True)
    open(os.path.join(kdir, 'SqueakTap.kicad_pcb'), 'w').write(kicad())
    print('panel %.1f x %.1f mm, %d pads, %d tracks, %d pour regions, %d tabs, %d mouse-bite holes' % (PANEL_W, PANEL_H, len(pads), len(tracks), len(pour_regions), len(TABS), len(bites)))


if __name__ == '__main__':
    main()
