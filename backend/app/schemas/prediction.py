from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PredictionBase(BaseModel):
    match_id: int
    toss_winner_pred: Optional[str] = None       # team name
    match_winner_pred: Optional[str] = None      # team name
    mom_pred: Optional[str] = None               # player name
    toss_confidence: Optional[float] = None      # 0.0 - 1.0
    match_confidence: Optional[float] = None


class PredictionCreate(PredictionBase):
    pass


class PredictionOut(PredictionBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}