from typing import Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import RedirectResponse, HTMLResponse
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


@router.get("/login/google")
async def login_google(request: Request):
    """Redirect to Google or display a mock login bypass if credentials aren't set."""
    if not settings.google_client_id or not settings.google_client_secret:
        # Serves a beautifully styled dev bypass page.
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>MemeGPT Developer Bypass</title>
            <style>
                body {
                    background-color: #0b0f19;
                    color: #f3f4f6;
                    font-family: system-ui, -apple-system, sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    margin: 0;
                }
                .card {
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 16px;
                    padding: 32px;
                    width: 380px;
                    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
                    backdrop-filter: blur(12px);
                }
                h2 { margin-top: 0; color: #a3e635; font-size: 24px; text-align: center; }
                p { color: #9ca3af; font-size: 14px; text-align: center; margin-bottom: 24px; }
                .input-group { margin-bottom: 20px; }
                label { display: block; margin-bottom: 8px; font-size: 12px; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.05em; }
                input {
                    width: 100%;
                    padding: 12px;
                    background: rgba(0, 0, 0, 0.2);
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 8px;
                    color: #fff;
                    font-size: 14px;
                    box-sizing: border-box;
                }
                input:focus { outline: none; border-color: #a3e635; }
                button {
                    width: 100%;
                    padding: 12px;
                    background: #a3e635;
                    border: none;
                    border-radius: 8px;
                    color: #000;
                    font-weight: bold;
                    font-size: 14px;
                    cursor: pointer;
                    transition: background 0.2s;
                }
                button:hover { background: #bef264; }
            </style>
        </head>
        <body>
            <div class="card">
                <h2>Developer Bypass</h2>
                <p>Google OAuth credentials are not configured in your backend <code>.env</code>. Enter your email below to bypass login locally.</p>
                <form action="/api/auth/callback/google/mock" method="get">
                    <div class="input-group">
                        <label for="email">Email Address</label>
                        <input type="email" id="email" name="email" value="lokhandejay90@gmail.com" required>
                    </div>
                    <button type="submit">Log In (Mock Google OAuth)</button>
                </form>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    backend_callback_uri = f"{str(request.base_url).rstrip('/')}/api/auth/callback/google"
    # Note: request.base_url includes a trailing slash (e.g. http://localhost:8000/) so we strip it and join /api/auth/callback/google properly
    if not backend_callback_uri.startswith("http"):
        backend_callback_uri = f"http://localhost:8000/api/auth/callback/google"

    google_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        "response_type=code"
        f"&client_id={settings.google_client_id}"
        f"&redirect_uri={backend_callback_uri}"
        "&scope=openid%20email%20profile"
        "&access_type=offline"
        "&prompt=consent"
    )
    return RedirectResponse(url=google_url)


@router.get("/callback/google/mock")
async def mock_callback_google(
    email: EmailStr,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    # Get or create user
    user = await get_user_by_email(email, db)
    if not user:
        user_id = str(uuid4())
        user = await create_user(email, user_id, db)

    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(user.id)
    _set_refresh_cookie(response, refresh_token)

    frontend_redirect_url = f"{settings.frontend_url.rstrip('/')}/auth/callback?token={access_token}"
    return RedirectResponse(url=frontend_redirect_url)


@router.get("/callback/google")
async def callback_google(
    request: Request,
    response: Response,
    code: str,
    db: AsyncSession = Depends(get_db)
):
    backend_callback_uri = f"{str(request.base_url).rstrip('/')}/api/auth/callback/google"
    if not backend_callback_uri.startswith("http"):
        backend_callback_uri = f"http://localhost:8000/api/auth/callback/google"

    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": backend_callback_uri,
            }
        )
        if token_res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to retrieve token from Google: {token_res.text}")
        
        token_data = token_res.json()
        access_token_google = token_data.get("access_token")
        
        user_info_res = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token_google}"}
        )
        if user_info_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to retrieve user info from Google")
        
        user_info = user_info_res.json()
        email = user_info.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Google account did not provide an email address")

    # Get or create user
    user = await get_user_by_email(email, db)
    if not user:
        user_id = str(uuid4())
        user = await create_user(email, user_id, db)

    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(user.id)
    _set_refresh_cookie(response, refresh_token)

    frontend_redirect_url = f"{settings.frontend_url.rstrip('/')}/auth/callback?token={access_token}"
    return RedirectResponse(url=frontend_redirect_url)

