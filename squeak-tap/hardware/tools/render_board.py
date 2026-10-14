"""Render board-top.png / board-bottom.png (website images) from a Gerber set."""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
sys.path.insert(0, os.path.dirname(__file__))
from gerb import *

d, out_dir = sys.argv[1], sys.argv[2]   # optional 3rd arg: 'green'
PPM_OUT, SS = 24, 3
ppm = PPM_OUT * SS
MASK = (20, 21, 24); CU = (44, 46, 52); GOLD = (214, 178, 98); SILK = (244, 241, 232); FR4 = (58, 52, 40)
if len(sys.argv) > 3 and sys.argv[3] == 'green':       # classic green solder mask
    MASK = (22, 92, 50); CU = (52, 138, 74); FR4 = (150, 130, 80)


def L(suffix):
    f = [x for x in os.listdir(d) if x.endswith(suffix)][0]
    return np.array(render(*parse_gerber(open(os.path.join(d, f)).read()), ppm=ppm)) > 127


def holes():
    img = Image.new('L', (int(BOARD_W * ppm), int(BOARD_H * ppm)), 0)
    dr = ImageDraw.Draw(img)
    for suf in ('-PTH.drl', '-NPTH.drl'):
        f = [x for x in os.listdir(d) if x.endswith(suf)][0]
        for h in parse_drill(open(os.path.join(d, f)).read()):
            r = h[0] / 2 * ppm
            if len(h) == 5:
                dr.line([(h[1] * ppm, (BOARD_H - h[2]) * ppm), (h[3] * ppm, (BOARD_H - h[4]) * ppm)], fill=255, width=int(2 * r))
                for x, y in ((h[1], h[2]), (h[3], h[4])):
                    dr.ellipse([x * ppm - r, (BOARD_H - y) * ppm - r, x * ppm + r, (BOARD_H - y) * ppm + r], fill=255)
            else:
                x, y = h[1] * ppm, (BOARD_H - h[2]) * ppm
                dr.ellipse([x - r, y - r, x + r, y + r], fill=255)
    return np.array(img) > 127


outline = L('Edge_Cuts.gm1')
# Board = enclosed areas big enough to be a board; small enclosed areas are routed cutouts (slots).
_lab, _n = ndi.label(~outline)
_outside = set(np.unique(np.concatenate([_lab[0], _lab[-1], _lab[:, 0], _lab[:, -1]]))) - {0}
_sizes = ndi.sum(np.ones_like(_lab), _lab, range(1, _n + 1))
board = outline.copy()
for _i in range(1, _n + 1):
    if _i not in _outside and _sizes[_i - 1] / ppm ** 2 > 50:
        board |= _lab == _i
hl = holes()


def compose(cu, mask, silk):
    H, W = cu.shape
    rgb = np.zeros((H, W, 3), np.uint8)
    rgb[:] = MASK
    rgb[cu] = CU
    rgb[mask & ~cu] = FR4
    rgb[mask & cu] = GOLD
    if silk is not None:
        rgb[silk & ~mask] = SILK
    alpha = (board & ~hl).astype(np.uint8) * 255
    im = Image.fromarray(np.dstack([rgb, alpha]), 'RGBA')
    return im.resize((int(BOARD_W * PPM_OUT), int(BOARD_H * PPM_OUT)), Image.LANCZOS)


top = compose(L('F_Cu.gtl'), L('F_Mask.gts'), L('F_SilkS.gto'))
top.save(os.path.join(out_dir, 'board-top.png'), optimize=True)
bot = compose(L('B_Cu.gbl'), L('B_Mask.gbs'), None).transpose(Image.FLIP_LEFT_RIGHT)
bot.save(os.path.join(out_dir, 'board-bottom.png'), optimize=True)
print('ok', top.size)
