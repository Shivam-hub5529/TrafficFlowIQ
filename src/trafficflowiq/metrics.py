from __future__ import annotations

import numpy as np
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, roc_auc_score


def queue_metrics(y_true, score, threshold: float = 0.5) -> dict:
    y = np.asarray(y_true).astype(int)
    s = np.asarray(score, dtype=float)
    pred = (s >= threshold).astype(int)
    tp, fp, fn = int(((pred == 1) & (y == 1)).sum()), int(((pred == 1) & (y == 0)).sum()), int(((pred == 0) & (y == 1)).sum())
    out = {
        "n": int(len(y)), "prevalence": float(y.mean()), "threshold": float(threshold),
        "iou": tp / max(tp + fp + fn, 1),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
    }
    if 0 < y.sum() < len(y):
        out["roc_auc"] = float(roc_auc_score(y, s))
        out["pr_auc"] = float(average_precision_score(y, s))
    else:
        out["roc_auc"] = out["pr_auc"] = float("nan")
    return out


def best_f1_threshold(y_true, score) -> float:
    y = np.asarray(y_true).astype(int)
    s = np.asarray(score, dtype=float)
    best, best_t = -1.0, 0.5
    for t in np.unique(np.round(np.quantile(s, np.linspace(0.5, 0.995, 120)), 4)):
        f1 = f1_score(y, (s >= t).astype(int), zero_division=0)
        if f1 > best:
            best, best_t = f1, float(t)
    return best_t


def rmse(a, b) -> float:
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = ~(np.isnan(a) | np.isnan(b))
    return float(np.sqrt(np.mean((a[ok] - b[ok]) ** 2))) if ok.any() else float("nan")
