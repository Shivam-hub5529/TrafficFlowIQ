"""Train the queue-risk models (baselines, LightGBM, calibration, per-horizon models).

Usage:  PYTHONPATH=src python scripts/train_queue.py [--source synthetic|kaggle]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

from trafficflowiq import config as C
from trafficflowiq.data import load_panel
from trafficflowiq.features import build_queue_features, valid_rows
from trafficflowiq.labels import build_labels
from trafficflowiq.metrics import best_f1_threshold, queue_metrics
from trafficflowiq.modelio import save_bundle
from trafficflowiq.splits import split_boundaries, split_masks

LGB_PARAMS = dict(n_estimators=600, learning_rate=0.05, num_leaves=31, min_child_samples=40,
                  subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, random_state=42, verbose=-1)
LOGREG_FEATURES = ["ratio_t", "speed_pct_chg_6", "up_ratio_t", "occ_t", "tod_sin", "tod_cos", "is_weekend", "n_queued_12"]


def git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=C.ROOT, stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "no-git"


def main(source: str) -> None:
    t0 = time.time()
    panel = load_panel(source)
    feats = build_queue_features(panel)
    labels = build_labels(panel)
    df = feats.join(labels)
    df = df[valid_rows(df) & df["y_any"].notna()].copy()
    ts = df.index.get_level_values("timestamp")
    val_start, test_start = split_boundaries(panel.index)
    masks = split_masks(ts, val_start, test_start)
    tr, va, te = (df[masks[k]] for k in ("train", "val", "test"))
    print(f"rows  train={len(tr):,}  val={len(va):,}  test={len(te):,}   val_start={val_start}  test_start={test_start}")
    print(f"queue prevalence (y_any)  train={tr.y_any.mean():.3f} val={va.y_any.mean():.3f} test={te.y_any.mean():.3f}")

    feat_cols = [c for c in feats.columns if c != "step_idx"]
    results: dict = {"baselines": {}, "split": {"val_start": str(val_start), "test_start": str(test_start), "purge_min": C.PURGE_MIN,
                                                 "rows": {"train": len(tr), "val": len(va), "test": len(te)}}}

    # ---------------- baselines (all fit on train only) -----------------------------
    # (a) persistence
    pers = lambda d: d["queued_t"].fillna(0).to_numpy()
    # (b) historical average by link and 30-minute time bucket
    key = lambda d: list(zip(d.index.get_level_values("link_id"), (d["minute_of_day"] // 30).astype(int)))
    hist = tr.groupby([tr.index.get_level_values("link_id"), (tr["minute_of_day"] // 30).astype(int)])["y_any"].mean().to_dict()
    hist_score = lambda d: np.array([hist.get(k, tr.y_any.mean()) for k in key(d)])
    # (c) logistic regression on a few interpretable features
    lr = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(max_iter=500, C=1.0))
    lr.fit(tr[LOGREG_FEATURES], tr["y_any"].astype(int))
    base_scores = {"persistence": pers, "historical_average": hist_score, "logistic_regression": lambda d: lr.predict_proba(d[LOGREG_FEATURES])[:, 1]}
    for name, fn in base_scores.items():
        thr = 0.5 if name == "persistence" else best_f1_threshold(va["y_any"], fn(va))
        results["baselines"][name] = {"val": queue_metrics(va["y_any"], fn(va), thr), "test": queue_metrics(te["y_any"], fn(te), thr)}

    # ---------------- main model: LightGBM + isotonic calibration -------------------
    model = lgb.LGBMClassifier(**LGB_PARAMS)
    model.fit(tr[feat_cols], tr["y_any"].astype(int), eval_set=[(va[feat_cols], va["y_any"].astype(int))],
              eval_metric="average_precision", callbacks=[lgb.early_stopping(40, verbose=False)])
    raw_va = model.predict_proba(va[feat_cols])[:, 1]
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(raw_va, va["y_any"])
    cal = lambda d: iso.predict(model.predict_proba(d[feat_cols])[:, 1])
    thr = best_f1_threshold(va["y_any"], cal(va))
    results["lightgbm"] = {"best_iteration": int(model.best_iteration_ or model.n_estimators), "threshold": thr,
                           "val": queue_metrics(va["y_any"], cal(va), thr), "test": queue_metrics(te["y_any"], cal(te), thr),
                           "test_uncalibrated": queue_metrics(te["y_any"], model.predict_proba(te[feat_cols])[:, 1], 0.5)}
    # per-link breakdown on test
    pt = cal(te)
    per_link = {}
    for lid, g in te.assign(p=pt).groupby(level="link_id"):
        if g.y_any.sum() >= 5:
            per_link[int(lid)] = queue_metrics(g.y_any, g.p, thr)
    results["lightgbm"]["test_per_link"] = per_link

    # ---------------- per-horizon models (forecast strip) --------------------------
    horizon_models = {}
    for h in C.HORIZONS_MIN:
        col = f"y_{h}"
        trh, vah = tr[tr[col].notna()], va[va[col].notna()]
        m = lgb.LGBMClassifier(**{**LGB_PARAMS, "n_estimators": 300})
        m.fit(trh[feat_cols], trh[col].astype(int), eval_set=[(vah[feat_cols], vah[col].astype(int))],
              eval_metric="average_precision", callbacks=[lgb.early_stopping(30, verbose=False)])
        rv = m.predict_proba(vah[feat_cols])[:, 1]
        iso_h = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(rv, vah[col])
        teh = te[te[col].notna()]
        ph = iso_h.predict(m.predict_proba(teh[feat_cols])[:, 1])
        horizon_models[h] = {"model": m, "calibrator": iso_h}
        results.setdefault("horizons", {})[str(h)] = queue_metrics(teh[col], ph, 0.5)

    # ---------------- save ---------------------------------------------------------
    out_dir = C.MODELS_DIR / "queue" / "v1.0.0"
    meta = {"model_version": C.QUEUE_MODEL_VERSION, "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"), "git_commit": git_hash(),
            "data_source": source, "features": feat_cols, "threshold": thr, "hist_steps": C.HIST_STEPS, "horizon_min": C.HORIZONS_MIN,
            "queue_ratio": C.QUEUE_RATIO, "lightgbm_params": LGB_PARAMS}
    card = f"""# Model card: {C.QUEUE_MODEL_VERSION}

