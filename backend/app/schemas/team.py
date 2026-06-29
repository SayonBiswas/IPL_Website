from pydantic import BaseModel
from typing import Optional


class TeamBase(BaseModel):
    name: str
    city: str
    wins: int = 0
    losses: int = 0
    logo_url: Optional[str] = None


class TeamCreate(TeamBase):
    pass


class TeamOut(TeamBase):
    id: int

    model_config = {"from_attributes": True}