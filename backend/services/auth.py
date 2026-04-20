from typing import Optional
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt
from datetime import datetime, timedelta

from core.config import settings
from db.session import get_db
from models.models import User

security = HTTPBearer(auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload
    except jwt.PyJWTError:
        return None


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user from JWT token or API key (optional - returns None if not authenticated)"""
    
    # Check for API key in headers
    api_key = request.headers.get("X-API-Key")
    if api_key:
        result = await db.execute(select(User).where(User.api_key == api_key))
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