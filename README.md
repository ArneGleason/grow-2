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
    python -m grow init             # render the ten founders in seeds/ into archive/
    python -m grow sheet            # the show, at http://127.0.0.1:8765

If there are no songs yet, pressing start makes the bands write their
first ones (about a minute), and the "jam" button writes more at any time.
`python -m grow band init -n 4` does the same from the terminal.

Then watch the show. The players are families: each founder's lineage is a
character with a name and a color. A song is written together: a tempo, a
number of bars, and one part per player, each part made in answer to the
parts already there, every part exactly the song's length so the band plays
in lockstep. A set is a few songs; each song plays as an intro (a part or
two alone), the full band walking through its own family (the song, then
the versions where someone answered differently, each part changing on the
beat), a shift (a further version, or a player answering live on stage),
and an outro. While a player answers, its bubble says what it is doing
(listening to whom, trying what, hearing it, what it chose and why), and a
dotted line runs from a player to the one it is answering.

You conduct. Drag a player forward to hear more of them, back to hear
less, sideways to place them. Drag a resting player onto the stage and they
join the song and answer the others. Double-click to encourage; shift and
double-click to discourage (it silences them; again to let them back in).
The figure at the front of the stage is you, the conductor. Click it to
direct: a mood (mysterious, energetic, angry, tranquil, playful) sets
defaults for the rest, and you can override any of them: which sounds
(modular drone, digital, analog, percussive, plucked, texture, pad, voice,
glass), the space (dry, room, hall, echo, space echo, applied live to the
mix), a tempo range, a groove (straight, swing, broken, drone, free), and
the pitch material (classical modes, microtonal: 19 or 31 equal divisions,
Bohlen-Pierce, 7 equal; or free), plus a line of words for the mind. New
songs are cast and gridded from it, parts joining a song are tuned and
grooved to it, answers include "groove" and "tune" as relations to it, and
"retake song" refits the current song to it on the spot. Each player has
its own silhouette by palette.

The dial on the right is your mood. Hold it low for a few seconds and the
player you like least answers the others again, live, in a few seconds, and
says what they did ("echoes 1.5 beats late", "sits out bars 3 and 5",
"moves up an octave to make room"). Hold it high and the scene is kept as a
moment and runs longer. Between songs, if "grow between songs" is on, the
bands write more from what you approved and the new versions are announced.
Pause, next scene, next song, stop, and the keyboard all work. Everything
you do is recorded; that is the vote. The grid of niches is still at `/map`.

Growing without the show:

    python -m grow band run -g 10   # ten generations of songs: players answering each other
    python -m grow run -g 20 -b 8   # the woodshed: families vary their own pieces alone
    python -m grow taste            # train the taste probe from what you approved, rescore

Optional ears and minds:

    pip install -e '.[clap]'        # CLAP audio embeddings for novelty and taste
    GROW_MODEL=qwen3:8b python -m grow band run -g 10 --mind   # a local Ollama model writes parts with the others in front of it

The archive directory is the terrarium. It is not committed; the source is
the seeds and the loop.

## How a part answers

A responder is a relation to what the others are playing, never an opinion
about whether it is good: echo one named player's rhythm late by some
beats, double them in unison, play where the others are quiet, thin where
they are busy and thicken where they are sparse, move register away from a
neighbor, sit out a bar or two, take the conductor's groove or scale, or
vary the part without looking. A part can also take a shape over its own
length, so a phrase goes somewhere instead of looping in place: spiral up
or down, climb a step each bar, grow from a whisper, fade, rise and fall,
hurry toward the end, slow as it goes, take a breath and come back in a new
register, repeat a motif shedding a note each time, speak in long and
short, ask and answer a step away, or break off halfway. Founders join a
band with a gesture already applied. With the mind on, a language model
writes the part with the other parts in front of it and is asked for a
shape. A player drafts a few candidates, hears each in the mix, and puts
forward the one its own ear prefers: before any approval exists that ear is
geometry (did my part change the mix, is the mix new for this family);
after, it is a probe trained on your reaction to songs this player was in.

## What the map shows (at `/map`)

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
