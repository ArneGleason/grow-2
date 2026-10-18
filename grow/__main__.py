"""Command line for Grow 2.

  python -m grow init                 render the founders into the archive
  python -m grow run -g 20 -b 8       grow for 20 generations, 8 children each
  python -m grow run -g 20 --mind     let the local model author some children
  python -m grow sheet                open the listening sheet (then listen)
  python -m grow taste                train the taste probe from your votes
  python -m grow status               print the map
  python -m grow band init -n 3       bands jam: songs written together
  python -m grow band run -g 10       grow songs by responding
  python -m grow stats                what has accumulated
  python -m grow backup               snapshot the archive's text (genomes, songs, events) to backups/
"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import ARCHIVE_DIR, SEEDS_DIR


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="grow", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--archive", default=ARCHIVE_DIR)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init"); p.add_argument("--seeds", default=SEEDS_DIR); p.add_argument("--seed", type=int)
    p = sub.add_parser("run")
    p.add_argument("-g", "--generations", type=int, default=10)
    p.add_argument("-b", "--batch", type=int, default=8)
    p.add_argument("--mind", action="store_true", help="use the local model for a share of children")
    p.add_argument("--mind-share", type=float, default=0.3)
    p.add_argument("--no-embedding", action="store_true")
    p.add_argument("--seed", type=int)
    p = sub.add_parser("band")
    p.add_argument("what", choices=["init", "run", "status"])
    p.add_argument("-n", "--songs", type=int, default=3)
    p.add_argument("-g", "--generations", type=int, default=5)
    p.add_argument("-b", "--batch", type=int, default=6)
    p.add_argument("--mind", action="store_true")
    p.add_argument("--seed", type=int)
    p = sub.add_parser("sheet"); p.add_argument("--port", type=int, default=8765)
    sub.add_parser("taste")
    sub.add_parser("status")
    sub.add_parser("stats")
    p = sub.add_parser("backup"); p.add_argument("--to", default="backups")
    a = ap.parse_args(argv)

    if a.cmd == "init":
        from .grow import Grower
        g = Grower(a.archive, seed=a.seed)
        n = g.init_from_seeds(a.seeds)
        print(f"{n} founders in the archive")
        for line in g.archive.status_lines():
            print(line)
    elif a.cmd == "run":
        from .grow import Grower
        g = Grower(a.archive, seed=a.seed, use_mind=a.mind, use_embedding=False if a.no_embedding else None)
        g.run(a.generations, a.batch, a.mind_share)
    elif a.cmd == "band":
        from .band import Band
        b = Band(a.archive, seed=a.seed, use_mind=a.mind)
        if a.what == "init":
            b.init_songs(a.songs)
        elif a.what == "run":
            from .taste import read_events
            prefs = read_events(Path(a.archive) / "events.csv")
            import math as _m
            weights = {s.id: _m.exp(min(prefs.get(s.id, 0.0), 3.0)) for s in b.songs.alive()} if prefs else None
            b.run(a.generations, a.batch, weights)
        print(b.songs.status_line())
    elif a.cmd == "sheet":
        from .sheet import serve
        serve(a.archive, a.port)
    elif a.cmd == "taste":
        from .archive import Archive
        from .taste import train, MIN_VOTED_CLIPS
        root = Path(a.archive)
        arc = Archive.open(root)
        model = train(arc, root / "events.csv", root / "taste.json")
        if model is None:
            print(f"not enough voted clips yet (need {MIN_VOTED_CLIPS}); listen more")
        else:
            print(f"taste probe trained on {model['n_votes']} clips; fit r2 {model['fit_r2']:.2f}; embedding {model['use_embedding']}")
            from .taste import Probe
            probe = Probe(model)
            arc.rescore(lambda c: (0.7 * probe.score(c) + 0.3 * arc.novelty(c.feats(), c.embedding, exclude=c.id), f"taste{model['n_votes']}"))  # same blend as Grower.ear
            print("archive rescored with the new ear")
    elif a.cmd == "stats":
        from .stats import report
        for line in report(Path(a.archive)):
            print(line)
    elif a.cmd == "backup":
        from .stats import backup
        out = backup(Path(a.archive), Path(a.to))
        print(f"wrote {out}")
    elif a.cmd == "status":
        from .archive import Archive
        for line in Archive.open(a.archive).status_lines():
            print(line)


if __name__ == "__main__":
    main()
