# Architecture

```
Browser (Next.js on Vercel)
   |  HTTPS JSON (NEXT_PUBLIC_API_URL)
   v
FastAPI (Docker on Render/Railway/HF Spaces)
   |-- startup: load LightGBM models, calibrators, serving parquet ONCE
   |-- /predict/queue : lookup feature row -> predict_proba -> isotonic -> tree-SHAP -> plain-language reasons
   |-- /reconstruct   : mask window -> build recon features -> LightGBM -> physics post-correction
   `-- shared package src/trafficflowiq (same feature code as training)

Offline (your laptop):  synthetic|kaggle -> panel -> features/labels -> split (days + purge) -> train -> models/ + data/serving/
```

Why replay instead of a live feed: the competition data is historical, so the app replays held-out windows. This also enables the
"reveal what actually happened" feature, which makes the model's hits and misses visible.

Latency: the API does a dictionary-style lookup plus seven tiny tree predictions; measured ~15 ms locally.
