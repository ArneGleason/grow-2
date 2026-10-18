"""Songs: pieces written together.

A song is a grid (tempo, bars) and one part per player, every part exactly
the song's length so they play in lockstep. The song is the organism the
show plays and the listener approves. Parts are its organs; they live in the
clip archive with status "part" so a family's repertoire includes them.

Nothing here judges music. The grid is a convention, like a count-in.
"""

from __future__ import annotations

import json
import math
import random
import secrets
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

import numpy as np
import soundfile as sf

from .archive import Archive, Clip, GRID, CELL_CAPACITY, cell_of
from .body import render, Rendered
from .ears import Descriptors, describe, features, FEATURE_KEYS
from .genome import Genome, SCORE_RE, I_LINE_RE, save as save_genome

BEATS_PER_BAR = 4

# stage names for the founders; anything else takes its founder's first word
STAGE_NAMES = {
    "drone-additive": "Moss", "modular-drone": "Moss", "fm-bells": "Chime", "digital-chime": "Chime",
    "grain-weather": "Weather", "noise-drums": "Tick", "drum-kit": "Tick", "pluck-garden": "Pluck",
    "squelch": "Squelch", "analog-bass": "Squelch", "pad-dusk": "Dusk", "pulse-wire": "Wire",
    "voice-moth": "Moth", "glass-bowl": "Bowl",
}


def stage_name(archive: Archive, family: str) -> str:
    root = archive.clips.get(family)
    founder = (root.genome.name if root else family) or family
    return STAGE_NAMES.get(founder, founder.split("-")[0].capitalize() or family)


def family_palette(archive: Archive, family: str) -> str:
    from .direction import palette_of
    root = archive.clips.get(family)
    return palette_of(root.genome.text) if root else "digital"


@dataclass
class Song:
    tempo: float
    bars: int
    parts: dict[str, str]                 # family id -> clip id
    id: str = field(default_factory=lambda: secrets.token_hex(4))
    name: str = ""
    parent: str | None = None
    generation: int = 0
    author: str = "jam"                   # jam | respond | swap | add | drop | grid
    note: str = ""
    created: float = field(default_factory=time.time)
    status: str = "alive"
    quality: float = 0.0
    ear: str = "novelty"
    descriptors: dict | None = None
    cell: list[int] | None = None
    scale: str = ""                       # the scale the band was tuned to, if any
    root_hz: float = 110.0
    groove: str = "free"

    @property
    def beat(self) -> float:
        return 60.0 / self.tempo

    @property
    def seconds(self) -> float:
        return self.bars * BEATS_PER_BAR * self.beat

    def grid_text(self) -> str:
        t = f"{self.tempo:.0f} bpm, {self.bars} bars of {BEATS_PER_BAR} beats, {self.seconds:.1f} seconds total"
        if self.scale:
            t += f", tuned to {self.scale} on {self.root_hz:.0f} Hz"
        if self.groove and self.groove != "free":
            t += f", {self.groove} groove"
        return t

    def child(self, author: str, note: str, parts: dict[str, str] | None = None, tempo: float | None = None, bars: int | None = None) -> "Song":
        return Song(tempo=tempo or self.tempo, bars=bars or self.bars, parts=dict(parts or self.parts),
                    parent=self.id, generation=self.generation + 1, author=author, note=note,
                    scale=self.scale, root_hz=self.root_hz, groove=self.groove)


# ------------------------------------------------------------- score helpers

def score_rows(text: str) -> tuple[list[str], list[tuple[int, list[str]]]]:
    """The score's lines, and (line index, tokens) for each i-statement before `e`."""
    m = SCORE_RE.search(text)
    if not m:
        return [], []
    lines = m.group(1).splitlines()
    rows = []
    for i, line in enumerate(lines):
        if line.strip() == "e":
            break
        im = I_LINE_RE.match(line)
        if not im:
            continue
        toks = line.split()
        if toks[0] == "i":
            toks = ["i" + toks[1]] + toks[2:]
        rows.append((i, toks))
    return lines, rows


def with_score_rows(text: str, lines: list[str], rows: list[tuple[int, list[str]]], extra: list[list[str]] | None = None) -> str:
    """Rebuild the score: i-lines before `e` are replaced by `rows` (others dropped),
    `extra` i-lines are added just before `e`."""
    keep = {i: toks for i, toks in rows}
    end = next((j for j, l in enumerate(lines) if l.strip() == "e"), len(lines))
    out = []
    for i, line in enumerate(lines):
        if i in keep:
            out.append(" ".join(keep[i]))
        elif i < end and I_LINE_RE.match(line):
            continue
        else:
            out.append(line)
    end = next((j for j, l in enumerate(out) if l.strip() == "e"), None)
    if end is None:
        out.append("e"); end = len(out) - 1
    if extra:
        out[end:end] = [" ".join(r) for r in extra]
    body = "\n".join(out)
    return SCORE_RE.sub(lambda _: f"<CsScore>\n{body}\n</CsScore>", text, count=1)


