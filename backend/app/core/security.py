from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

from app.config import get_settings

settings = get_settings()

# --- Password hashing ---
# bcrypt is the recommended algorithm for password storage.
# deprecated="auto" means older hashes are automatically re-hashed on next login.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password. Store the result, never the original."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if plain_password matches the stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


# --- JWT tokens ---

def _create_token(data: dict, secret: str, expires_delta: timedelta) -> str:
    """Internal helper — builds and signs a JWT with an expiry claim."""
    payload = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    payload.update({"exp": expire})
    return jwt.encode(payload, secret, algorithm=settings.ALGORITHM)


def create_access_token(user_id: int, role: str) -> str:
    """
    Short-lived token (default 30 min) sent with every request.
    Carries: sub (user id as string), role.
    """
    return _create_token(
        data={"sub": str(user_id), "role": role},
        secret=settings.SECRET_KEY,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: int) -> str:
    """
    Long-lived token (default 7 days) used only to issue new access tokens.
    Stored in an httpOnly cookie — never exposed to page JS.
    """
    return _create_token(
        data={"sub": str(user_id)},
        secret=settings.REFRESH_SECRET_KEY,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_access_token(token: str) -> dict:
    """
    Decode and validate an access token.
    Raises HTTP 401 if the token is invalid or expired.
    Returns the payload dict (contains 'sub' and 'role').
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token. Please log in again.",
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("sub") is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


def decode_refresh_token(token: str) -> int:
    """
    Decode and validate a refresh token.
    Returns the user_id (int) or raises HTTP 401.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token. Please log in again.",
    )
    try:
        payload = jwt.decode(
            token, settings.REFRESH_SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return int(user_id)
    except JWTError:
        raise credentials_exception


def require_role(required_role: str, current_role: str) -> None:
    """
    Raise HTTP 403 if the current user's role does not match.
    Usage: require_role("admin", current_user.role)
    """
    if current_role != required_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )