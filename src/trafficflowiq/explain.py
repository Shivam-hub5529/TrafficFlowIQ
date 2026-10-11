"""Turn per-feature SHAP-style contributions into plain-language reasons.

LightGBM's `pred_contrib=True` returns exact tree-SHAP values, so no extra dependency is needed.
Features are grouped into human concepts; raw feature names only appear in the "advanced" list.
"""
from __future__ import annotations

import math

CONCEPTS = [  # (concept, tuple of feature-name prefixes)
    ("speed_drop", ("speed_chg_", "speed_pct_chg_", "max_drop5_12", "speed_lag_", "speed_std_12")),
    ("speed_level", ("speed_t", "ratio_t", "speed_mean_12", "speed_min_12", "speed_max_12", "ratio_min_12", "ffs_kmh")),
    ("upstream", ("up_", "gap_up_minus_cur")),
    ("downstream", ("down_", "gap_cur_minus_down")),
    ("occupancy", ("occ_",)),
    ("volume", ("flow_pl_", "density_t")),
    ("recent_queue", ("queued_t", "n_queued_12")),
    ("ramp", ("ramp_", "has_ramp")),
    ("time", ("tod_", "minute_of_day", "is_weekend")),
    ("geometry", ("lanes", "length_km")),
    ("data_gaps", ("n_missing_speed_12",)),
]


def concept_of(feature: str) -> str:
    for name, prefixes in CONCEPTS:
        if any(feature == p or feature.startswith(p) for p in prefixes):
            return name
    return "other"


def _num(row, key, default=float("nan")):
    v = row.get(key, default)
    return default if v is None else float(v)


def _text(concept: str, up: bool, row: dict) -> str:
    speed, ratio = _num(row, "speed_t"), _num(row, "ratio_t")
    if concept == "speed_drop":
        pct = -_num(row, "speed_pct_chg_6") * 100
        if up:
            return f"Speed has dropped {pct:.0f}% in the last 30 minutes" if pct > 1 else "Speeds have been unstable over the last hour"
        return "Speed has been steady or recovering over the last hour"
    if concept == "speed_level":
        return (f"Speed is already low: {speed:.0f} km/h, {ratio:.0%} of free-flow" if up
                else f"Speed is close to free-flow ({speed:.0f} km/h)")
    if concept == "upstream":
        r = _num(row, "up_ratio_t")
        return ("Traffic upstream is already slowing down" if up
                else "Traffic upstream is moving freely" if not math.isnan(r) else "Little queue pressure from upstream")
    if concept == "downstream":
        return ("Traffic downstream is slow and can back up onto this link" if up else "Traffic downstream is flowing")
    if concept == "occupancy":
        return (f"Road occupancy is high ({_num(row, 'occ_t'):.0f}%): many vehicles per stretch of road" if up
                else "Road occupancy is low: few vehicles per stretch of road")
    if concept == "volume":
        return "Traffic volume per lane is high" if up else "Traffic volume per lane is light"
    if concept == "recent_queue":
        return "This link was already queued during the last hour" if up else "No queuing on this link in the last hour"
    if concept == "ramp":
        return ("Ramp data is unavailable, so the model had less information to work with" if _num(row, "ramp_bad_t") >= 1
                else "Ramp flow adds traffic to this link" if up else "Ramp flow is not adding much traffic")
    if concept == "time":
        hh, mm = divmod(int(_num(row, "minute_of_day", 0)), 60)
        return (f"{hh:02d}:{mm:02d} is a time of day when queues are common" if up else f"{hh:02d}:{mm:02d} is usually a quiet time of day")
    if concept == "geometry":
        return "The road layout (lanes and length) makes queues more likely here" if up else "The road layout makes queues less likely here"
    if concept == "data_gaps":
        return "Several recent sensor readings are missing" if up else "Sensor data is complete"
    return "Other conditions raise the risk" if up else "Other conditions lower the risk"


def explain(contribs: dict[str, float], row: dict, top_k: int = 3, min_abs: float = 0.02) -> dict:
    """contribs: feature -> contribution (log-odds). Returns plain reasons + advanced raw list."""
    grouped: dict[str, float] = {}
    for feat, c in contribs.items():
        grouped[concept_of(feat)] = grouped.get(concept_of(feat), 0.0) + float(c)
    ranked = sorted(grouped.items(), key=lambda kv: abs(kv[1]), reverse=True)
    reasons = []
    for concept, c in ranked:
        if abs(c) < min_abs and len(reasons) >= 1:
            continue
        reasons.append({"concept": concept, "direction": "up" if c > 0 else "down",
                        "strength": round(abs(c), 3), "text": _text(concept, c > 0, row)})
        if len(reasons) >= top_k:
            break
    adv = sorted(contribs.items(), key=lambda kv: abs(kv[1]), reverse=True)[:8]
    advanced = [{"feature": k, "value": (None if row.get(k) is None or (isinstance(row.get(k), float) and math.isnan(row.get(k))) else round(float(row.get(k)), 3)),
                 "contribution": round(float(v), 3)} for k, v in adv]
    return {"reasons": reasons, "advanced": advanced}


def risk_label(p: float, low: float = 0.30, high: float = 0.60) -> str:
    return "low" if p < low else "moderate" if p < high else "high"
