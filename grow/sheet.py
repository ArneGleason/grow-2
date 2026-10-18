"""The listening sheet: the only acceptance test, so it has to be fun.

One server, two pages:

- `/` is the show. Players are families (each founder's lineage is a
  character with a name and a repertoire). A set is several songs; a song is
  a few scenes (intro, full band, a shift, outro) in which players play
  pieces from their repertoires together, mixed live in the browser. The
  listener drags players front or back, silences or encourages them, and
  turns a mood dial. All of that is heard immediately and recorded to
  archive/events.csv. Between songs the show can breed a generation from
  what was approved, and new pieces join the repertoires on the spot.
- `/map` is the grid: every niche, every clip, lineage and genome text.

Nothing here judges the music. The set builder chooses for contrast and
variety, which is arrangement, not taste; the listener's actions are the
taste.
"""

from __future__ import annotations

import csv
import json
import math
import random
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import ARCHIVE_DIR
from .archive import Archive, Clip, GRID
from .genome import instrument_labels, score_events
from .taste import read_events
from .song import SongArchive, Song, stage_name, family_palette
from . import direction as direction_mod
from .direction import SHAPES, PALETTES, SPACES, GROOVES, PITCHES, MOODS, SCALES

STATIC = Path(__file__).parent / "static"

from .song import STAGE_NAMES


def _clip_payload(archive: Archive, c: Clip, with_score: bool = False) -> dict:
    d = {
        "id": c.id, "name": c.genome.name or c.id, "generation": c.genome.generation,
        "author": c.genome.author, "note": c.genome.note, "status": c.status,
        "facts": c.descriptors.facts(), "quality": c.quality, "ear": c.ear,
        "seconds": c.descriptors.seconds, "cell": list(c.cell), "created": c.genome.created,
        "lineage": [
            {"id": a.id, "name": a.genome.name or a.id, "generation": a.genome.generation,
             "author": a.genome.author, "note": a.genome.note, "status": a.status}
            for a in archive.lineage(c.id)
        ],
    }
    if with_score:
        labels = instrument_labels(c.genome.text)
        events = score_events(c.genome.text, c.descriptors.seconds)
        used = sorted(set(e["instr"] for e in events)) or sorted(labels)
        d["performers"] = [{"instr": n, "label": labels.get(n, f"voice {n}")} for n in used]
        d["events"] = events
        d["about"] = getattr(c, "about", "") or ""
    else:
        d["csd"] = c.genome.text
    return d


def _map_payload(archive: Archive) -> dict:
    clips, cells = {}, {}
    for c in archive.clips.values():
        clips[c.id] = _clip_payload(archive, c)
        if c.status == "alive":
            cells.setdefault(f"{c.cell[0]},{c.cell[1]}", []).append(c.id)
    return {"clips": clips, "cells": cells, "status": archive.status_lines()[0], "grid": GRID}


# ------------------------------------------------------------------ the show

def _players(archive: Archive, prefs: dict[str, float]) -> list[dict]:
    fams: dict[str, list[Clip]] = {}
    for c in archive.clips.values():
        if c.status in ("alive", "part"):
            fams.setdefault(archive.family_of(c.id), []).append(c)
    roots = sorted(fams, key=lambda rid: archive.clips[rid].genome.created if rid in archive.clips else 0)
    players = []
    for i, rid in enumerate(roots):
        root = archive.clips.get(rid)
        founder = (root.genome.name if root else rid) or rid
        rep = []
        for c in sorted(fams[rid], key=lambda c: c.genome.created):
            d = _clip_payload(archive, c, with_score=True)
            d["pref"] = prefs.get(c.id, 0.0)
            d["heard"] = c.id in prefs
            rep.append(d)
        pal = family_palette(archive, rid)
        players.append({"id": rid, "name": stage_name(archive, rid), "founder": founder, "color": i, "repertoire": rep,
                        "palette": pal, "shape": SHAPES.get(pal, "blob")})
    return players


