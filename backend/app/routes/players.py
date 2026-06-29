from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from app.deps import get_db, get_optional_user
from app.core.rate_limiter import limiter, LIMIT_STANDARD

router = APIRouter(prefix="/players", tags=["players"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
@limiter.limit(LIMIT_STANDARD)
def players_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
    team_id: Optional[int] = None,      # ?team_id=3  filters by team
    role: Optional[str] = None,          # ?role=Batsman
):
    from app.db.models.player import Player
    from app.db.models.team import Team

    query = db.query(Player)

    if team_id:
        query = query.filter(Player.team_id == team_id)
    if role:
        query = query.filter(Player.role == role)

    players = query.order_by(Player.name.asc()).all()
    teams = db.query(Team).order_by(Team.name.asc()).all()   # for filter dropdown

    return templates.TemplateResponse(
        "players/index.html",
        {
            "request": request,
            "current_user": current_user,
            "players": players,
            "teams": teams,
            "selected_team_id": team_id,
            "selected_role": role,
        },
    )


@router.get("/{player_id}", response_class=HTMLResponse)
@limiter.limit(LIMIT_STANDARD)
def player_detail(
    player_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    from app.db.models.player import Player

    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found.")

    return templates.TemplateResponse(
        "players/detail.html",
        {
            "request": request,
            "current_user": current_user,
            "player": player,
        },
    )