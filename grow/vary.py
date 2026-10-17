"""Variation operators on genome text.

Three are blind (they do not know what the text means) and one is a mind.
Blind operators carry most of the load because they never fail to produce
something; the sandbox rejects what does not render. The mind operator is
asked to move a clip toward empty territory on the map and may change the
instrument as well as the notes.

None of these operators knows anything about scales, meters, or style.
"""

from __future__ import annotations

import math
import random
import re

from .genome import Genome

NUM_RE = re.compile(r"(?<![\w.])(-?\d+\.\d+|-?\d+)(?![\w.])")
HEADER_WORDS = ("sr", "ksmps", "nchnls", "0dbfs", "instr", "endin", "opcode", "endop")


def _line_is_protected(line: str) -> bool:
    s = line.strip()
    if not s or s.startswith(";"):
        return True
    if s.startswith("f") and len(s) > 1 and (s[1].isspace() or s[1].isdigit()):
        return True  # function tables: GEN numbers and sizes must stay valid
    first = s.split()[0]
    return first in HEADER_WORDS or first.rstrip("0123456789") in ("instr",)


def _jitter_number(tok: str, rng: random.Random, sigma: float) -> str:
    if "." in tok:
        v = float(tok)
        if v == 0.0:
            return tok
        return f"{v * math.exp(rng.gauss(0, sigma)):.4g}"
    v = int(tok)
    if abs(v) <= 4:
        return tok  # table numbers, small flags, counts: leave alone
    nv = int(round(v * math.exp(rng.gauss(0, sigma))))
    return str(max(nv, 1) if v > 0 else nv)


def jitter(parent: Genome, rng: random.Random, n: int | None = None, sigma: float = 0.35) -> Genome:
    """Perturb a few numeric literals anywhere in the orchestra or score."""
    lines = parent.text.splitlines()
    spots: list[tuple[int, int]] = []
    for i, line in enumerate(lines):
        if _line_is_protected(line):
            continue
        for m in NUM_RE.finditer(line):
            spots.append((i, m.start()))
    if not spots:
        return parent.child(parent.text, "jitter", "no numbers to move")
    n = n or rng.choice([1, 2, 3, 4, 6])
    chosen = rng.sample(spots, min(n, len(spots)))
    chosen.sort(reverse=True)
    for i, start in chosen:
        line = lines[i]
        m = NUM_RE.match(line, start)
        if not m:
            continue
        new = _jitter_number(m.group(0), rng, sigma)
        lines[i] = line[: m.start()] + new + line[m.end():]
    return parent.child("\n".join(lines) + "\n", "jitter", f"moved {len(chosen)} numbers")


def _score_lines(score: str) -> tuple[list[str], list[int]]:
    lines = score.splitlines()
    idx = [i for i, l in enumerate(lines) if l.strip().startswith("i")]
    return lines, idx


def _parse_i(line: str) -> list[str] | None:
    parts = line.split()
    if not parts or not parts[0].startswith("i"):
        return None
    if parts[0] == "i":
        parts = ["i" + parts[1]] + parts[2:]
    return parts


