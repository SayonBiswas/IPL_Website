from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.core.rate_limiter import limiter, LIMIT_PREDICTIONS

router = APIRouter(prefix="/predictions", tags=["predictions"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
@limiter.limit(LIMIT_PREDICTIONS)
def predictions_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.db.models.prediction import Prediction
    from app.db.models.match import Match

    # All predictions joined with their match info
    predictions = (
        db.query(Prediction)
        .join(Match, Prediction.match_id == Match.id)
        .order_by(Match.match_date.asc())
        .all()
    )

    return templates.TemplateResponse(
        "predictions/index.html",
        {
            "request": request,
            "current_user": current_user,
            "predictions": predictions,
        },
    )


@router.get("/{match_id}", response_class=HTMLResponse)
@limiter.limit(LIMIT_PREDICTIONS)
def prediction_detail(
    match_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.db.models.prediction import Prediction
    from app.db.models.match import Match
    from app.db.models.team import Team

    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found.")

    prediction = (
        db.query(Prediction).filter(Prediction.match_id == match_id).first()
    )

    # If no prediction exists yet, generate one on the fly
    if not prediction:
        try:
            from ml.predict import predict_match
            result = predict_match(match, db)

            prediction = Prediction(
                match_id=match.id,
                toss_winner_pred=result["toss_winner"],
                match_winner_pred=result["match_winner"],
                mom_pred=result["man_of_match"],
                toss_confidence=result["toss_confidence"],
                match_confidence=result["match_confidence"],
            )
            db.add(prediction)
            db.commit()
            db.refresh(prediction)
        except Exception as e:
            # ML model not trained yet — show page with no prediction
            prediction = None

    team1 = db.query(Team).filter(Team.id == match.team1_id).first()
    team2 = db.query(Team).filter(Team.id == match.team2_id).first()

    return templates.TemplateResponse(
        "predictions/detail.html",
        {
            "request": request,
            "current_user": current_user,
            "match": match,
            "team1": team1,
            "team2": team2,
            "prediction": prediction,
        },
    )