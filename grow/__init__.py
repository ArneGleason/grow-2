"""Grow 2: a musical terrarium that grows by listening.

The loop is make -> hear -> keep -> vary. Everything a reader needs to
understand the system is in these modules:

- genome:  a clip's program (a Csound .csd) plus lineage metadata
- body:    renders a genome to audio inside a sandbox (the only rails)
- ears:    turns audio into descriptors and, optionally, an embedding
- archive: the map of niches; what is kept and why
- vary:    the mutation and crossover operators on genome text
- mind:    a local language model that rewrites genomes and names clips
- taste:   a per-ear probe trained on human votes
- grow:    the loop
- sheet:   the listening page, which also records votes and replays
"""

ARCHIVE_DIR = "archive"
SEEDS_DIR = "seeds"
