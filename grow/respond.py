"""Responding: one player rewrites its part given the others.

This is the operator that makes a band. A responder is a relation to what
the others are playing, never an opinion about whether it is good:

- echo:      play another part's rhythm, late by some beats
- double:    play another part's rhythm in unison
- gaps:      play where the others are quiet
- contrast:  thin where the others are dense, thicken where they are sparse
- room:      move register away from a neighbor
- rest:      drop out for a bar or two
- self:      vary my own part without looking (jitter, score edit)
- mind:      a language model writes the part with the others in front of it

A player drafts several candidates, hears each one in the mix, and puts
forward the one its own ear prefers. Before any approval exists that ear is
geometry: did my part change the mix, and is the mix new for this family.
After, it is a probe trained on the listener's reaction to songs this
player was in.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np

from .archive import Archive
from .ears import Descriptors, describe, features
from .genome import Genome
from . import mind as mind_mod
from .song import (Song, SongArchive, score_rows, with_score_rows, fnum, part_wav, read_stem, mix_stems,
                   envelope, hear_part, keep_part, discard_part, render_mix, fit_to_grid, stage_name, BEATS_PER_BAR)
from .taste import family_probe
from . import vary
from .direction import Direction, groove_rows, tune_rows

RESPONDERS = ["echo", "double", "gaps", "contrast", "room", "rest", "self"]


def groove(my_text, song, direction, rng):
    """Re-seat my onsets on the groove the conductor asked for."""
    g = direction.groove if direction else song.groove
    if not g or g == "free":
        return None, ""
    lines, rows = score_rows(my_text)
    rows, changed = groove_rows(rows, g, song.beat, song.seconds, rng)
    if not changed:
        return None, ""
    return with_score_rows(my_text, lines, rows), f"takes the {g} groove"


def tune(my_text, song, direction, rng):
    """Snap my pitches to the band's scale."""
    scale = song.scale or (direction.pick_scale(rng) if direction else None)
    if not scale:
        return None, ""
    lines, rows = score_rows(my_text)
    rows, changed = tune_rows(rows, scale, song.root_hz)
    if not changed:
        return None, ""
    return with_score_rows(my_text, lines, rows), f"tunes to {scale}"


# ------------------------------------------------------------ what the others do

def events_of(text: str) -> list[tuple[float, float, list[str]]]:
    """(start, dur, tokens) for each i-line."""
    _, rows = score_rows(text)
    out = []
    for _, toks in rows:
        s, d = fnum(toks[1]), fnum(toks[2])
        if s is not None and d is not None:
            out.append((s, d, toks))
    return out


def others_of(archive: Archive, song: Song, family: str) -> list[tuple[str, str]]:
    """(family, part text) for every other player in the song."""
    out = []
    for fam, cid in song.parts.items():
        if fam == family or cid not in archive.clips:
            continue
        out.append((stage_name(archive, fam), archive.clips[cid].genome.text))
    return out


def others_mix(archive: Archive, song: Song, family: str) -> tuple[np.ndarray, int]:
    wavs = [part_wav(archive, cid) for fam, cid in song.parts.items() if fam != family and part_wav(archive, cid).exists()]
    data, sr = mix_stems(wavs, song.seconds) if wavs else (np.zeros((int(song.seconds * 44100), 2), np.float32), 44100)
    return data.mean(axis=1), sr


# ------------------------------------------------------------------ responders

def _template(my_events, rng):
    """My own events as templates for new ones: instrument and extra p-fields."""
    return [toks for _, _, toks in my_events] or None


def _new_events(template, starts_durs, rng, amp_scale=1.0):
    rows, k = [], 0
    for s, d in starts_durs:
        t = list(template[k % len(template)]); k += 1
        t[1], t[2] = f"{s:.3f}", f"{max(d, 0.05):.3f}"
        if amp_scale != 1.0:
            for i in range(3, len(t)):
                v = fnum(t[i])
                if v is not None and 0 < v <= 1.0:
                    t[i] = f"{v * amp_scale:.3f}"; break
        rows.append(t)
    return rows


