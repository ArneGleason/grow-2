"""The body renders a genome to audio inside a sandbox.

These are the only rails in Grow 2, and they are rails on the sandbox, not
on the music:

- it must compile and render within a time budget,
- it must be between MIN_SECONDS and MAX_SECONDS long (longer is trimmed),
- it must not be silent,
- it is normalized so nothing is painfully loud.

Dissonance, noise, roughness, silence inside a clip, and broken phrases are
all allowed. The ears decide what survives; the body only decides what is
physically a clip.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

MIN_SECONDS = 3.0
MAX_SECONDS = 30.0
RENDER_TIMEOUT = 40.0
TARGET_PEAK = 0.85
PART_LEVEL_DB = -20.0           # sounding RMS for a song part
MIN_ACTIVE_RATIO = 0.08       # fraction of 50 ms frames above the silence floor
SILENCE_FLOOR_DB = -50.0


@dataclass
class Rendered:
    ok: bool
    reason: str = ""
    wav: Path | None = None
    seconds: float = 0.0
    audio: np.ndarray | None = None   # mono float32 at `sr`
    sr: int = 44100


def csound_available() -> bool:
    return shutil.which("csound") is not None


def render(text: str, out_wav: Path, fixed_seconds: float | None = None) -> Rendered:
    """Render .csd text to out_wav. Never raises for a bad genome.

    With `fixed_seconds` the result is a part of a song: it is padded with
    silence or trimmed to exactly that length so every part of a song plays
    in lockstep, and its level is left as written (only pulled down if it
    would clip), because a band's balance belongs to the writers.
    """
    if not csound_available():
        return Rendered(False, "csound binary not found on PATH")
    with tempfile.TemporaryDirectory(prefix="grow-render-") as tmp:
        csd = Path(tmp) / "genome.csd"
        csd.write_text(text)
        raw = Path(tmp) / "raw.wav"
        cmd = ["csound", "-d", "-m0", "-W", "-f", "-o", str(raw), str(csd)]
        try:
            proc = subprocess.run(
                cmd, cwd=tmp, capture_output=True, text=True, timeout=RENDER_TIMEOUT,
                env={**os.environ, "CSNOSTOP": "1"},
            )
        except subprocess.TimeoutExpired:
            return Rendered(False, f"render exceeded {RENDER_TIMEOUT:.0f}s")
        if proc.returncode != 0 or not raw.exists():
            tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-3:]
            return Rendered(False, "csound failed: " + " | ".join(tail)[:300])
        try:
            data, sr = sf.read(str(raw), dtype="float32", always_2d=True)
        except Exception as exc:  # noqa: BLE001
            return Rendered(False, f"unreadable audio: {exc}")

    if not np.all(np.isfinite(data)):
        return Rendered(False, "audio contains NaN or inf")
    if fixed_seconds:
        n = int(fixed_seconds * sr)
        if data.shape[0] < n:
            data = np.vstack([data, np.zeros((n - data.shape[0], data.shape[1]), dtype=data.dtype)])
        data = data[:n]
    else:
        if data.shape[0] < int(MIN_SECONDS * sr):
            return Rendered(False, f"shorter than {MIN_SECONDS:.0f}s")
        data = data[: int(MAX_SECONDS * sr)]

    peak = float(np.max(np.abs(data)))
    if peak < 1e-5:
        return Rendered(False, "silent")
    if fixed_seconds:
        # a part: level its sounding RMS to PART_LEVEL_DB so every player can be
        # heard before the listener sets the balance; cap the peak
        m = data.mean(axis=1)
        fr = int(0.05 * sr)
        nf = len(m) // fr
        if nf:
            fr_rms = np.sqrt((m[: nf * fr].reshape(nf, fr) ** 2).mean(axis=1))
            loud = fr_rms[fr_rms > 10 ** (SILENCE_FLOOR_DB / 20)]
            rms = float(np.sqrt((loud ** 2).mean())) if len(loud) else float(np.sqrt((m ** 2).mean()))
            if rms > 1e-6:
                data = data * min(10 ** (PART_LEVEL_DB / 20) / rms, 0.95 / peak)
    else:
        data = data * (TARGET_PEAK / peak)

    mono = data.mean(axis=1)
    frame = int(0.05 * sr)
    nframes = len(mono) // frame
    if nframes == 0:
        return Rendered(False, "too short to analyze")
    frames = mono[: nframes * frame].reshape(nframes, frame)
    rms_db = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-9)
    active = float((rms_db > SILENCE_FLOOR_DB).mean())
    if active < (0.03 if fixed_seconds else MIN_ACTIVE_RATIO):
        return Rendered(False, f"mostly silent (active {active:.0%})")

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_wav), data, sr, subtype="PCM_16")
    return Rendered(True, wav=out_wav, seconds=len(mono) / sr, audio=mono.astype(np.float32), sr=sr)
