"""Train traffic-state reconstruction models (speed, flow per lane) with simulated sensor dropouts.

Usage:  PYTHONPATH=src python scripts/train_recon.py [--source synthetic|kaggle]
"""
from __future__ import annotations

import argparse
import json
import time

import lightgbm as lgb
import numpy as np
import pandas as pd

from trafficflowiq import config as C
from trafficflowiq import physics
from trafficflowiq.data import load_panel
from trafficflowiq.metrics import rmse
from trafficflowiq.modelio import save_bundle
from trafficflowiq.recon import build_recon_features, gap_lengths, mask_panel
from trafficflowiq.splits import split_boundaries

PARAMS = dict(n_estimators=500, learning_rate=0.05, num_leaves=31, min_child_samples=30, subsample=0.8,
              subsample_freq=1, colsample_bytree=0.8, random_state=42, verbose=-1)
SEEDS = {"train": 11, "val": 22, "test": 33}
RATE = 0.15


def make_set(panel, rows_sel, split: str, target: str):
    """Mask `panel`, build features, return X, y, extras for masked cells inside `rows_sel` (time mask)."""
    masked, ms, mf = mask_panel(panel, RATE, SEEDS[split])
    m = ms if target == "speed" else mf
    X = build_recon_features(masked, target)
    truth = getattr(panel, target).to_numpy().ravel()
    sel = m.ravel() & np.repeat(rows_sel, panel.speed.shape[1])
    gl = gap_lengths(m).ravel()
    Xs = X[sel]
    return Xs, truth[sel], gl[sel], panel.meta.reindex(panel.links)["ffs_kmh"].to_numpy()[np.tile(np.arange(len(panel.links)), len(panel.index))][sel]


def main(source: str) -> None:
    t0 = time.time()
    panel = load_panel(source)
    val_start, test_start = split_boundaries(panel.index)
    idx = panel.index
    sets = {"train": np.asarray(idx < val_start), "val": np.asarray((idx >= val_start) & (idx < test_start)), "test": np.asarray(idx >= test_start)}
    results, models = {}, {}
    for target in ("speed", "flow_pl"):
        data = {s: make_set(panel, sets[s], s, target) for s in sets}
        Xtr, ytr, _, _ = data["train"]
        Xva, yva, _, _ = data["val"]
        Xte, yte, gte, ffs_te = data["test"]
        ok = ~np.isnan(ytr); okv = ~np.isnan(yva)
        m = lgb.LGBMRegressor(**PARAMS)
        m.fit(Xtr[ok], ytr[ok], eval_set=[(Xva[okv], yva[okv])], callbacks=[lgb.early_stopping(40, verbose=False)])
        pred = m.predict(Xte)
        unit = "km/h" if target == "speed" else "veh/h/lane"
        base_interp = Xte["x_interp"].fillna(Xte["x_locf"]).fillna(pd.Series(ytr).mean())
        base_locf = Xte["x_locf"].fillna(base_interp)
        base_nbr = pd.concat([Xte["up_x"], Xte["down_x"]], axis=1).mean(axis=1).fillna(base_interp)
        res = {"unit": unit, "n_test_points": int(len(yte)),
               "rmse_lightgbm": rmse(yte, pred), "rmse_linear_interpolation": rmse(yte, base_interp),
               "rmse_last_observation": rmse(yte, base_locf), "rmse_neighbor_link_average": rmse(yte, base_nbr),
               "by_gap": {}}
        for name, sel in (("single_point", gte == 1), ("short_gap_2_4", (gte >= 2) & (gte <= 4)), ("long_gap_5_plus", gte >= 5)):
            if sel.sum() > 10:
                res["by_gap"][name] = {"n": int(sel.sum()), "lightgbm": rmse(yte[sel], pred[sel]), "linear_interpolation": rmse(yte[sel], base_interp[sel])}
        res["best_iteration"] = int(m.best_iteration_ or m.n_estimators)
        results[target] = res
        models[target] = m
        results[f"_pred_{target}"] = (pred, yte, ffs_te)

    # ---- physics consistency (on reconstructed test points, before/after light post-correction) ----
    ps, ys, ffs_s = results.pop("_pred_speed")
    pf, yf, _ = results.pop("_pred_flow_pl")
    n = min(len(ps), len(pf))
    # pair speed and flow predictions only where both exist for evaluation of violations (independent masks -> use truth for the other)
    # speed predictions with TRUE flow, and flow predictions with TRUE speed
    results["physics"] = {
        "speed_pred_above_free_flow_rate": float(np.mean(ps > ffs_s * 1.05)),
        "flow_pred_above_capacity_rate": float(np.mean(pf > C.CAPACITY_PL)),
        "note": "Post-correction clips speed to [3, free-flow] and flow to [0, min(capacity, jam density x speed)].",
    }
    sp_c, _ = physics.postcorrect(ps, np.zeros_like(ps), ffs_s)
    results["physics"]["rmse_speed_after_postcorrect"] = rmse(ys, sp_c)

    out = C.MODELS_DIR / "reconstruction" / "v1.0.0"
    feat_lists = {t: list(models[t].feature_name_) for t in models}
    meta = {"model_version": C.RECON_MODEL_VERSION, "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"), "data_source": source,
            "train_mask_rate": RATE, "features": feat_lists}
    save_bundle(out, {"speed_model": models["speed"], "flow_model": models["flow_pl"]}, meta,
                {"metrics.json": json.dumps(results, indent=2, default=float)})
    print(json.dumps(results, indent=1, default=float))
    print(f"saved to {out} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="synthetic")
    main(ap.parse_args().source)
