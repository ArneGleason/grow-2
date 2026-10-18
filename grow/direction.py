"""The conductor's direction.

A direction is the listener's request, not a judgment: which sounds, what
space, how fast, what groove, what pitch material, what mood. It reaches
the music through real paths:

- new songs pick their tempo and cast from it,
- parts joining a song are fitted to its groove and tuned to its scale,
- responders include "groove" and "tune" as relations to it,
- the mind is told it in words,
- the space is applied live to the mix on stage.

Moods are presets for the other fields, written out in the open so they
can be argued with. Nothing here says what is good; it says what was asked.
"""

from __future__ import annotations

import json
import math
import random
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

PALETTES = ["modular drone", "digital", "analog", "percussive", "plucked", "texture", "pad", "voice", "glass"]
SPACES = ["dry", "room", "hall", "echo", "space echo"]
GROOVES = ["straight", "swing", "broken", "drone", "free"]
PITCHES = ["modes", "microtonal", "free"]

# scale steps in cents within one period (an octave unless noted)
SCALES: dict[str, dict] = {
    "ionian":       {"cents": [0, 200, 400, 500, 700, 900, 1100], "period": 1200},
    "dorian":       {"cents": [0, 200, 300, 500, 700, 900, 1000], "period": 1200},
    "phrygian":     {"cents": [0, 100, 300, 500, 700, 800, 1000], "period": 1200},
    "lydian":       {"cents": [0, 200, 400, 600, 700, 900, 1100], "period": 1200},
    "mixolydian":   {"cents": [0, 200, 400, 500, 700, 900, 1000], "period": 1200},
    "aeolian":      {"cents": [0, 200, 300, 500, 700, 800, 1000], "period": 1200},
    "locrian":      {"cents": [0, 100, 300, 500, 600, 800, 1000], "period": 1200},
    "pentatonic":   {"cents": [0, 200, 400, 700, 900], "period": 1200},
    "whole tone":   {"cents": [0, 200, 400, 600, 800, 1000], "period": 1200},
    "19-edo":       {"cents": [round(1200 * k / 19, 2) for k in range(19)], "period": 1200},
    "31-edo":       {"cents": [round(1200 * k / 31, 2) for k in range(31)], "period": 1200},
    "bohlen-pierce": {"cents": [round(1901.955 * k / 13, 2) for k in range(13)], "period": 1901.955},
    "7-edo":        {"cents": [round(1200 * k / 7, 2) for k in range(7)], "period": 1200},
}
MODAL = ["ionian", "dorian", "phrygian", "lydian", "mixolydian", "aeolian", "locrian", "pentatonic", "whole tone"]
MICRO = ["19-edo", "31-edo", "bohlen-pierce", "7-edo"]

MOODS: dict[str, dict] = {
    "open":       {},
    "mysterious": {"tempo": [58, 84], "groove": "free", "pitch": "modes", "scales": ["phrygian", "locrian", "whole tone", "19-edo"],
                   "space": "hall", "palette": ["modular drone", "texture", "voice", "glass"]},
    "energetic":  {"tempo": [112, 144], "groove": "straight", "pitch": "modes", "scales": ["mixolydian", "lydian", "pentatonic"],
                   "space": "room", "palette": ["percussive", "analog", "digital"]},
    "angry":      {"tempo": [100, 134], "groove": "broken", "pitch": "free", "scales": ["phrygian", "locrian"],
                   "space": "dry", "palette": ["analog", "percussive", "texture", "digital"]},
    "tranquil":   {"tempo": [52, 76], "groove": "drone", "pitch": "modes", "scales": ["lydian", "ionian", "pentatonic"],
                   "space": "hall", "palette": ["pad", "plucked", "glass", "modular drone"]},
    "playful":    {"tempo": [96, 124], "groove": "swing", "pitch": "modes", "scales": ["mixolydian", "pentatonic", "dorian"],
                   "space": "echo", "palette": ["plucked", "digital", "percussive", "voice"]},
}

SHAPES = {"modular drone": "blob", "digital": "square", "analog": "hex", "percussive": "diamond", "plucked": "teardrop",
          "texture": "cloud", "pad": "pill", "voice": "egg", "glass": "triangle"}


