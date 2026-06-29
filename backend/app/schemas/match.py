from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MatchBase(BaseModel):
    team1_id: int
    team2_id: int
    venue: str
    match_date: datetime
    result: Optional[str] = None          # e.g. "Mumbai Indians won by 6 wickets"
    winner_id: Optional[int] = None
    toss_winner_id: Optional[int] = None
    toss_decision: Optional[str] = None   # "bat" or "field"
    man_of_match_id: Optional[int] = None
    is_completed: bool = False


class MatchCreate(MatchBase):
    pass


class MatchOut(MatchBase):
    id: int

    model_config = {"from_attributes": True}