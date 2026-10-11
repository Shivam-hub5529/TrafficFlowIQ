"""Export the compact files the API needs: test-period features, test-period panel, link metadata, featured moments.

Usage:  PYTHONPATH=src python scripts/export_serving.py [--source synthetic|kaggle]
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from trafficflowiq import config as C
from trafficflowiq.data import load_panel
from trafficflowiq.features import build_queue_features, valid_rows
from trafficflowiq.labels import build_labels
from trafficflowiq.panel import panel_to_long
from trafficflowiq.splits import split_boundaries


def main(source: str) -> None:
    panel = load_panel(source)
    _, test_start = split_boundaries(panel.index)
    feats = build_queue_features(panel)          # computed on the FULL panel, so early test rows have real history
    labels = build_labels(panel)
    df = feats.join(labels)
    ts = df.index.get_level_values("timestamp")
    df = df[(ts >= test_start) & valid_rows(df)]
    C.SERVING_DIR.mkdir(parents=True, exist_ok=True)
    feat_cols = [c for c in feats.columns if c != "step_idx"]
    out = df[feat_cols].reset_index()
    out["link_id"] = out["link_id"].astype(int)
    out.to_parquet(C.SERVING_DIR / "features_test.parquet", index=False, compression="zstd")

    pan = panel.slice(test_start - pd.Timedelta(hours=2), panel.index.max() + pd.Timedelta(hours=1))
    panel_to_long(pan).to_parquet(C.SERVING_DIR / "panel_test.parquet", index=False, compression="zstd")

    # featured moments: queue forms soon / calm peak time
    feat_moments = {}
    d = df.reset_index()
    d["hour"] = d["timestamp"].dt.hour
    for lid, g in d.groupby("link_id"):
        picks = []
        onset = g[(g.y_any == 1) & (g.queued_t == 0) & (g.ratio_t > 0.75)]
        if len(onset):
            for i in np.linspace(0, len(onset) - 1, num=min(3, len(onset))).astype(int):
                r = onset.iloc[i]
                picks.append({"timestamp": r.timestamp.isoformat(), "kind": "queue_forms", "title": "A queue forms within 30 minutes"})
        calm = g[(g.y_any == 0) & g.hour.between(16, 18) & (g.is_weekend == 0)]
        if len(calm):
            r = calm.iloc[len(calm) // 2]
            picks.append({"timestamp": r.timestamp.isoformat(), "kind": "stays_clear", "title": "Busy hour, but stays clear"})
        feat_moments[int(lid)] = picks

    meta = panel.meta.reset_index(drop=True).copy()
    links = []
    for _, r in meta.iterrows():
        lid = int(r.link_id)
        g = d[d.link_id == lid]
        links.append({"link_id": lid, "name": r["name"], "lanes": int(r.lanes), "length_km": float(r.length_km), "ffs_kmh": float(r.ffs_kmh),
                      "queue_threshold_kmh": round(C.QUEUE_RATIO * float(r.ffs_kmh), 1), "ramp_type": r.ramp_type,
                      "upstream_id": int(r.upstream_id), "downstream_id": int(r.downstream_id),
                      "first_time": g.timestamp.min().isoformat(), "last_time": (g.timestamp.max() - pd.Timedelta(minutes=30)).isoformat(),
                      "featured": feat_moments.get(lid, [])})
    (C.SERVING_DIR / "links.json").write_text(json.dumps({"data_source": source, "test_start": str(test_start), "links": links}, indent=2))
    print(f"exported features={len(out):,} rows, panel={len(pan.index):,} steps, links={len(links)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="synthetic")
    main(ap.parse_args().source)
