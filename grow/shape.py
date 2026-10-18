"""Gestures: ways a part can go somewhere over its own length.

A loop is a circle. A phrase has a shape: it rises or falls, hurries or
lingers, swells or fades, breathes and comes back changed, states a thing
and answers it, breaks off. These are transformations of a part's events as
functions of time, applied to the part's own material. They are relations
to time, not opinions about quality; the player's ear still chooses.

Every gesture takes (rows, song, rng) where rows are (line index, tokens)
for i-statements, and returns (rows, note) or (None, "") when it does not
apply.
"""

from __future__ import annotations

import math
import random

from .direction import tune_rows

GESTURES = ["spiral_up", "spiral_down", "stairs", "swell", "fade", "arch", "rush", "drag",
            "breath", "fragment", "long_short", "question_answer", "break_off"]


def _f(s):
    try:
        return float(s)
    except ValueError:
        return None


def _pitch_col(rows):
    for _, toks in rows:
        for k in range(3, len(toks)):
            v = _f(toks[k])
            if v is not None and 20 <= v <= 8000:
                return k
    return None


def _amp_col(rows):
    for _, toks in rows:
        for k in range(3, len(toks)):
            v = _f(toks[k])
            if v is not None and 0 < v <= 1.0:
                return k
    return None


def _starts(rows):
    out = []
    for i, toks in rows:
        s, d = _f(toks[1]), _f(toks[2])
        if s is not None and d is not None:
            out.append((s, d, i, toks))
    return sorted(out, key=lambda e: e[0])


def _retune(rows, song):
    if song.scale:
        rows, _ = tune_rows(rows, song.scale, song.root_hz)
    return rows


# ------------------------------------------------------------------ register

def spiral(rows, song, rng, up=True, octaves=1.0):
    col = _pitch_col(rows)
    if col is None:
        return None, ""
    L = song.seconds
    for _, toks in rows:
        s, v = _f(toks[1]), _f(toks[col])
        if s is None or v is None:
            continue
        m = 2 ** ((s / L) * octaves * (1 if up else -1))
        nv = v * m
        if 20 <= nv <= 8000:
            toks[col] = f"{nv:.4g}"
    return _retune(rows, song), f"spirals {'up' if up else 'down'} over the phrase"


