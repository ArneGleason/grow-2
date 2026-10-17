"""The mind is a local language model, used for what minds are good at:

- rewriting a genome (instrument and score) toward a described direction,
- naming a clip from its facts and lineage.

It never ranks clips by number and it never decides what survives. If the
model is unreachable or returns junk, the caller falls back to blind
variation. Point GROW_MODEL at whatever `ollama list` shows.
"""

from __future__ import annotations

import json
import os
import random
import urllib.error
import urllib.request

from .genome import Genome, extract_csd

OLLAMA_URL = os.environ.get("GROW_OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("GROW_MODEL", "qwen3:8b")
TIMEOUT = float(os.environ.get("GROW_MIND_TIMEOUT", "120"))

SYSTEM_REWRITE = """You write Csound .csd files for a small musical terrarium.
Return exactly one complete .csd between <CsoundSynthesizer> and </CsoundSynthesizer> and nothing else.
Keep the header lines sr, ksmps, nchnls and 0dbfs = 1 unchanged. Keep amplitudes between 0 and 0.8.
Keep the whole score between 6 and 20 seconds, and put every score event before the final e line. Use only opcodes that exist in Csound 6.
You may change the instrument as freely as the notes: new synthesis, filters, envelopes, delays, noise, silence.
Nothing has to be in tune, in time, or pleasant. It has to be different in the way asked, and it has to render."""

SYSTEM_NAME = """You name sounds for a musical terrarium. Reply with a two or three word name only, lowercase, no punctuation."""


def available() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=3) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def _chat(system: str, user: str, num_predict: int = 2048) -> str | None:
    body = json.dumps({
        "model": MODEL,
        "stream": False,
        "think": False,
        "options": {"temperature": 0.9, "num_predict": num_predict},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = json.loads(r.read().decode())
        return data.get("message", {}).get("content")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def rewrite(parent: Genome, facts: str, nudge: str, rng: random.Random) -> Genome | None:
    flavor = rng.choice([
        "Change the instrument's sound as much as the notes.",
        "Keep the instrument but change what it plays.",
        "Add a second instrument that answers the first.",
        "Take something away.",
        "Make one thing in it stranger.",
    ])
    user = (
        f"Here is the current genome:\n\n{parent.text}\n\n"
        f"What it sounds like now: {facts}.\n"
        f"Make a variant that is {nudge}. {flavor}\n"
        "Return the complete .csd only."
    )
    reply = _chat(SYSTEM_REWRITE, user)
    if not reply:
        return None
    csd = extract_csd(reply)
    if not csd or csd == parent.text:
        return None
    return parent.child(csd + "\n", "mind", f"asked for: {nudge}")


def name(facts: str, lineage_names: list[str], rng: random.Random) -> str | None:
    user = f"Facts: {facts}.\nAncestors: {', '.join(lineage_names) or 'none'}.\nName it."
    reply = _chat(SYSTEM_NAME, user, num_predict=16)
    if not reply:
        return None
    words = [w.strip(".,!\"'").lower() for w in reply.split()][:3]
    return " ".join(w for w in words if w) or None


# A fallback namer so clips have names even without a mind. Words only; no
# musical judgment is encoded here, only something to say out loud.
ADJ = ["quiet", "brass", "wet", "hollow", "tin", "slow", "burnt", "glass", "paper", "stone",
       "thin", "rusty", "pale", "loud", "wire", "fog", "salt", "moth", "velvet", "crooked"]
NOUN = ["garden", "engine", "bell", "ladder", "harbor", "kettle", "orbit", "lantern", "marsh", "clock",
        "needle", "shelf", "wheel", "thread", "cellar", "kite", "ember", "pocket", "river", "hinge"]


def fallback_name(rng: random.Random) -> str:
    return f"{rng.choice(ADJ)} {rng.choice(NOUN)}"
