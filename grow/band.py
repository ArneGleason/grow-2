"""The band loop: songs written together, grown by responding.

  init:  a few bands jam. Each picks players, a tempo and a bar count; the
         first lays down a fitted founder piece, each next player joins and
         answers what is already there.
  run:   each generation picks parent songs (uniformly, or weighted by the
         listener's approval) and makes children: mostly one player
         responding to the others; sometimes a part swapped for a relative,
         a player added, a player dropped, or the tempo moved. Children go
         to the song map; the ear decides who stays.
"""

from __future__ import annotations

import math
import random
import time
from pathlib import Path

from . import ARCHIVE_DIR
from .archive import Archive
from .ears import Descriptors, describe, features
from .genome import Genome
from . import mind as mind_mod
from .respond import respond, jam
from .song import (Song, SongArchive, fit_to_grid, hear_part, keep_part, discard_part, render_mix, stage_name)
from .taste import Probe


class Band:
    def __init__(self, root: Path | str = ARCHIVE_DIR, seed: int | None = None, use_mind: bool = False, verbose: bool = True):
        self.root = Path(root)
        self.archive = Archive.open(self.root)
        self.songs = SongArchive(self.root)
        self.rng = random.Random(seed)
        self.verbose = verbose
        self.use_mind = use_mind and mind_mod.available()
        if use_mind and not self.use_mind:
            self.say("mind requested but Ollama is not reachable; blind responders only")
        self.probe = Probe.load(self.root / "taste.json")
        self.born: list[dict] = []

    def say(self, msg: str) -> None:
        if self.verbose:
            print(msg, flush=True)

    # ------------------------------------------------------------ families
    def families(self) -> dict[str, list]:
        fams: dict[str, list] = {}
        for c in self.archive.clips.values():
            if c.status in ("alive", "part"):
                fams.setdefault(self.archive.family_of(c.id), []).append(c)
        return fams

    def name_song(self) -> str:
        taken = {s.name for s in self.songs.songs.values()}
        for _ in range(30):
            nm = mind_mod.fallback_name(self.rng)
            if nm not in taken:
                return nm
        return f"song {len(self.songs.songs) + 1}"

    # ------------------------------------------------------------------ ear
    def ear(self, song: Song) -> tuple[float, str]:
        f = self.songs.feats(song)
        if f is None:
            return 0.0, "unheard"
        nov = self.songs.novelty(f, exclude=song.id)
        if self.probe is None:
            return nov, "novelty"
        return 0.7 * self.probe.score_feats(f) + 0.3 * nov, f"taste{self.probe.n_votes}"

    # ----------------------------------------------------------------- init
    def init_songs(self, n: int = 3, tempos=(72, 84, 96, 108, 120), bars_choices=(4, 8, 8)) -> list[Song]:
        fams = self.families()
        founders = {fam: next((c for c in clips if c.genome.author == "seed"), clips[0]) for fam, clips in fams.items()}
        if not founders:
            self.say("no families; run `python -m grow init` first")
            return []
        out = []
        for _ in range(n):
            k = min(len(founders), self.rng.choice([2, 3, 3, 4]))
            cast = self.rng.sample(sorted(founders), k)
            tempo, bars = self.rng.choice(tempos), self.rng.choice(bars_choices)
            name = self.name_song()
            self.say(f"jam: {name} · {' + '.join(stage_name(self.archive, f) for f in cast)} · {tempo} bpm, {bars} bars")
            song = jam(self.archive, self.songs, [(f, founders[f].id) for f in cast], tempo, bars, self.rng, self.use_mind, name, self.verbose)
            kept, why = self.songs.offer(song, self.ear)
            self.say(f"  {'+' if kept else '-'} {song.name}: {why}  [{Descriptors(**song.descriptors).facts() if song.descriptors else 'no mix'}]")
            out.append(song)
        return out

    # ------------------------------------------------------------ operators
    def swap_part(self, song: Song, family: str) -> tuple[Song | None, str]:
        """Replace a player's part with a relative from the family, fitted to the grid."""
        fam_clips = [c for c in self.families().get(family, []) if c.id != song.parts.get(family)]
        if not fam_clips:
            return None, "no relative to swap in"
        base = self.rng.choice(fam_clips)
        text = fit_to_grid(base.genome.text, song.seconds, song.beat, quantize=True, rng=self.rng)
        r, d = hear_part(self.archive, text, song)
        if not r.ok:
            discard_part(d); return None, f"swap failed: {r.reason}"
        clip = keep_part(self.archive, base.genome.child(text, "fit", f"{base.genome.name} fitted"), d, song, family, describe(r.audio, r.sr))
        child = song.child("swap", f"{stage_name(self.archive, family)} brings in {base.genome.name}", parts={**song.parts, family: clip.id})
        return child, "swapped"

    def add_player(self, song: Song) -> tuple[Song | None, str]:
        fams = self.families()
        free = [f for f in fams if f not in song.parts]
        if not free:
            return None, "everyone is already playing"
        family = self.rng.choice(free)
        founders = [c for c in fams[family] if c.genome.author == "seed"] or fams[family]
        base = self.rng.choice(founders)
        text = fit_to_grid(base.genome.text, song.seconds, song.beat, quantize=True, rng=self.rng)
        r, d = hear_part(self.archive, text, song)
        if not r.ok:
            discard_part(d); return None, f"could not join: {r.reason}"
        clip = keep_part(self.archive, base.genome.child(text, "fit", f"{base.genome.name} fitted"), d, song, family, describe(r.audio, r.sr))
        joined = song.child("add", f"{stage_name(self.archive, family)} joins", parts={**song.parts, family: clip.id})
        answered, _ = respond(self.archive, self.songs, joined, family, self.rng, self.use_mind, k=3)
        if answered is not None:
            answered.note = f"{stage_name(self.archive, family)} joins and answers"; answered.author = "add"
            return answered, "joined and answered"
        return joined, "joined"

    def drop_player(self, song: Song) -> tuple[Song | None, str]:
        if len(song.parts) < 2:
            return None, "cannot drop the only player"
        family = self.rng.choice(sorted(song.parts))
        parts = {f: c for f, c in song.parts.items() if f != family}
        return song.child("drop", f"{stage_name(self.archive, family)} sits this one out", parts=parts), "dropped"

    # ----------------------------------------------------------------- loop
    def generation(self, batch: int = 6, weights: dict[str, float] | None = None) -> int:
        pool = self.songs.alive()
        if not pool:
            self.say("no songs; run `python -m grow band init` first")
            return 0
        kept = 0
        for _ in range(batch):
            parent = self.rng.choices(pool, weights=[max(1e-3, weights.get(s.id, 1.0)) for s in pool])[0] if weights else self.rng.choice(pool)
            r = self.rng.random()
            child, why = None, ""
            if r < 0.7 or len(parent.parts) < 2:
                family = self.rng.choice(sorted(parent.parts))
                child, why = respond(self.archive, self.songs, parent, family, self.rng, self.use_mind, k=3, verbose=self.verbose)
            elif r < 0.8:
                child, why = self.swap_part(parent, self.rng.choice(sorted(parent.parts)))
            elif r < 0.9:
                child, why = self.add_player(parent)
            else:
                child, why = self.drop_player(parent)
            if child is None:
                self.say(f"  x {parent.name}: {why}")
                continue
            child.name = parent.name if child.author == "respond" else self.name_song() if child.author in ("add", "drop") else parent.name
            desc = render_mix(self.archive, self.songs, child)
            if desc is None:
                self.say(f"  x {child.note}: no mix"); continue
            kept_, why2 = self.songs.offer(child, self.ear)
            mark = "+" if kept_ else "-"
            self.say(f"  {mark} {child.name:16s} {child.note:40s} {why2}  [{desc.facts()}]")
            if kept_:
                kept += 1
                self.born.append({"id": child.id, "name": child.name, "note": child.note, "parent": parent.name, "author": child.author})
        return kept

    def run(self, generations: int, batch: int = 6, weights: dict[str, float] | None = None) -> None:
        for g in range(generations):
            self.say(f"generation {g + 1}/{generations}")
            k = self.generation(batch, weights)
            self.say(f"  kept {k}/{batch}")
        self.say(self.songs.status_line())