def stairs(rows, song, rng):
    col = _pitch_col(rows)
    if col is None:
        return None, ""
    bar = song.beat * 4
    step = rng.choice([2 ** (2 / 12), 2 ** (3 / 12), 2 ** (5 / 12), 2 ** (-2 / 12), 2 ** (-5 / 12)])
    for _, toks in rows:
        s, v = _f(toks[1]), _f(toks[col])
        if s is None or v is None:
            continue
        nv = v * step ** int(s // bar)
        if 20 <= nv <= 8000:
            toks[col] = f"{nv:.4g}"
    return _retune(rows, song), f"climbs a step {'up' if step > 1 else 'down'} each bar"


# ------------------------------------------------------------------ dynamics

def envelope(rows, song, rng, shape):
    col = _amp_col(rows)
    if col is None:
        return None, ""
    L = song.seconds
    for _, toks in rows:
        s, v = _f(toks[1]), _f(toks[col])
        if s is None or v is None:
            continue
        t = s / L
        if shape == "swell":
            g = 0.35 + 0.65 * t
        elif shape == "fade":
            g = 1.0 - 0.65 * t
        else:  # arch
            g = 0.4 + 0.6 * math.sin(math.pi * t)
        toks[col] = f"{min(1.0, v * g):.3f}"
    return rows, {"swell": "grows from a whisper", "fade": "fades away", "arch": "rises and falls"}[shape]


# --------------------------------------------------------------------- time

def warp(rows, song, rng, accel=True):
    """Accelerando or ritardando: event times bunch toward the end or the start."""
    L = song.seconds
    p = rng.choice([1.5, 1.8, 2.2]) if accel else rng.choice([0.45, 0.55, 0.7])
    q = song.beat / 4
    out = []
    for i, toks in rows:
        s, d = _f(toks[1]), _f(toks[2])
        if s is None or d is None:
            out.append((i, toks)); continue
        u = max(0.0, min(1.0, s / L))
        ns = L * (u ** p)
        slope = p * (u ** (p - 1)) if u > 0 else (p if p < 1 else 0.2)
        nd = max(0.05, min(d * slope, L - ns))
        ns = round(ns / q) * q
        if ns >= L - 0.05:
            continue
        toks[1], toks[2] = f"{ns:.3f}", f"{nd:.3f}"
        out.append((i, toks))
    if not out:
        return None, ""
    return out, "hurries toward the end" if accel else "slows as it goes"


def long_short(rows, song, rng):
    """Durations follow a spoken pattern: long, short, short, long."""
    ev = _starts(rows)
    if len(ev) < 3:
        return None, ""
    pattern = rng.choice([[1.0, 0.3, 0.3, 1.0], [0.3, 0.3, 1.2], [1.4, 0.25, 0.25, 0.25], [0.5, 1.0, 0.25]])
    for k, (s, d, i, toks) in enumerate(ev):
        nxt = ev[k + 1][0] if k + 1 < len(ev) else song.seconds
        ioi = max(0.1, nxt - s)
        toks[2] = f"{max(0.05, ioi * pattern[k % len(pattern)]):.3f}"
    return rows, "speaks in long and short"


# ------------------------------------------------------------------- phrase

def breath(rows, song, rng):
    """A bar of silence at a bar line, then the rest comes back in a new register."""
    bar = song.beat * 4
    if song.bars < 3:
        return None, ""
    cut = rng.randint(1, song.bars - 2) * bar
    col = _pitch_col(rows)
    f = rng.choice([0.5, 2.0, 2 ** (7 / 12), 2 ** (-5 / 12)])
    out = []
    for i, toks in rows:
        s = _f(toks[1])
        if s is None:
            out.append((i, toks)); continue
        if cut <= s < cut + bar:
            continue
        if s >= cut + bar and col is not None:
            v = _f(toks[col])
            if v is not None and 20 <= v * f <= 8000:
                toks[col] = f"{v * f:.4g}"
        out.append((i, toks))
    if not out or len(out) == len(rows):
        return None, ""
    return _retune(out, song), f"takes a breath at bar {int(cut // bar) + 1} and comes back {'higher' if f > 1 else 'lower'}"


def fragment(rows, song, rng):
    """The first bar is a motif; the part repeats it, shedding a note each time."""
    bar = song.beat * 4
    motif = [(s, d, toks) for s, d, _, toks in _starts(rows) if s < bar]
    if len(motif) < 2:
        return None, ""
    out, n, k = [], len(motif), 0
    t = 0.0
    while t < song.seconds - 0.05:
        keep = motif[: max(1, n - k)]
        for s, d, toks in keep:
            if t + s >= song.seconds - 0.05:
                break
            nt = list(toks); nt[1] = f"{t + s:.3f}"; nt[2] = f"{min(d, song.seconds - t - s):.3f}"
            out.append((len(out), nt))
        t += bar
        k = (k + 1) % n
    return out, "repeats a motif, dropping a note each time"


def question_answer(rows, song, rng):
    """The second half restates the first a step away and lands on a long note."""
    L = song.seconds
    half = L / 2
    first = [(s, d, toks) for s, d, _, toks in _starts(rows) if s < half]
    if len(first) < 2:
        return None, ""
    col = _pitch_col(rows)
    f = rng.choice([2 ** (2 / 12), 2 ** (-2 / 12), 2 ** (5 / 12), 2 ** (-7 / 12)])
    out = [(k, list(toks)) for k, (s, d, toks) in enumerate(first)]
    for s, d, toks in first:
        nt = list(toks); nt[1] = f"{s + half:.3f}"
        if col is not None:
            v = _f(nt[col])
            if v is not None and 20 <= v * f <= 8000:
                nt[col] = f"{v * f:.4g}"
        out.append((len(out), nt))
    last = out[-1][1]
    s = _f(last[1])
    if s is not None:
        last[2] = f"{max(_f(last[2]) or 0.1, min(L - s, song.beat * 3)):.3f}"
    return _retune(out, song), "asks, then answers a step away"


def break_off(rows, song, rng):
    """Halfway, abandon the material: the second half is a different gesture."""
    L = song.seconds
    half = L / 2
    first = [(i, toks) for i, toks in rows if (_f(toks[1]) or 0) < half]
    second = [(i, toks) for i, toks in rows if (_f(toks[1]) or 0) >= half]
    if len(first) < 1 or len(second) < 1:
        return None, ""
    choice = rng.choice(["thin", "double_time", "octave", "hold"])
    out = list(first)
    if choice == "thin":
        out += second[::2]
        what = "then thins out"
    elif choice == "double_time":
        for i, toks in second:
            s, d = _f(toks[1]), _f(toks[2])
            if s is None or d is None:
                continue
            t1 = list(toks); t1[2] = f"{max(0.05, d / 2):.3f}"; out.append((i, t1))
            t2 = list(toks); t2[1] = f"{min(L - 0.05, s + d / 2):.3f}"; t2[2] = f"{max(0.05, d / 2):.3f}"; out.append((len(rows) + i, t2))
        what = "then doubles the pace"
    elif choice == "octave":
        col = _pitch_col(second)
        f = rng.choice([0.5, 2.0])
        for i, toks in second:
            if col is not None:
                v = _f(toks[col])
                if v is not None and 20 <= v * f <= 8000:
                    toks[col] = f"{v * f:.4g}"
            out.append((i, toks))
        what = "then jumps " + ("up" if f > 1 else "down") + " an octave"
    else:
        i, toks = second[0]
        toks[2] = f"{max(0.05, L - (_f(toks[1]) or half)):.3f}"
        out.append((i, toks))
        what = "then holds one note"
    return _retune(out, song), "breaks off halfway, " + what


# ------------------------------------------------------------------- choose

def apply(name: str, rows, song, rng):
    if name == "spiral_up":
        return spiral(rows, song, rng, up=True)
    if name == "spiral_down":
        return spiral(rows, song, rng, up=False)
    if name == "stairs":
        return stairs(rows, song, rng)
    if name in ("swell", "fade", "arch"):
        return envelope(rows, song, rng, name)
    if name == "rush":
        return warp(rows, song, rng, accel=True)
    if name == "drag":
        return warp(rows, song, rng, accel=False)
    if name == "breath":
        return breath(rows, song, rng)
    if name == "fragment":
        return fragment(rows, song, rng)
    if name == "long_short":
        return long_short(rows, song, rng)
    if name == "question_answer":
        return question_answer(rows, song, rng)
    if name == "break_off":
        return break_off(rows, song, rng)
    return None, ""


def gesture(rows, song, rng, name: str | None = None):
    """Apply one gesture (random unless named). Returns (rows, note) or (None, '')."""
    names = [name] if name else list(GESTURES)
    rng.shuffle(names)
    for n in names:
        copy = [(i, list(toks)) for i, toks in rows]
        out, note = apply(n, copy, song, rng)
        if out:
            return out, note
    return None, ""
