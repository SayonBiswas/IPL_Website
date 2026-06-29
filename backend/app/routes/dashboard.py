from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.deps import get_db, get_optional_user
from app.core.rate_limiter import limiter, LIMIT_STANDARD

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
@limiter.limit(LIMIT_STANDARD)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    from app.db.models.match import Match
    from app.db.models.team import Team

    # Upcoming matches (not completed), ordered by date
    upcoming_matches = (
        db.query(Match)
        .filter(Match.is_completed == False)
        .order_by(Match.match_date.asc())
        .limit(10)
        .all()
    )

    # Recent completed matches
    recent_matches = (
        db.query(Match)
        .filter(Match.is_completed == True)
        .order_by(Match.match_date.desc())
        .limit(5)
        .all()
    )

    # Points table — teams sorted by wins desc
    standings = (
        db.query(Team)
        .order_by(Team.wins.desc(), Team.losses.asc())
        .all()
    )

    return templates.TemplateResponse(
        "dashboard/index.html",
        {
            "request": request,
            "current_user": current_user,
            "upcoming_matches": upcoming_matches,
            "recent_matches": recent_matches,
            "standings": standings,
        },
    )


@router.get("/schedule/live", response_class=HTMLResponse)
@limiter.limit(LIMIT_STANDARD)
def live_scores_partial(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    HTMX partial — returns only the live scores section HTML.
    Called every 30 seconds by hx-trigger="every 30s" in dashboard/index.html.
    """
    from app.db.models.match import Match

    live_matches = (
        db.query(Match)
        .filter(Match.is_completed == False)
        .order_by(Match.match_date.asc())
        .limit(3)
        .all()
    )

    return templates.TemplateResponse(
        "dashboard/_live_scores.html",
        {"request": request, "live_matches": live_matches},
    )