#!/usr/bin/env python3
"""Squeak Tap host tool: capture the Cheap Squeak Deluxe DAC stream and make WAVs.

By Ethical Paul.

    pip install pyserial numpy scipy

    python squeak_tap.py ports
    python squeak_tap.py capture PORT theme.sqt        (Ctrl-C to stop)
    python squeak_tap.py info theme.sqt
    python squeak_tap.py wav theme.sqt theme.wav                  (48 kHz)
    python squeak_tap.py wav theme.sqt theme.wav --rate native    (one sample per DAC update)
    python squeak_tap.py wav theme.sqt theme_cab.wav --cabinet    (sounds like the cabinet)

A .sqt file is exactly what the board sent: a 16-byte header ("SQTP",
version, sample_hz, sample_bits) followed by little-endian 32-bit event
words. Bits 0-11 of a word are the sample (D0-D9, then MARK active-low on
bit 10), bits 12-31 the ticks since the previous word. ticks == 0xFFFFF is a control
word: code 0x001 = events dropped, 0x002 = sampler stalled, 0x0FF = end.
"""

import argparse
import struct
import sys
import time

import numpy as np

TICKS_CTRL = 0xFFFFF
CTRL_NAMES = {0x001: "events dropped (USB too slow)", 0x002: "sampler stalled", 0x0FF: "end"}
DAC_MASK = 0x3FF
MARK_BIT = 1 << 10          # low = pressed
HI_BITS = 0x3FC             # PIA port A -> DAC bits 2-9
LO_BITS = 0x003             # PIA port B (PB6, PB7) -> DAC bits 0-1


# ---------------------------------------------------------------- capture --

def cmd_ports(_args):
    from serial.tools import list_ports
    for p in list_ports.comports():
        tag = "  <- Squeak Tap?" if (p.vid == 0x2E8A) else ""
        print(f"{p.device:20s} {p.description}{tag}")


def cmd_capture(args):
    import serial
    port = serial.Serial(args.port, 115200, timeout=0.2)
    port.reset_input_buffer()
    port.write(b"X")                     # in case a capture was left running
    time.sleep(0.2)
    port.reset_input_buffer()
    port.write(b"S")
    hdr = port.read(16)
    if len(hdr) != 16 or hdr[:4] != b"SQTP":
        sys.exit(f"No Squeak Tap header from {args.port} (got {hdr!r})")
    _, ver, rate, bits = struct.unpack("<4sIII", hdr)
    print(f"Capturing at {rate} Hz (firmware {ver}). Press Ctrl-C to stop.")

    total = 0
    t0 = time.time()
    with open(args.out, "wb") as f:
        f.write(hdr)
        try:
            while args.seconds is None or time.time() - t0 < args.seconds:
                data = port.read(65536)
                if data:
                    f.write(data)
                    total += len(data)
                print(f"\r  {time.time() - t0:7.1f} s  {total // 4:10d} events", end="")
        except KeyboardInterrupt:
            pass
        port.write(b"X")
        # Read the tail until the end control word arrives.
        tail = b""
        deadline = time.time() + 3
        end_word = struct.pack("<I", (TICKS_CTRL << 12) | 0x0FF)
        while time.time() < deadline:
            chunk = port.read(65536)
            tail += chunk
            if end_word in tail[-8:] or (not chunk and tail):
                break
        f.write(tail)
        total += len(tail)
    print(f"\nSaved {total // 4} events to {args.out}")


# ---------------------------------------------------------------- decode --

def load(path):
    """Return (rate, t_ticks, samples, controls) with absolute tick times."""
    raw = open(path, "rb").read()
    if raw[:4] != b"SQTP":
        sys.exit(f"{path} is not a Squeak Tap capture")
    _, ver, rate, bits = struct.unpack("<4sIII", raw[:16])
    n = (len(raw) - 16) // 4
    words = np.frombuffer(raw[16:16 + 4 * n], dtype="<u4")
    ticks = (words >> 12).astype(np.int64)
    vals = (words & 0xFFF).astype(np.int32)
    is_ctrl = ticks == TICKS_CTRL
    controls = []
    if is_ctrl.any():
        # Control words carry no time; give them the time of the next event.
        t_all = np.cumsum(np.where(is_ctrl, 0, ticks))
        for i in np.flatnonzero(is_ctrl):
            controls.append((int(t_all[i]), int(vals[i])))
    keep = ~is_ctrl
    t = np.cumsum(ticks[keep])
    return rate, t, vals[keep], controls


