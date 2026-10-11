"""Data loading. Two sources:

* synthetic stand-in (default; reproducible, no download needed)
* the real TrafficFlowBench files from Kaggle (fill in the column mapping below)
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import PROCESSED_DIR, RAW_DIR
from .panel import LONG_COLUMNS, Panel, panel_from_long
from .synthetic import generate

# >>> EDIT AFTER READING THE KAGGLE DATA TAB <<<
# Map the competition's column names to the canonical names this project uses.
KAGGLE_COLUMN_MAP = {
    # "their_timestamp_col": "timestamp",
    # "their_link_col": "link_id",
    # "their_speed_col": "speed_kmh",
    # "their_flow_col": "flow_vph",
    # "their_occupancy_col": "occupancy_pct",
    # "their_ramp_flow_col": "ramp_flow_vph",
    # "their_ramp_quality_col": "ramp_quality",   # 0 = good, anything else = low quality / unavailable
}
KAGGLE_LINK_MAP = {
    # "their_link_col": "link_id", "their_lanes": "lanes", "their_length": "length_km",
    # "their_ffs": "ffs_kmh", "their_upstream": "upstream_id", "their_downstream": "downstream_id",
    # plus a "ramp_type" column: "on", "off" or "none", and a "name" column
}


def load_real(speed_file: str | Path, links_file: str | Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not KAGGLE_COLUMN_MAP or not KAGGLE_LINK_MAP:
        raise NotImplementedError("Fill KAGGLE_COLUMN_MAP / KAGGLE_LINK_MAP in src/trafficflowiq/data.py first (see docs/data.md).")
    long = pd.read_csv(speed_file).rename(columns=KAGGLE_COLUMN_MAP)[LONG_COLUMNS]
    meta = pd.read_csv(links_file).rename(columns=KAGGLE_LINK_MAP)
    return long, meta


def load_dataset(source: str = "synthetic", **kw) -> tuple[pd.DataFrame, pd.DataFrame]:
    if source == "synthetic":
        return generate(**kw)
    if source == "kaggle":
        return load_real(RAW_DIR / "speed_flow.csv", RAW_DIR / "links.csv")
    raise ValueError(source)


def load_panel(source: str = "synthetic", **kw) -> Panel:
    long, meta = load_dataset(source, **kw)
    return panel_from_long(long, meta)
