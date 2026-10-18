"""What has accumulated, and how to keep it.

The archive folder is the terrarium's memory: genomes, lineage, songs, what
players considered, every reaction the listener had, every direction given,
every moment kept. Audio is a cache derived from genomes, so a backup of the
text is a backup of everything.
"""

from __future__ import annotations

import csv
import json
import tarfile
import time
from collections import Counter
from pathlib import Path

TEXT_SUFFIXES = {".csd", ".json", ".csv", ".jsonl", ".log", ".md", ".gitignore"}


def report(root: Path) -> list[str]:
    root = Path(root)
    if not root.exists():
        return [f"no archive at {root}"]
    clips = list((root / "clips").glob("*/meta.json")) if (root / "clips").exists() else []
    songs = list((root / "songs").glob("*/song.json")) if (root / "songs").exists() else []
    status = Counter()
    families = Counter()
    authors = Counter()
    for m in clips:
        try:
            d = json.loads(m.read_text())
        except (OSError, ValueError):
            continue
        status[d.get("status", "?")] += 1
        authors[d.get("author", "?")] += 1
        if d.get("family"):
            families[d["family"]] += 1
    sstatus = Counter()
    for f in songs:
        try:
            sstatus[json.loads(f.read_text()).get("status", "?")] += 1
        except (OSError, ValueError):
            continue
    events = root / "events.csv"
    kinds = Counter()
    first = last = None
    heard = set()
    if events.exists():
        with events.open() as fh:
            for row in csv.DictReader(fh):
                kinds[row.get("kind", "?")] += 1
                heard.add(row.get("clip", ""))
                t = row.get("time")
                if t and t.isdigit():
                    first = min(first or int(t), int(t)); last = max(last or int(t), int(t))
    moments = sum(1 for _ in (root / "moments.jsonl").open()) if (root / "moments.jsonl").exists() else 0
    directions = sum(1 for _ in (root / "direction.log").open()) if (root / "direction.log").exists() else 0
    probes = sorted(p.name for p in root.glob("taste*.json"))
    wavs = list(root.rglob("*.wav"))
    wav_mb = sum(w.stat().st_size for w in wavs) / 1e6
    text_mb = sum(f.stat().st_size for f in root.rglob("*") if f.is_file() and f.suffix in TEXT_SUFFIXES) / 1e6
    lines = [
        f"archive: {root}",
        f"pieces: {len(clips)} ({', '.join(f'{k} {v}' for k, v in status.most_common())})",
        f"  by birth: {', '.join(f'{k} {v}' for k, v in authors.most_common())}",
        f"  song parts by family: {len(families)} families",
        f"songs: {len(songs)} ({', '.join(f'{k} {v}' for k, v in sstatus.most_common())})",
        f"reactions: {sum(kinds.values())} ({', '.join(f'{k} {v}' for k, v in kinds.most_common())})",
        f"  pieces and songs heard: {len(heard)}",
    ]
    if first and last:
        lines.append(f"  listening between {time.strftime('%Y-%m-%d', time.localtime(first))} and {time.strftime('%Y-%m-%d', time.localtime(last))}")
    lines += [
        f"moments kept: {moments}; directions given: {directions}; taste probes: {len(probes)}",
        f"on disk: {text_mb:.1f} MB of text (the memory), {wav_mb:.0f} MB of audio (a cache that re-renders)",
    ]
    return lines


def backup(root: Path, to: Path) -> Path:
    """A dated tarball of everything except audio and embeddings."""
    root, to = Path(root), Path(to)
    to.mkdir(parents=True, exist_ok=True)
    out = to / f"grow-archive-{time.strftime('%Y%m%d-%H%M%S')}.tar.gz"
    with tarfile.open(out, "w:gz") as tar:
        for f in sorted(root.rglob("*")):
            if f.is_file() and f.suffix in TEXT_SUFFIXES:
                tar.add(f, arcname=str(f.relative_to(root.parent)))
    return out
