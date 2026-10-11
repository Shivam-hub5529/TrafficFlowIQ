"""Synthetic stand-in for TrafficFlowBench.

WHY THIS EXISTS: the Kaggle data cannot be redistributed or downloaded
automatically. This generator produces data with the same *kind* of structure
(5-minute speed / flow / occupancy, ramp flows with quality flags, link geometry,
upstream/downstream topology) so that the whole pipeline, API and web app run
end to end. Replace it with the real data via `data.load_real()` for final results.

The traffic is physically motivated: a lane-drop bottleneck, rush-hour demand,
random incidents, queues that spread upstream, and flows that obey conservation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import QUEUE_RATIO, STEP_MIN


def make_links() -> pd.DataFrame:
    rows = [
        # id, name,                                lanes, km, ffs, ramp
        (0, "Mainline A: Oak St to 5th Ave",        3, 2.0, 105, "none"),
        (1, "Mainline B: 5th Ave to Harbor Rd",     3, 1.6, 105, "on"),
        (2, "Mainline C: Harbor Rd to Mill Creek",  3, 2.4, 105, "off"),
        (3, "Mainline D: Mill Creek to Route 9",    3, 1.2, 100, "on"),
        (4, "Mainline E: Route 9 to Lakeview",      2, 1.8, 100, "none"),
        (5, "Mainline F: Lakeview to Airport Rd",   2, 2.2, 100, "off"),
        (6, "Mainline G: Airport Rd to County Line", 3, 3.0, 110, "none"),
    ]
    meta = pd.DataFrame(rows, columns=["link_id", "name", "lanes", "length_km", "ffs_kmh", "ramp_type"])
    n = len(meta)
    meta["upstream_id"] = [i - 1 if i > 0 else -1 for i in range(n)]
    meta["downstream_id"] = [i + 1 if i < n - 1 else -1 for i in range(n)]
    return meta


def _demand(minute_of_day: np.ndarray, weekend: bool) -> np.ndarray:
    m = minute_of_day.astype(float)
    g = lambda mu, sd, a: a * np.exp(-0.5 * ((m - mu) / sd) ** 2)
    if weekend:
        return 0.22 + g(13 * 60, 160, 0.30)
    return 0.22 + g(7 * 60 + 45, 55, 0.62) + g(17 * 60 + 10, 75, 0.80) + g(12 * 60 + 30, 90, 0.10)


def _smooth_asym(x: np.ndarray, up: float, down: float) -> np.ndarray:
    """Fast rise, slow recovery: congestion forms quickly and clears slowly."""
    y = np.zeros_like(x)
    for i in range(1, len(x)):
        a = up if x[i] > y[i - 1] else down
        y[i] = y[i - 1] + a * (x[i] - y[i - 1])
    return y


def generate(n_days: int = 42, start: str = "2025-01-06", seed: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    meta = make_links()
    n_links = len(meta)
    steps_day = 24 * 60 // STEP_MIN
    T = n_days * steps_day
    ts = pd.date_range(start, periods=T, freq=f"{STEP_MIN}min")
    mod = (ts.hour * 60 + ts.minute).to_numpy()
    dow = ts.dayofweek.to_numpy()

    lanes = meta["lanes"].to_numpy(float)
    ffs = meta["ffs_kmh"].to_numpy(float)
    BOTTLE = 4
    CAP_PL = 2200.0

    # ---- demand ------------------------------------------------------------
    d = np.zeros(T)
    for day in range(n_days):
        sl = slice(day * steps_day, (day + 1) * steps_day)
        weekend = dow[sl][0] >= 5
        scale = rng.normal(1.0, 0.07)
        d[sl] = _demand(mod[sl], weekend) * scale
    noise = np.zeros(T)
    for t in range(1, T):
        noise[t] = 0.9 * noise[t - 1] + rng.normal(0, 0.012)
    d = np.clip(d + noise, 0.05, None)

    # ---- ramp flows (true) -------------------------------------------------
    q0 = 3 * 1250.0 * d                       # mainline entering flow (veh/h)
    ramp_true = np.zeros((T, n_links))
    for j, rt in enumerate(meta["ramp_type"]):
        if rt == "on":
            ramp_true[:, j] = q0 * (0.12 if j == 1 else 0.15) * (1 + rng.normal(0, 0.05, T))
        elif rt == "off":
            ramp_true[:, j] = q0 * (0.10 if j == 2 else 0.12) * (1 + rng.normal(0, 0.05, T))
    sign = np.where(meta["ramp_type"].eq("on"), 1.0, np.where(meta["ramp_type"].eq("off"), -1.0, 0.0))

    # ---- demand chain (uncapped) to measure load on the bottleneck ----------
    D = np.zeros((T, n_links))
    D[:, 0] = q0
    for j in range(1, n_links):
        D[:, j] = D[:, j - 1] + sign[j] * ramp_true[:, j]
    load = D[:, BOTTLE] / (lanes[BOTTLE] * CAP_PL)
    src = {BOTTLE: _smooth_asym(np.clip((load - 0.86) / 0.12, 0, 1), 0.45, 0.10)}

    # ---- incidents: extra queue sources on random links ---------------------
    for day in range(n_days):
        for _ in range(rng.poisson(1.2)):
            k = int(rng.integers(1, n_links - 1))
            t0 = day * steps_day + int(rng.integers(5 * 12, 22 * 12))
            dur = int(rng.integers(5, 14))
            s = src.setdefault(k, np.zeros(T))
            s[t0:t0 + dur] = np.maximum(s[t0:t0 + dur], rng.uniform(0.6, 1.0))
    src = {k: _smooth_asym(v, 0.5, 0.12) for k, v in src.items()}

    # ---- congestion intensity per link (spreads upstream with delay) -------
    c = np.zeros((T, n_links))
    for k, s in src.items():
        for i in range(n_links):
            if i <= k:
                lag = k - i
                shifted = np.concatenate([np.zeros(lag), s[: T - lag]]) if lag else s
                c[:, i] = np.maximum(c[:, i], shifted * (0.93 ** lag))
            else:
                c[:, i] = np.maximum(c[:, i], 0.08 * s)
    c = np.clip(c, 0, 1)

    # ---- speed -------------------------------------------------------------
    speed = np.zeros((T, n_links))
    for j in range(n_links):
        ar = np.zeros(T)
        for t in range(1, T):
            ar[t] = 0.7 * ar[t - 1] + rng.normal(0, 0.012)
        mild = 0.10 * np.clip((d - 0.55) / 0.5, 0, 1) ** 2      # pre-breakdown slowing
        ratio = 0.98 - mild - 0.70 * c[:, j] + ar
        speed[:, j] = np.clip(ratio, 0.12, 1.02) * ffs[j]

    # ---- flow (conservation chain + capacity with queue discharge drop) ----
    Q = np.zeros((T, n_links))
    Q[:, 0] = q0
    for j in range(1, n_links):
        Q[:, j] = Q[:, j - 1] + sign[j] * ramp_true[:, j]
    for j in range(n_links):
        Q[:, j] = np.minimum(Q[:, j], lanes[j] * CAP_PL * (1 - 0.12 * c[:, j]))
    for j in range(BOTTLE, 0, -1):                              # backward pass
        Q[:, j - 1] = np.minimum(Q[:, j - 1], Q[:, j] - sign[j] * ramp_true[:, j])
    Q = Q * (1 + rng.normal(0, 0.025, Q.shape))
    Q = np.clip(Q, 50, None)

    density = Q / lanes / np.maximum(speed, 5)                  # veh/km/lane
    occ = np.clip(density * 0.65 + rng.normal(0, 0.8, Q.shape), 0.5, 95)

    # ---- sensor imperfections ---------------------------------------------
    speed_o, flow_o, occ_o = speed.copy(), Q.copy(), occ.copy()
    for arr in (speed_o, flow_o, occ_o):
        arr[rng.random(arr.shape) < 0.012] = np.nan
        for _ in range(int(0.002 * T * n_links)):
            r, cidx, ln = int(rng.integers(0, T - 10)), int(rng.integers(0, n_links)), int(rng.integers(3, 9))
            arr[r:r + ln, cidx] = np.nan

    ramp_obs = np.full((T, n_links), np.nan)
    ramp_q = np.zeros((T, n_links), dtype=int)
    for j, rt in enumerate(meta["ramp_type"]):
        if rt == "none":
            continue
        r = rng.random(T)
        q = np.where(r < 0.05, 1, 0)
        q = np.where(r > 0.98, 2, q)
        for _ in range(int(T / 700)):                           # multi-hour outages
            s = int(rng.integers(0, T - 30))
            q[s:s + int(rng.integers(12, 30))] = 2
        val = ramp_true[:, j] * (1 + rng.normal(0, 0.03, T))
        val = np.where(q == 1, val * rng.uniform(0.4, 1.6, T), val)
        val = np.where(q == 2, 0.0, val)                        # unavailable logged as 0
        ramp_obs[:, j], ramp_q[:, j] = val, q

    long = pd.DataFrame({
        "timestamp": np.repeat(ts.to_numpy(), n_links),
        "link_id": np.tile(meta["link_id"].to_numpy(), T),
        "speed_kmh": speed_o.ravel(),
        "flow_vph": flow_o.ravel(),
        "occupancy_pct": occ_o.ravel(),
        "ramp_flow_vph": ramp_obs.ravel(),
        "ramp_quality": ramp_q.ravel(),
    })
    return long, meta


def queue_prevalence(long: pd.DataFrame, meta: pd.DataFrame) -> float:
    m = long.merge(meta[["link_id", "ffs_kmh"]], on="link_id")
    ok = m["speed_kmh"].notna()
    return float((m.loc[ok, "speed_kmh"] <= QUEUE_RATIO * m.loc[ok, "ffs_kmh"]).mean())