@dataclass
class Direction:
    mood: str = "open"
    palette: list[str] = field(default_factory=list)      # empty = anything
    space: str = "room"
    tempo: list[int] = field(default_factory=lambda: [72, 120])
    groove: str = "free"
    pitch: str = "free"                                    # modes | microtonal | free
    scale: str = ""                                        # empty = pick from the mood's scales / all
    root_hz: float = 110.0
    words: str = ""                                        # anything else, for the mind

    def apply_mood(self, mood: str) -> "Direction":
        self.mood = mood
        m = MOODS.get(mood, {})
        if m:
            self.tempo = list(m["tempo"]); self.groove = m["groove"]; self.pitch = m["pitch"]
            self.space = m["space"]; self.palette = list(m["palette"]); self.scale = ""
        return self

    def pick_tempo(self, rng: random.Random) -> int:
        lo, hi = sorted(int(v) for v in self.tempo[:2]) if len(self.tempo) >= 2 else (72, 120)
        return rng.randint(lo, max(lo, hi))

    def pick_scale(self, rng: random.Random) -> str | None:
        if self.pitch == "free":
            return None
        if self.scale and self.scale in SCALES:
            return self.scale
        pool = MOODS.get(self.mood, {}).get("scales") or (MODAL if self.pitch == "modes" else MICRO)
        pool = [s for s in pool if (s in MICRO) == (self.pitch == "microtonal")] or (MICRO if self.pitch == "microtonal" else MODAL)
        return rng.choice(pool)

    def text(self) -> str:
        bits = []
        if self.mood != "open":
            bits.append(f"mood: {self.mood}")
        if self.palette:
            bits.append("sound: " + ", ".join(self.palette))
        bits.append(f"space: {self.space}")
        bits.append(f"tempo around {self.tempo[0]}-{self.tempo[1]} bpm")
        bits.append(f"groove: {self.groove}")
        bits.append("pitch: " + (self.pitch if not self.scale else f"{self.pitch} ({self.scale})"))
        if self.words:
            bits.append(self.words)
        return "; ".join(bits)


def asdict_(d: Direction) -> dict:
    return asdict(d)


def load(root: Path | str) -> Direction:
    p = Path(root) / "direction.json"
    if p.exists():
        try:
            d = json.loads(p.read_text())
            return Direction(**{k: v for k, v in d.items() if k in Direction.__dataclass_fields__})
        except (OSError, ValueError, TypeError):
            pass
    return Direction()


def save(root: Path | str, d: Direction) -> None:
    p = Path(root) / "direction.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(d), indent=1))


# ---------------------------------------------------------------- palettes

PALETTE_RE = re.compile(r"^\s*;\s*palette\s*:\s*(.+?)\s*$", re.M)


def palette_of(text: str) -> str:
    m = PALETTE_RE.search(text)
    return m.group(1).strip().lower() if m else "digital"


def cast_weight(palette: str, d: Direction) -> float:
    if not d.palette:
        return 1.0
    return 3.0 if palette in d.palette else 0.6


# ------------------------------------------------------------------ pitch

def scale_pitches(scale: str, root_hz: float, lo: float = 20.0, hi: float = 8000.0) -> list[float]:
    s = SCALES[scale]
    out = []
    period = s["period"] / 1200.0  # in octaves
    k = -8
    while True:
        base = root_hz * (2 ** (period * k))
        if base > hi:
            break
        for c in s["cents"]:
            f = base * (2 ** (c / 1200.0))
            if lo <= f <= hi:
                out.append(f)
        k += 1
    return sorted(out)


def quantize_hz(hz: float, pitches: list[float]) -> float:
    if not pitches:
        return hz
    lh = math.log(hz)
    return min(pitches, key=lambda p: abs(math.log(p) - lh))


def tune_rows(rows, scale: str | None, root_hz: float) -> tuple[list, bool]:
    """Snap pitch-like p-fields (20..8000) in i-line token lists to the scale."""
    if not scale:
        return rows, False
    pitches = scale_pitches(scale, root_hz)
    changed = False
    for _, toks in rows:
        for k in range(3, len(toks)):
            try:
                v = float(toks[k])
            except ValueError:
                continue
            if 20 <= v <= 8000:
                q = quantize_hz(v, pitches)
                if abs(q - v) > 0.01:
                    toks[k] = f"{q:.4g}"; changed = True
                break  # one pitch column per event
    return rows, changed


# ------------------------------------------------------------------ groove

def groove_rows(rows, groove: str, beat: float, seconds: float, rng: random.Random) -> tuple[list, bool]:
    """Re-seat onsets on the grid the conductor asked for."""
    if groove in ("free", "") or not rows:
        return rows, False
    out = []
    for i, toks in rows:
        try:
            s, d = float(toks[1]), float(toks[2])
        except ValueError:
            out.append((i, toks)); continue
        if groove == "straight":
            q = beat / 4
            s = round(s / q) * q
        elif groove == "swing":
            q = beat / 2
            n = round(s / q)
            s = n * q + (q * 0.33 if n % 2 == 1 else 0.0)
        elif groove == "broken":
            if rng.random() < 0.15:
                continue
            if rng.random() < 0.35:
                s += rng.choice([-1, 1]) * beat / 8
        elif groove == "drone":
            if rng.random() < 0.55:
                continue
            d *= rng.choice([2, 3, 4])
            s = round(s / beat) * beat
        s = max(0.0, min(s, seconds - 0.05))
        d = max(0.05, min(d, seconds - s))
        toks[1], toks[2] = f"{s:.3f}", f"{d:.3f}"
        out.append((i, toks))
    if not out:
        return rows, False
    return out, True
