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
