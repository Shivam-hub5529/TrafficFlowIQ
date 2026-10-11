import pandas as pd
from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.schemas.api import ReconRequest, ReconResponse
from app.services import predictor, reconstructor
from app.services.store import get_store

router = APIRouter()


@router.post("/reconstruct", response_model=ReconResponse)
def reconstruct(req: ReconRequest):
    try:
        return reconstructor.reconstruct(get_store(), req.link_id, pd.Timestamp(req.start), pd.Timestamp(req.end), req.mask_rate, req.seed, settings.max_recon_hours)
    except predictor.NotFound as e:
        raise HTTPException(404, str(e))
    except predictor.Unprocessable as e:
        raise HTTPException(422, str(e))
