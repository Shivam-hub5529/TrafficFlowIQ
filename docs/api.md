# API reference (interactive docs at `/docs`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness, model versions, data source |
| GET | `/links` | link metadata |
| GET | `/scenarios?link_id=3` | available dates + featured moments; add `&date=YYYY-MM-DD` for times |
| GET | `/history?link_id&timestamp` | last 60 minutes of speed (preview) |
| POST | `/predict/queue` | queue risk, forecast strip, reasons |
| GET | `/outcome?link_id&timestamp` | what actually happened in the next 30 minutes |
| POST | `/reconstruct` | hide readings and rebuild speed + flow per lane |
| GET | `/model/info` | metrics and model card |

## POST /predict/queue
```json
{ "link_id": 3, "timestamp": "2025-02-12T16:25:00" }
```
Response fields: `risk` (chance of any queue in the next 30 min), `label` (low/moderate/high), `verdict`, `threshold_used`,
`horizon_risk` (chance of being queued at exactly +5 ... +30 min), `history`, `reasons` (plain language), `advanced` (SHAP values),
`data_quality`, `model_version`.

## POST /reconstruct
```json
{ "link_id": 3, "start": "2025-02-12T16:00:00", "end": "2025-02-12T18:00:00", "mask_rate": 0.2, "seed": 7 }
```
Returns per-step `speed_est / speed_true / speed_interp` (and flow), RMSE for the model and for linear interpolation, and a physics report.

## Errors
| Code | When |
|---|---|
| 404 | unknown `link_id` |
| 422 | timestamp not on the 5-minute grid, outside the available range, no complete 60-minute history, window too long, invalid body |
| 500 | unexpected; body contains a `request_id`, never a stack trace |
