from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.schemas.auth import RegisterRequest, LoginRequest
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.core.rate_limiter import limiter, LIMIT_AUTH
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")

COOKIE_OPTS = {
    "httponly": True,
    "samesite": "lax",
    "secure": settings.APP_ENV == "production",  # HTTPS only in prod
}


# ── Pages ──────────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "error": None})


# ── Actions ────────────────────────────────────────────────────────────────────

@router.post("/register")
@limiter.limit(LIMIT_AUTH)
def register(
    request: Request,
    response: Response,
    form: RegisterRequest,
    db: Session = Depends(get_db),
):
    from app.db.models.user import User

    existing = db.query(User).filter(User.email == form.email).first()
    if existing:
        # Return the register page with an error message (HTMX-friendly)
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "An account with this email already exists."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user = User(
        email=form.email,
        hashed_password=hash_password(form.password),
        role=form.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Issue tokens immediately after registration
    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id)

    resp = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    resp.set_cookie("access_token", access_token, **COOKIE_OPTS)
    resp.set_cookie("refresh_token", refresh_token, **COOKIE_OPTS)
    return resp


@router.post("/login")
@limiter.limit(LIMIT_AUTH)
def login(
    request: Request,
    form: LoginRequest,
    db: Session = Depends(get_db),
):
    from app.db.models.user import User

    user = db.query(User).filter(User.email == form.email).first()
    if not user or not verify_password(form.password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Incorrect email or password."},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id)

    resp = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    resp.set_cookie("access_token", access_token, **COOKIE_OPTS)
    resp.set_cookie("refresh_token", refresh_token, **COOKIE_OPTS)
    return resp


@router.post("/refresh")
def refresh_token(request: Request, db: Session = Depends(get_db)):
    """
    Issue a new access token using the refresh token cookie.
    Called automatically by the frontend when an access token expires.
    """
    from app.db.models.user import User

    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token.")

    user_id = decode_refresh_token(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    new_access_token = create_access_token(user.id, user.role)
    resp = Response()
    resp.set_cookie("access_token", new_access_token, **COOKIE_OPTS)
    return resp


@router.post("/logout")
def logout():
    resp = RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)
    resp.delete_cookie("access_token")
    resp.delete_cookie("refresh_token")
    return resp