from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4

from core.config import settings
from db.session import get_db
from models.models import User
from services.auth import (
    get_current_user_optional,
    get_user_by_email,
    create_user,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    REFRESH_COOKIE_NAME,
)

router = APIRouter()


class UserCreate(BaseModel):
    email: EmailStr
    provider: str  # "google", "github", etc.
    provider_id: str


class UserResponse(BaseModel):
    id: str
    email: str
    plan: str
    daily_limit: int
    daily_used: int
    api_key: Optional[str] = None
    api_key_prefix: Optional[str] = None
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        plan=user.plan,
        daily_limit=user.daily_limit,
        daily_used=user.daily_used,
        api_key=None,  # Never expose the database hash
        api_key_prefix=user.api_key_prefix,
        created_at=user.created_at.isoformat(),
    )


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """
    Attach the refresh token as an httpOnly cookie.

    This is the actual fix for the "JWT in localStorage" finding: the
    long-lived credential never touches JavaScript. The frontend only ever
    holds the short-lived access token, in memory.
    """
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
        path="/api/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/api/auth")


@router.post("/login", response_model=TokenResponse)
async def login_or_create_user(
    user_data: UserCreate,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Login existing user or create new user via OAuth.

    NOTE: the Google-OAuth redirect flow that lands on /auth/callback (see
    frontend/src/pages/AuthCallback.tsx) is handled by a separate backend
    route not included in this codebase snapshot. That route should be
    updated to call create_refresh_token() + _set_refresh_cookie() the same
    way this endpoint does, or OAuth-only users will simply be signed out
    once their access token expires (safe, but worse UX) until that route
    is updated for parity.
    """
    # Check if user exists
    user = await get_user_by_email(user_data.email, db)
    
    if not user:
        # Create new user
        user_id = str(uuid4())
        user = await create_user(user_data.email, user_id, db)
    
    # Create access token (short-lived) + refresh token (httpOnly cookie)
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(user.id)
    _set_refresh_cookie(response, refresh_token)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=_user_response(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Mint a new short-lived access token from the httpOnly refresh cookie.

    The frontend calls this silently on app load (and can call it again
    whenever an API request comes back 401) instead of ever persisting the
    access token itself in localStorage.
    """
    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token provided")

    payload = verify_refresh_token(raw_refresh)
    if not payload:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")

    # Rotate the refresh token on every use — limits the window in which a
    # stolen refresh token (e.g. via a compromised network/device) is valid.
    access_token = create_access_token(data={"sub": user.id})
    new_refresh_token = create_refresh_token(user.id)
    _set_refresh_cookie(response, new_refresh_token)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=_user_response(user),
    )


@router.post("/logout")
async def logout(response: Response):
    """Clear the refresh cookie. The (short-lived) access token in memory
    on the client is simply dropped by the frontend; nothing server-side
    to revoke for it given its short TTL."""
    _clear_refresh_cookie(response)
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user_optional)
):
    """Get current user information"""
    
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    return _user_response(current_user)
