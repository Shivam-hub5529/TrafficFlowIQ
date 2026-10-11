from __future__ import annotations

import numpy as np
import pandas as pd

from trafficflowiq import config as C
from trafficflowiq import physics
from trafficflowiq.metrics import rmse
from trafficflowiq.recon import build_recon_features, mask_panel

from app.services.predictor import NotFound, Unprocessable
from app.services.store import Store

PAD = 6  # steps of context kept on each side of the window


def _nn(v):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), 2)


def reconstruct(store: Store, link_id: int, start: pd.Timestamp, end: pd.Timestamp, rate: float, seed: int, max_hours: int) -> dict:
    if link_id not in store.links:
        raise NotFound(f"Unknown link_id {link_id}")
    if end <= start:
        raise Unprocessable("`end` must be after `start`.")
    if (end - start) > pd.Timedelta(hours=max_hours):
        raise Unprocessable(f"Window too long: maximum is {max_hours} hours.")
    p = store.panel
    lo, hi = p.index.min() + pd.Timedelta(minutes=C.STEP_MIN * PAD), p.index.max() - pd.Timedelta(minutes=C.STEP_MIN * PAD)
    if start < lo or end > hi:
        raise Unprocessable(f"Window must lie within {lo:%Y-%m-%d %H:%M} and {hi:%Y-%m-%d %H:%M}.")
    pad = pd.Timedelta(minutes=C.STEP_MIN * PAD)
    sub = p.slice(start - pad, end + pad)
    masked, ms, mf = mask_panel(sub, rate, seed, links=[link_id])
    win = (sub.index >= start) & (sub.index <= end)
    col = list(sub.links).index(link_id)

    out = {}
    for target, model_key in (("speed", "speed_model"), ("flow_pl", "flow_model")):
        X = build_recon_features(masked, target)
        pred = store.r_objs[model_key].predict(X[store.r_meta["features"][target]]).reshape(len(sub.index), len(sub.links))[:, col]
        out[target] = (pred, X["x_interp"].to_numpy().reshape(len(sub.index), len(sub.links))[:, col])
    ffs = store.links[link_id]["ffs_kmh"]
    sp_raw, fl_raw = out["speed"][0], out["flow_pl"][0]
    sp_cor, fl_cor = physics.postcorrect(sp_raw, fl_raw, ffs)

    true_s, true_f = sub.speed[link_id].to_numpy(), sub.flow_pl[link_id].to_numpy()
    obs_s, obs_f = masked.speed[link_id].to_numpy(), masked.flow_pl[link_id].to_numpy()
    m_s, m_f = ms[:, col], mf[:, col]
    est_s = np.where(m_s, sp_cor, obs_s)
    est_f = np.where(m_f, fl_cor, obs_f)
    int_s, int_f = out["speed"][1], out["flow_pl"][1]

    pts = []
    for i in np.where(win)[0]:
        pts.append({"t": sub.index[i].strftime("%Y-%m-%d %H:%M"), "was_missing_speed": bool(m_s[i]), "was_missing_flow": bool(m_f[i]),
                    "speed_obs": _nn(obs_s[i]), "speed_est": _nn(est_s[i]), "speed_true": _nn(true_s[i]),
                    "flow_obs": _nn(obs_f[i]), "flow_est": _nn(est_f[i]), "flow_true": _nn(true_f[i]),
                    "speed_interp": _nn(int_s[i]), "flow_interp": _nn(int_f[i])})
    w_s, w_f = m_s & win, m_f & win
    rm = {"speed": _nn(rmse(true_s[w_s], est_s[w_s])) if w_s.any() else None,
          "flow_per_lane": _nn(rmse(true_f[w_f], est_f[w_f])) if w_f.any() else None}
    base = {"speed": _nn(rmse(true_s[w_s], np.where(np.isnan(int_s[w_s]), ffs * 0.8, int_s[w_s]))) if w_s.any() else None,
            "flow_per_lane": _nn(rmse(true_f[w_f], np.where(np.isnan(int_f[w_f]), 1000, int_f[w_f]))) if w_f.any() else None}

    # physics check on the reconstructed series inside the window
    viol_raw = physics.any_point_violation(np.where(win, np.where(m_s, sp_raw, obs_s), np.nan), np.where(win, np.where(m_f, fl_raw, obs_f), np.nan), ffs)
    viol_cor = physics.any_point_violation(np.where(win, est_s, np.nan), np.where(win, est_f, np.nan), ffs)
    n_chk = int((win & ~np.isnan(est_s) & ~np.isnan(est_f)).sum())
    phys = {"checked_points": n_chk,
            "violations_pct_raw": round(100 * float(np.nansum(viol_raw)) / max(n_chk, 1), 2),
            "violations_pct_after_correction": round(100 * float(np.nansum(viol_cor)) / max(n_chk, 1), 2),
            "checks": ["Speed never exceeds free-flow speed", "Density (flow ÷ speed) never exceeds jam density",
                       "Flow per lane never exceeds lane capacity"],
            "explanation": "Reconstructed values must make physical sense: cars cannot travel faster than free-flow, and a lane cannot carry more "
                           "vehicles than its capacity or than the road can hold at that speed. A light correction clips any value outside those limits."}
    return {"link_id": link_id, "points": pts, "n_masked_speed": int(w_s.sum()), "n_masked_flow": int(w_f.sum()),
            "rmse": rm, "rmse_baseline_linear": base, "physics": phys, "model_version": store.r_meta["model_version"]}
