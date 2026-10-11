# Deployment guide

Architecture: **Vercel** (Next.js frontend) -> HTTPS JSON -> **Render / Railway / Fly / Hugging Face Space** (FastAPI in Docker).
Vercel is not used for the backend: LightGBM + pandas exceed practical serverless bundle and cold-start limits.

## Environment variables
| Where | Name | Example |
|---|---|---|
| Frontend (Vercel) | `NEXT_PUBLIC_API_URL` | `https://trafficflowiq-api.onrender.com` |
| Backend | `ALLOWED_ORIGINS` | `https://trafficflowiq.vercel.app` (comma-separated) |
| Backend | `LOG_LEVEL` | `INFO` |
| Backend (optional) | `MODEL_DIR`, `SERVING_DIR`, `QUEUE_MODEL_VERSION`, `RECON_MODEL_VERSION` | defaults point at the repo folders |

## Checklist
1. `make train export test` locally (or use the committed artifacts).
2. `docker build -t trafficflowiq-api .` then `docker run -p 8000:8000 -e ALLOWED_ORIGINS=http://localhost:3000 trafficflowiq-api`.
3. Open http://localhost:8000/docs and check `/health`.
4. Push to GitHub.
5. Render: New > Web Service > connect repo > Runtime Docker (uses `render.yaml`). Set `ALLOWED_ORIGINS` to a placeholder first.
6. Check `https://<api>/health`.
7. Vercel: Import repo, **Root Directory = `frontend`**, add `NEXT_PUBLIC_API_URL`, deploy.
8. Go back to the backend and set `ALLOWED_ORIGINS` to the real Vercel URL (no trailing slash). Redeploy.
9. Free tiers sleep: the first request can take 30-60 s. The UI shows a "server may be waking up" message; optionally ping `/health` with an uptime monitor.

## Testing the deployed app
```bash
API=https://<your-api>
curl $API/health
curl "$API/scenarios?link_id=3"
curl -X POST $API/predict/queue -H 'Content-Type: application/json' -d '{"link_id":3,"timestamp":"2025-02-12T16:25:00"}'
```
Then: pick a featured moment in the UI, predict, reveal the outcome, try an invalid time, test on a phone.
**Train/serve skew check:** the risk for a fixed scenario from the deployed API must equal the notebook value (`notebooks/04_queue_lightgbm.ipynb`).

## Where models live
Artifacts are small (<2 MB total) so they are baked into the Docker image. If they grow, upload them to Hugging Face Hub or a GitHub Release and download on startup.
