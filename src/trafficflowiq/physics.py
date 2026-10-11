"""Simple, explainable physics-consistency checks.

1. Speed cannot exceed free-flow speed (small tolerance).
2. Density = flow per lane / speed cannot exceed jam density (fundamental diagram).
3. Flow per lane cannot exceed lane capacity.
4. Vehicle conservation: flow into a link + ramp flow ~= flow out (within tolerance).
Conservation is only tested where the ramp reading is trustworthy (not missing evidence).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import CAPACITY_PL, CONSERVATION_TOL, JAM_DENSITY


def point_violations(speed, flow_pl, ffs) -> dict[str, np.ndarray]:
    speed, flow_pl, ffs = (np.asarray(x, float) for x in (speed, flow_pl, ffs))
    with np.errstate(invalid="ignore", divide="ignore"):
        dens = flow_pl / np.maximum(speed, 5.0)
        return {
            "speed_above_free_flow": speed > ffs * 1.05,
            "density_above_jam": dens > JAM_DENSITY,
            "flow_above_capacity": flow_pl > CAPACITY_PL,
        }


def any_point_violation(speed, flow_pl, ffs) -> np.ndarray:
    v = point_violations(speed, flow_pl, ffs)
    return v["speed_above_free_flow"] | v["density_above_jam"] | v["flow_above_capacity"]


def postcorrect(speed, flow_pl, ffs):
    """Light physics post-correction: clip into the feasible region."""
    ffs = np.asarray(ffs, float)
    sp = np.clip(np.asarray(speed, float), 3.0, ffs)
    fl = np.clip(np.asarray(flow_pl, float), 0.0, CAPACITY_PL)
    fl = np.minimum(fl, JAM_DENSITY * sp)                     # q = k*v <= kj*v
    return sp, fl


def conservation_violation_rate(flow: pd.DataFrame, ramp: pd.DataFrame, meta: pd.DataFrame, mask: pd.DataFrame | None = None) -> float:
    """Share of (link, time) pairs where inflow + ramp differs from outflow by > tolerance."""
    bad, tot = 0, 0
    for j, row in meta.iterrows():
        up = row["upstream_id"]
        if up < 0 or up not in flow.columns or j not in flow.columns:
            continue
        r = ramp[j] if row["ramp_type"] != "none" else pd.Series(0.0, index=flow.index)
        sgn = 1.0 if row["ramp_type"] == "on" else -1.0
        expected = flow[up] + sgn * r.fillna(np.nan)
        actual = flow[j]
        ok = expected.notna() & actual.notna()
        if mask is not None:
            ok &= mask[j] | mask[up]
        rel = (expected[ok] - actual[ok]).abs() / np.maximum(actual[ok], 100.0)
        bad += int((rel > CONSERVATION_TOL).sum())
        tot += int(ok.sum())
    return bad / tot if tot else float("nan")
