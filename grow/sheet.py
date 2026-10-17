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

STATIC = Path(__file__).parent / "static"

# stage names for the founders; anything else takes its founder's first word
STAGE_NAMES = {
    "drone-additive": "Moss", "fm-bells": "Chime", "grain-weather": "Weather",
    "noise-drums": "Tick", "pluck-garden": "Pluck", "squelch": "Squelch",
}


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
    for c in archive.alive():
        fams.setdefault(archive.family_of(c.id), []).append(c)
    roots = sorted(fams, key=lambda rid: archive.clips[rid].genome.created if rid in archive.clips else 0)
    players = []
    for i, rid in enumerate(roots):
        root = archive.clips.get(rid)
        founder = (root.genome.name if root else rid) or rid
        name = STAGE_NAMES.get(founder, founder.split("-")[0].capitalize() or rid)
        rep = []
        for c in sorted(fams[rid], key=lambda c: c.genome.created):
            d = _clip_payload(archive, c, with_score=True)
            d["pref"] = prefs.get(c.id, 0.0)
            d["heard"] = c.id in prefs
            rep.append(d)
        players.append({"id": rid, "name": name, "founder": founder, "color": i, "repertoire": rep})
    return players


def _pick_clip(player: dict, rng: random.Random, exclude: str | None = None) -> str:
    """A piece from the repertoire: approved pieces more often, unheard ones get a look."""
    reps = [c for c in player["repertoire"] if c["id"] != exclude] or player["repertoire"]
    w = [math.exp(min(c["pref"], 3.0)) * (1.6 if not c["heard"] else 1.0) for c in reps]
    return rng.choices(reps, weights=w)[0]["id"]


def _songs(players: list[dict], n_songs: int, rng: random.Random) -> list[dict]:
    songs = []
    if not players:
        return songs
    for _ in range(n_songs):
        k = min(len(players), rng.choice([2, 3, 3, 4, 4, 5]))
        cast = rng.sample(players, k)
        base = {p["id"]: _pick_clip(p, rng) for p in cast}
        order = [p["id"] for p in cast]
        rng.shuffle(order)
        slots = sorted(rng.sample(range(10), k))
        xs = {pid: 0.12 + 0.76 * (slots[i] + 0.5) / 10 for i, pid in enumerate(order)}
        depths = {pid: rng.uniform(0.15, 0.7) for pid in order}

        def members(ids: list[str], clips: dict[str, str]) -> list[dict]:
            return [{"player": pid, "clip": clips[pid], "x": round(xs[pid], 3), "depth": round(depths[pid], 3), "muted": False} for pid in ids]

        half = max(1, k // 2)
        shifted = dict(base)
        who = rng.choice(cast)
        shifted[who["id"]] = _pick_clip(who, rng, exclude=base[who["id"]])
        scenes = [
            {"kind": "intro", "members": members(order[:half], base), "seconds": rng.randint(16, 24)},
            {"kind": "full", "members": members(order, base), "seconds": rng.randint(28, 44)},
            {"kind": "shift", "members": members(order, shifted), "seconds": rng.randint(24, 40), "shifted": who["id"]},
            {"kind": "outro", "members": members(order[-half:], shifted), "seconds": rng.randint(14, 22)},
        ]
        names = {p["id"]: p["name"] for p in cast}
        title = " & ".join(names[pid] for pid in order)
        songs.append({"title": title, "cast": order, "scenes": scenes})
    return songs


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
        from .grow import Grower
        t0 = time.time()
        try:
            prefs = read_events(self.events)
            g = Grower(self.root, use_mind=mind, verbose=False)
            weights = {c.id: math.exp(min(prefs.get(c.id, 0.0), 3.0)) for c in g.archive.alive()}
            kept = g.generation(batch=batch, weights=weights)
            self.last = {"kept": kept, "tried": batch, "born": g.born, "seconds": round(time.time() - t0),
                         "rejected": [r["reason"] for r in g.archive.rejections][-batch:], "when": time.time()}
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
                players = _players(arc, read_events(events))
                n = max(1, min(12, int(q.get("songs", ["4"])[0])))
                self._json({"players": players, "songs": _songs(players, n, rng), "status": arc.status_lines()[0]})
            elif url.path == "/grow":
                self._json(live.status())
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
