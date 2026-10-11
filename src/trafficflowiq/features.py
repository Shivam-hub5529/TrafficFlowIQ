"""Queue-prediction features.

LEAKAGE RULE: every feature at time t uses data at times <= t only. Only
`.shift(k)` with k >= 0 and trailing rolling windows are used. The test
`tests/test_no_leakage.py` verifies this by corrupting the future and checking
that features at t do not change.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import HIST_STEPS, QUEUE_RATIO
from .labels import long_index
from .panel import Panel

QUEUE_FEATURES: list[str] = []   # filled by build_queue_features on first call


def _neighbor(wide: pd.DataFrame, meta: pd.DataFrame, col: str) -> pd.DataFrame:
    """For every link, the series of its upstream/downstream neighbour (NaN if none)."""
    ids = meta[col].reindex(wide.columns).to_numpy()
    out = np.full(wide.shape, np.nan)
    pos = {c: i for i, c in enumerate(wide.columns)}
    vals = wide.to_numpy()
    for j, nid in enumerate(ids):
        if nid in pos:
            out[:, j] = vals[:, pos[nid]]
    return pd.DataFrame(out, index=wide.index, columns=wide.columns)


def _sincos(index: pd.DatetimeIndex, n_links: int):
    m = (index.hour * 60 + index.minute).to_numpy()
    ang = 2 * np.pi * m / 1440.0
    tile = lambda a: np.repeat(a[:, None], n_links, axis=1)
    return tile(np.sin(ang)), tile(np.cos(ang)), tile((index.dayofweek >= 5).astype(float)), tile(m.astype(float))


def build_queue_features(panel: Panel) -> pd.DataFrame:
    """Return a (timestamp, link_id)-indexed table of features, plus `step_idx`."""
    W = HIST_STEPS
    links = panel.links
    n = len(links)
    meta = panel.meta.reindex(links)
    ffs = meta["ffs_kmh"].to_numpy(float)[None, :]
    lanes = meta["lanes"].to_numpy(float)[None, :]
    length = meta["length_km"].to_numpy(float)[None, :]
    has_ramp = (meta["ramp_type"] != "none").to_numpy()[None, :]
    ramp_is_on = (meta["ramp_type"] == "on").to_numpy()[None, :]

    S, F, O = panel.speed, panel.flow_pl, panel.occ
    R = S.div(ffs[0], axis=1)
    queued = (R <= QUEUE_RATIO).astype(float).where(R.notna())
    f: dict[str, pd.DataFrame | np.ndarray] = {}

    # current state
    f["speed_t"], f["flow_pl_t"], f["occ_t"], f["ratio_t"] = S, F, O, R
    f["queued_t"] = queued
    f["density_t"] = F / S.clip(lower=5)

    # lags (t-5, t-15, t-30, t-55)
    for k in (1, 3, 6, 11):
        f[f"speed_lag_{k}"] = S.shift(k)
    f["flow_pl_lag_3"] = F.shift(3)
    f["occ_lag_3"] = O.shift(3)

    # trend and volatility over trailing windows
    for k in (3, 6, 11):
        f[f"speed_chg_{k}"] = S - S.shift(k)
        f[f"speed_pct_chg_{k}"] = (S - S.shift(k)) / S.shift(k).clip(lower=5)
    f["occ_chg_6"] = O - O.shift(6)
    roll = S.rolling(W, min_periods=3)
    f["speed_mean_12"], f["speed_min_12"], f["speed_max_12"], f["speed_std_12"] = roll.mean(), roll.min(), roll.max(), roll.std()
    f["max_drop5_12"] = (-S.diff()).rolling(W, min_periods=3).max()
    f["ratio_min_12"] = R.rolling(W, min_periods=3).min()
    f["n_queued_12"] = queued.fillna(0).rolling(W, min_periods=1).sum()
    f["n_missing_speed_12"] = S.isna().astype(float).rolling(W, min_periods=1).sum()

    # spatial context
    for tag, col in (("up", "upstream_id"), ("down", "downstream_id")):
        Sn = _neighbor(S, meta, col)
        Rn = _neighbor(R, meta, col)
        On = _neighbor(O, meta, col)
        f[f"{tag}_ratio_t"] = Rn
        f[f"{tag}_speed_chg_6"] = Sn - Sn.shift(6)
        f[f"{tag}_ratio_min_12"] = Rn.rolling(W, min_periods=3).min()
        f[f"{tag}_occ_t"] = On
    f["gap_up_minus_cur"] = f["up_ratio_t"] - R
    f["gap_cur_minus_down"] = R - f["down_ratio_t"]

    # ramp evidence: bad readings are NaN + explicit missing indicators
    Rp = panel.ramp
    Bad = panel.ramp_bad.astype(float)
    f["ramp_flow_t"] = Rp
    f["ramp_flow_mean_12"] = Rp.rolling(W, min_periods=2).mean()
    f["ramp_bad_t"] = Bad
    f["ramp_bad_frac_12"] = Bad.rolling(W, min_periods=1).mean()

    # static + calendar
    ones = np.ones((len(S), n))
    f["lanes"], f["length_km"], f["ffs_kmh"] = ones * lanes, ones * length, ones * ffs
    f["has_ramp"], f["ramp_is_on"] = ones * has_ramp, ones * ramp_is_on
    s, c, wk, mod = _sincos(S.index, n)
    f["tod_sin"], f["tod_cos"], f["is_weekend"], f["minute_of_day"] = s, c, wk, mod

    idx = long_index(panel)
    cols = {k: (v.to_numpy() if isinstance(v, pd.DataFrame) else v).ravel() for k, v in f.items()}
    out = pd.DataFrame(cols, index=idx)
    out["step_idx"] = np.repeat(np.arange(len(S)), n)
    global QUEUE_FEATURES
    QUEUE_FEATURES = [c for c in out.columns if c != "step_idx"]
    return out


def valid_rows(feats: pd.DataFrame) -> pd.Series:
    """A prediction is possible only with a full 60-min window and an observed current speed."""
    return (feats["step_idx"] >= HIST_STEPS - 1) & feats["speed_t"].notna()