def score_edit(parent: Genome, rng: random.Random) -> Genome:
    """One structural edit to the score: stretch, thin, echo, reverse, or recolor a column."""
    score = parent.score()
    lines, idx = _score_lines(score)
    if len(idx) < 2:
        return jitter(parent, rng)
    op = rng.choice(["stretch", "thin", "echo", "reverse", "column", "column"])
    rows = [(_parse_i(lines[i]), i) for i in idx]
    rows = [(p, i) for p, i in rows if p and len(p) >= 3]
    if not rows:
        return jitter(parent, rng)

    def fnum(s: str) -> float | None:
        try:
            return float(s)
        except ValueError:
            return None

    if op == "stretch":
        k = math.exp(rng.uniform(-0.6, 0.6))
        for p, i in rows:
            for col in (1, 2):
                v = fnum(p[col])
                if v is not None:
                    p[col] = f"{v * k:.3f}"
            lines[i] = " ".join(p)
        note = f"stretched time x{k:.2f}"
    elif op == "thin":
        keep = max(2, int(len(rows) * rng.uniform(0.5, 0.9)))
        drop = set(i for _, i in rng.sample(rows, len(rows) - keep))
        lines = [l for j, l in enumerate(lines) if j not in drop]
        note = f"dropped {len(drop)} events"
    elif op == "echo":
        shift = rng.choice([0.125, 0.25, 0.33, 0.5, 0.75, 1.0, 1.5])
        picks = rng.sample(rows, max(1, len(rows) // rng.choice([2, 3, 4])))
        extra = []
        for p, _ in picks:
            q = list(p)
            v = fnum(q[1])
            if v is None:
                continue
            q[1] = f"{v + shift:.3f}"
            extra.append(" ".join(q))
        end = next((j for j, l in enumerate(lines) if l.strip() == "e"), len(lines))
        lines[end:end] = extra
        note = f"echoed {len(extra)} events by {shift}s"
    elif op == "reverse":
        ends = [fnum(p[1]) + fnum(p[2]) for p, _ in rows if fnum(p[1]) is not None and fnum(p[2]) is not None]
        total = max(ends) if ends else 0.0
        for p, i in rows:
            s, d = fnum(p[1]), fnum(p[2])
            if s is None or d is None:
                continue
            p[1] = f"{max(0.0, total - s - d):.3f}"
            lines[i] = " ".join(p)
        note = "reversed the order of events"
    else:  # column: scale one p-field across all events of one instrument
        instrs = sorted(set(p[0] for p, _ in rows))
        target = rng.choice(instrs)
        widths = [len(p) for p, _ in rows if p[0] == target]
        if min(widths) <= 3:
            return jitter(parent, rng)
        col = rng.randrange(3, min(widths))
        k = math.exp(rng.gauss(0, 0.5))
        for p, i in rows:
            if p[0] != target:
                continue
            v = fnum(p[col])
            if v is not None:
                p[col] = f"{v * k:.4g}"
            lines[i] = " ".join(p)
        note = f"scaled p{col + 1} of {target} by x{k:.2f}"
    return parent.child(parent.with_parts(score="\n" + "\n".join(lines) + "\n"), "score", note)


def crossover(a: Genome, b: Genome, rng: random.Random) -> Genome:
    """A's instruments play B's score. Instrument numbers are remapped onto A's."""
    a_instrs = sorted(set(int(m) for m in re.findall(r"^\s*instr\s+(\d+)", a.instruments(), re.M)))
    if not a_instrs:
        return jitter(a, rng)
    score = b.score()
    lines = score.splitlines()
    out = []
    for line in lines:
        p = _parse_i(line) if line.strip().startswith("i") else None
        if p:
            try:
                n = int(p[0][1:])
            except ValueError:
                out.append(line)
                continue
            p[0] = "i" + str(a_instrs[n % len(a_instrs)])
            out.append(" ".join(p))
        else:
            out.append(line)
    # carry any f-tables A's instruments relied on
    a_tables = [l for l in a.score().splitlines() if l.strip().startswith("f")]
    b_tables = set(l.strip() for l in out if l.strip().startswith("f"))
    extra = [l for l in a_tables if l.strip() not in b_tables]
    new_score = "\n" + "\n".join(extra + out) + "\n"
    child = a.child(a.with_parts(score=new_score), "cross", f"{a.name or a.id} body playing {b.name or b.id} score", other=b)
    return child


def blind(parent: Genome, rng: random.Random, mate: Genome | None = None) -> Genome:
    r = rng.random()
    if mate is not None and r < 0.2:
        return crossover(parent, mate, rng)
    if r < 0.55:
        return jitter(parent, rng)
    return score_edit(parent, rng)
