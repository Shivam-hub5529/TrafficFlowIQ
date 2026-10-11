"""Traffic-state reconstruction: fill missing speed and flow-per-lane.

Reconstruction is RETROSPECTIVE, so it may use values on both sides of a gap
(before and after). This is different from queue prediction, which never sees the future.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .features import _neighbor, _sincos
from .labels import long_index
from .panel import Panel

TARGETS = ("speed", "flow_pl")


def simulate_mask(shape, rate: float, rng: np.random.Generator) -> np.ndarray:
    """Mixture of single-point dropouts (60%) and bursts of 3-8 steps (40%)."""
    T, n = shape
    m = rng.random(shape) < rate * 0.6
    n_starts = int(rate * 0.4 * T * n / 5.5)
    for _ in range(n_starts):
        r, c, ln = int(rng.integers(0, T)), int(rng.integers(0, n)), int(rng.integers(3, 9))
        m[r:r + ln, c] = True
    return m


def gap_lengths(mask: np.ndarray) -> np.ndarray:
    """For every masked cell, the length of the run of masked cells it belongs to."""
    out = np.zeros(mask.shape, dtype=int)
    for j in range(mask.shape[1]):
        col, i = mask[:, j], 0
        while i < len(col):
            if col[i]:
                k = i
                while k < len(col) and col[k]:
                    k += 1
                out[i:k, j] = k - i
                i = k
            else:
                i += 1
    return out


def mask_panel(panel: Panel, rate: float, seed: int, links: list | None = None):
    """Hide speed and flow independently. Returns (masked panel, speed mask, flow mask).
    Masks only cover cells that were originally observed (we need ground truth)."""
    rng = np.random.default_rng(seed)
    shape = panel.speed.shape
    ms, mf = simulate_mask(shape, rate, rng), simulate_mask(shape, rate, rng)
    if links is not None:
        keep = np.array([l in links for l in panel.links])[None, :]
        ms, mf = ms & keep, mf & keep
    ms &= panel.speed.notna().to_numpy()
    mf &= panel.flow_pl.notna().to_numpy()
    p = panel.copy()
    p.speed = p.speed.mask(ms)
    p.flow_pl = p.flow_pl.mask(mf)
    p.flow = p.flow.mask(mf)
    return p, ms, mf


def _interp(df: pd.DataFrame) -> pd.DataFrame:
    return df.interpolate(method="linear", limit_area="inside", axis=0)


def build_recon_features(panel: Panel, target: str) -> pd.DataFrame:
    """Features for reconstructing `target` ('speed' or 'flow_pl'). Built from the MASKED panel."""
    assert target in TARGETS
    links = panel.links
    n = len(links)
    meta = panel.meta.reindex(links)
    X = getattr(panel, target)
    other = panel.flow_pl if target == "speed" else panel.speed
    f: dict[str, pd.DataFrame | np.ndarray] = {}

    for k in (1, 2, 3):
        f[f"x_m{k}"] = X.shift(k)
        f[f"x_p{k}"] = X.shift(-k)
    f["x_interp"] = _interp(X)
    f["x_locf"] = X.ffill(limit=12)
    f["other_t"] = other
    f["other_interp"] = _interp(other)
    f["occ_t"] = panel.occ
    f["occ_interp"] = _interp(panel.occ)
    for tag, col in (("up", "upstream_id"), ("down", "downstream_id")):
        f[f"{tag}_x"] = _neighbor(_interp(X), meta, col)
        f[f"{tag}_other"] = _neighbor(_interp(other), meta, col)
        f[f"{tag}_occ"] = _neighbor(_interp(panel.occ), meta, col)
    f["ramp_t"] = panel.ramp
    f["ramp_bad_t"] = panel.ramp_bad.astype(float)

    ones = np.ones((len(X), n))
    f["lanes"] = ones * meta["lanes"].to_numpy(float)[None, :]
    f["ffs_kmh"] = ones * meta["ffs_kmh"].to_numpy(float)[None, :]
    f["has_ramp"] = ones * (meta["ramp_type"] != "none").to_numpy()[None, :]
    s, c, wk, _ = _sincos(X.index, n)
    f["tod_sin"], f["tod_cos"], f["is_weekend"] = s, c, wk

    idx = long_index(panel)
    out = pd.DataFrame({k: (v.to_numpy() if isinstance(v, pd.DataFrame) else v).ravel() for k, v in f.items()}, index=idx)
    return out
