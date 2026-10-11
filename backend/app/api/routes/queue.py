import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.schemas.api import FutureCheck, QueueRequest, QueueResponse
from app.services import predictor
from app.services.store import get_store

router = APIRouter()


def _wrap(fn, *a):
    try:
        return fn(get_store(), *a)
    except predictor.NotFound as e:
        raise HTTPException(404, str(e))
    except predictor.Unprocessable as e:
        raise HTTPException(422, str(e))


@router.post("/predict/queue", response_model=QueueResponse)
def predict_queue(req: QueueRequest):
    return _wrap(predictor.predict_queue, req.link_id, pd.Timestamp(req.timestamp))


@router.get("/history")
def history(link_id: int = Query(..., ge=0), timestamp: str = Query(...)):
    return _wrap(predictor.history_preview, link_id, pd.Timestamp(timestamp))


@router.get("/outcome", response_model=FutureCheck)
def outcome(link_id: int = Query(..., ge=0), timestamp: str = Query(...)):
    return _wrap(predictor.future_check, link_id, pd.Timestamp(timestamp))


@router.get("/scenarios")
def scenarios(link_id: int = Query(..., ge=0), date: str | None = None):
    return _wrap(predictor.scenarios, link_id, date)
