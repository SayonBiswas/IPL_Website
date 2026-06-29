from typing import Generator, Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.security import decode_access_token


# --- Database dependency ---

def get_db() -> Generator[Session, None, None]:
    """
    Yields a database session and ensures it is closed after the request,
    even if an exception occurs.

    Usage in a route:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Auth dependency ---

def get_current_user(request: Request, db: Session = Depends(get_db)) -> "User":  # noqa: F821
    """
    Reads the access token from the httpOnly cookie set at login.
    Decodes it, looks up the user in the database, and returns the User ORM object.
    Raises HTTP 401 if the cookie is missing, token is invalid, or user not found.

    Usage in a route:
        @router.get("/protected")
        def protected(current_user = Depends(get_current_user)):
            ...
    """
    # Import here to avoid circular imports (models import Base which is in db/)
    from app.db.models.user import User

    token: Optional[str] = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in.",
        )

    payload = decode_access_token(token)
    user_id: int = int(payload["sub"])

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Please log in again.",
        )

    return user


def get_current_admin(current_user=Depends(get_current_user)):
    """
    Extends get_current_user — additionally checks that the user's role is 'admin'.
    Raises HTTP 403 if not.

    Usage in a route:
        @router.post("/admin/retrain")
        def retrain(current_user = Depends(get_current_admin)):
            ...
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


def get_optional_user(request: Request, db: Session = Depends(get_db)):
    """
    Like get_current_user but returns None instead of raising 401.
    Use on pages that are visible to guests but show extra info when logged in.
    """
    from app.db.models.user import User

    token: Optional[str] = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id: int = int(payload["sub"])
        return db.query(User).filter(User.id == user_id).first()
    except Exception:
        return None