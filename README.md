# TrafficFlowIQ: Freeway Congestion & Queue Prediction System

*Know where the queue will form before it does.*

An end-to-end machine-learning web app inspired by the **2026 IEEE Big Data - Traffic Flow Bench (TrafficFlowBench)** challenge.
Pick a freeway link and a moment in time; the app reads the previous 60 minutes and returns the chance of a queue in the next 30 minutes,
a minute-by-minute forecast, and the top reasons in plain language. A second tool rebuilds missing speed and flow readings and checks the result against simple traffic physics.

> **Read this first: the data in this repo is synthetic.** TrafficFlowBench cannot be redistributed, so `src/trafficflowiq/synthetic.py`
> generates a physically motivated stand-in with the same structure (5-min speed/flow/occupancy, ramp flows with quality flags, link geometry, topology).
> Everything runs end to end, but the metrics below describe the stand-in, which is **easier than real traffic**.
> To get real results, follow [`data/README.md`](data/README.md) (about an hour of column mapping), retrain, and update this table.

## Scope
1. **Main:** queue prediction (queued = speed <= 60% of free-flow), 60 min history -> next 30 min.
2. **Secondary:** reconstruction of missing speed and flow per lane.
3. **Optional:** physics-consistency explanation (free-flow limit, jam density, lane capacity).
4. Not implemented: OD / path-flow demand estimation.

## Key design rules
- **No future information.** Every feature at time *t* uses data <= *t*. `tests/test_no_leakage.py` corrupts the future and asserts features do not change.
- **Chronological split by whole days** (70/15/15) with a 90-minute purge gap; calibration and threshold use validation only; test is scored once.
- **Missing evidence is not zero.** Low-quality / unavailable ramp readings become `NaN` plus explicit `ramp_bad_*` indicators (`tests/test_no_leakage.py::test_bad_ramp_is_missing_not_zero`).
- **Explanations, not just probabilities.** Exact tree-SHAP from LightGBM, grouped into concepts and translated to sentences (`src/trafficflowiq/explain.py`).
- **One feature codebase** (`src/trafficflowiq`) is shared by training and the API to prevent train/serve skew.
- **No training in the frontend.** The Vercel app only renders and calls the API.

## Results on the synthetic test period (7 held-out days)
| Model | F1 | Precision | Recall | IoU | PR-AUC | ROC-AUC |
|---|---|---|---|---|---|---|
| Persistence (queued now = queued later) | 0.816 | 0.942 | 0.720 | 0.689 | 0.700 | 0.858 |
| Historical average (link x time of day) | 0.596 | 0.708 | 0.515 | 0.425 | 0.519 | 0.856 |
| Logistic regression | 0.861 | 0.926 | 0.804 | 0.756 | 0.891 | 0.964 |
| **LightGBM + isotonic calibration** | **0.915** | 0.975 | 0.863 | 0.844 | 0.915 | 0.976 |

Reconstruction (15% of readings hidden): speed RMSE **1.83 km/h** vs 2.12 for linear interpolation; flow RMSE **27.7 veh/h/lane** vs 33.7.
Per-horizon ROC-AUC falls from 1.00 (+5 min) to 0.96 (+30 min). Full numbers: `models/queue/v1.0.0/metrics.json`, `models/reconstruction/v1.0.0/metrics.json`.

Caveat on these numbers: the synthetic queue is caused by smooth demand plus random incidents. Incident onsets are not predictable from the
preceding hour, which is why some "queue forms" demo moments get a low risk. That is intentional and honest.

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
make train export test            # retrains on synthetic data, exports serving files, runs tests (artifacts are already committed)

make api                          # terminal 1: http://localhost:8000/docs
cp frontend/.env.local.example frontend/.env.local
make web                          # terminal 2: http://localhost:3000
```

## Repository map
```
src/trafficflowiq/   shared ML code: synthetic, panel, labels, features, splits, metrics, physics, recon, explain, modelio
scripts/             train_queue.py, train_recon.py, export_serving.py
models/              queue/v1.0.0, reconstruction/v1.0.0 (joblib + feature_list, threshold, metrics, model_card)
data/serving/        compact parquet files the API reads (test-period features, panel, links.json)
backend/             FastAPI app (routes, schemas, services) + tests + requirements
frontend/            Next.js 14 + TypeScript + Tailwind app for Vercel
notebooks/           01..06 walk-through (EDA -> explainability)
docs/                api.md, deployment.md, architecture.md
report/              case-study report (outline + draft text)
```

## Deploy
See [`docs/deployment.md`](docs/deployment.md): frontend on Vercel (root directory `frontend`), backend Docker image on Render/Railway/Hugging Face Spaces.

## Limitations
Replay of recorded windows, not a live feed; synthetic data until swapped for TrafficFlowBench; the physics check is a simple rule set;
isotonic calibration and the F1 threshold share the validation set; events after the prediction time cannot be foreseen.

## License
MIT. TrafficFlowBench data is subject to the Kaggle competition rules.
