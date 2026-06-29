from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.core.rate_limiter import limiter
from app.routes import auth, dashboard, teams, players, analytics, predictions, tournament, admin

settings = get_settings()

# ── App instance ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="IPL Dashboard",
    description="IPL match timetable, player stats, analytics and predictions.",
    version="1.0.0",
    # Disable /docs and /redoc in production
    docs_url="/docs" if settings.APP_ENV == "development" else None,
    redoc_url="/redoc" if settings.APP_ENV == "development" else None,
)

# ── Rate limiter ───────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Security headers middleware ────────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.APP_ENV == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response


app.add_middleware(SecurityHeadersMiddleware)

# ── CORS ───────────────────────────────────────────────────────────────────────
# Only matters if you ever call the API from a different origin.
# For a pure Jinja2 site this is mostly a safety net.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── Static files ───────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(teams.router)
app.include_router(players.router)
app.include_router(analytics.router)
app.include_router(predictions.router)
app.include_router(tournament.router)
app.include_router(admin.router)

# ── Startup: create DB tables if they don't exist ─────────────────────────────
@app.on_event("startup")
def create_tables():
    """
    Creates all tables on startup if they don't already exist.
    In production you should use Alembic migrations instead,
    but this is fine for development / first run.
    """
    from app.db.base import Base
    from app.db.session import engine

    # Import all models so SQLAlchemy registers them with Base.metadata
    from app.db.models import user, team, player, match, prediction  # noqa: F401

    Base.metadata.create_all(bind=engine)