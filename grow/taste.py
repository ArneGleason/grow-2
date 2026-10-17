"""A taste probe: an ear trained on human votes.

Votes and replays come from the listening sheet (archive/events.csv). The
probe is a ridge regression from a clip's features (and embedding, if the
embedding ear is installed) to a preference score. It is deliberately tiny:
a few dozen votes are enough to start, and it is retrained from scratch
every time, so it never drifts away from the ear that trained it.

A second player is a second probe trained on a different vote stream.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from .archive import Archive, Clip
from .ears import FEATURE_KEYS

MIN_VOTED_CLIPS = 12


def read_events(path: Path) -> dict[str, float]:
    """Fold events into one preference value per clip.

    vote up = +1, vote down = -1, each replay after the first = +0.5 (capped).
    """
    if not path.exists():
        return {}
    votes: dict[str, float] = defaultdict(float)
    plays: dict[str, int] = defaultdict(int)
    with path.open() as fh:
        for row in csv.DictReader(fh):
            cid = row.get("clip", "")
            if not cid:
                continue
            kind = row.get("kind")
            if kind == "vote":
                votes[cid] += float(row.get("value", 0) or 0)
            elif kind == "play":
                plays[cid] += 1
    out: dict[str, float] = {}
    for cid in set(votes) | set(plays):
        replay = min(max(plays[cid] - 1, 0) * 0.5, 2.0)
        if cid in votes or plays[cid] > 1:
            out[cid] = float(np.clip(votes[cid], -2, 2) + replay)
    return out


def _design(clip: Clip, mu: np.ndarray, sd: np.ndarray, use_embedding: bool) -> np.ndarray:
    x = (clip.feats() - mu) / sd
    if use_embedding and clip.embedding is not None:
        x = np.concatenate([x, clip.embedding * 4.0])
    return x


def train(archive: Archive, events_path: Path, out_path: Path, ridge: float = 2.0) -> dict | None:
    prefs = read_events(events_path)
    voted = [archive.clips[cid] for cid in prefs if cid in archive.clips]
    if len(voted) < MIN_VOTED_CLIPS:
        return None
    use_embedding = all(c.embedding is not None for c in voted)
    pool = archive.alive() or voted
    feats = np.stack([c.feats() for c in pool])
    mu, sd = feats.mean(axis=0), feats.std(axis=0) + 1e-6
    X = np.stack([_design(c, mu, sd, use_embedding) for c in voted])
    y = np.array([prefs[c.id] for c in voted])
    X1 = np.hstack([X, np.ones((len(X), 1))])
    lam = ridge * np.eye(X1.shape[1])
    lam[-1, -1] = 0.0
    w = np.linalg.solve(X1.T @ X1 + lam, X1.T @ y)
    pred = X1 @ w
    fit = float(1 - ((y - pred) ** 2).sum() / (((y - y.mean()) ** 2).sum() + 1e-9))
    model = {
        "weights": w.tolist(), "mu": mu.tolist(), "sd": sd.tolist(),
        "use_embedding": use_embedding, "n_votes": len(voted), "fit_r2": fit,
        "feature_keys": FEATURE_KEYS,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(model, indent=1))
    return model


class Probe:
    def __init__(self, model: dict):
        self.w = np.array(model["weights"])
        self.mu = np.array(model["mu"])
        self.sd = np.array(model["sd"])
        self.use_embedding = bool(model["use_embedding"])
        self.n_votes = model.get("n_votes", 0)

    @classmethod
    def load(cls, path: Path) -> "Probe | None":
        if not path.exists():
            return None
        return cls(json.loads(path.read_text()))

    def score(self, clip: Clip) -> float:
        x = _design(clip, self.mu, self.sd, self.use_embedding)
        if len(x) + 1 != len(self.w):
            x = (clip.feats() - self.mu) / self.sd
            if len(x) + 1 != len(self.w):
                return 0.0
        return float(np.dot(self.w[:-1], x) + self.w[-1])
