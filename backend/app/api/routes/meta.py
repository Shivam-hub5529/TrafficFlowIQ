from fastapi import APIRouter

from app.services.store import get_store

router = APIRouter()


@router.get("/health")
def health():
    s = get_store()
    return {"status": "ok", "queue_model": s.q_meta["model_version"], "reconstruction_model": s.r_meta["model_version"], "data_source": s.data_source}


@router.get("/links")
def links():
    return {"data_source": get_store().data_source, "links": [{k: v for k, v in l.items() if k != "featured"} for l in get_store().links.values()]}


@router.get("/model/info")
def model_info():
    s = get_store()
    q, r = s.q_metrics, s.r_metrics
    return {"queue_model_version": s.q_meta["model_version"], "trained_at": s.q_meta["trained_at"], "data_source": s.data_source,
            "threshold": s.threshold, "split": q["split"], "baselines": q["baselines"],
            "lightgbm": {k: q["lightgbm"][k] for k in ("val", "test", "best_iteration")}, "horizons": q["horizons"],
            "reconstruction": {"version": s.r_meta["model_version"], **{k: v for k, v in r.items()}},
            "model_card": s.model_card}