def fnum(s: str) -> float | None:
    try:
        return float(s)
    except ValueError:
        return None


def fit_to_grid(text: str, seconds: float, beat: float, quantize: bool = True, rng: random.Random | None = None,
                groove: str | None = None, scale: str | None = None, root_hz: float = 110.0) -> str:
    """Re-time a piece so its score spans the song's length and sits on the beat.

    Starts and durations are scaled so the last event ends near `seconds`,
    starts are snapped to the nearest quarter beat, and anything past the end
    is dropped. A convention, not a judgment: it is how a part joins a band.
    """
    lines, rows = score_rows(text)
    if not rows:
        return text
    ends = [fnum(t[1]) + fnum(t[2]) for _, t in rows if fnum(t[1]) is not None and fnum(t[2]) is not None]
    span = max(ends) if ends else seconds
    k = seconds / span if span > 0 else 1.0
    kept = []
    for i, toks in rows:
        s, d = fnum(toks[1]), fnum(toks[2])
        if s is None or d is None:
            continue
        s *= k; d *= k
        if quantize:
            q = beat / 4
            s = round(s / q) * q
        if s >= seconds - 0.01:
            continue
        d = min(d, seconds - s)
        toks[1], toks[2] = f"{s:.3f}", f"{max(d, 0.05):.3f}"
        kept.append((i, toks))
    if groove or scale:
        from .direction import groove_rows, tune_rows
        r = rng or random.Random()
        if groove:
            kept, _ = groove_rows(kept, groove, beat, seconds, r)
        if scale:
            kept, _ = tune_rows(kept, scale, root_hz)
    return with_score_rows(text, lines, kept)


# ------------------------------------------------------------------- audio

def read_stem(wav: Path, seconds: float, sr_expect: int = 44100) -> np.ndarray:
    data, sr = sf.read(str(wav), dtype="float32", always_2d=True)
    n = int(seconds * sr)
    if data.shape[0] < n:
        data = np.vstack([data, np.zeros((n - data.shape[0], data.shape[1]), dtype=np.float32)])
    return data[:n]


def mix_stems(wavs: list[Path], seconds: float) -> tuple[np.ndarray, int]:
    """Sum stems (already in lockstep) to one stereo array; peak-normalized for listening."""
    sr = 44100
    acc = None
    for w in wavs:
        d = read_stem(w, seconds, sr)
        acc = d if acc is None else acc + d
    if acc is None:
        return np.zeros((int(seconds * sr), 2), dtype=np.float32), sr
    peak = float(np.max(np.abs(acc)))
    if peak > 1e-6:
        acc = acc * (0.85 / peak)
    return acc.astype(np.float32), sr


def envelope(mono: np.ndarray, sr: int, hop_s: float = 0.05) -> np.ndarray:
    hop = max(1, int(hop_s * sr))
    n = len(mono) // hop
    if n == 0:
        return np.zeros(1)
    return np.sqrt((mono[: n * hop].reshape(n, hop) ** 2).mean(axis=1))


# ------------------------------------------------------------- song archive

