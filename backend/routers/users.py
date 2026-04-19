from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import uuid4

from ..db.session import get_db
from ..models.models import User, GeneratedMeme
from ..services.auth import get_current_user

router = APIRouter()


@router.get("/stats")
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get user statistics"""
    
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Get meme count
    meme_count_result = await db.execute(
        select(func.count(GeneratedMeme.id)).where(GeneratedMeme.user_id == current_user.id)
    )
    meme_count = meme_count_result.scalar() or 0
    
    # Get total shares
    shares_result = await db.execute(
        select(func.sum(GeneratedMeme.share_count)).where(GeneratedMeme.user_id == current_user.id)
    )
    total_shares = shares_result.scalar() or 0
    
    return {
        "total_memes": meme_count,
        "total_shares": total_shares,
        "plan": current_user.plan,
        "daily_limit": current_user.daily_limit,
        "daily_used": current_user.daily_used,
        "api_key_exists": bool(current_user.api_key)
    }


@router.post("/regenerate-api-key")
async def regenerate_api_key(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Regenerate API key for API plan users"""
    
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if current_user.plan != "api":
        raise HTTPException(status_code=403, detail="API key only available for API plan users")
    
    # Generate new API key
    new_api_key = f"mgpt_{uuid4().hex}"
    current_user.api_key = new_api_key
    
    await db.commit()
    await db.refresh(current_user)
    
    return {"api_key": new_api_key}