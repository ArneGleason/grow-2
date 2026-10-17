"""Ears turn audio into facts.

Two ears live here:

- the descriptor ear: cheap signal measurements (how dense, how bright, how
  loud, how noisy, how pulsed). These define the map's axes and are the facts
  the mind gets to reason about. They are measurements, not judgments.
- the embedding ear (optional): a CLAP audio embedding, used for novelty and
  for the taste probe once votes exist. Install the `clap` extra to enable it.

Nothing in this file says what is good. That is the point.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict

import numpy as np
from scipy import signal, ndimage

NPERSEG = 2048
HOP = 512


@dataclass
class Descriptors:
    seconds: float
    loudness_db: float        # mean RMS in dBFS
    loudness_range_db: float  # p95 - p10 of frame loudness, sounding frames only
    silence_ratio: float      # fraction of frames under the floor
    onset_density: float      # onsets per second
    centroid_hz: float        # mean spectral centroid, sounding frames only
    flatness: float           # 0 = pure tone, 1 = white noise
    low_ratio: float          # energy below 200 Hz
    high_ratio: float         # energy above 4 kHz
    pulse_strength: float     # 0..1, how periodic the onsets are
    pulse_period_s: float     # the period that strength refers to

    def as_dict(self) -> dict:
        return asdict(self)

    def facts(self) -> str:
        """A short human/model-readable sentence of facts."""
        return (
            f"{self.seconds:.0f}s long; {self.onset_density:.1f} onsets/s; "
            f"centroid {self.centroid_hz:.0f} Hz; loudness {self.loudness_db:.0f} dB "
            f"with {self.loudness_range_db:.0f} dB of range; {self.silence_ratio:.0%} silence; "
            f"flatness {self.flatness:.2f}; low {self.low_ratio:.0%}, high {self.high_ratio:.0%}; "
            f"pulse {self.pulse_strength:.2f} at {self.pulse_period_s:.2f}s"
        )


# The feature vector used for novelty and for the taste probe. Order matters
# only for consistency; all entries are roughly unit-scaled after z-scoring.
FEATURE_KEYS = [
    "loudness_range_db", "silence_ratio", "log_onset", "log_centroid",
    "flatness", "low_ratio", "high_ratio", "pulse_strength",
]


def features(d: Descriptors) -> np.ndarray:
    return np.array([
        d.loudness_range_db,
        d.silence_ratio,
        math.log10(max(d.onset_density, 0.05)),
        math.log2(max(d.centroid_hz, 40.0)),
        d.flatness,
        d.low_ratio,
        d.high_ratio,
        d.pulse_strength,
    ], dtype=np.float64)


def describe(mono: np.ndarray, sr: int) -> Descriptors:
    x = mono.astype(np.float64)
    seconds = len(x) / sr

    f, t, Z = signal.stft(x, fs=sr, nperseg=NPERSEG, noverlap=NPERSEG - HOP, padded=False, boundary=None)
    mag = np.abs(Z) + 1e-12
    power = mag ** 2
    frame_energy = power.sum(axis=0)
    frame_db = 10 * np.log10(frame_energy / NPERSEG + 1e-12)
    sounding = frame_db > -50.0
    if sounding.sum() < 2:
        sounding = np.ones_like(sounding, dtype=bool)

    # loudness
    frame = HOP
    n = len(x) // frame
    rms = np.sqrt((x[: n * frame].reshape(n, frame) ** 2).mean(axis=1)) if n else np.array([1e-9])
    rms_db = 20 * np.log10(rms + 1e-9)
    loud = rms_db[rms_db > -50.0]
    loudness_db = float(20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9))
    loudness_range = float(np.percentile(loud, 95) - np.percentile(loud, 10)) if len(loud) > 4 else 0.0
    silence_ratio = float((rms_db <= -50.0).mean())

    # spectral shape
    centroid = (f[:, None] * mag).sum(axis=0) / (mag.sum(axis=0) + 1e-12)
    centroid_hz = float(centroid[sounding].mean())
    flat = np.exp(np.log(mag).mean(axis=0)) / (mag.mean(axis=0) + 1e-12)
    flatness = float(np.clip(flat[sounding].mean(), 0, 1))
    total = power.sum() + 1e-12
    low_ratio = float(power[f < 200].sum() / total)
    high_ratio = float(power[f > 4000].sum() / total)

    # onsets by spectral flux
    # onsets: SuperFlux-style. Compress magnitudes, then compare each frame
    # against a max-filtered previous frame so energy that merely slides to a
    # neighboring bin (vibrato, beating between close partials) does not count
    # as new. A drifting drone reads near zero; a struck note reads high.
    cmag = np.log1p(50.0 * mag)
    prev = ndimage.maximum_filter1d(cmag[:, :-1], size=3, axis=0)
    flux = np.maximum(0, cmag[:, 1:] - prev).sum(axis=0) / (cmag[:, 1:].sum(axis=0) + 1e-12)
    min_gap = max(1, int(0.06 * sr / HOP))
    peaks, _ = signal.find_peaks(flux, prominence=0.08, height=0.12, distance=min_gap)
    onset_density = float(len(peaks) / seconds)

    # pulse: autocorrelation of the flux curve between 0.2 and 2.0 s
    fl = flux - flux.mean()
    ac = np.correlate(fl, fl, mode="full")[len(fl) - 1:]
    ac = ac / (ac[0] + 1e-12)
    lo, hi = int(0.2 * sr / HOP), int(2.0 * sr / HOP)
    if hi > lo + 1 and len(ac) > hi:
        seg = ac[lo:hi]
        k = int(np.argmax(seg))
        pulse_strength = float(np.clip(seg[k], 0, 1))
        pulse_period = float((lo + k) * HOP / sr)
    else:
        pulse_strength, pulse_period = 0.0, 0.0

    return Descriptors(
        seconds=float(seconds),
        loudness_db=loudness_db,
        loudness_range_db=loudness_range,
        silence_ratio=silence_ratio,
        onset_density=onset_density,
        centroid_hz=centroid_hz,
        flatness=flatness,
        low_ratio=low_ratio,
        high_ratio=high_ratio,
        pulse_strength=pulse_strength,
        pulse_period_s=pulse_period,
    )


# ---------------------------------------------------------------- embedding ear

_clap = None


def embedding_available() -> bool:
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def embed(mono: np.ndarray, sr: int) -> np.ndarray | None:
    """CLAP audio embedding, or None when the optional extra is not installed."""
    global _clap
    if not embedding_available():
        return None
    import torch
    from transformers import ClapModel, ClapProcessor
    if _clap is None:
        name = "laion/clap-htsat-unfused"
        _clap = (ClapModel.from_pretrained(name).eval(), ClapProcessor.from_pretrained(name))
    model, proc = _clap
    target = 48000
    if sr != target:
        n = int(len(mono) * target / sr)
        mono = signal.resample(mono, n)
    with torch.no_grad():
        inputs = proc(audios=mono.astype(np.float32), sampling_rate=target, return_tensors="pt")
        vec = model.get_audio_features(**inputs)[0]
    vec = vec / (vec.norm() + 1e-9)
    return vec.cpu().numpy().astype(np.float32)
