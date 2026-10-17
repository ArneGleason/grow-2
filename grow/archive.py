"""The archive is the terrarium: a map of niches, each holding a few clips.

This is MAP-Elites in its simplest form. The map's axes are two descriptor
measurements (how many events per second, how bright). A new clip enters if
its cell has room, or if it scores higher than the weakest occupant on the
current ear. Before any votes exist the ear is novelty: distance from
everything else in the archive. Once votes exist the ear is the taste probe.

Nothing hand-written says what is good. Evicted clips keep their files so
lineages stay playable.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import ARCHIVE_DIR
from .ears import FEATURE_KEYS, features, Descriptors
from .genome import Genome, load as load_genome

GRID = 10
CELL_CAPACITY = 3
ONSET_RANGE = (math.log10(0.1), math.log10(16.0))      # onsets per second, log10
CENTROID_RANGE = (math.log2(80.0), math.log2(8000.0))  # Hz, log2


def cell_of(d: Descriptors) -> tuple[int, int]:
    def bin_(v: float, lo: float, hi: float) -> int:
        return int(np.clip((v - lo) / (hi - lo) * GRID, 0, GRID - 1))
    cx = bin_(math.log10(max(d.onset_density, 1e-3)), *ONSET_RANGE)
    cy = bin_(math.log2(max(d.centroid_hz, 1.0)), *CENTROID_RANGE)
    return cx, cy


@dataclass
class Clip:
    genome: Genome
    descriptors: Descriptors
    cell: tuple[int, int]
    dir: Path
    status: str = "alive"
    embedding: np.ndarray | None = None
    quality: float = 0.0
    ear: str = "novelty"

    @property
    def id(self) -> str:
        return self.genome.id

    @property
    def wav(self) -> Path:
        return self.dir / "clip.wav"

    def feats(self) -> np.ndarray:
        return features(self.descriptors)


@dataclass
class Archive:
    root: Path
    clips: dict[str, Clip] = field(default_factory=dict)   # all clips, alive or evicted
    rejections: list[dict] = field(default_factory=list)

    # ------------------------------------------------------------ persistence
    @classmethod
    def open(cls, root: Path | str = ARCHIVE_DIR) -> "Archive":
        root = Path(root)
        arc = cls(root=root)
        clips_dir = root / "clips"
        if clips_dir.exists():
            for d in sorted(clips_dir.iterdir()):
                if not (d / "meta.json").exists():
                    continue
                genome, meta = load_genome(d)
                desc = Descriptors(**meta["descriptors"])
                emb = None
                if (d / "embedding.npy").exists():
                    emb = np.load(d / "embedding.npy")
                arc.clips[genome.id] = Clip(
                    genome=genome, descriptors=desc, cell=tuple(meta["cell"]), dir=d,
                    status=meta.get("status", "alive"), embedding=emb,
                    quality=meta.get("quality", 0.0), ear=meta.get("ear", "novelty"),
                )
        return arc

    def clip_dir(self, clip_id: str) -> Path:
        return self.root / "clips" / clip_id

    def _write_meta(self, clip: Clip) -> None:
        meta = clip.genome.meta()
        meta.update({
            "descriptors": clip.descriptors.as_dict(),
            "cell": list(clip.cell),
            "status": clip.status,
            "quality": clip.quality,
            "ear": clip.ear,
        })
        (clip.dir / "meta.json").write_text(json.dumps(meta, indent=1))

    def log_rejection(self, genome: Genome, reason: str) -> None:
        rec = {"id": genome.id, "author": genome.author, "parent": genome.parent, "reason": reason, "note": genome.note}
        self.rejections.append(rec)
        self.root.mkdir(parents=True, exist_ok=True)
        with (self.root / "rejected.jsonl").open("a") as fh:
            fh.write(json.dumps(rec) + "\n")

    # ------------------------------------------------------------------ views
    def alive(self) -> list[Clip]:
        return [c for c in self.clips.values() if c.status == "alive"]

    def occupants(self, cell: tuple[int, int]) -> list[Clip]:
        return [c for c in self.alive() if c.cell == cell]

    def grid(self) -> dict[tuple[int, int], list[Clip]]:
        g: dict[tuple[int, int], list[Clip]] = {}
        for c in self.alive():
            g.setdefault(c.cell, []).append(c)
        return g

    def empty_cells(self) -> list[tuple[int, int]]:
        g = self.grid()
        return [(x, y) for x in range(GRID) for y in range(GRID) if (x, y) not in g]

    def lineage(self, clip_id: str) -> list[Clip]:
        out: list[Clip] = []
        seen = set()
        cur = self.clips.get(clip_id)
        while cur and cur.id not in seen:
            out.append(cur)
            seen.add(cur.id)
            cur = self.clips.get(cur.genome.parent) if cur.genome.parent else None
        return out

    # ---------------------------------------------------------------- novelty
    def _feature_stats(self) -> tuple[np.ndarray, np.ndarray]:
        pool = self.alive()
        if len(pool) < 2:
            return np.zeros(len(FEATURE_KEYS)), np.ones(len(FEATURE_KEYS))
        m = np.stack([c.feats() for c in pool])
        return m.mean(axis=0), m.std(axis=0) + 1e-6

    def novelty(self, feats: np.ndarray, embedding: np.ndarray | None = None, k: int = 5, exclude: str | None = None) -> float:
        """Mean distance to the k nearest alive clips. Geometry, not taste."""
        pool = [c for c in self.alive() if c.id != exclude]
        if not pool:
            return 1.0
        mu, sd = self._feature_stats()
        z = (feats - mu) / sd
        dists = []
        for c in pool:
            dz = np.linalg.norm((c.feats() - mu) / sd - z)
            if embedding is not None and c.embedding is not None:
                de = float(1.0 - np.dot(embedding, c.embedding))  # cosine distance, 0..2
                dz = 0.5 * dz + 2.0 * de
            dists.append(dz)
        dists.sort()
        return float(np.mean(dists[:k]))

    # ------------------------------------------------------------------ entry
    def is_duplicate(self, feats: np.ndarray, text: str) -> bool:
        for c in self.alive():
            if c.genome.text == text:
                return True
        mu, sd = self._feature_stats()
        z = (feats - mu) / sd
        for c in self.alive():
            if np.linalg.norm((c.feats() - mu) / sd - z) < 0.05:
                return True
        return False

    def offer(self, clip: Clip, scorer) -> tuple[bool, str]:
        """Try to place a clip. Returns (kept, reason). Writes files when kept.

        `scorer(clip) -> (quality, ear_name)` is the current ear. The cell's
        occupants are re-scored at the same moment so nobody holds a niche on
        a stale number as the map fills in around them.
        """
        quality, ear = scorer(clip)
        clip.quality, clip.ear = quality, ear
        cell = clip.cell
        occ = self.occupants(cell)
        if len(occ) < CELL_CAPACITY:
            self._admit(clip)
            return True, f"new niche {cell}" if not occ else f"room in {cell}"
        for c in occ:
            c.quality, c.ear = scorer(c)
            self._write_meta(c)
        weakest = min(occ, key=lambda c: c.quality)
        if quality > weakest.quality:
            weakest.status = "evicted"
            self._write_meta(weakest)
            self._admit(clip)
            return True, f"replaced {weakest.genome.name or weakest.id} in {cell} ({ear} {quality:.2f} > {weakest.quality:.2f})"
        return False, f"cell {cell} full; {ear} {quality:.2f} <= {weakest.quality:.2f}"

    def _admit(self, clip: Clip) -> None:
        clip.status = "alive"
        self.clips[clip.id] = clip
        self._write_meta(clip)
        if clip.embedding is not None:
            np.save(clip.dir / "embedding.npy", clip.embedding)

    def rescore(self, scorer) -> None:
        """Re-evaluate every alive clip with a new ear (after taste training)."""
        for c in self.alive():
            c.quality, c.ear = scorer(c)
            self._write_meta(c)

    # -------------------------------------------------------------- selection
    def pick_parent(self, rng: random.Random, recent: list[str] | None = None) -> Clip | None:
        pool = self.alive()
        if not pool:
            return None
        if recent and rng.random() < 0.25:
            fresh = [self.clips[i] for i in recent if i in self.clips and self.clips[i].status == "alive"]
            if fresh:
                return rng.choice(fresh)
        return rng.choice(pool)

    def nudge_toward_empty(self, clip: Clip, rng: random.Random) -> str:
        """Describe, in words, a direction from this clip toward an empty niche."""
        empties = self.empty_cells()
        if not empties:
            return rng.choice(["stranger", "more alive", "less polite", "more surprising"])
        tx, ty = rng.choice(empties)
        cx, cy = clip.cell
        words = []
        if tx > cx + 1:
            words.append("much denser, with many more events per second")
        elif tx > cx:
            words.append("a little denser")
        elif tx < cx - 1:
            words.append("much sparser, with long gaps")
        elif tx < cx:
            words.append("a little sparser")
        if ty > cy + 1:
            words.append("much brighter and higher")
        elif ty > cy:
            words.append("somewhat brighter")
        elif ty < cy - 1:
            words.append("much darker and lower")
        elif ty < cy:
            words.append("somewhat darker")
        return ", ".join(words) if words else "different in character but similar in density and brightness"

    def status_lines(self) -> list[str]:
        g = self.grid()
        alive = self.alive()
        evicted = sum(1 for c in self.clips.values() if c.status == "evicted")
        declined = sum(1 for c in self.clips.values() if c.status == "declined")
        lines = [f"{len(alive)} alive clips in {len(g)}/{GRID*GRID} niches; {evicted} evicted; {declined} declined; {len(self.rejections)} rejected this run"]
        lines.append("map (rows: bright at top; columns: sparse left to dense right)")
        for y in range(GRID - 1, -1, -1):
            row = ""
            for x in range(GRID):
                n = len(g.get((x, y), []))
                row += " ." if n == 0 else f" {n}"
            lines.append(row)
        return lines
