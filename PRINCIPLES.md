# Principles

Ten rules for Grow 2. Each one exists because its opposite failed in Grow 1
(see `LESSONS.md`). Change them when listening says so, not when a plan
says so.

1. **The ear test is the only acceptance test.** A change is done when a
   person listens and would play more of the clips twice. Nothing about the
   music is ever proven by a unit test, a smoke test, or a log line.

2. **No hand-written judgment.** The system never contains a function that
   decides whether music is good. Judgments come from measurements of sound,
   human votes, probes trained on those votes, and a model describing what it
   is told in words. Measurements are facts, not scores.

3. **Rails on the sandbox, never on the music.** A clip must render, finish
   in time, not be silent, and not be painfully loud. That is the whole list.
   Dissonance, noise, long silence, roughness, broken phrases, and strange
   instruments are allowed.

4. **The genome includes the instrument.** A clip's program contains its
   sound and its notes together. A variation can change what a thing is made
   of. Adding a sound never means editing the engine.

5. **Content is data.** If a new piece, sound, or behavior requires a code
   change, the code has become the composer. Put it in the genome instead.

6. **Grow by filling the map, not by climbing a number.** The archive is a
   map of niches defined by measurements. A clip survives by claiming empty
   territory or by beating a neighbor on an ear. Stepping stones count.
   Parents come from the whole map.

7. **Off the clock.** Everything renders and listens in batch, faster than
   real time. Nothing waits on a playback clock. Thirty seconds of thinking
   per candidate is fine when there are a hundred candidates.

8. **Minds author and describe; ears decide.** The language model writes
   programs, proposes directions in words, and names things. It never ranks
   clips by number and never decides what survives.

9. **Players are ears first.** A player is defined by what it loves to hear:
   a vote stream and the probe trained on it. Two players with different
   ears make different music from the same bodies. Bands are maps; a second
   band is a second map with its own ears.

10. **Memory is clips and votes.** One running `NOTES.md` with dates, what
    was tried, and what was heard. No review queue, no handoff folder, no
    inspector panels. Tests exist only for the sandbox and the store. If the
    notes outgrow the archive, the project is drifting.
