# Lessons from Grow 1

This is the only thing carried over from the first attempt. Grow 1 ran for
thirty-five days in mid 2026 as a browser app: three synth voices, a
top-down terrarium canvas, a local language model, and a long chain of
scorers, candidates, votes, and inspectors around them. It ended with
roughly twenty-seven thousand lines of TypeScript, four hundred kilobytes of
process notes, and music that its owner described as ever more elaborate and
ever more stale. The system "couldn't hear what was good." A whole-repository
review in October 2026 found the structural reasons. They are recorded here
so Grow 2 does not repeat them.

Each lesson has three parts: what we did, what happened, what we take.

## 1. We built everything except an ear

**What we did.** Every judgment in the system was a rule the author wrote:
a taste ladder, a prosody scorer, a melody scorer, a form scorer, a
consensus table. "Listening" read back the velocities the engine itself had
just emitted. No audio feature existed anywhere in the project.

**What happened.** The scorer was the generator's own template written a
second time. The generator produced the template by default, so generation
zero already sat near the optimum. "Evolution" climbed a hill whose top it
started on. Nothing external, no audio, no human vote, no model judgment, no
learned function, ever entered the objective.

**What we take.** The ear comes first and the ear is never hand-written.
Judgments come from measurements of sound, from human votes, from probes
trained on those votes, and from a model describing what it is told in
words. If you find yourself writing a function that decides whether music is
good, stop.

## 2. Safety rails became the design

**What we did.** Early, sensible rules: the app owns every note; model
output is data, not instruction; everything deterministic and inspectable.

**What happened.** The rules hardened into law. The local model, the only
component that could have surprised anyone, was allowed to say "quieter" or
"up an octave" for four beats, in one session mode, after a manual health
check. Its actual note ideas were validated and then thrown away. Every
course correction was re-expressed as another deterministic, inspect-only
subsystem because that was the only shape the rails allowed.

**What we take.** Rails go on the sandbox, not on the music. A clip must
render, finish in time, not be silent, and not be painfully loud. Inside
those rails, anything is allowed: dissonance, noise, silence, roughness,
broken phrases, new instruments. The ears decide what survives, not the
rules.

## 3. Three frozen bodies

**What we did.** A sine kick, a triangle bass, a sine lead. No effects, no
mixer, no samples. A fourth player could not make sound without editing the
transport's dispatch code.

**What happened.** With three fixed timbres there was nothing to hear a
difference in. The last diagnosis before the project stalled named this
("frozen synth body") but the proposed fix was more knobs on the same three
synths.

**What we take.** The genome includes the instrument. A variation must be
able to change what a thing is made of, not only what notes it plays.
Adding a sound never means editing the engine. Content is data.

## 4. The process selected for stale

**What we did.** Ninety-five small increments in thirty-five days, each
reviewed, each smoke-tested, each required to be deterministic and
inspectable by browser hooks. Sixty-nine review files. A review queue that
grew to a hundred and fifty carry-forward lines.

**What happened.** Each increment added a rule, because a rule is what fits
in a reviewable, testable increment. Thirty-five reviews ended "blockers:
none" and listed forward notes that became the next increment. One JSON
field consumed five increments. The reviewer verified by reading hook output
because it could not hear the audio. The owner's ear appears in the project
log five times, all in the last two weeks, always as "pivoted after Arne
reported." A listening acceptance test was first written on the last day.

**What we take.** Creative search needs batches of throwaway attempts judged
by an ear, not increments judged by a test. Small reviewed increments are
right for the sandbox and the store, and wrong for the music. The listening
sheet is the only acceptance test. Memory is clips and votes, not prose.

## 5. "Evolution" was a costume

**What we did.** A candidate store, fitness, elites, reservoirs, branches,
lineage, generations.

**What happened.** Each cycle injected a fresh random batch unrelated to
the elites. Each elite spawned one child by an operator chosen from a hash
of constants, so it proposed the identical child every generation. Each
mutation silenced the expressive part of the genome. "Diversity" measured
distance between score vectors, not between phrases. The human votes were
written to a database and never read back. It was a ranking with
persistence, not a search.

**What we take.** Use a real search shape and keep it honest. Quality
diversity: a map of niches defined by measurements, where a weird clip in
an empty niche is a stepping stone even if nobody likes it yet. Parents are
drawn from the whole map. Votes are read back and used. If a mechanism has
the name of a search but not the behavior, it is a costume.

## 6. The browser was the wrong home

**What we did.** Web audio, a canvas renderer, a Vite dev server, an
inspector with fourteen panels. Forty-five percent of the code was interface.

**What happened.** A browser is real-time only. It cannot batch-render a
hundred candidates offline, cannot run audio-understanding models, and
pulls every hour of work toward another panel. For a system with three
sounds, most of the effort went into looking at them.

**What we take.** The organism lives in a headless process that can render
hundreds of clips an hour and run real ears. The browser is a window onto
the archive, built last, and only as far as listening requires.

## 7. The ideas were good

**What we did.** Wrote principles before building: a shared listening frame;
imagined, committed, and heard as three states of an idea; session modes with
real silence; players as disagreeing temperaments rather than one objective
score; a producer who speaks in ordinary language and can be ignored;
best-moments as a small tray; terrariums that hear each other.

**What happened.** Almost none of it was built. The code went elsewhere.

**What we take.** Keep the ideas, lose the code. Players are ears before they
are hands. A second player is a second ear trained on a different vote
stream. A second band is a second map with its own ears. The producer is a
direction the ears can be nudged in. Those are all cheap once the first ear
exists, and impossible before it.