def to_steps(t, s):
    """Collapse to the DAC value only, dropping words where it did not change."""
    v = s & DAC_MASK
    keep = np.ones(len(v), bool)
    keep[1:] = v[1:] != v[:-1]
    return t[keep], v[keep]


def deglitch(t, v, max_ticks):
    """Remove half-written values left between the PIA port A and port B writes.

    A segment is dropped when it lasts at most max_ticks, the step into it
    changed bits from one PIA port only, and the step out of it changed bits
    from the other port only.
    """
    if len(v) < 3:
        return t, v, 0
    d_in = v[1:-1] ^ v[:-2]
    d_out = v[2:] ^ v[1:-1]
    dur = t[2:] - t[1:-1]
    only_hi_in = (d_in & LO_BITS) == 0
    only_lo_in = (d_in & HI_BITS) == 0
    only_hi_out = (d_out & LO_BITS) == 0
    only_lo_out = (d_out & HI_BITS) == 0
    glitch = (dur <= max_ticks) & ((only_hi_in & only_lo_out) | (only_lo_in & only_hi_out))
    keep = np.ones(len(v), bool)
    keep[1:-1] = ~glitch
    t2, v2 = t[keep], v[keep]
    # Removing a segment can leave two equal neighbours; merge them.
    k = np.ones(len(v2), bool)
    k[1:] = v2[1:] != v2[:-1]
    return t2[k], v2[k], int(glitch.sum())


def marks(t, s):
    """Tick times when the MARK button went down."""
    down = (s & MARK_BIT) == 0
    edges = np.flatnonzero(down[1:] & ~down[:-1]) + 1
    if len(down) and down[0]:
        edges = np.r_[0, edges]
    return t[edges]


