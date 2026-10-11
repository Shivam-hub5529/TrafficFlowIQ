"""Chronological split by whole days with a purge gap (no future-data leakage)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import PURGE_MIN, TRAIN_FRAC, VAL_FRAC


def split_boundaries(index: pd.DatetimeIndex, train_frac=TRAIN_FRAC, val_frac=VAL_FRAC):
    days = np.array(sorted(index.normalize().unique()))
    n = len(days)
    n_train, n_val = int(round(n * train_frac)), int(round(n * val_frac))
    return pd.Timestamp(days[n_train]), pd.Timestamp(days[n_train + n_val])  # val_start, test_start


def split_masks(ts: pd.Series | pd.DatetimeIndex, val_start, test_start, purge_min=PURGE_MIN) -> dict[str, np.ndarray]:
    """Rows whose label window (t..t+30) could touch the next period are purged."""
    ts = pd.DatetimeIndex(ts)
    gap = pd.Timedelta(minutes=purge_min)
    return {
        "train": np.asarray(ts < val_start - gap),
        "val": np.asarray((ts >= val_start) & (ts < test_start - gap)),
        "test": np.asarray(ts >= test_start),
    }
