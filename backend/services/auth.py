from typing import Optional
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt
from datetime import datetime, timedelta, timezone

from core.config import settings
from db.session import get_db
from models.models import User
from services.api_key import hash_api_key

security = HTTPBearer(auto_error=False)

# Name of the httpOnly cookie carrying the refresh token. Kept here (rather
# than only in config) so routers can import a single canonical constant.
REFRESH_COOKIE_NAME = settings.refresh_cookie_name


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a short-lived JWT access token.

    Phase 1 change: this used to default to a 7-day expiry and was the
    *only* token type, which is why the frontend had to keep it in
    localStorage indefinitely (XSS exposure). It now defaults to a short
    TTL driven by settings; see create_refresh_token() for the
    long-lived, httpOnly-cookie-only counterpart that keeps users signed in.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived refresh token.

    This is only ever transmitted as an httpOnly cookie (see
    routers/auth.py's _set_refresh_cookie) — JavaScript never has access
    to it, which is what actually closes the XSS-token-theft gap that
    storing the access token in localStorage opened up.
    """
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {"sub": user_id, "type": "refresh", "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def verify_token(token: str) -> Optional[dict]:
    """Verify a JWT access token and return its payload."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") not in (None, "access"):
            # Reject a refresh token presented as an access token, and
            # vice versa — they are not interchangeable.
            return None
        return payload
    except jwt.PyJWTError:
        return None


def verify_refresh_token(token: str) -> Optional[dict]:
    """Verify a JWT refresh token specifically (checks the `type` claim)."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            return None
        return payload
    except jwt.PyJWTError:
        return None


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user from JWT token or API key (optional - returns None if not authenticated)"""
    
    # Check for API key in headers — hash it and compare against stored hash
    api_key = request.headers.get("X-API-Key")
    if api_key:
        key_hash = hash_api_key(api_key)
        result = await db.execute(select(User).where(User.api_key == key_hash))
        user = result.scalar_one_or_none()
        if user:
            return user
    
    # Check for JWT token
    if credentials:
        payload = verify_token(credentials.credentials)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                return user
    
    return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from JWT token or API key (required - raises exception if not authenticated)"""
    user = await get_current_user_optional(request, credentials, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Require an authenticated user with the is_admin flag set.

    Phase 1 security remediation: gates every destructive/administrative
    endpoint (storage cleanup & R2 migration, job-queue cleanup, template
    reseeding) that was previously reachable by anyone, authenticated or not.
    """
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for this operation",
        )
    return current_user


async def get_user_by_email(email: str, db: AsyncSession) -> Optional[User]:
    """Get user by email"""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(email: str, user_id: str, db: AsyncSession) -> User:
    """Create new user"""
    user = User(
        id=user_id,
        email=email,
        plan="free",
        daily_limit=settings.rate_limit_free
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