def estimate_period(t, rate):
    """Estimate the CSD's DAC update period from the gaps between changes.

    Gaps are whole multiples of the true period (repeated values are
    invisible). Take the most common short gap as a first guess, count how
    many periods each gap spans, and divide total time by total periods.
    Rounding happens per gap, so the estimate cannot drift on long captures.
    Returns (period_ticks, phase_ticks, fit_score) or (None, 0, 0).
    """
    gaps = np.diff(t)
    short = gaps[(gaps > 0) & (gaps < rate // 1000)]   # under 1 ms
    if len(short) < 100:
        return None, 0.0, 0.0
    hist = np.bincount(short)
    mode = int(np.argmax(hist))
    near = short[np.abs(short - mode) <= max(2, mode // 20)]
    p = float(near.mean())
    g = gaps.astype(np.float64)
    for _ in range(3):
        m = np.round(g / p)
        ok = (m >= 1) & (np.abs(g / p - m) < 0.3) & (m <= 64)
        p = float(g[ok].sum() / m[ok].sum())
    # Grid phase: circular mean of the change times modulo the period.
    ang = 2 * np.pi * (t.astype(np.float64) % p) / p
    phase = float(np.angle(np.mean(np.exp(1j * ang))) / (2 * np.pi) * p) % p
    off = ((t - phase) / p) % 1.0
    off = np.minimum(off, 1.0 - off)
    score = float(np.mean(off < 0.25))
    return p, phase, score


# ---------------------------------------------------------------- render --

def render_box(t, v, rate, out_rate, t_start, t_end):
    """Exact area of the DAC staircase over each output bin (box filter)."""
    edges = t_start + np.arange(int((t_end - t_start) * out_rate / rate) + 1) * (rate / out_rate)
    # Cumulative area of a step function is piecewise linear, so np.interp is exact.
    level = v.astype(np.float64)
    tt = t.astype(np.float64)
    area = np.concatenate([[0.0], np.cumsum(level[:-1] * np.diff(tt))])
    a_edges = np.interp(edges, tt, area, left=0.0, right=area[-1])
    # Extend past the last change with the final level.
    past = edges > tt[-1]
    a_edges[past] = area[-1] + level[-1] * (edges[past] - tt[-1])
    return np.diff(a_edges) / (rate / out_rate)


def render_native(t, v, period, phase, t_start, t_end):
    """One sample per DAC update period, taken mid-period."""
    first = phase + period / 2
    k0 = np.ceil((t_start - first) / period)
    k1 = np.floor((t_end - first) / period)
    grid = first + np.arange(k0, k1 + 1) * period
    idx = np.searchsorted(t, grid, side="right") - 1
    return v[np.clip(idx, 0, None)].astype(np.float64)


def cabinet_sos(fs):
    """The CSD's analog chain after the DAC, from the schematic's part values."""
    from scipy import signal
    k = 1e3
    p = 1e-12
    stages = []
    # U3 input stage: R111 120k || C113 270p over R112 120k (unity, one pole).
    stages.append(([1.0], [120 * k * 270 * p, 1.0]))
    # U3 multiple-feedback low-pass: R1 = R113 33k, R2 = R116 33k, R3 = R117 18k,
    # C1 = C115 5600p (to ground), C2 = C118 270p (feedback).
    R1, R2, R3, C1, C2 = 33 * k, 33 * k, 18 * k, 5600 * p, 270 * p
    stages.append(([1.0 / (R1 * R3 * C1 * C2)],
                   [1.0, (1 / C1) * (1 / R1 + 1 / R2 + 1 / R3), 1.0 / (R2 * R3 * C1 * C2)]))
    # U2 stage: R115 150k into C112 470p, R109 82k to the input; R108 150k || C111 150p.
    R115, R109, C112, R108, C111 = 150 * k, 82 * k, 470 * p, 150 * k, 150 * p
    stages.append(([R108], np.polymul([R108 * C111, 1.0], [R115 * R109 * C112, R115 + R109])))
    # U2 output stage: R102 160k || C109 68p over R101 24k.
    stages.append(([160 * k / (24 * k)], [160 * k * 68 * p, 1.0]))
    # Coupling caps (C114 1u into R113 33k) block DC, about 5 Hz.
    stages.append(([33 * k * 1e-6, 0.0], [33 * k * 1e-6, 1.0]))
    sos = []
    for b, a in stages:
        bz, az = signal.bilinear(b, a, fs)
        sos.append(signal.tf2sos(bz, az))
    return np.vstack(sos)


def cmd_info(args):
    rate, t, s, controls = load(args.file)
    dur = (t[-1] - t[0]) / rate if len(t) else 0
    print(f"{args.file}: {len(t)} event words, {dur:.2f} s at {rate} Hz")
    for when, code in controls:
        print(f"  {when / rate:9.3f} s  {CTRL_NAMES.get(code, hex(code))}")
    m = marks(t, s)
    for i, when in enumerate(m):
        print(f"  mark {i + 1}: {when / rate:.3f} s")
    tt, v = to_steps(t, s)
    tg, vg, n_g = deglitch(tt, v, int(args.glitch_us * rate / 1e6))
    print(f"  DAC changes: {len(v)}, half-written values removed: {n_g}")
    print(f"  DAC range: {vg.min()}..{vg.max()} (of 0..1023)")
    p, _, score = estimate_period(tg, rate)
    if p:
        print(f"  update period: {p / rate * 1e6:.3f} us = {rate / p:.1f} Hz "
              f"({score * 100:.0f}% of changes on a regular grid)")
    gaps = np.diff(tt)
    short = gaps[gaps < 64]
    if len(short):
        h = np.bincount(short, minlength=64)
        top = np.argsort(h)[::-1][:6]
        print("  most common short gaps (us: count): " +
              ", ".join(f"{g * 1e6 / rate:.1f}: {h[g]}" for g in sorted(top) if h[g]))


def cmd_wav(args):
    from scipy import signal
    from scipy.io import wavfile

    rate, t, s, controls = load(args.file)
    if any(code in (0x001, 0x002) for _, code in controls):
        print("Warning: this capture has gaps (see 'info').", file=sys.stderr)

    t_start, t_end = float(t[0]), float(t[-1])
    m = marks(t, s)
    if args.from_mark:
        if args.from_mark > len(m):
            sys.exit(f"Only {len(m)} marks in this capture")
        t_start = float(m[args.from_mark - 1])
    if args.start is not None:
        t_start = float(t[0]) + args.start * rate
    if args.length is not None:
        t_end = min(t_end, t_start + args.length * rate)

    tt, v = to_steps(t, s)
    if not args.keep_glitches:
        tt, v, n_g = deglitch(tt, v, int(args.glitch_us * rate / 1e6))
        print(f"Removed {n_g} half-written values")

    if args.rate == "native":
        p, phase, score = estimate_period(tt, rate)
        if p is None:
            sys.exit("Not enough DAC activity to find the update rate")
        out_rate = rate / p
        print(f"Native update rate {out_rate:.2f} Hz ({score * 100:.0f}% on grid)")
        if score < 0.9:
            print("Warning: updates are not on a steady timer; prefer a fixed --rate.",
                  file=sys.stderr)
        x = render_native(tt, v, p, phase, t_start, t_end)
        wav_rate = int(round(out_rate))
    else:
        wav_rate = int(args.rate)
        # Exact box integral at about 4x, filtered there, then a polyphase low-pass down.
        mid = 176400 if 176400 % wav_rate == 0 else 192000
        x = render_box(tt, v, rate, mid, t_start, t_end) - 512.0
        if args.cabinet:
            x = signal.sosfilt(cabinet_sos(mid), x)
        from math import gcd
        g = gcd(wav_rate, mid)
        x = signal.resample_poly(x, wav_rate // g, mid // g)

    if args.rate == "native":
        x = x - 512.0                                 # DAC mid-scale = 0
        if args.cabinet:
            x = signal.sosfilt(cabinet_sos(wav_rate), x)
    if args.cabinet or args.normalize:
        peak = np.max(np.abs(x)) or 1.0
        y = np.round(x / peak * 32767 * 10 ** (-1 / 20))
    else:
        y = np.round(x * 64)                          # 10-bit value -> 16-bit
    y = np.clip(y, -32768, 32767).astype(np.int16)
    wavfile.write(args.out, wav_rate, y)
    print(f"Wrote {args.out}: {len(y) / wav_rate:.2f} s at {wav_rate} Hz")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("ports", help="list serial ports")

    c = sub.add_parser("capture", help="record from the board")
    c.add_argument("port")
    c.add_argument("out")
    c.add_argument("--seconds", type=float, help="stop after this long")

    i = sub.add_parser("info", help="summarise a capture")
    i.add_argument("file")
    i.add_argument("--glitch-us", type=float, default=10.0)

    w = sub.add_parser("wav", help="convert a capture to WAV")
    w.add_argument("file")
    w.add_argument("out")
    w.add_argument("--rate", default="48000", help="output rate in Hz, or 'native'")
    w.add_argument("--cabinet", action="store_true", help="apply the CSD analog filter")
    w.add_argument("--normalize", action="store_true", help="scale to -1 dBFS peak")
    w.add_argument("--from-mark", type=int, help="start at the Nth MARK press")
    w.add_argument("--start", type=float, help="start this many seconds in")
    w.add_argument("--length", type=float, help="seconds to keep")
    w.add_argument("--glitch-us", type=float, default=10.0,
                   help="longest half-written value to remove (default 10 us)")
    w.add_argument("--keep-glitches", action="store_true")

    args = ap.parse_args()
    {"ports": cmd_ports, "capture": cmd_capture, "info": cmd_info, "wav": cmd_wav}[args.cmd](args)


if __name__ == "__main__":
    main()
