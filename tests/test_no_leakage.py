"""The most important test in the project: features at time t must not change when the FUTURE changes."""
import numpy as np

from trafficflowiq.features import build_queue_features
from trafficflowiq.panel import panel_from_long
from trafficflowiq.splits import split_boundaries, split_masks
from trafficflowiq.synthetic import generate


def test_features_ignore_future():
    long, meta = generate(n_days=6, seed=1)
    p = panel_from_long(long, meta)
    base = build_queue_features(p)
    cut = p.index[len(p.index) // 2]
    q = p.copy()
    for df in (q.speed, q.flow, q.flow_pl, q.occ, q.ramp):
        df.loc[df.index > cut] = 12345.0          # wreck everything after the cut
    q.ramp_bad.loc[q.ramp_bad.index > cut] = True
    new = build_queue_features(q)
    ts = base.index.get_level_values("timestamp")
    a, b = base[ts <= cut], new[ts <= cut]
    np.testing.assert_allclose(a.to_numpy(float), b.to_numpy(float), equal_nan=True)


def test_bad_ramp_is_missing_not_zero():
    long, meta = generate(n_days=3, seed=2)
    p = panel_from_long(long, meta)
    assert not (p.ramp[p.ramp_bad] == 0).any().any()
    assert p.ramp[p.ramp_bad].isna().all().all()


def test_splits_are_chronological_with_purge():
    long, meta = generate(n_days=20, seed=3)
    p = panel_from_long(long, meta)
    vs, ts_ = split_boundaries(p.index)
    m = split_masks(p.index, vs, ts_)
    assert p.index[m["train"]].max() < vs and p.index[m["val"]].min() >= vs and p.index[m["test"]].min() >= ts_
    assert (vs - p.index[m["train"]].max()).total_seconds() >= 90 * 60
    assert not (m["train"] & m["val"]).any() and not (m["val"] & m["test"]).any()