class SongArchive:
    """The map of songs: same niches as the clip map, measured on the mix."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.dir = self.root / "songs"
        self.songs: dict[str, Song] = {}
        if self.dir.exists():
            for d in sorted(self.dir.iterdir()):
                f = d / "song.json"
                if f.exists():
                    try:
                        self.songs[d.name] = Song(**json.loads(f.read_text()))
                    except (OSError, ValueError, TypeError):
                        continue

    def song_dir(self, song_id: str) -> Path:
        return self.dir / song_id

    def save(self, song: Song) -> None:
        d = self.song_dir(song.id); d.mkdir(parents=True, exist_ok=True)
        (d / "song.json").write_text(json.dumps(asdict(song), indent=1))
        self.songs[song.id] = song

    def alive(self) -> list[Song]:
        return [s for s in self.songs.values() if s.status == "alive"]

    def lineage(self, song_id: str) -> list[Song]:
        out, seen = [], set()
        cur = self.songs.get(song_id)
        while cur and cur.id not in seen:
            out.append(cur); seen.add(cur.id)
            cur = self.songs.get(cur.parent) if cur.parent else None
        return out

    def children(self, song_id: str) -> list[Song]:
        return [s for s in self.songs.values() if s.parent == song_id]

    def feats(self, song: Song) -> np.ndarray | None:
        return features(Descriptors(**song.descriptors)) if song.descriptors else None

    def _stats(self) -> tuple[np.ndarray, np.ndarray]:
        m = [f for f in (self.feats(s) for s in self.alive()) if f is not None]
        if len(m) < 2:
            return np.zeros(len(FEATURE_KEYS)), np.ones(len(FEATURE_KEYS))
        m = np.stack(m)
        return m.mean(axis=0), m.std(axis=0) + 1e-6

    def novelty(self, feats: np.ndarray, k: int = 5, exclude: str | None = None) -> float:
        mu, sd = self._stats()
        z = (feats - mu) / sd
        d = sorted(np.linalg.norm((f - mu) / sd - z) for s in self.alive() if s.id != exclude and (f := self.feats(s)) is not None)
        return float(np.mean(d[:k])) if d else 1.0

    def occupants(self, cell: tuple[int, int]) -> list[Song]:
        return [s for s in self.alive() if s.cell and tuple(s.cell) == tuple(cell)]

    def is_duplicate(self, song: Song) -> bool:
        parts = set(song.parts.values())
        f = self.feats(song)
        mu, sd = self._stats()
        for s in self.alive():
            if s.id == song.id:
                continue
            if set(s.parts.values()) == parts:
                return True
            g = self.feats(s)
            if f is not None and g is not None and np.linalg.norm((f - mu) / sd - (g - mu) / sd) < 0.05:
                return True
        return False

    def offer(self, song: Song, scorer) -> tuple[bool, str]:
        if self.is_duplicate(song):
            song.status = "duplicate"; self.save(song)
            return False, "duplicate of a song already on the map"
        quality, ear = scorer(song)
        song.quality, song.ear = quality, ear
        cell = tuple(song.cell or (0, 0))
        occ = [s for s in self.occupants(cell) if s.id != song.id]
        if len(occ) < CELL_CAPACITY:
            song.status = "alive"; self.save(song)
            return True, f"new niche {cell}" if not occ else f"room in {cell}"
        for s in occ:
            s.quality, s.ear = scorer(s); self.save(s)
        weakest = min(occ, key=lambda s: s.quality)
        if quality > weakest.quality:
            weakest.status = "evicted"; self.save(weakest)
            song.status = "alive"; self.save(song)
            return True, f"replaced {weakest.name or weakest.id} in {cell}"
        song.status = "declined"; self.save(song)
        return False, f"cell {cell} full; {ear} {quality:.2f} <= {weakest.quality:.2f}"

    def status_line(self) -> str:
        alive = self.alive()
        cells = {tuple(s.cell) for s in alive if s.cell}
        return f"{len(alive)} songs in {len(cells)}/{GRID * GRID} niches; {len(self.songs) - len(alive)} retired"


# ----------------------------------------------------------- parts on disk

def part_wav(archive: Archive, clip_id: str) -> Path:
    return archive.clip_dir(clip_id) / "clip.wav"


def hear_part(archive: Archive, text: str, song: Song) -> tuple[Rendered, Path]:
    """Render a candidate part at the song's length into a scratch clip dir."""
    cid = secrets.token_hex(4)
    d = archive.clip_dir(cid)
    r = render(text, d / "clip.wav", fixed_seconds=song.seconds)
    return r, d


def keep_part(archive: Archive, genome: Genome, clip_dir: Path, song: Song, family: str, desc: Descriptors) -> Clip:
    """Store a part in the clip archive with status 'part' so it joins the family's repertoire."""
    genome.id = clip_dir.name
    if not genome.name:
        # a part is named by what it did, so the stage can say "Moss · doubles the rhythm"
        note = genome.note or ""
        genome.name = note.replace(" fitted to the grid", "").replace(" fitted", "") if note else f"{song.name} part"
    clip = Clip(genome=genome, descriptors=desc, cell=cell_of(desc), dir=clip_dir, status="part")
    archive.clips[clip.id] = clip
    save_genome(genome, clip_dir, extra={
        "descriptors": desc.as_dict(), "cell": list(clip.cell), "status": "part",
        "quality": 0.0, "ear": "part", "song": song.id, "family": family,
        "grid": {"tempo": song.tempo, "bars": song.bars, "seconds": song.seconds},
    })
    return clip


def discard_part(clip_dir: Path) -> None:
    if clip_dir.exists():
        for f in clip_dir.iterdir():
            f.unlink()
        clip_dir.rmdir()


def render_mix(archive: Archive, songs: SongArchive, song: Song) -> Descriptors | None:
    """Mix the song's stems, save mix.wav, and measure it. Returns the mix descriptors."""
    wavs = [part_wav(archive, cid) for cid in song.parts.values() if part_wav(archive, cid).exists()]
    if not wavs:
        return None
    data, sr = mix_stems(wavs, song.seconds)
    d = songs.song_dir(song.id); d.mkdir(parents=True, exist_ok=True)
    sf.write(str(d / "mix.wav"), data, sr, subtype="PCM_16")
    desc = describe(data.mean(axis=1), sr)
    song.descriptors = desc.as_dict(); song.cell = list(cell_of(desc))
    return desc
