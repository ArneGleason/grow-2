# Grow 2

A local musical terrarium that grows by listening.

Small sound-making organisms live in an archive shaped like a map. Each one
is a short program (a Csound `.csd`) that is both an instrument and what it
plays. The loop is simple: make a variant, render it to audio, hear it with
real ears, keep it if it claims new territory or beats a neighbor, repeat.
The ears are measurements of sound, a local audio-embedding model, and
probes trained on a human's votes. A local language model may rewrite
genomes and name things. Nothing in the code decides what is good.

This is the second attempt. The first one is archived at
[ArneGleason/grow](https://github.com/ArneGleason/grow); what it taught is in
`LESSONS.md`, and the rules that came out of it are in `PRINCIPLES.md`.
Those two files are the whole doctrine. There is no plan document.

## Run it

Needs Python 3.11+ and Csound 6 on the PATH (`brew install csound` on
macOS, `apt install csound` on Debian or Ubuntu). macOS ships only
`python3`, so make a virtual environment first; inside it, `python` and
`pip` exist and nothing touches the system Python.

    python3 -m venv .venv
    source .venv/bin/activate       # again in every new terminal
    pip install -e .                # numpy, scipy, soundfile
    python -m grow init             # render the six founders in seeds/ into archive/
    python -m grow run -g 20 -b 8   # grow for 20 generations, 8 children each
    python -m grow sheet            # listen at http://127.0.0.1:8765

Then listen for an evening. Every play and every thumbs up or down is
recorded. When a dozen clips have votes:

    python -m grow taste            # train the taste probe, rescore the map
    python -m grow run -g 20        # the map now grows toward what you kept

Optional ears and minds:

    pip install -e '.[clap]'        # CLAP audio embeddings for novelty and taste
    GROW_MODEL=qwen3:8b python -m grow run -g 20 --mind   # a local Ollama model authors a share of children

The archive directory is the terrarium. It is not committed; the source is
the seeds and the loop.

## What you are looking at

The map has two axes: how many events per second (left sparse, right dense)
and how bright (bottom dark, top bright). Each cell holds up to three clips.
A new clip gets in if the cell has room, or if the current ear rates it above
the weakest occupant. Before any votes exist the ear is novelty, so the map
fills outward. After votes exist the ear is your taste, blended with
novelty so it keeps churning.

Clips keep their lineage. Click an ancestor in the sheet to hear where a
sound came from. Evicted clips stay playable for that reason.

## The question

How many clips would you play twice?

That number, compared across seasons, is the only measure of progress. If it
does not rise, change the body, the ear, or the operators, and run again. If
it still does not rise after a couple of tries, stop and say so in
`NOTES.md`.

## Shape of what comes next

Only after the first listening session, and only as far as listening asks:

- a second ear trained on a different vote stream, which is a second player;
- a second map with its own ears, which is a second band, with occasional
  migration between them;
- a producer: a sentence that nudges the ears for a season;
- seasons and extinctions: wipe a region of the map and watch it re-colonize;
- found sound as a body type;
- a window on the archive that is nicer than the sheet, built last.
