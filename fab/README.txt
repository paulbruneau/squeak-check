SQUEAK CHECK! — Midway sound board bench tester — REV E.5
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
labels all unchanged). +12V now runs between the SOUND2 trace and the RESET
button on the back. Netlist identical to E.3.

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

Sound numbers: the connector carries 4 bits per strobe. The boards' firmware
generally treats commands as pairs of nibbles ("command followed by command"),
so a single dial+PLAY press sends one nibble. Try single presses first; for other
sounds, dial the first nibble, press PLAY, dial the second, press PLAY. The exact
command list lives in each game's sound ROMs and is not documented in MAME.

Start with the VOLUME knob turned down (fully counter-clockwise). Line-level mono audio
appears on both RCA jacks; feed an amplifier or powered speaker.

VERIFICATION
------------
Raster DRC at 0.04 mm: 0 shorts, 0 opens, 0 clearance < 0.30 mm, 0 islands.
Netlist = Rev D5 original + the four E.1 changes + the on-board pot (E.3),
checked pin by pin.
Gerbers re-read with gerbonara and diffed against the checked geometry:
0 mismatches on copper, mask and silk. (No KiCad/Altium DRC available here —
preview the zip in your fab's Gerber viewer before ordering.)

ORDERING
--------
2 layers, FR-4, 1.6 mm, 1 oz, any mask colour, white silk, ENIG or HASL.
98 x 80 mm. Upload the Gerbers/ folder zipped.
