from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import subprocess
import sys

from app.deps import get_db, get_current_admin
from app.core.rate_limiter import limiter, LIMIT_ADMIN

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
@limiter.limit(LIMIT_ADMIN)
def admin_panel(
    request: Request,
    current_user=Depends(get_current_admin),
):
    return templates.TemplateResponse(
        "admin/index.html",
        {
            "request": request,
            "current_user": current_user,
            "message": None,
            "error": None,
        },
    )


@router.post("/retrain", response_class=HTMLResponse)
@limiter.limit(LIMIT_ADMIN)
def retrain_models(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """
    Triggers ml/train.py as a subprocess.
    This runs synchronously for simplicity — fine for a medium-level project.
    For large datasets consider running it as a background task.
    """
    message = None
    error = None

    try:
        result = subprocess.run(
            [sys.executable, "ml/train.py"],
            capture_output=True,
            text=True,
            timeout=300,   # 5 minute max
        )
        if result.returncode == 0:
            message = "Models retrained successfully."
        else:
            error = f"Training failed: {result.stderr[:500]}"
    except subprocess.TimeoutExpired:
        error = "Training timed out after 5 minutes."
    except Exception as e:
        error = f"Unexpected error: {str(e)}"

    return templates.TemplateResponse(
        "admin/index.html",
        {
            "request": request,
            "current_user": current_user,
            "message": message,
            "error": error,
        },
    )