def _pick_clip(player: dict, rng: random.Random, exclude: str | None = None) -> str:
    """A piece from the repertoire: approved pieces more often, unheard ones get a look."""
    reps = [c for c in player["repertoire"] if c["id"] != exclude] or player["repertoire"]
    w = [math.exp(min(c["pref"], 3.0)) * (1.6 if not c["heard"] else 1.0) for c in reps]
    return rng.choices(reps, weights=w)[0]["id"]


def _song_payload(archive: Archive, songs: SongArchive, song: Song, prefs: dict[str, float]) -> dict:
    return {"id": song.id, "name": song.name, "note": song.note, "author": song.author, "generation": song.generation,
            "seconds": song.seconds, "tempo": song.tempo, "bars": song.bars, "status": song.status,
            "scale": song.scale, "groove": song.groove, "tried": song.tried, "chose": song.chose,
            "parts": {fam: cid for fam, cid in song.parts.items() if cid in archive.clips},
            "pref": prefs.get(song.id, 0.0), "heard": song.id in prefs,
            "lineage": [{"id": a.id, "note": a.note, "author": a.author, "generation": a.generation} for a in songs.lineage(song.id)]}


def _songs(archive: Archive, songs: SongArchive, players: list[dict], n_songs: int, rng: random.Random, prefs: dict[str, float]) -> list[dict]:
    """A set: songs the band wrote together, each as intro / full / shift / outro.

    The shift is a child of the song when one exists (someone answered
    differently); otherwise it is marked live and a player answers on stage.
    """
    alive = songs.alive()
    if not alive:
        return []
    weights = [math.exp(min(prefs.get(s.id, 0.0), 3.0)) * (1.6 if s.id not in prefs else 1.0) for s in alive]
    picks: list[Song] = []
    pool = list(alive)
    names: set[str] = set()
    for _ in range(min(n_songs, len(pool))):
        fresh = [p for p in pool if p.name not in names] or pool   # one version of each song per set
        i = rng.choices(range(len(fresh)), weights=[weights[alive.index(p)] for p in fresh])[0]
        pick = fresh[i]; pool.remove(pick); names.add(pick.name); picks.append(pick)
    by_id = {p["id"]: p for p in players}
    out = []
    for song in picks:
        fams = [f for f in song.parts if f in by_id and song.parts[f] in archive.clips]
        if not fams:
            continue
        order = list(fams); rng.shuffle(order)
        slots = sorted(rng.sample(range(0, 10, 2), len(order))) if len(order) <= 5 else sorted(rng.sample(range(10), len(order)))  # keep players apart on stage
        xs = {f: 0.12 + 0.76 * (slots[i] + 0.5) / 10 for i, f in enumerate(order)}
        depths = {f: rng.uniform(0.15, 0.7) for f in order}

        def members(sg: Song, ids: list[str]) -> list[dict]:
            return [{"player": f, "clip": sg.parts[f], "x": round(xs.get(f, 0.5), 3), "depth": round(depths.get(f, 0.4), 3), "muted": False}
                    for f in ids if f in sg.parts and sg.parts[f] in archive.clips]

        half = max(1, len(order) // 2)

        def ok_kid(k: Song) -> bool:
            return bool(k.descriptors) and k.status in ("alive", "declined", "evicted") and abs(k.seconds - song.seconds) < 0.01

        # a chain: the song, then versions of it where someone answered differently,
        # played back to back in lockstep so the band moves through its own family
        chain, cur = [song], song
        for _ in range(3):
            kids = [k for k in songs.children(cur.id) if ok_kid(k)]
            if not kids:
                break
            cur = rng.choice(kids); chain.append(cur)
        shift = chain[-1] if len(chain) > 1 else None
        loop = round(song.seconds, 3)
        links = [{"song": sg.id, "members": members(sg, [f for f in order if f in sg.parts] + [f for f in sg.parts if f not in order]),
                  "note": sg.note if sg is not song else "", "tried": sg.tried, "chose": sg.chose} for sg in chain]
        scenes = [
            {"kind": "intro", "song": song.id, "members": members(song, order[:half]), "seconds": round(song.seconds, 1), "loop": loop},
            {"kind": "full", "song": song.id, "members": members(song, order), "seconds": round(song.seconds * len(links), 1), "loop": loop,
             "chain": links, "note": (f"then {len(links) - 1} answer{'s' if len(links) > 2 else ''}" if len(links) > 1 else "")},
        ]
        if shift is not None:
            kids2 = [k for k in songs.children(shift.id) if ok_kid(k)]
            nxt = rng.choice(kids2) if kids2 else None
            if nxt is not None:
                scenes.append({"kind": "shift", "song": nxt.id, "members": members(nxt, [f for f in order if f in nxt.parts] + [f for f in nxt.parts if f not in order]),
                               "seconds": round(nxt.seconds, 1), "loop": loop, "note": nxt.note, "tried": nxt.tried, "chose": nxt.chose})
            else:
                scenes.append({"kind": "shift", "song": shift.id, "members": members(shift, [f for f in order if f in shift.parts] + [f for f in shift.parts if f not in order]),
                               "seconds": round(shift.seconds, 1), "loop": loop, "live": rng.choice([f for f in order if f in shift.parts] or order), "note": "someone answers live"})
        else:
            scenes.append({"kind": "shift", "song": song.id, "members": members(song, order), "seconds": round(song.seconds, 1), "loop": loop,
                           "live": rng.choice(order), "note": "someone answers live"})
        last = chain[-1]
        scenes.append({"kind": "outro", "song": last.id, "members": members(last, [f for f in order[-half:] if f in last.parts] or list(last.parts)[:half]), "seconds": round(song.seconds, 1), "loop": loop})
        title = song.name + " · " + " & ".join(by_id[f]["name"] for f in order)
        out.append({"id": song.id, "title": title, "cast": order, "scenes": scenes, "song": _song_payload(archive, songs, song, prefs)})
    return out


class LiveRespond:
    """A player answers, or joins, on stage: one job at a time, in a background thread."""

    def __init__(self, root: Path):
        self.root = root
        self.lock = threading.Lock()
        self.jobs: dict[str, dict] = {}

    def start(self, kind: str, song_id: str, family: str, mind: bool, nudge: str | None) -> dict:
        job_id = f"{kind}:{song_id}:{family}:{int(time.time())}"
        with self.lock:
            if any(not j.get("done") for j in self.jobs.values()):
                return {"started": False, "reason": "someone is already answering"}
            self.jobs[job_id] = {"done": False, "kind": kind, "song": song_id, "family": family, "started": time.time(), "thoughts": []}
        threading.Thread(target=self._run, args=(job_id, kind, song_id, family, mind, nudge), daemon=True).start()
        return {"started": True, "job": job_id}

    def _run(self, job_id: str, kind: str, song_id: str, family: str, mind: bool, nudge: str | None) -> None:
        from .band import Band
        from .respond import respond
        job = self.jobs[job_id]
        try:
            b = Band(self.root, use_mind=mind, verbose=False)
            song = b.songs.songs.get(song_id)
            if song is None:
                job.update(done=True, error="no such song"); return
            def progress(text: str) -> None:
                job["thoughts"].append(text)
            if kind == "regrid":
                child, why = b.regrid(song)
            elif kind == "join":
                if family in song.parts:
                    # already in this song, only sitting out the scene: bring the part back in
                    job.update(done=True, child=song.id, clip=song.parts[family], note=f"{stage_name(b.archive, family)} comes back in",
                               kept=None, how="", seconds=round(time.time() - job["started"], 1))
                    return
                child, why = b.add_player(song, family)
            else:
                if family not in song.parts:
                    job.update(done=True, error="that player is not in this song"); return
                child, why = respond(b.archive, b.songs, song, family, b.rng, b.use_mind, k=3, nudge=nudge, direction=b.direction, progress=progress)
            if child is None:
                job.update(done=True, error=why); return
            child.name = song.name
            if child.descriptors is None:
                from .song import render_mix
                render_mix(b.archive, b.songs, child)
            kept, how = b.songs.offer(child, b.ear)
            about = ""
            cl = b.archive.clips.get(child.parts.get(family, ""))
            if cl is not None:
                about = getattr(cl, "about", "") or ""
            job.update(done=True, child=child.id, clip=child.parts.get(family), note=child.note, kept=kept, how=how,
                       tried=child.tried, chose=child.chose, about=about, seconds=round(time.time() - job["started"], 1))
        except Exception as exc:  # noqa: BLE001
            job.update(done=True, error=str(exc)[:200])

    def status(self, job_id: str) -> dict:
        return self.jobs.get(job_id, {"done": True, "error": "unknown job"})


class LiveJam:
    """Bands write songs on demand, in a background thread."""

    def __init__(self, root: Path):
        self.root = root
        self.running = False
        self.last: dict | None = None
        self.lock = threading.Lock()

    def status(self) -> dict:
        return {"running": self.running, "last": self.last}

    def start(self, n: int, mind: bool) -> bool:
        with self.lock:
            if self.running:
                return False
            self.running = True
        threading.Thread(target=self._run, args=(n, mind), daemon=True).start()
        return True

    def _run(self, n: int, mind: bool) -> None:
        from .band import Band
        t0 = time.time()
        try:
            b = Band(self.root, use_mind=mind, verbose=False)
            songs = b.init_songs(n)
            self.last = {"songs": [s.name for s in songs], "seconds": round(time.time() - t0), "when": time.time()}
        except Exception as exc:  # noqa: BLE001
            self.last = {"error": str(exc)[:200], "when": time.time()}
        finally:
            self.running = False


class LiveGrow:
    """One generation at a time, in a background thread, parents weighted by approval."""

    def __init__(self, root: Path, events: Path):
        self.root, self.events = root, events
        self.lock = threading.Lock()
        self.running = False
        self.last: dict | None = None
        self.count = 0

    def status(self) -> dict:
        return {"running": self.running, "last": self.last, "generations": self.count}

    def start(self, batch: int, mind: bool) -> bool:
        with self.lock:
            if self.running:
                return False
            self.running = True
        threading.Thread(target=self._run, args=(batch, mind), daemon=True).start()
        return True

    def _run(self, batch: int, mind: bool) -> None:
        from .band import Band
        t0 = time.time()
        try:
            prefs = read_events(self.events)
            b = Band(self.root, use_mind=mind, verbose=False)
            weights = {s.id: math.exp(min(prefs.get(s.id, 0.0), 3.0)) for s in b.songs.alive()}
            kept = b.generation(batch=batch, weights=weights)
            self.last = {"kept": kept, "tried": batch, "born": b.born, "seconds": round(time.time() - t0), "when": time.time()}
            self.count += 1
        except Exception as exc:  # noqa: BLE001
            self.last = {"error": str(exc)[:200], "when": time.time()}
        finally:
            self.running = False


def serve(root: Path | str = ARCHIVE_DIR, port: int = 8765) -> None:
    root = Path(root).resolve()
    events = root / "events.csv"
    moments = root / "moments.jsonl"
    rng = random.Random()
    live = LiveGrow(root, events)
    answering = LiveRespond(root)
    jamming = LiveJam(root)

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(root), **k)

        def log_message(self, *a):  # quiet
            pass

        def _send(self, body: bytes, ctype: str, code: int = 200) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code: int = 200) -> None:
            self._send(json.dumps(obj).encode(), "application/json", code)

        def do_GET(self):
            url = urlparse(self.path)
            q = parse_qs(url.query)
            if url.path == "/":
                self._send((STATIC / "stage.html").read_bytes(), "text/html; charset=utf-8")
            elif url.path == "/map":
                self._send((STATIC / "map.html").read_bytes(), "text/html; charset=utf-8")
            elif url.path == "/favicon.ico":
                self.send_response(204); self.end_headers()
            elif url.path == "/data":
                self._json(_map_payload(Archive.open(root)))
            elif url.path == "/players":
                arc = Archive.open(root)
                self._json({"players": _players(arc, read_events(events)), "status": arc.status_lines()[0]})
            elif url.path == "/show":
                arc = Archive.open(root)
                prefs = read_events(events)
                players = _players(arc, prefs)
                sa = SongArchive(root)
                n = max(1, min(12, int(q.get("songs", ["4"])[0])))
                self._json({"players": players, "songs": _songs(arc, sa, players, n, rng, prefs),
                            "status": arc.status_lines()[0] + " · " + sa.status_line(),
                            "direction": direction_mod.asdict_(direction_mod.load(root))})
            elif url.path == "/direction":
                self._json({"direction": direction_mod.asdict_(direction_mod.load(root)),
                            "options": {"moods": list(MOODS), "palettes": PALETTES, "spaces": SPACES, "grooves": GROOVES,
                                        "pitches": PITCHES, "scales": list(SCALES)}})
            elif url.path == "/grow":
                self._json(live.status())
            elif url.path in ("/respond", "/join", "/regrid"):
                self._json(answering.status(q.get("job", [""])[0]))
            elif url.path == "/jam":
                self._json(jamming.status())
            else:
                super().do_GET()

        def do_POST(self):
            url = urlparse(self.path)
            q = parse_qs(url.query)
            n = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(n) if n else b""
            if url.path == "/grow":
                batch = max(1, min(16, int(q.get("batch", ["6"])[0])))
                mind = q.get("mind", ["0"])[0] in ("1", "true", "yes")
                started = live.start(batch, mind)
                self._json({"started": started, **live.status()})
                return
            if url.path == "/direction":
                try:
                    body = json.loads(raw.decode()) if raw else {}
                except json.JSONDecodeError:
                    self.send_response(400); self.end_headers(); return
                d = direction_mod.load(root)
                if "mood" in body and body["mood"] != d.mood:
                    d.apply_mood(str(body["mood"]))
                for k in ("palette", "space", "tempo", "groove", "pitch", "scale", "root_hz", "words"):
                    if k in body and body[k] is not None:
                        setattr(d, k, body[k])
                d.tempo = [int(float(v)) for v in (d.tempo or [72, 120])[:2]] if isinstance(d.tempo, list) else [72, 120]
                direction_mod.save(root, d)
                with (root / "direction.log").open("a") as fh:
                    fh.write(json.dumps({"time": time.time(), "direction": direction_mod.asdict_(d)}) + "\n")
                self._json({"direction": direction_mod.asdict_(d)})
                return
            if url.path in ("/respond", "/join", "/regrid"):
                mind = q.get("mind", ["0"])[0] in ("1", "true", "yes")
                nudge = q.get("nudge", [None])[0]
                self._json(answering.start(url.path.strip("/"), q.get("song", [""])[0], q.get("player", [""])[0], mind, nudge))
                return
            if url.path == "/jam":
                n = max(1, min(8, int(q.get("n", ["3"])[0])))
                mind = q.get("mind", ["0"])[0] in ("1", "true", "yes")
                self._json({"started": jamming.start(n, mind), **jamming.status()})
                return
            if url.path == "/moment":
                try:
                    m = json.loads(raw.decode())
                except json.JSONDecodeError:
                    self.send_response(400); self.end_headers(); return
                m["time"] = time.time()
                with moments.open("a") as fh:
                    fh.write(json.dumps(m)[:20000] + "\n")
                self.send_response(204); self.end_headers()
                return
            if url.path != "/event":
                self.send_response(404); self.end_headers(); return
            try:
                ev = json.loads(raw.decode())
                batch = ev if isinstance(ev, list) else [ev]
            except json.JSONDecodeError:
                self.send_response(400); self.end_headers(); return
            new = not events.exists()
            with events.open("a", newline="") as fh:
                w = csv.writer(fh)
                if new:
                    w.writerow(["time", "clip", "kind", "value", "pos"])
                for e in batch[:400]:
                    w.writerow([
                        f"{time.time():.0f}", str(e.get("clip", ""))[:16], str(e.get("kind", ""))[:10],
                        f"{float(e.get('value', 0) or 0):.3f}", f"{float(e.get('pos', 0) or 0):.3f}",
                    ])
            self.send_response(204); self.end_headers()

    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"the show is at http://127.0.0.1:{port}   (the map is at /map; ctrl-c to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
