# Board tools

Python scripts used to make and check Rev E.6 from the Rev E.5 Gerbers. They need Python 3 with numpy, scipy, scikit-image and Pillow; no KiCad.

The original board generator (`design.py`, mentioned on the schematic) isn't in the repo, so the Gerbers are the source of truth. These scripts edit them in place.

| Script | What it does |
| --- | --- |
| `gerb.py` | Minimal Gerber/Excellon reader and rasteriser used by everything else |
| `drc.py DIR PCB` | Netlist (every hole vs the KiCad nets), islands, net-to-net clearance, thin copper, silk on pads |
| `kicad_vs_gerber.py DIR PCB` | Redraws the KiCad tracks/pads and compares them with the Gerber copper |
| `render_board.py DIR OUT` | Renders `board-top.png` / `board-bottom.png` for the website |
| `grid.py SILK MASK x0 x1 y0 y1 OUT [ppm]` | Zoomed silkscreen view with a 1 mm grid, for layout work |
| `routes.py`, `make_e6.py`, `kicad_e6.py` | E.6 dial fix: rerouted S0-S3 tracks (Gerbers and KiCad), pour keep-outs, silk 0/8 and REV E.6 |
| `silkedit.py` | Moves/scales silkscreen outlines in place |
| `bigtext.py`, `check_silk.py` | Raises small silkscreen text to 1.1 mm and checks spacing |
| `credits.py`, `add_email.py` | Header layout: credit + email stack, supported-boards stack |

Silkscreen text is stored as outlines, so new text is drawn from a font file and traced. The credit line is Barlow Condensed SemiBold; the TTF and its licence (SIL OFL) are in `fab/fonts/`.

Coordinates are Gerber millimetres with Y up (KiCad Y = 80 − Gerber Y).
