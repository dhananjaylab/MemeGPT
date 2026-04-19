from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from ..db.session import get_db
from ..models.models import User
from ..services.auth import (
    get_current_user_optional,
    get_user_by_email,
    create_user,
    create_access_token,
    get_current_user
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
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


@router.post("/login", response_model=TokenResponse)
async def login_or_create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Login existing user or create new user via OAuth"""
    
    # Check if user exists
    user = await get_user_by_email(user_data.email, db)
    
    if not user:
        # Create new user
        user_id = str(uuid4())
        user = await create_user(user_data.email, user_id, db)
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id})
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            plan=user.plan,
            daily_limit=user.daily_limit,
            daily_used=user.daily_used,
            api_key=user.api_key,
            created_at=user.created_at.isoformat()
        )
    )


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
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        plan=current_user.plan,
        daily_limit=current_user.daily_limit,
        daily_used=current_user.daily_used,
        api_key=current_user.api_key,
        created_at=current_user.created_at.isoformat()
    )