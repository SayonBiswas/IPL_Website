from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.deps import get_db, get_optional_user
from app.core.rate_limiter import limiter, LIMIT_STANDARD

router = APIRouter(prefix="/teams", tags=["teams"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
@limiter.limit(LIMIT_STANDARD)
def teams_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    from app.db.models.team import Team

    teams = db.query(Team).order_by(Team.name.asc()).all()

    return templates.TemplateResponse(
        "teams/index.html",
        {
            "request": request,
            "current_user": current_user,
            "teams": teams,
        },
    )


@router.get("/{team_id}", response_class=HTMLResponse)
@limiter.limit(LIMIT_STANDARD)
def team_detail(
    team_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    from app.db.models.team import Team
    from app.db.models.player import Player
    from app.db.models.match import Match

    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found.")

    players = (
        db.query(Player)
        .filter(Player.team_id == team_id)
        .order_by(Player.name.asc())
        .all()
    )

    # Recent matches involving this team
    recent_matches = (
        db.query(Match)
        .filter(
            (Match.team1_id == team_id) | (Match.team2_id == team_id),
            Match.is_completed == True,
        )
        .order_by(Match.match_date.desc())
        .limit(5)
        .all()
    )

    return templates.TemplateResponse(
        "teams/detail.html",
        {
            "request": request,
            "current_user": current_user,
            "team": team,
            "players": players,
            "recent_matches": recent_matches,
        },
    )