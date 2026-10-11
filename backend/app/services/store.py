"""Loads everything once at startup: models, explainer inputs, serving tables."""
from __future__ import annotations

import json
import logging

import numpy as np
import pandas as pd

from trafficflowiq.modelio import load_bundle
from trafficflowiq.panel import panel_from_long

from app.core.config import settings

log = logging.getLogger("trafficflowiq")


class Store:
    def __init__(self) -> None:
        qdir = settings.model_dir / "queue" / settings.queue_model_version
        rdir = settings.model_dir / "reconstruction" / settings.recon_model_version
        self.q_objs, self.q_meta = load_bundle(qdir, ["queue_model", "queue_calibrator", "horizon_models"])
        self.r_objs, self.r_meta = load_bundle(rdir, ["speed_model", "flow_model"])
        self.q_metrics = json.loads((qdir / "metrics.json").read_text())
        self.r_metrics = json.loads((rdir / "metrics.json").read_text())
        self.model_card = (qdir / "model_card.md").read_text()
        self.features: list[str] = self.q_meta["features"]
        self.threshold: float = float(self.q_meta["threshold"])

        info = json.loads((settings.serving_dir / "links.json").read_text())
        self.data_source: str = info["data_source"]
        self.links: dict[int, dict] = {l["link_id"]: l for l in info["links"]}

        f = pd.read_parquet(settings.serving_dir / "features_test.parquet")
        f["timestamp"] = pd.to_datetime(f["timestamp"])
        self.feat = f.set_index(["link_id", "timestamp"]).sort_index()

        long = pd.read_parquet(settings.serving_dir / "panel_test.parquet")
        meta = pd.DataFrame(info["links"]).rename(columns={"ffs_kmh": "ffs_kmh"})
        meta = meta[["link_id", "name", "lanes", "length_km", "ffs_kmh", "ramp_type", "upstream_id", "downstream_id"]]
        self.panel = panel_from_long(long, meta)
        log.info("Store ready: %d feature rows, %d links, source=%s", len(self.feat), len(self.links), self.data_source)

        # warm-up so the first real request is fast
        row = self.feat.iloc[[0]][self.features]
        self.q_objs["queue_model"].predict_proba(row)


store: Store | None = None


def get_store() -> Store:
    global store
    if store is None:
        store = Store()
    return store
