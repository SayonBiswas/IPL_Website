from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.deps import get_db, get_current_user
from app.core.rate_limiter import limiter, LIMIT_STANDARD

router = APIRouter(prefix="/analytics", tags=["analytics"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
@limiter.limit(LIMIT_STANDARD)
def analytics(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),   # must be logged in
):
    from app.db.models.team import Team
    from app.db.models.player import Player
    from app.db.models.match import Match

    # --- Win rate per team ---
    # Returns list of (team_name, wins, losses)
    teams = db.query(Team).all()
    win_rate_data = [
        {
            "team": t.name,
            "wins": t.wins,
            "losses": t.losses,
            "win_rate": round(t.wins / (t.wins + t.losses) * 100, 1)
            if (t.wins + t.losses) > 0
            else 0,
        }
        for t in teams
    ]

    # --- Top run scorers ---
    top_batsmen = (
        db.query(Player)
        .filter(Player.runs > 0)
        .order_by(Player.runs.desc())
        .limit(10)
        .all()
    )

    # --- Top wicket takers ---
    top_bowlers = (
        db.query(Player)
        .filter(Player.wickets > 0)
        .order_by(Player.wickets.desc())
        .limit(10)
        .all()
    )

    # --- Total matches played so far ---
    total_matches = db.query(func.count(Match.id)).filter(Match.is_completed == True).scalar()

    return templates.TemplateResponse(
        "analytics/index.html",
        {
            "request": request,
            "current_user": current_user,
            "win_rate_data": win_rate_data,
            "top_batsmen": top_batsmen,
            "top_bowlers": top_bowlers,
            "total_matches": total_matches,
        },
    )