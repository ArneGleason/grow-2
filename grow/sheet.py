"""The listening sheet: the only acceptance test, so it has to be fun.

Two pages, one server:

- `/` is the show. The archive plays as a set list, each clip's instruments
  appear as performers who play their parts and react to a mood dial you
  turn while you listen. Every dial reading, skip, replay, and vote is
  appended to archive/events.csv, which is what the taste probe trains on.
- `/map` is the grid: every niche, every clip, lineage and genome text, for
  when you want to look rather than watch.

Nothing here judges the music. It only makes listening pleasant and records
what you did.
"""

from __future__ import annotations

import csv
import json
import random
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import ARCHIVE_DIR
from .archive import Archive, Clip, GRID
from .genome import instrument_labels, score_events

STATIC = Path(__file__).parent / "static"


def _clip_payload(archive: Archive, c: Clip, with_score: bool = False) -> dict:
    d = {
        "id": c.id, "name": c.genome.name or c.id, "generation": c.genome.generation,
        "author": c.genome.author, "note": c.genome.note, "status": c.status,
        "facts": c.descriptors.facts(), "quality": c.quality, "ear": c.ear,
        "seconds": c.descriptors.seconds, "cell": list(c.cell),
        "csd": c.genome.text,
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
    return d


def _map_payload(archive: Archive) -> dict:
    clips, cells = {}, {}
    for c in archive.clips.values():
        clips[c.id] = _clip_payload(archive, c)
        if c.status == "alive":
            cells.setdefault(f"{c.cell[0]},{c.cell[1]}", []).append(c.id)
    return {"clips": clips, "cells": cells, "status": archive.status_lines()[0], "grid": GRID}


def _setlist(archive: Archive, mode: str, n: int, rng: random.Random) -> list[dict]:
    alive = archive.alive()
    if not alive:
        return []
    if mode == "newest":
        picks = sorted(alive, key=lambda c: c.genome.created, reverse=True)[:n]
    elif mode == "lineage":
        root = max(alive, key=lambda c: (len(archive.lineage(c.id)), rng.random()))
        picks = list(reversed(archive.lineage(root.id)))[-n:]
    elif mode == "walk":
        cur = rng.choice(alive)
        picks, seen = [cur], {cur.id}
        while len(picks) < n:
            x, y = cur.cell
            near = [c for c in alive if c.id not in seen and abs(c.cell[0] - x) <= 2 and abs(c.cell[1] - y) <= 2]
            if not near:
                near = [c for c in alive if c.id not in seen]
                if not near:
                    break
            cur = rng.choice(near)
            picks.append(cur); seen.add(cur.id)
    elif mode == "founders":
        picks = [c for c in alive if c.genome.author == "seed"][:n]
    else:  # tour: mostly the newest, a few elders, shuffled
        by_age = sorted(alive, key=lambda c: c.genome.created, reverse=True)
        fresh = by_age[: max(n, 2 * n // 3)]
        elders = by_age[len(fresh):]
        picks = fresh[: 2 * n // 3] + rng.sample(elders, min(len(elders), n - 2 * n // 3))
        rng.shuffle(picks)
    return [_clip_payload(archive, c, with_score=True) for c in picks]


def serve(root: Path | str = ARCHIVE_DIR, port: int = 8765) -> None:
    root = Path(root).resolve()
    events = root / "events.csv"
    rng = random.Random()

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(root), **k)

        def log_message(self, *a):  # quiet
            pass

        def _send(self, body: bytes, ctype: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urlparse(self.path)
            q = parse_qs(url.query)
            if url.path == "/":
                self._send((STATIC / "stage.html").read_bytes(), "text/html; charset=utf-8")
            elif url.path == "/map":
                self._send((STATIC / "map.html").read_bytes(), "text/html; charset=utf-8")
            elif url.path == "/data":
                self._send(json.dumps(_map_payload(Archive.open(root))).encode(), "application/json")
            elif url.path == "/favicon.ico":
                self.send_response(204); self.end_headers()
            elif url.path == "/setlist":
                mode = q.get("mode", ["tour"])[0]
                n = max(1, min(60, int(q.get("n", ["12"])[0])))
                self._send(json.dumps(_setlist(Archive.open(root), mode, n, rng)).encode(), "application/json")
            else:
                super().do_GET()

        def do_POST(self):
            if self.path != "/event":
                self.send_response(404); self.end_headers(); return
            n = int(self.headers.get("Content-Length", 0))
            try:
                ev = json.loads(self.rfile.read(n).decode())
                batch = ev if isinstance(ev, list) else [ev]
            except json.JSONDecodeError:
                self.send_response(400); self.end_headers(); return
            new = not events.exists()
            with events.open("a", newline="") as fh:
                w = csv.writer(fh)
                if new:
                    w.writerow(["time", "clip", "kind", "value", "pos"])
                for e in batch[:200]:
                    w.writerow([
                        f"{time.time():.0f}", str(e.get("clip", ""))[:16], str(e.get("kind", ""))[:8],
                        f"{float(e.get('value', 0) or 0):.3f}", f"{float(e.get('pos', 0) or 0):.3f}",
                    ])
            self.send_response(204); self.end_headers()

    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"the show is at http://127.0.0.1:{port}   (the map is at /map; ctrl-c to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
