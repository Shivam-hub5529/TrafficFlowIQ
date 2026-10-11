"""Panel: wide (time x link) matrices for each measurement.

Quality rule (important): ramp readings with quality != 0 (low quality or
unavailable) become NaN = *missing evidence*, never zero flow.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import STEP_MIN

LONG_COLUMNS = ["timestamp", "link_id", "speed_kmh", "flow_vph", "occupancy_pct", "ramp_flow_vph", "ramp_quality"]


@dataclass
class Panel:
    speed: pd.DataFrame        # km/h
    flow: pd.DataFrame         # veh/h (all lanes)
    flow_pl: pd.DataFrame      # veh/h/lane
    occ: pd.DataFrame          # %
    ramp: pd.DataFrame         # veh/h, NaN when low quality / unavailable / no ramp
    ramp_bad: pd.DataFrame     # bool: link HAS a ramp but the reading is unusable
    meta: pd.DataFrame         # indexed by link_id

    @property
    def index(self) -> pd.DatetimeIndex:
        return self.speed.index

    @property
    def links(self) -> list:
        return list(self.speed.columns)

    def slice(self, start, end) -> "Panel":
        sl = lambda df: df.loc[start:end]
        return Panel(sl(self.speed), sl(self.flow), sl(self.flow_pl), sl(self.occ), sl(self.ramp), sl(self.ramp_bad), self.meta)

    def copy(self) -> "Panel":
        return Panel(*(getattr(self, f).copy() for f in ("speed", "flow", "flow_pl", "occ", "ramp", "ramp_bad")), self.meta)


def _wide(long: pd.DataFrame, col: str, idx: pd.DatetimeIndex, links: list) -> pd.DataFrame:
    return long.pivot_table(index="timestamp", columns="link_id", values=col, aggfunc="last").reindex(index=idx, columns=links)


def panel_from_long(long: pd.DataFrame, meta: pd.DataFrame) -> Panel:
    """Build a Panel from the canonical long table. Verifies the 5-minute grid."""
    missing = set(LONG_COLUMNS) - set(long.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    long = long.copy()
    long["timestamp"] = pd.to_datetime(long["timestamp"])
    meta = meta.set_index("link_id", drop=False) if "link_id" in meta.columns and meta.index.name != "link_id" else meta
    links = list(meta.index)
    idx = pd.date_range(long["timestamp"].min(), long["timestamp"].max(), freq=f"{STEP_MIN}min")  # inserts NaN gaps
    speed = _wide(long, "speed_kmh", idx, links)
    flow = _wide(long, "flow_vph", idx, links)
    occ = _wide(long, "occupancy_pct", idx, links)
    ramp_raw = _wide(long, "ramp_flow_vph", idx, links)
    q = _wide(long, "ramp_quality", idx, links)
    has_ramp = (meta["ramp_type"] != "none").reindex(links).to_numpy()
    ramp_bad = ((q.fillna(2) != 0) | ramp_raw.isna()) & has_ramp[None, :]
    ramp = ramp_raw.where(~ramp_bad & has_ramp[None, :])        # NaN, not 0
    lanes = meta["lanes"].reindex(links).to_numpy(float)
    return Panel(speed, flow, flow.div(lanes, axis=1), occ, ramp, ramp_bad.astype(bool), meta)


def panel_to_long(p: Panel) -> pd.DataFrame:
    """Back to the long table (cleaned ramp: bad readings stored as NaN, quality 2)."""
    T, n = p.speed.shape
    return pd.DataFrame({
        "timestamp": np.repeat(p.index.to_numpy(), n),
        "link_id": np.tile(np.array(p.links), T),
        "speed_kmh": p.speed.to_numpy().ravel(),
        "flow_vph": p.flow.to_numpy().ravel(),
        "occupancy_pct": p.occ.to_numpy().ravel(),
        "ramp_flow_vph": p.ramp.to_numpy().ravel(),
        "ramp_quality": np.where(p.ramp_bad.to_numpy(), 2, 0).ravel(),
    })
