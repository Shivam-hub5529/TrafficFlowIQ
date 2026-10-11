# TrafficFlowIQ: Freeway Congestion & Queue Prediction System
*Case-study report (draft). Sections marked TODO need your own analysis after you swap in the real TrafficFlowBench data.*

## 1. Abstract
Freeway queues form quickly and clear slowly, so a warning a few minutes ahead is valuable. TrafficFlowIQ predicts, for a chosen freeway link,
the probability of a queue (speed <= 60% of free-flow) in the next 30 minutes using only the previous 60 minutes of data, explains the
prediction in plain language, and reconstructs missing speed and flow readings with a simple physics check. A calibrated LightGBM model
reached F1 0.915 and PR-AUC 0.915 on a held-out test period of a synthetic stand-in dataset, against F1 0.816 for persistence.
The system is deployed as a Next.js app on Vercel with a FastAPI backend. TODO: replace with TrafficFlowBench results and add the live URL.

## 2. Introduction
Short-term congestion forecasting supports ramp metering, traveller information and incident response. This project turns the
2026 IEEE Big Data TrafficFlowBench challenge into a usable product.

## 3. Problem statement
- **Task A (main):** given data in (t-60 min, t], predict whether link L is queued at any 5-minute step in (t, t+30 min].
- **Task B:** reconstruct masked speed and flow per lane.
- **Constraints:** no future information; low-quality ramp readings are missing evidence, not zero flow; explanation required.

## 4. Business and real-world context
Operators need lead time and a reason. A probability with no explanation is hard to act on; a reason ("upstream is already slowing") tells operators where to look.
Reconstruction matters because real detectors fail, and downstream tools need complete data.

## 5. Traffic-flow background
Speed v, flow q (veh/h), density k (veh/km) and occupancy are linked by q = k v. The fundamental diagram says flow rises with density up to
capacity, then falls as the road jams. Queues spread upstream as shockwaves. Conservation: vehicles entering a link plus on-ramp flow minus off-ramp flow equals vehicles leaving, up to storage.
TODO: add 2-3 citations (Greenshields 1935; Lighthill-Whitham-Richards; HCM).

## 6. Dataset
Competition data: five-minute synthetic freeway traffic with speed, flow, occupancy, ramp flows, link geometry, topology and path incidence (path incidence unused here).
Stand-in data used in this draft: 7 links, 42 days, lane-drop bottleneck at link 4, incidents, ramp quality flags, ~1-2% random sensor dropouts, ~5% overall queue prevalence.
TODO: describe real schema, number of links, ramp quality encoding.

## 7. Exploratory data analysis
Notebook `01_eda`. Include: queue share by hour and link; speed distributions; missingness by link and by ramp quality flag; flow-speed scatter (fundamental diagram).

## 8. Methodology
- Wide (time x link) panel; 5-minute grid enforced, gaps inserted as NaN.
- Labels: y_h = queued at t+h (h = 5..30); y_any = any of them.
- Split: whole days, 70/15/15, 90-minute purge gap; threshold and calibrator from validation; test scored once.
- Leakage test: corrupt all data after t, assert features at t unchanged.

## 9. Feature engineering
Queue features (all <= t): current speed/flow/occupancy/ratio; lags at 5, 15, 30, 55 min; changes over 15/30/55 min; rolling mean/min/max/std; largest 5-minute drop; queued steps in the last hour;
upstream and downstream ratios and trends; ramp flow plus `ramp_bad` indicators; geometry; time-of-day sin/cos; weekend; density.
Reconstruction features: values on both sides of a gap, linear interpolation, the other variable, occupancy, neighbour links, ramps, geometry, time.
TODO: ablation (drop spatial / ramp / calendar groups and report PR-AUC change).

## 10. Model development
Baselines: persistence, historical average, logistic regression; reconstruction: linear interpolation, last observation, neighbour average.
Main: LightGBM (early stopping on validation PR-AUC), isotonic calibration, six per-horizon models for the forecast strip.
Not built (by design): sequence models. Add a GRU only if it beats LightGBM PR-AUC by a meaningful margin; otherwise report as a negative result.
TODO: XGBoost comparison; Optuna tuning with expanding-window CV.

## 11. Evaluation and results (synthetic stand-in)
| Model | F1 | Precision | Recall | IoU | PR-AUC | ROC-AUC |
|---|---|---|---|---|---|---|
| Persistence | 0.816 | 0.942 | 0.720 | 0.689 | 0.700 | 0.858 |
| Historical average | 0.596 | 0.708 | 0.515 | 0.425 | 0.519 | 0.856 |
| Logistic regression | 0.861 | 0.926 | 0.804 | 0.756 | 0.891 | 0.964 |
| LightGBM + calibration | 0.915 | 0.975 | 0.863 | 0.844 | 0.915 | 0.976 |

Reconstruction (15% masked): speed RMSE 1.83 vs 2.12 km/h (linear interpolation); flow 27.7 vs 33.7 veh/h/lane.
**Honest finding:** for single-point gaps linear interpolation is slightly better (speed 1.30 vs 1.43); the model wins on gaps of 2+ steps
(2.00 vs 2.69 km/h for gaps of 5+). A hybrid that falls back to interpolation for isolated points is a sensible improvement.
Error analysis: queue onsets caused by incidents have little warning in the prior hour and are mostly missed.

## 12. Explainability
Exact tree-SHAP (LightGBM `pred_contrib`), grouped into concepts (speed drop, upstream slowdown, occupancy, ramp data gaps, time of day, geometry) and mapped to sentences. Raw features stay in an "Advanced details" panel.
TODO: global SHAP summary plot (notebook 06) and 2-3 worked examples with screenshots.

## 13. Web application design
Pages: Home, Predict (link, date, time, featured moments, speed preview, VMS-style result, forecast strip, reasons, reveal), Fill sensor gaps (mask rate, charts, RMSE vs baseline, physics toggle), About the model.
TODO: add screenshots.

## 14. Deployment
Vercel (frontend) + Docker FastAPI on Render/Railway/HF Spaces; models baked into the image; models and tables loaded once at startup; CORS restricted to the Vercel origin. See `docs/deployment.md`.

## 15. Limitations
Synthetic data until replaced; replay not live; incident-driven queues unpredictable; simple physics rules; calibration and threshold share the validation set; no uncertainty intervals.

## 16. Future scope
Live sensor ingestion; graph neural networks over topology; conformal prediction intervals; OD / path-flow estimation using path-incidence data; a physics-informed loss for reconstruction.

## 17. Conclusion
TODO after real-data results.

## 18. References
- 2026 IEEE Big Data Cup, "Traffic Flow Bench", Kaggle competition page.
- Ke et al. (2017), LightGBM, NeurIPS.
- Lundberg & Lee (2017), A unified approach to interpreting model predictions (SHAP).
- Lighthill & Whitham (1955); Richards (1956), traffic flow on long crowded roads.
- Highway Capacity Manual (TRB).