def echo(my_text, my_events, other_events, song, rng, delay_beats=None):
    tpl = _template(my_events, rng)
    if not tpl or not other_events:
        return None, ""
    delay = (delay_beats if delay_beats is not None else rng.choice([0.5, 1, 1.5, 2, 4])) * song.beat
    sd = [(s + delay, min(d, 2 * song.beat)) for s, d, _ in other_events if s + delay < song.seconds - 0.05]
    sd = sd[:48]
    if not sd:
        return None, ""
    lines, _ = score_rows(my_text)
    text = with_score_rows(my_text, lines, [], _new_events(tpl, sd, rng, 0.85))
    return text, f"echoes {'%.1f' % (delay / song.beat)} beats late"


def double(my_text, my_events, other_events, song, rng):
    text, _ = echo(my_text, my_events, other_events, song, rng, delay_beats=0)
    return text, "doubles the rhythm"


def gaps(my_text, my_events, others_env, sr_hop, song, rng):
    tpl = _template(my_events, rng)
    if not tpl:
        return None, ""
    env = others_env
    if env.max() < 1e-5:
        return None, ""
    quiet = env < np.percentile(env, 30)
    hop_s = sr_hop
    sd, t, i = [], 0.0, 0
    beat = song.beat
    while t < song.seconds - 0.05:
        j = int(t / hop_s)
        if j < len(quiet) and quiet[j]:
            d = rng.choice([0.5, 1, 1, 2]) * beat
            sd.append((t, min(d, song.seconds - t)))
            t += d
        else:
            t += beat / 2
    if not sd:
        return None, ""
    lines, _ = score_rows(my_text)
    return with_score_rows(my_text, lines, [], _new_events(tpl, sd[:48], rng)), "plays in the gaps"


