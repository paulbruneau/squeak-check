SQUEAK CHECK! — Midway sound board bench tester — REV E.6
By Ethical Paul
=========================================================

WHAT IT TESTS
-------------
Verified against the original Bally/Midway schematics (Spy Hunter, Rampage/Star
Guards and Sarge manuals). All three boards share the same J1/J2/J3 pinout and the
same command interface (4 sound-select bits + SIRQ strobe, 2 status bits back):

  Cheap Squeak Deluxe  A080-91671 (68000)   Spy Hunter, Turbo Tag (proto)
  Sounds Good          A080-91671-G000 PCB  Rampage, Power Drive, Star Guards,
                       (a later revision of  Xenophobe, Spy Hunter II, Blasted,
                        the same bare board) Intl. Team Laser (proto)
  Turbo Cheap Squeak   (6809)               Sarge, Max RPM, Demolition Derby,
                                            Spy Hunter II (2nd board)

NOT compatible: Super Sound I/O (SSIO), and the Williams System 11 boards in
Arch Rivals / Pigskin / Tri-Sports. Pinball-era Bally boards (Cheap Squeak,
Sounds Deluxe, pinball TCS) use different harnesses and were not checked.

REV E.6: HEX DIAL FITS WITH ITS 0 AT THE TOP.
- On E.5 the SW1 footprint's pin map assumed the Grayhill 94HBB16T went in with
  the 0 on its dial toward the BOTTOM of the board. The switch fits its holes
  either way round, and fitted with 0 at the top (the natural way) it swapped
  SOUND0<->SOUND1 and SOUND2<->SOUND3 (dial 1 sent 2, dial 4 sent 8, etc.).
- E.6 turns the footprint's pin numbers 180 degrees: with the 0 at the top,
  pin 1 is the top-left hole and drives SOUND0. Hole positions are unchanged;
  the four sound tracks are swapped where they meet the resistors:
    SW1 top-left hole     -> S0 (RS0/RPD0)   front copper
    SW1 bottom-right hole -> S1 (RS1/RPD1)   back copper
    SW1 bottom-left hole  -> S2 (RS2/RPD2)   front copper
    SW1 top-right hole    -> S3 (RS3/RPD3)   back copper
- Silkscreen: a "0" replaces the top dial tick and an "8" the bottom one, so
  the switch's printed 0 lines up with the silk 0. REV E.5 -> REV E.6.
- Silkscreen text: every label is now at least 1.1 mm tall (capital height)
  with strokes of about 0.2 mm; the smallest used to be 0.72 mm. Grown in
  place: the LED legend, LINE LEVEL note, power-tag pills, F1/F2/5V/12V,
  resistor values, column headings, TRIGGER, 1uF, AWG notes, LOUDER/VOLUME,
  PICK A SOUND, INSERT POWER / KK-396, and the size and mounting notes.
  "5V 1A · 12V 0.5A" is now two lines ("5V 1A" / "12V 0.5A") to clear the
  RCA jack outline. Nothing moved onto pads; copper and drills unchanged.
- Header under the title is now two stacks. Left: "By Ethical Paul" over
  "paul@ethicalpaul.com". Right, at 1.3 mm: CHEAP SQUEAK DELUXE / SOUNDS GOOD
  / TURBO CHEAP SQUEAK (replaces the one-line "... · BENCH TESTER" subtitle).
- REV E.6 / board size / mounting block scaled up 1.6x (REV 2.2 mm, notes
  1.8 mm) and centred in the open area between the SOUND2 row and J2.
- Three small ground-pour keep-outs on the back (around 29.8,51.8 / 32.3,47.4 /
  30.9,30.1 in Gerber coordinates) stop the rerouted tracks from leaving an
  unconnected pour island and two thin necks.
- Schematic unchanged electrically (dial 1-2-4-8 -> SOUND0-3); the KiCad
  symbol now lists SW1's pins in footprint order (1, CL, 4, 8, CR, 2).
- E.5 BOARDS: fit SW1 with its 0 toward the BOTTOM edge to get the right bits.
Every other hole, part, net and label is unchanged from E.5.

REV E.5: POWER PROTECTION AND INDICATORS (review feedback).
- F1 (Bourns MF-R135, 1.35 A hold) on +5 V and F2 (MF-R050, 0.5 A hold) on +12 V:
  resettable fuses right after the power header, so a shorted sound board
  can't cook the tester's traces or connector.
- D1/D2 green LEDs on +5 V and +12 V, AFTER the fuses (1k / 3.3k, ~3 mA): a dark
  LED means no supply or a tripped fuse.
