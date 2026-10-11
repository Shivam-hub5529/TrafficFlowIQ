from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class QueueRequest(BaseModel):
    link_id: int = Field(..., ge=0, description="Freeway link id")
    timestamp: datetime = Field(..., description="Prediction time t (naive local time, 5-minute grid)")


class Reason(BaseModel):
    concept: str
    direction: Literal["up", "down"]
    strength: float
    text: str


class AdvancedFeature(BaseModel):
    feature: str
    value: Optional[float]
    contribution: float


class HistoryPoint(BaseModel):
    t: str
    speed: Optional[float]


class DataQuality(BaseModel):
    ramp_available: Optional[bool]    # None = link has no ramp
    missing_speed_readings: int
    note: str


class QueueResponse(BaseModel):
    link_id: int
    timestamp: str
    risk: float
    label: Literal["low", "moderate", "high"]
    verdict: str
    threshold_used: float
    horizon_risk: dict[str, float]
    queue_speed_kmh: float
    free_flow_kmh: float
    history: list[HistoryPoint]
    reasons: list[Reason]
    advanced: list[AdvancedFeature]
    data_quality: DataQuality
    model_version: str


class FutureCheck(BaseModel):
    future: list[HistoryPoint]
    queued_in_next_30: Optional[bool]
    min_speed_kmh: Optional[float]


class ReconRequest(BaseModel):
    link_id: int = Field(..., ge=0)
    start: datetime
    end: datetime
    mask_rate: float = Field(0.2, ge=0.05, le=0.5)
    seed: int = Field(7, ge=0, le=10_000)


class ReconPoint(BaseModel):
    t: str
    was_missing_speed: bool
    was_missing_flow: bool
    speed_obs: Optional[float]
    speed_est: Optional[float]
    speed_true: Optional[float]
    flow_obs: Optional[float]
    flow_est: Optional[float]
    flow_true: Optional[float]
    speed_interp: Optional[float]
    flow_interp: Optional[float]


class PhysicsReport(BaseModel):
    checked_points: int
    violations_pct_raw: float
    violations_pct_after_correction: float
    checks: list[str]
    explanation: str


class ReconResponse(BaseModel):
    link_id: int
    points: list[ReconPoint]
    n_masked_speed: int
    n_masked_flow: int
    rmse: dict[str, Optional[float]]
    rmse_baseline_linear: dict[str, Optional[float]]
    physics: PhysicsReport
    model_version: str
