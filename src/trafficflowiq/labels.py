"""Queue labels. Labels use FUTURE data and are used only as training targets."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import HORIZONS_MIN, QUEUE_RATIO, STEP_MIN
from .panel import Panel


def long_index(panel: Panel) -> pd.MultiIndex:
    T, n = panel.speed.shape
    return pd.MultiIndex.from_arrays([np.repeat(panel.index.to_numpy(), n), np.tile(np.array(panel.links), T)],
                                     names=["timestamp", "link_id"])


def build_labels(panel: Panel) -> pd.DataFrame:
    """y_h = queued at exactly t+h; y_any = any queue in (t, t+30min]. NaN if unobservable."""
    ffs = panel.meta["ffs_kmh"].reindex(panel.links).to_numpy(float)
    ratio = panel.speed.div(ffs, axis=1)
    out = {}
    stack = []
    for h in HORIZONS_MIN:
        k = h // STEP_MIN
        fut = ratio.shift(-k)
        y = (fut <= QUEUE_RATIO).astype(float).where(fut.notna())
        out[f"y_{h}"] = y.to_numpy().ravel()
        stack.append(y.to_numpy())
    arr = np.stack(stack)                                  # (H, T, n)
    all_nan = np.isnan(arr).all(axis=0)
    any_ = np.where(all_nan, np.nan, np.nanmax(np.where(np.isnan(arr), -1.0, arr), axis=0))
    out["y_any"] = any_.ravel()
    return pd.DataFrame(out, index=long_index(panel))