- Suggested supply printed on the board: 5 V 1 A, 12 V 0.5 A (estimated from
  the sound board's chips; measure your own board).
- Mounting note on the silk: M3 or #4-40, pan head no bigger than 5.6 mm.
- LED self-test legend moved into the how-to panel to make room.
Harness holes, pin order, names and every sound-board signal are unchanged.

REV E.4: BOARD NARROWED 108 -> 98 MM. J1 stays on the left edge; the resistor
block tucked in against the J1 labels and everything else slid left (J2, J3, pot,
RCA jacks and power header move as groups, with pitches, hole sizes, pin order and
labels all unchanged). +12V now runs between the SOUND2 trace (SOUND3 from
E.6 on) and the RESET button on the back. Netlist identical to E.3.

REV E.3: VOLUME POT ON THE BOARD. The J5 A/W/B wire pads are gone; RV1 (Bourns
PTV09A-4020U-B102, 1k linear, 9 mm, vertical 20 mm knurled shaft
you turn by hand - no knob needed) sits in the
bottom-right corner, wired pin 1 = VOL_END_B (J3-12), pin 2 = VOL_WIPER (J3-1),
pin 3 = VOL_END_A (J3-10) so turning it CLOCKWISE = LOUDER (the MC3340 attenuates
more as the wiper voltage rises). Its two side tabs are soldered to ground for
strength. Every other net, hole and label is unchanged from E.2. Part numbers in
BOM.csv are Mouser numbers.

REV E.2 (layout): PLAY button and its debounce cap moved right beside the hex
dial; "By Ethical Paul" added under the title. No circuit change from E.1.

REV E.1 CHANGES (from Rev E / Rev D5)
------------------------------------
1. RESET POLARITY FIXED. J2-9/10 is active-LOW on all three boards (e.g. CSD:
   100k pull-up -> 40106 -> 74LS04 -> diodes pull the 68000 RST/HALT low). Rev D5
   held RESET low through 10k, which would keep the board in reset permanently.
   Now: RRST (10k) pulls RESET up to +5V; the RESET button pulls it to GND.
2. SIRQ polarity hardwired "fire low"; JP1 removed. All three boards idle SIRQ
   high (100k on-board pull-up) and the same game hardware drives them with the
   same signal (Spy Hunter II feeds a Sounds Good and a TCS from the same control
   bits). RIRQ (10k) pulls SIRQ up to +5V; PLAY pulls it to GND.
3. PLAY debounce: C1 1 uF across the button (~10 ms with RIRQ).
4. E-GND (J2-7) tied to GND. Sounds Good grounds it on-board; CSD/TCS use it as
   the return for their input filter capacitors.
Harness hole sizes, pin order, duplicate pins and all silk names are unchanged.

USING IT
--------
Power-up: the sound board's green LED flashes once per passed self-test:
  1-4 = ROMs (U7, U8, U17, U18), 5 = RAM (U6, U16), 6 = PIA (U9).
  Six flashes = pass. Where it stops = the failed step. (Star Guards manual.)

Red TEST button ON the sound board: wired to the 68000's interrupt lines
(pulls IPL0-2 -> level 7). What it does is decided by that game's ROMs. On the
sister pinball boards it plays one fixed test sound (a "bong" or an explosion)
or just reboots the board; it is not a cycle through all sounds.

Sound numbers: the connector carries 4 bits per strobe; one dial+PLAY press
sends the number on the dial. The command list lives in each game's sound ROMs
and is not documented in MAME. Spy Hunter CSD (only the two low bits matter):
1 = full Peter Gunn theme, 2 = short intro, 3 = the "player died" ending (send
it while the theme is playing). Other games' ROMs may expect a sequence of
presses.

Start with the VOLUME knob turned down (fully counter-clockwise). Line-level mono audio
appears on both RCA jacks; feed an amplifier or powered speaker.

VERIFICATION (Rev E.6)
---------------------
Gerbers re-read with an independent parser and rasterised at 0.04 mm:
- Netlist: every one of the 135 holes' copper checked against the intended
  net (23 nets): 0 shorts, 0 opens, 0 unconnected copper islands.
- Clearance between different nets: 0.50 mm minimum on top, 0.40 mm on the
  back (rule 0.30 mm). Same as E.5; the rerouted tracks have 0.68 mm or more.
- Thin copper: the new keep-outs leave four tiny pointed tips of ground pour
  (under 0.3 mm long), the same kind of feature E.5 already had at its
  thermal spokes and corners. Fabs handle these.
- Drills: 98 plated + 37 non-plated, all on their pads; files unchanged from E.5.
- Silkscreen: none on exposed pads; all text at least 1.1 mm tall and
  0.2 mm or more from other silk (the power tags keep their E.5 spacing).
- KiCad PCB tracks and pads redrawn and compared with the Gerber copper:
  identical on top, and every KiCad track present on the back.
(No KiCad/Altium DRC was run here. Preview the zip in your fab's Gerber viewer
before ordering.)

ORDERING
--------
2 layers, FR-4, 1.6 mm, 1 oz, any mask colour, white silk, ENIG or HASL.
98 x 80 mm. Upload SqueakCheck_RevE6_Gerbers.zip as it is.
