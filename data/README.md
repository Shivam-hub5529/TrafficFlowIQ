# Data

No raw data is committed. Two sources are supported:

## 1. Synthetic stand-in (default)
`src/trafficflowiq/synthetic.py` generates 42 days of 5-minute traffic on a 7-link freeway with a lane-drop bottleneck, rush hours,
incidents, ramp sensors with quality flags, and sensor dropouts. It exists so the whole pipeline runs end to end without a download.
**It is easier than real traffic. Do not report its metrics as TrafficFlowBench results.**

## 2. Real TrafficFlowBench (Kaggle: "2026 IEEE Big Data - Traffic Flow Bench")
1. Accept the competition rules on Kaggle and download the files into `data/raw/`.
2. Read the Data tab. Note the exact file names, column names, units (km/h vs mph), and how ramp quality is encoded.
3. Fill `KAGGLE_COLUMN_MAP` and `KAGGLE_LINK_MAP` in `src/trafficflowiq/data.py` (and adjust `load_real` to your file names).
4. Canonical long schema the code expects:

| column | meaning |
|---|---|
| timestamp | 5-minute grid |
| link_id | freeway link |
| speed_kmh, flow_vph, occupancy_pct | measurements (flow = all lanes) |
| ramp_flow_vph, ramp_quality | ramp flow; quality 0 = good, anything else = low quality / unavailable |

Link table: `link_id, name, lanes, length_km, ffs_kmh, ramp_type (on|off|none), upstream_id, downstream_id` (-1 if none).
If the competition gives topology as an edge list, derive `upstream_id` / `downstream_id` from it (links with several neighbours
need small changes in `features._neighbor`).
5. Retrain: `python scripts/train_queue.py --source kaggle && python scripts/train_recon.py --source kaggle && python scripts/export_serving.py --source kaggle`.
