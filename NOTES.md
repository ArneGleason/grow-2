# Notes

One running log. Date, what was tried, what was heard. Newest at the bottom.

## 2026-10-17 — kernel

Built the first loop in a cloud session with Csound 6.18 available but no
way to listen, so everything below is numbers and plumbing. Nobody has heard
these clips yet. The first real entry in this file is Arne's.

What exists:

- six founders in `seeds/`: additive drone, FM bells, a grain cloud, a kick
  and noise-hit pattern, plucked strings with a delay, a saw through a
  resonant lowpass. All six render and land in six different niches.
- the sandbox (`body.py`): render, trim to 30 s, reject silent or failed,
  normalize peak. Zero render failures from blind variation in the first
  runs, which says the operators are conservative rather than that the
  sandbox is loose.
- descriptor ear (`ears.py`): loudness, loudness range, silence ratio, onset
  density, centroid, flatness, low and high energy share, pulse strength and
  period. Onset detection took three tries. A plain spectral flux read a
  sustained drone as five onsets a second because two low partials 27 Hz
  apart make the leakage bins between them oscillate faster than the frame
  rate. Third-octave band sums did not fix it. SuperFlux-style detection
  (log-compressed magnitude against a max-filtered previous frame) did:
  drone 0.3/s, bells 0.4, plucks 1.2, drums 3.0, acid pattern 4.3, grain
  cloud 5.0.
- the map (`archive.py`): 10 by 10 over log onset density and log centroid,
  three clips per cell, novelty as the ear until votes exist, occupants
  re-scored whenever their cell is contested.
- blind operators (`vary.py`): numeric jitter, score edits (stretch, thin,
  echo, reverse, scale a column), crossover (one body plays another's
  score). Mind rewrite through Ollama with a nudge toward an empty niche.
- the sheet (`sheet.py`), the taste probe (`taste.py`), the CLI.

What the numbers said in a run of six generations of eight blind children:
26 of 48 kept, 9 duplicates, 0 render failures, map from 6 niches to 14. The
map fills along the bottom-left (sparse and dark) fastest because stretch
and thin are easy moves; the bright, dense corner stays empty. That is a
job for the mind or for a founder that lives there.

Known soft spots, deliberately left:

- the taste probe will memorize the first dozen votes (ridge regression,
  nine weights); it only becomes an ear after a few dozen. Say so on the
  sheet if it misbehaves.
- fallback names come from two word lists; the mind names better.
- the duplicate check is a tight descriptor distance; it correctly caught a
  stub model that appended events after the score's end marker, which
  Csound ignores. A real model may do the same. The prompt now says where
  events go.
- no embedding ear was exercised here (no torch in the container).

Next: Arne installs csound, runs init and twenty generations, opens the
sheet, listens for an evening, and writes down how many clips he would play
twice. Then `python -m grow taste`, twenty more generations, and the same
question.

## 2026-10-17 — the show

Arne ran the kernel on the Mac and got the grid up. Verdict: tedious, not
fun. He wants performances laid out for him, a dial to turn while they play
instead of a thumb per clip, and performers he can watch.

Built: `/` is now the show. A set list (tour, newest, a walk across the map,
one family oldest to newest, or the founders) plays in a row. Each
instrument in a piece's program is a performer on the stage, drawn from the
score: it pulses on its note events, holds while a note sustains, sits
dimmed and resting if it has no part in this piece, and its eyes and mouth
follow the mood dial. A piano-roll strip along the bottom shows the piece
coming. The dial is a vertical slider, the arrow keys, or the mouse wheel
over the stage. Dial readings go out whenever the dial moves and every two
seconds while a piece plays, tagged with the position in the piece. Skips
before a third of a piece count against it. The taste probe reads all of
this (`taste.read_events`).

Why it matters beyond fun: a continuous dial through a whole piece is far
richer than one vote per clip, and later it can say which moments were
loved, not only which pieces.

Verified headless: the page loads, a set plays, the dial changes, events
post with positions, the map page still works. Nobody has watched it yet.

Soft spots: performer amplitude and pitch are guessed from p-fields (the
first value in 0..1, the first in 20..8000), which is only a picture.
Performers are per piece; they do not yet persist as characters across a
family. That is the obvious next step once the show is fun to sit through:
the performers become the players, and each player gets an ear.
