from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.core.rate_limiter import limiter, LIMIT_PREDICTIONS

router = APIRouter(prefix="/tournament", tags=["tournament"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
@limiter.limit(LIMIT_PREDICTIONS)
def tournament(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.db.models.match import Match
    from app.db.models.team import Team
    from app.db.models.player import Player

    # --- Remaining matches (not completed) ---
    remaining_matches = (
        db.query(Match)
        .filter(Match.is_completed == False)
        .order_by(Match.match_date.asc())
        .all()
    )

    # --- Simulate tournament winner ---
    tournament_winner = None
    player_of_tournament = None
    simulation_error = None

    try:
        from ml.predict import predict_tournament_winner, predict_player_of_tournament
        tournament_winner = predict_tournament_winner(remaining_matches, db)
        player_of_tournament = predict_player_of_tournament(db)
    except Exception as e:
        simulation_error = "Prediction models not available yet. Run training first."

    # --- Current standings for context ---
    standings = (
        db.query(Team)
        .order_by(Team.wins.desc())
        .all()
    )

    # --- Top performers for Player of Tournament context ---
    top_players = (
        db.query(Player)
        .order_by(Player.runs.desc())
        .limit(5)
        .all()
    )

    return templates.TemplateResponse(
        "tournament/index.html",
        {
            "request": request,
            "current_user": current_user,
            "tournament_winner": tournament_winner,
            "player_of_tournament": player_of_tournament,
            "remaining_matches": remaining_matches,
            "standings": standings,
            "top_players": top_players,
            "simulation_error": simulation_error,
        },
    )