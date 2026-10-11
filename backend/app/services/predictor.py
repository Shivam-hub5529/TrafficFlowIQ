from __future__ import annotations

import numpy as np
import pandas as pd

from trafficflowiq import config as C
from trafficflowiq.explain import explain, risk_label

from app.services.store import Store


class NotFound(Exception):
    pass


class Unprocessable(Exception):
    pass


def _speed_series(store: Store, link_id: int, start: pd.Timestamp, end: pd.Timestamp):
    s = store.panel.speed[link_id].loc[start:end]
    return [{"t": t.strftime("%Y-%m-%d %H:%M"), "speed": None if np.isnan(v) else round(float(v), 1)} for t, v in s.items()]


def _check(store: Store, link_id: int, ts: pd.Timestamp) -> pd.Series:
    if link_id not in store.links:
        raise NotFound(f"Unknown link_id {link_id}")
    if ts.minute % C.STEP_MIN != 0 or ts.second != 0:
        raise Unprocessable("Timestamp must be on a 5-minute boundary (for example 17:05).")
    try:
        return store.feat.loc[(link_id, ts)]
    except KeyError:
        l = store.links[link_id]
        raise Unprocessable(
            f"No complete 60-minute history for link {link_id} at {ts:%Y-%m-%d %H:%M}. "
            f"Choose a time between {l['first_time'][:16].replace('T', ' ')} and {l['last_time'][:16].replace('T', ' ')} "
            "(the speed reading at that moment must also be available).")


def predict_queue(store: Store, link_id: int, ts: pd.Timestamp) -> dict:
    row = _check(store, link_id, ts)
    X = row[store.features].to_frame().T.astype(float)
    link = store.links[link_id]

    # Main 30-minute risk (calibrated)
    raw = float(store.q_objs["queue_model"].predict_proba(X)[:, 1][0])
    p_any = float(store.q_objs["queue_calibrator"].predict([raw])[0])

    # Exact tree-SHAP contributions (log-odds) straight from LightGBM
    contrib = store.q_objs["queue_model"].predict(X, pred_contrib=True)[0][:-1]
    contribs = dict(zip(store.features, contrib))
    expl = explain(contribs, row.to_dict())

    # Forecast strip
    horizon = {}
    for h, bundle in store.q_objs["horizon_models"].items():
        r = float(bundle["model"].predict_proba(X)[:, 1][0])
        horizon[str(h)] = round(float(bundle["calibrator"].predict([r])[0]), 3)
    # Monotone presentation: risk of "any queue by h" never decreases... but horizon models are "queued at exactly h": keep as-is.

    hist = _speed_series(store, link_id, ts - pd.Timedelta(minutes=55), ts)
    n_missing = sum(1 for p in hist if p["speed"] is None)
    has_ramp = link["ramp_type"] != "none"
    ramp_ok = None if not has_ramp else not bool(row["ramp_bad_t"] >= 1)
    if not has_ramp:
        note = "This link has no ramp sensors."
    elif ramp_ok:
        note = "Ramp sensors are reporting normally."
    else:
        note = "Ramp data is unavailable or low quality right now. It was treated as missing, not as zero flow, so the model had less information."
    label = risk_label(p_any, C.RISK_LOW, C.RISK_HIGH)
    verdict = {"low": "Queue unlikely in the next 30 minutes", "moderate": "A queue is possible in the next 30 minutes",
               "high": "A queue is likely in the next 30 minutes"}[label]
    return {
        "link_id": link_id, "timestamp": ts.isoformat(), "risk": round(p_any, 3), "label": label, "verdict": verdict,
        "threshold_used": round(store.threshold, 3), "horizon_risk": horizon,
        "queue_speed_kmh": link["queue_threshold_kmh"], "free_flow_kmh": link["ffs_kmh"],
        "history": hist, "reasons": expl["reasons"], "advanced": expl["advanced"],
        "data_quality": {"ramp_available": ramp_ok, "missing_speed_readings": n_missing, "note": note},
        "model_version": store.q_meta["model_version"],
    }


def history_preview(store: Store, link_id: int, ts: pd.Timestamp) -> dict:
    _check(store, link_id, ts)
    link = store.links[link_id]
    return {"link_id": link_id, "timestamp": ts.isoformat(), "history": _speed_series(store, link_id, ts - pd.Timedelta(minutes=55), ts),
            "queue_speed_kmh": link["queue_threshold_kmh"], "free_flow_kmh": link["ffs_kmh"]}


def future_check(store: Store, link_id: int, ts: pd.Timestamp) -> dict:
    """The 'what actually happened' reveal (possible only because the demo replays held-out data)."""
    _check(store, link_id, ts)
    fut = _speed_series(store, link_id, ts + pd.Timedelta(minutes=5), ts + pd.Timedelta(minutes=30))
    vals = [p["speed"] for p in fut if p["speed"] is not None]
    thr = store.links[link_id]["queue_threshold_kmh"]
    return {"future": fut, "queued_in_next_30": (min(vals) <= thr) if vals else None, "min_speed_kmh": min(vals) if vals else None}


def scenarios(store: Store, link_id: int, date: str | None) -> dict:
    if link_id not in store.links:
        raise NotFound(f"Unknown link_id {link_id}")
    idx = store.feat.loc[link_id].index
    # the last 30 minutes of the dataset have no "what happened next", so exclude them
    idx = idx[idx <= pd.Timestamp(store.links[link_id]["last_time"])]
    if date is None:
        days = pd.Series(idx.normalize()).drop_duplicates()
        return {"dates": [d.strftime("%Y-%m-%d") for d in days], "featured": store.links[link_id]["featured"]}
    d = pd.Timestamp(date)
    day = idx[(idx >= d) & (idx < d + pd.Timedelta(days=1))]
    return {"times": [t.strftime("%H:%M") for t in day]}
