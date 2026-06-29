from pydantic import BaseModel
from typing import Optional


class PlayerBase(BaseModel):
    name: str
    team_id: int
    role: str                       # Batsman, Bowler, All-rounder, Wicket-keeper
    nationality: Optional[str] = None
    runs: int = 0
    wickets: int = 0
    matches_played: int = 0
    highest_score: Optional[int] = None
    batting_average: Optional[float] = None
    bowling_average: Optional[float] = None
    image_url: Optional[str] = None


class PlayerCreate(PlayerBase):
    pass


class PlayerOut(PlayerBase):
    id: int

    model_config = {"from_attributes": True}