**Task:** probability that a freeway link has at least one queued 5-minute interval (speed <= 60% of free-flow) in the next 30 minutes,
from the previous 60 minutes of data only.

**Data source:** `{source}` {"(SYNTHETIC stand-in, replace with TrafficFlowBench for real results)" if source == "synthetic" else ""}
**Split:** chronological by whole day, 90-minute purge gap. Val starts {val_start.date()}, test starts {test_start.date()}.
**Model:** LightGBM + isotonic calibration (fit on validation). Decision threshold {thr:.3f} (max F1 on validation).

| Metric (test) | Value |
|---|---|
""" + "\n".join(f"| {k} | {v:.3f} |" for k, v in results["lightgbm"]["test"].items() if isinstance(v, float)) + """

**Known limits:** calibrator and threshold share the validation set (slightly optimistic); queues driven by events not
visible in the 60-minute window (e.g. a crash 10 minutes from now) cannot be predicted.
"""
    save_bundle(out_dir, {"queue_model": model, "queue_calibrator": iso, "horizon_models": horizon_models}, meta,
                {"feature_list.json": json.dumps(feat_cols, indent=2), "threshold.json": json.dumps({"threshold": thr}),
                 "metrics.json": json.dumps(results, indent=2, default=float), "model_card.md": card})
    print(json.dumps({k: results[k] for k in ("baselines", "lightgbm")}, indent=1, default=float)[:4000])
    print(f"saved to {out_dir}   ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="synthetic")
    main(ap.parse_args().source)
