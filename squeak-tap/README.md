# Squeak Tap

Captures the Cheap Squeak Deluxe's audio as the exact 10-bit values the 68000 writes to its AD7533 DAC, and turns them into WAV files. By Ethical Paul.

The hardware is a DAC-socket adapter plus a Raspberry Pi Pico capture board, ordered together on one panel and snapped apart at mouse-bite tabs. This folder holds the board files, the firmware and the PC tool.

## Files

| Path | What it is |
| --- | --- |
| `hardware/out/SqueakTap_RevA_Gerbers.zip` | Gerbers and drills for the two-board panel (91 × 60 mm, mouse-bite tabs between the boards), ready to order |
| `hardware/` | Board generator, schematic, BOM, KiCad file, renders (see `hardware/README.md`) |
| `firmware/uf2/squeak_tap_pico2.uf2` | Ready-to-flash firmware for the Pico 2 |
| `firmware/uf2/squeak_tap_pico.uf2` | Ready-to-flash firmware for the original Pico |
| `firmware/*.c, *.h, sampler.pio, CMakeLists.txt` | Firmware source (Pico SDK 2.2.0) |
| `host/squeak_tap.py` | Capture, inspect and convert to WAV |

## Flash the Pico

Hold BOOTSEL, plug the Pico into USB, and drag the matching `.uf2` onto the RPI-RP2 / RP2350 drive. It reappears as a serial port named "Squeak Tap".

## Record the theme

```
pip install pyserial numpy scipy
python host/squeak_tap.py ports                    # find the port
python host/squeak_tap.py capture COM5 spyhunter.sqt
```

Start the capture, press MARK (SW1) on the capture board just before the theme starts, then trigger the sound. Press Ctrl-C when it finishes. The Pico's LED is lit while capturing and flickers when the DAC is active.

## Make WAVs

```
python host/squeak_tap.py info spyhunter.sqt
python host/squeak_tap.py wav spyhunter.sqt theme_native.wav --rate native --from-mark 1
python host/squeak_tap.py wav spyhunter.sqt theme_48k.wav --from-mark 1
python host/squeak_tap.py wav spyhunter.sqt theme_cabinet.wav --cabinet --from-mark 1
```

- `--rate native` writes one sample per DAC update at the CSD's own rate. If the CSD updates on a steady timer, this is a lossless copy of what the board played. `info` shows the rate it found and how regular it is.
- The default writes 48 kHz (or any `--rate`), averaging the DAC level over each sample, then low-pass filtering properly.
- `--cabinet` adds the CSD's analog filter (U3/U2 stages, modelled from the schematic's part values), so it sounds like the machine instead of the raw DAC.
- Half-written values (the moment between the PIA port A and port B writes) are removed automatically. `--glitch-us` sets the longest one to remove, `--keep-glitches` turns it off.
- Unnormalized output maps DAC 512 to 0 and each DAC step to 64 counts, so the 10-bit values survive exactly in the 16-bit WAV.

## Build the firmware

```
export PICO_SDK_PATH=/path/to/pico-sdk      # 2.2.0
cmake -S firmware -B build -G Ninja          # Pico 2 (default)
cmake -S firmware -B build -G Ninja -DPICO_BOARD=pico
ninja -C build
```

## Stream format

`.sqt` files are exactly what the board sends: a 16-byte header (`SQTP`, u32 version, u32 sample rate 960000, u32 sample bits 11) followed by little-endian 32-bit words. Bits 0–9 of a word are D0–D9, bit 10 is MARK (active-low), bits 12–31 the 960 kHz ticks since the previous word. A word with ticks = 0xFFFFF is a control word: 0x001 events dropped, 0x002 sampler stalled, 0x0FF end of capture.
