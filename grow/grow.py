"""The loop: make, hear, keep, vary.

Each generation:
  1. pick parents from the map (uniformly; stepping stones count as much as
     favorites),
  2. make children: blind variation, or a mind rewrite nudged toward an empty
     niche,
  3. render each child in the sandbox; log what fails and why,
  4. hear it: descriptors, optional embedding, a cell on the map,
  5. offer it to the archive; the current ear (novelty, or the taste probe
     once votes exist) decides who stays.

Nothing here is a test of musical quality. The listening sheet is.
"""

from __future__ import annotations

import random
import time
from pathlib import Path

from . import ARCHIVE_DIR, SEEDS_DIR
from .archive import Archive, Clip, cell_of
from .body import render, csound_available
from .ears import describe, embed, embedding_available, features
from .genome import Genome, load_seed, save as save_genome
from . import mind as mind_mod
from .taste import Probe
from . import vary


class Grower:
    def __init__(self, root: Path | str = ARCHIVE_DIR, seed: int | None = None, use_mind: bool = False,
                 use_embedding: bool | None = None, verbose: bool = True):
        self.root = Path(root)
        self.archive = Archive.open(self.root)
        self.rng = random.Random(seed)
        self.verbose = verbose
        self.use_mind = use_mind and mind_mod.available()
        if use_mind and not self.use_mind:
            self.say("mind requested but Ollama is not reachable; using blind variation only")
        self.use_embedding = embedding_available() if use_embedding is None else use_embedding
        self.probe = Probe.load(self.root / "taste.json")
        self.recent: list[str] = []

    def say(self, msg: str) -> None:
        if self.verbose:
            print(msg, flush=True)

    # --------------------------------------------------------------- hearing
    def hear(self, genome: Genome) -> tuple[Clip | None, str]:
        clip_dir = self.archive.clip_dir(genome.id)
        wav = clip_dir / "clip.wav"
        r = render(genome.text, wav)
        if not r.ok:
            self._discard(clip_dir)
            return None, r.reason
        desc = describe(r.audio, r.sr)
        emb = embed(r.audio, r.sr) if self.use_embedding else None
        clip = Clip(genome=genome, descriptors=desc, cell=cell_of(desc), dir=clip_dir, embedding=emb)
        return clip, "ok"

    def _discard(self, clip_dir: Path) -> None:
        if clip_dir.exists():
            for f in clip_dir.iterdir():
                f.unlink()
            clip_dir.rmdir()

    def ear(self, clip: Clip) -> tuple[float, str]:
        """The current ear. Novelty until votes exist; then the probe, blended with novelty."""
        nov = self.archive.novelty(features(clip.descriptors), clip.embedding, exclude=clip.id)
        if self.probe is None:
            return nov, "novelty"
        return 0.7 * self.probe.score(clip) + 0.3 * nov, f"taste{self.probe.n_votes}"

    def christen(self, clip: Clip) -> None:
        if clip.genome.name:
            return
        nm = None
        if self.use_mind:
            ancestors = [c.genome.name for c in self.archive.lineage(clip.genome.parent)[:3] if c.genome.name] if clip.genome.parent else []
            nm = mind_mod.name(clip.descriptors.facts(), ancestors, self.rng)
        taken = {c.genome.name for c in self.archive.clips.values()}
        if not nm or nm in taken:
            for _ in range(20):
                nm = mind_mod.fallback_name(self.rng)
                if nm not in taken:
                    break
            else:
                nm = f"{nm} {clip.genome.generation}"
        clip.genome.name = nm

    # ---------------------------------------------------------------- making
    def offer(self, genome: Genome) -> bool:
        clip, reason = self.hear(genome)
        if clip is None:
            self.archive.log_rejection(genome, reason)
            self.say(f"  x {genome.author:6s} {reason}")
            return False
        feats = features(clip.descriptors)
        if self.archive.is_duplicate(feats, genome.text):
            self._discard(clip.dir)
            self.archive.log_rejection(genome, "duplicate")
            self.say(f"  x {genome.author:6s} duplicate")
            return False
        self.christen(clip)
        save_genome(genome, clip.dir)
        kept, why = self.archive.offer(clip, self.ear)
        mark = "+" if kept else "-"
        self.say(f"  {mark} {genome.author:6s} {clip.genome.name:18s} {why}   [{clip.descriptors.facts()}]")
        if kept:
            self.recent.append(clip.id)
            self.recent = self.recent[-20:]
        else:
            clip.status = "declined"
            self.archive.clips[clip.id] = clip
            self.archive._write_meta(clip)
        return kept

    def init_from_seeds(self, seeds_dir: Path | str = SEEDS_DIR) -> int:
        n = 0
        for path in sorted(Path(seeds_dir).glob("*.csd")):
            g = load_seed(path)
            self.say(f"seed {g.name}")
            if self.offer(g):
                n += 1
        return n

    def generation(self, batch: int = 8, mind_share: float = 0.3) -> int:
        kept = 0
        for _ in range(batch):
            parent = self.archive.pick_parent(self.rng, self.recent)
            if parent is None:
                self.say("archive is empty; run init first")
                return 0
            child: Genome | None = None
            if self.use_mind and self.rng.random() < mind_share:
                nudge = self.archive.nudge_toward_empty(parent, self.rng)
                t0 = time.time()
                child = mind_mod.rewrite(parent.genome, parent.descriptors.facts(), nudge, self.rng)
                self.say(f"  mind {'wrote' if child else 'failed'} in {time.time() - t0:.0f}s from {parent.genome.name}: {nudge}")
            if child is None:
                mate = self.archive.pick_parent(self.rng)
                child = vary.blind(parent.genome, self.rng, mate.genome if mate and mate.id != parent.id else None)
            if self.offer(child):
                kept += 1
        return kept

    def run(self, generations: int, batch: int = 8, mind_share: float = 0.3) -> None:
        if not csound_available():
            raise SystemExit("csound is not on PATH; install Csound 6 first")
        for g in range(generations):
            self.say(f"generation {g + 1}/{generations}")
            kept = self.generation(batch, mind_share)
            self.say(f"  kept {kept}/{batch}")
        for line in self.archive.status_lines():
            self.say(line)
