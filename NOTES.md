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

## 2026-10-17 — the band

Arne on the show: better, more interactive, but it felt like auditioning
sounds with no sense of progress; no way to stop; approval did not visibly
register; he wants players he can see and move front and back, silence or
encourage, who also move themselves; he wants to hear them play off each
other; and he wants the whole thing to be able to run on its own as a set
of small arranged pieces rather than one run-on mode.

Built: the unit of the show is now a scene with several players at once,
mixed live in the browser with Web Audio. Players are families (a
founder's whole lineage is one character with a repertoire). A song is
intro, full band, shift (one player tries a relative of their piece), and
outro; a set is a few songs with breaks. Drag changes gain, a distance
lowpass, and pan immediately; click silences; double-click encourages;
the dial is the mood. Players drift and wander on their own and step back
when they leave a scene. The band reacts within seconds: six seconds of
disapproval and the least-approved audible player swaps to a relative,
with a speech bubble and a line in the "they heard you" log; eight seconds
of approval keeps the moment (archive/moments.jsonl) and extends the
scene. Between songs the server breeds a generation in a background
thread with parents weighted by approval, and the newborns join the
repertoires live, announced by name and parent. Pause, next scene, next
song, stop, keyboard.

Honest limits: the pieces were never written to play together, so the
full-band scenes are collages, and the looping of unequal lengths phases
them against each other. Sometimes that is the point; often it will be
mush, and the conductor's job (silence, pull back) is what makes it music.
Nothing aligns to a shared pulse yet. The performer's pulses are read from
the score, not the audio. Approval feeds breeding immediately but the
taste probe still needs a dozen heard pieces before it steers the map.

Next, if this is fun: pieces that know about each other. A scene is
itself a genome (who, which piece, where), and kept moments are the first
population of arrangements. Then a shared pulse so players can lock, and
players whose ears differ.

## 2026-10-18 — written together

Arne, after the band: no honest evaluation is possible while the parts
were never written together. A collage is ruined by its worst element and
cannot show something coming together well. The parts have to respond to
each other, each in a way it independently thinks might work, and bear
fruit or not.

Built: the song is now the organism. A song is a tempo, a bar count, and
one part per player, every part rendered to exactly the song's length so
the band plays in lockstep (no more drift between loops). A band starts by
jamming in sequence: the first player lays down a founder piece fitted to
the grid, each next player joins with a fitted piece and then answers what
is already there. Growth is responding: a child song is the parent with one
player's part rewritten given the others. Responders (`respond.py`) are
relations, not judgments: echo, double, gaps, contrast, room, rest, self,
and the mind with the other parts in its prompt. A player drafts three,
hears each in the mix, and puts forward the one its own ear prefers;
before any approval exists that ear is geometry (the part must change the
mix; the mix should be new for the family), after it is a per-family probe
trained on Arne's reactions to songs that player was in
(`taste.train_families`). Songs have their own map (`SongArchive`), with a
duplicate check. The show plays songs: intro, full band, shift (a child
where someone answered differently, or a live answer on stage), outro.
Holding the dial low makes the least-approved player answer live in a few
seconds, and the stem swaps in at the matching phase of the loop. Between
songs, breeding is now song breeding.

What it did on the scratch archive: two jams (`fog river`: Tick + Chime +
Moss at 96; `burnt marsh`: Weather + Squelch + Tick at 84), lockstep
confirmed to the sample, children like "Weather echoes 1.5 beats late",
"Chime sits this one out", "Squelch joins and answers"; a live answer in
2.2 s under disapproval in the headless browser ("Chime moves up an
octave to make room"), kept on the map.

Honest limits: the founders were not written for any grid, so the first
jams are founders bent onto a grid, and the answering is cheap relations
plus whatever the mind can do. "Independently thinks it might work" is
real only once the per-family probes exist, which needs an evening of
dial. The mind path was exercised only with a stub here. Nobody has
listened.

Next: listen. If songs written together sound like a band more than the
collages did, the next moves are a shared pulse the mind is told about
(it is: the grid is in the prompt) and letting the players' ears disagree,
which they will as soon as each has its own probe.

## 2026-10-18 — "they just sit there"

Arne put players on the stage and nothing happened. Two causes: the sheet
had no songs yet (the jam step is easy to skip, and the page said nothing),
and dragging a resting player only moved them. Also: a single click to
silence was too easy to confuse with a double-click.

Changed: pressing start with no songs makes the bands write their first
three on the spot and says so; a "jam" button writes more at any time.
Dragging a resting player onto the stage makes them join the current song:
if they already have a part in it they come back in on the beat, otherwise
they get a fitted piece, answer the others, and the song becomes a child.
Single click now does nothing. Double-click encourages; shift plus
double-click discourages (silences; again to unmute).

Verified headless: an empty archive goes from zero songs to a playing intro
by itself; Moss dragged onto the stage came back in with the band in step;
click leaves mute alone, shift-double-click mutes, double-click encourages.

## 2026-10-18 — the conductor

Arne wants a place of his own on stage to give musical direction: the
sounds (digital, modular drone, different electronic ranges), the space
(reverb, echo, space echo, dry), tempo, groove, and a feel (mysterious,
energetic, angry, tranquil) that should touch tempo and pitch material,
with classical modes optional and microtonal or no modes possible. Also
silhouettes so players differ beyond color, and founders that actually
have body: some sounded like a click on nothing.

Built: `direction.py`. A direction is a request, never a judgment, and it
reaches the music only through real paths: new songs pick tempo and cast
from it; parts joining a song are grooved and tuned to it; responders gain
"groove" and "tune" as relations; the mind is told it in words; the space
is applied live to the mix bus in the browser (synthetic impulse responses
for room and hall, a tempo-synced feedback delay for echo, with a slow
wobble and darker filter for space echo). Moods are presets written out in
the open in `MOODS`; the user can override any field. Scales: the seven
modes, pentatonic, whole tone, 19-edo, 31-edo, Bohlen-Pierce, 7-edo, or
free. Songs remember their scale, root, and groove so answers stay in the
band's tuning. A "retake song" refits the current song to the direction.

Founders rebuilt, ten now, each tagged with a palette and given a body:
modular-drone, digital-chime, analog-bass, drum-kit, pluck-garden,
grain-weather, pad-dusk, pulse-wire, voice-moth, glass-bowl. Parts are
leveled by sounding RMS (-20 dBFS) at render so no instrument hides behind
another; the listener sets balance by dragging. Old archives keep the old
founders; start fresh (`rm -rf archive`, `python -m grow init`) to get the
new ten.

Verified: a tranquil/lydian direction cast Dusk, Bowl, Pluck and Moss at
54 and 60 bpm in lydian with a drone groove, pitches snapped to the scale;
in the browser, clicking the conductor opens the panel, choosing a mood
updates the direction and rebuilds the space, directing records it.
Nobody has listened.

## 2026-10-18 — phrases and thoughts

Arne: more fun to interact with, but the players' thinking is barely
telegraphed, and the music is the same note sequence all along, no prosody,
no going anywhere: quick and slow, long and short, loud and soft, spiral up
then down then break off. Choreography.

Built, for the music: `shape.py`, gestures a part can take over its own
length as relations to time, not judgments: spiral up/down, stairs, swell,
fade, arch, rush, drag, breath (a bar of silence, then back in a new
register), fragment (a motif shedding a note each repeat), long-short,
question-answer, break-off (halfway, thin / double the pace / jump an
octave / hold). "shape" is now a responder (weighted double), founders get
a gesture when they join a band, the mind is asked for a shape, and songs
default to 8-16 bars so an arc has room. Every gesture renders on every
founder. The full scene is now a chain: the song, then its descendants,
each one loop, with only the changed parts swapping in exactly on the loop
boundary (phase verified), so the band moves through its own family
instead of repeating. Echo and double now answer one named player.

For the thinking: `respond()` reports progress (listening to whom, trying
what, hearing each candidate, what it chose and by which ear); the stage
shows the latest thought in the player's bubble and logs the sequence;
songs remember what the player considered and the set list shows it; a
dotted attention line runs from a player to the player it is answering.

Verified headless: a chained full scene stepped from the song to its child
on the loop boundary with all stems still in phase; Moss drew a line to
Chime; a live answer streamed "hearing it: moves up an octave", "hearing
it: takes a breath", "chose: takes a breath at bar 2 and comes back lower".

Honest limit: gestures are blind transformations and the ear is still
novelty until Arne's dial trains the per-family probes; so for now they
make parts move, not make them good. That is the right order.
