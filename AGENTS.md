# For agents working in Grow 2

Grow 2 is a musical terrarium that grows by listening. Read `PRINCIPLES.md`
(ten rules) and `LESSONS.md` (why they exist) before changing anything. That
is the whole orientation. There is no review queue, no handoff folder, and no
plan document to keep in sync.

## How work happens here

- A unit of work is a season: a run of the loop toward a stated target
  ("fill the sparse-and-bright corner", "a body that can growl"), judged at a
  listening session. Not an increment judged by a test.
- The deliverable of a season is clips in the archive and a dated entry in
  `NOTES.md` saying what was tried and what was heard.
- If you cannot hear the audio, you are the wrong instrument for the ear
  test. Report descriptors and the map, say plainly that a person has to
  listen, and do not pretend otherwise.
- Tests exist only for `grow/body.py` (the sandbox) and `grow/archive.py`
  (the store). Do not write tests for musical behavior.
- Do not add an inspector, a dashboard, or a panel. The listening sheet is
  the window. Extend it only as far as listening requires.
- If you catch yourself writing a function that decides what is good, stop
  and reread principle 2.

## Running it

    python3 -m venv .venv && source .venv/bin/activate
    pip install -e .                # numpy, scipy, soundfile; needs csound 6 on PATH
    python -m grow init             # render the founders in seeds/ into archive/
    python -m grow band init -n 4   # bands jam: songs written together, parts in lockstep
    python -m grow band run -g 10   # grow songs: one player answers the others per child
    python -m grow run -g 20 -b 8   # the woodshed: families vary their own pieces alone
    python -m grow sheet            # the show at http://127.0.0.1:8765 (grid at /map)
    python -m grow taste            # train the taste probes from the votes, rescore

The song layer is `grow/song.py` (grid, parts, mixes, the song map),
`grow/respond.py` (the responders and the player's own ear), and
`grow/band.py` (jam and the song loop). Responders are relations, never
judgments; keep it that way.

Set `GROW_MODEL` to a tag from `ollama list`. Install the `clap` extra for the
embedding ear. `archive/` is ignored by git on purpose: it is the terrarium,
not the source.