def contrast(my_text, my_events, other_events, song, rng):
    if not my_events:
        return None, ""
    bar = song.beat * BEATS_PER_BAR
    counts = np.zeros(song.bars)
    for s, _, _ in other_events:
        b = int(s // bar)
        if 0 <= b < song.bars:
            counts[b] += 1
    med = np.median(counts)
    lines, rows = score_rows(my_text)
    kept, extra, seen_bar = [], [], set()
    for (i, toks) in rows:
        s, d = fnum(toks[1]), fnum(toks[2])
        if s is None:
            continue
        b = int(s // bar)
        dense = 0 <= b < song.bars and counts[b] > med
        if dense:
            if b in seen_bar:
                continue           # keep only my first event in a busy bar
            seen_bar.add(b); kept.append((i, toks))
        else:
            kept.append((i, toks))
            if s + song.beat / 2 < song.seconds - 0.05:
                t = list(toks); t[1] = f"{s + song.beat / 2:.3f}"; extra.append(t)
    return with_score_rows(my_text, lines, kept, extra[:24]), "thins where they are busy, doubles where they are sparse"


def room(my_text, my_events, song, rng, direction=None):
    """Move the pitch-like p-field an octave away."""
    lines, rows = score_rows(my_text)
    if not rows:
        return None, ""
    col = None
    for _, toks in rows:
        for k in range(3, len(toks)):
            v = fnum(toks[k])
            if v is not None and 20 <= v <= 8000:
                col = k; break
        if col:
            break
    if col is None:
        return None, ""
    f = direction or rng.choice([0.5, 2.0])
    for _, toks in rows:
        v = fnum(toks[col])
        if v is not None and 20 <= v * f <= 8000:
            toks[col] = f"{v * f:.4g}"
    return with_score_rows(my_text, lines, rows), f"moves {'up' if f > 1 else 'down'} an octave to make room"


def rest(my_text, my_events, song, rng):
    lines, rows = score_rows(my_text)
    if len(rows) < 3:
        return None, ""
    bar = song.beat * BEATS_PER_BAR
    n = rng.choice([1, 1, 2])
    silent = set(rng.sample(range(song.bars), min(n, song.bars)))
    kept = [(i, toks) for i, toks in rows if fnum(toks[1]) is not None and int(fnum(toks[1]) // bar) not in silent]
    if len(kept) == len(rows) or not kept:
        return None, ""
    return with_score_rows(my_text, lines, kept), f"sits out bar{'s' if n > 1 else ''} {', '.join(str(b + 1) for b in sorted(silent))}"


# ------------------------------------------------------------- the response

def candidates(archive: Archive, song: Song, family: str, rng: random.Random, use_mind: bool, k: int = 3,
               nudge: str | None = None, direction: Direction | None = None) -> list[tuple[Genome, str]]:
    """Draft k candidate parts for `family` in `song`, under the conductor's direction if any."""
    my_clip = archive.clips.get(song.parts.get(family, ""))
    if my_clip is None:
        return []
    my_text = my_clip.genome.text
    my_events = events_of(my_text)
    others = others_of(archive, song, family)
    other_events = sorted((e for _, t in others for e in events_of(t)), key=lambda e: e[0])
    om, sr = others_mix(archive, song, family)
    env = envelope(om, sr, 0.05)
    out: list[tuple[Genome, str]] = []
    ops = list(RESPONDERS)
    if direction and (direction.groove != "free" or song.groove not in ("", "free")):
        ops.append("groove")
    if song.scale or (direction and direction.pitch != "free"):
        ops.append("tune")
    rng.shuffle(ops)
    if use_mind and others:
        facts = describe(om, sr).facts()
        want = nudge or rng.choice(["answers them", "fills their gaps", "doubles one of them and then leaves", "contrasts them",
                                    "plays less than before", "takes the lead", "makes room for them", "argues with them"])
        if direction:
            want += ". The conductor asks for: " + direction.text()
        text = mind_mod.respond_part(my_text, stage_name(archive, family), others, song.grid_text(), facts, want)
        if text:
            out.append((my_clip.genome.child(text, "mind", f"asked to: {want}"), "mind"))
    for op in ops:
        if len(out) >= k:
            break
        text, note = None, ""
        if op == "echo" and other_events:
            text, note = echo(my_text, my_events, other_events, song, rng)
        elif op == "double" and other_events:
            text, note = double(my_text, my_events, other_events, song, rng)
        elif op == "gaps":
            text, note = gaps(my_text, my_events, env, 0.05, song, rng)
        elif op == "contrast" and other_events:
            text, note = contrast(my_text, my_events, other_events, song, rng)
        elif op == "room":
            text, note = room(my_text, my_events, song, rng)
        elif op == "rest":
            text, note = rest(my_text, my_events, song, rng)
        elif op == "groove":
            text, note = groove(my_text, song, direction, rng)
        elif op == "tune":
            text, note = tune(my_text, song, direction, rng)
        elif op == "self":
            g = vary.blind(my_clip.genome, rng)
            text, note = g.text, g.note
            op = g.author
        if text and text != my_text:
            out.append((my_clip.genome.child(text, op, note), op))
    return out


def player_ear(archive: Archive, songs: SongArchive, song: Song, family: str):
    """This player's ear: a probe trained on the listener's reactions to this
    family's pieces when one exists, otherwise novelty of the mix within the
    song's family tree plus the whole song map. Returns (scorer, name)."""
    probe = family_probe(archive.root, family)
    if probe is not None:
        return (lambda mix_desc, _audible: float(probe.score_feats(features(mix_desc)))), f"ear:{family[:4]}:{probe.n_votes}"
    def nov(mix_desc, audible):
        return songs.novelty(features(mix_desc), exclude=song.id) + 0.5 * audible
    return nov, "novelty"


def respond(archive: Archive, songs: SongArchive, song: Song, family: str, rng: random.Random,
            use_mind: bool = False, k: int = 3, nudge: str | None = None, verbose: bool = False,
            direction: Direction | None = None) -> tuple[Song | None, str]:
    """One player answers the others. Returns (child song, reason) or (None, why not)."""
    drafts = candidates(archive, song, family, rng, use_mind, k, nudge, direction)
    if not drafts:
        return None, "nothing to respond with"
    om, sr = others_mix(archive, song, family)
    without = features(describe(om, sr))
    mu, sd = songs._stats()
    scorer, ear_name = player_ear(archive, songs, song, family)
    best = None
    tried = []
    for genome, op in drafts:
        r, clip_dir = hear_part(archive, genome.text, song)
        if not r.ok:
            discard_part(clip_dir); tried.append(f"{op}: {r.reason}"); continue
        stems = [part_wav(archive, cid) for fam, cid in song.parts.items() if fam != family] + [clip_dir / "clip.wav"]
        data, msr = mix_stems(stems, song.seconds)
        mix_desc = describe(data.mean(axis=1), msr)
        with_me = features(mix_desc)
        audible = float(np.linalg.norm((with_me - mu) / sd - (without - mu) / sd))
        if audible < 0.05:
            discard_part(clip_dir); tried.append(f"{op}: inaudible in the mix"); continue
        score = scorer(mix_desc, min(audible, 2.0))
        tried.append(f"{op}: {score:.2f}")
        if best is None or score > best[0]:
            if best is not None:
                discard_part(best[2])
            best = (score, genome, clip_dir, op, r, mix_desc)
        else:
            discard_part(clip_dir)
    if best is None:
        return None, "no candidate rendered: " + "; ".join(tried)
    score, genome, clip_dir, op, r, mix_desc = best
    part_desc = describe(r.audio, r.sr)
    clip = keep_part(archive, genome, clip_dir, song, family, part_desc)
    child = song.child("respond", f"{stage_name(archive, family)} {genome.note or op}", parts={**song.parts, family: clip.id})
    child.name = song.name
    render_mix(archive, songs, child)
    if verbose:
        print(f"    {stage_name(archive, family)} chose {op} by {ear_name}: " + "; ".join(tried))
    return child, f"{op} by {ear_name}"


# ---------------------------------------------------------------- the jam

def jam(archive: Archive, songs: SongArchive, members: list[tuple[str, str]], tempo: float, bars: int,
        rng: random.Random, use_mind: bool = False, name: str = "", verbose: bool = False,
        direction: Direction | None = None) -> Song:
    """A band writes a song together: the first player lays a part down, each
    next player joins with a fitted piece and then answers what is there."""
    scale = direction.pick_scale(rng) if direction else None
    song = Song(tempo=tempo, bars=bars, parts={}, name=name, author="jam", note="written together",
                scale=scale or "", root_hz=direction.root_hz if direction else 110.0, groove=direction.groove if direction else "free")
    for n, (family, clip_id) in enumerate(members):
        base = archive.clips[clip_id]
        text = fit_to_grid(base.genome.text, song.seconds, song.beat, quantize=True, rng=rng,
                           groove=song.groove if song.groove != "free" else None, scale=song.scale or None, root_hz=song.root_hz)
        r, clip_dir = hear_part(archive, text, song)
        if not r.ok:
            discard_part(clip_dir)
            if verbose:
                print(f"    {stage_name(archive, family)} could not join: {r.reason}")
            continue
        g = base.genome.child(text, "fit", f"{base.genome.name} fitted to the grid")
        clip = keep_part(archive, g, clip_dir, song, family, describe(r.audio, r.sr))
        song.parts[family] = clip.id
        if n > 0:
            child, why = respond(archive, songs, song, family, rng, use_mind, k=3, verbose=verbose, direction=direction)
            if child is not None:
                child.name = song.name; child.author = "jam"; child.note = f"{stage_name(archive, family)} answered on joining"
                song = child
    render_mix(archive, songs, song)
    songs.save(song)
    return song
