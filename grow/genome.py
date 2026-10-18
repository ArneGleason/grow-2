"""A genome is a complete Csound .csd text plus lineage metadata.

The text is the whole organism: instruments (the body) and score (what it
plays). Nothing about the music lives outside this text. That is deliberate:
if a sound or a pattern can only be made by editing the engine, the engine
has become the composer, which is the failure Grow 1 taught us.
"""

from __future__ import annotations

import json
import re
import secrets
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

CSD_RE = re.compile(r"<CsoundSynthesizer>.*?</CsoundSynthesizer>", re.S)
INSTR_RE = re.compile(r"<CsInstruments>(.*?)</CsInstruments>", re.S)
SCORE_RE = re.compile(r"<CsScore>(.*?)</CsScore>", re.S)


def new_id() -> str:
    return secrets.token_hex(4)


@dataclass
class Genome:
    text: str
    id: str = field(default_factory=new_id)
    name: str = ""
    parent: str | None = None
    parents: list[str] = field(default_factory=list)
    generation: int = 0
    author: str = "seed"  # seed | jitter | score | cross | mind | human
    note: str = ""        # a one-line reason or nudge, for the lineage view
    created: float = field(default_factory=time.time)
    about: str = ""       # for a song part: the player it answers

    def instruments(self) -> str:
        m = INSTR_RE.search(self.text)
        return m.group(1) if m else ""

    def score(self) -> str:
        m = SCORE_RE.search(self.text)
        return m.group(1) if m else ""

    def with_parts(self, instruments: str | None = None, score: str | None = None) -> str:
        text = self.text
        if instruments is not None:
            text = INSTR_RE.sub(lambda _: f"<CsInstruments>{instruments}</CsInstruments>", text, count=1)
        if score is not None:
            text = SCORE_RE.sub(lambda _: f"<CsScore>{score}</CsScore>", text, count=1)
        return text

    def child(self, text: str, author: str, note: str = "", other: "Genome | None" = None) -> "Genome":
        parents = [self.id] + ([other.id] if other else [])
        return Genome(
            text=text,
            parent=self.id,
            parents=parents,
            generation=self.generation + 1,
            author=author,
            note=note,
        )

    def meta(self) -> dict:
        d = asdict(self)
        d.pop("text")
        d.pop("about", None)
        return d


def extract_csd(text: str) -> str | None:
    """Pull a complete .csd out of arbitrary text (a model reply, a file)."""
    m = CSD_RE.search(text)
    return m.group(0) if m else None


def load_seed(path: Path) -> Genome:
    text = path.read_text()
    csd = extract_csd(text)
    if csd is None:
        raise ValueError(f"{path} is not a complete .csd")
    return Genome(text=csd, name=path.stem, author="seed", note=f"founder {path.stem}")


def save(genome: Genome, clip_dir: Path, extra: dict | None = None) -> None:
    clip_dir.mkdir(parents=True, exist_ok=True)
    (clip_dir / "genome.csd").write_text(genome.text)
    meta = genome.meta()
    if extra:
        meta.update(extra)
    (clip_dir / "meta.json").write_text(json.dumps(meta, indent=1))


def load(clip_dir: Path) -> tuple[Genome, dict]:
    meta = json.loads((clip_dir / "meta.json").read_text())
    text = (clip_dir / "genome.csd").read_text()
    fields = {k: meta[k] for k in ("id", "name", "parent", "parents", "generation", "author", "note", "created") if k in meta}
    return Genome(text=text, **fields), meta


# ------------------------------------------------------------- for the stage

I_LINE_RE = re.compile(r"^\s*i\s*(\d+)\s+(\S+)\s+(\S+)(.*)$")


def instrument_labels(text: str) -> dict[int, str]:
    """instr number -> the comment line just above it, or 'voice N'."""
    labels: dict[int, str] = {}
    last_comment = ""
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(";"):
            last_comment = s.lstrip("; ").strip()
            continue
        m = re.match(r"^instr\s+(\d+)", s)
        if m:
            n = int(m.group(1))
            labels[n] = last_comment or f"voice {n}"
            last_comment = ""
            continue
        if s:
            last_comment = ""
    return labels


def score_events(text: str, max_seconds: float = 30.0) -> list[dict]:
    """The score's note events as [{instr, start, dur, amp, pitch}], for animation.

    amp is a guess: the first p-field in (0, 1]; pitch the first in [20, 8000].
    These drive pictures, not sound, so a wrong guess costs nothing.
    """
    out = []
    m = SCORE_RE.search(text)
    if not m:
        return out
    for line in m.group(1).splitlines():
        if line.strip() == "e":
            break
        im = I_LINE_RE.match(line)
        if not im:
            continue
        try:
            start, dur = float(im.group(2)), float(im.group(3))
        except ValueError:
            continue
        if start > max_seconds:
            continue
        rest = []
        for tok in im.group(4).split():
            if tok.startswith(";"):
                break
            try:
                rest.append(float(tok))
            except ValueError:
                pass
        amp = next((v for v in rest if 0 < v <= 1.0), 0.5)
        pitch = next((v for v in rest if 20 <= v <= 8000), 0.0)
        out.append({"instr": int(im.group(1)), "start": start, "dur": max(dur, 0.05), "amp": amp, "pitch": pitch})
    out.sort(key=lambda e: e["start"])
    return out
