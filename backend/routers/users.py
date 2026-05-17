from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from db.session import get_db
from models.models import User, GeneratedMeme
from services.auth import get_current_user
from services.api_key import generate_api_key

router = APIRouter()

@router.get("/me")
async def get_user_me(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get current user profile"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.email.split("@")[0],
        "avatar_url": None,
        "plan": current_user.plan,
        "daily_limit": current_user.daily_limit,
        "daily_used": current_user.daily_used,
        # Never return the full key or its hash — only the display prefix
        "api_key_prefix": current_user.api_key_prefix,
        "has_api_key": bool(current_user.api_key),
        "created_at": current_user.created_at.isoformat() if current_user.created_at else "",
        "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else "",
    }


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
@router.post("/rotate-key")
async def regenerate_api_key(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Regenerate API key for API plan users.

    The plaintext key is returned in this response **exactly once**.
    Only the SHA-256 hash is stored in the database.  The user must
    copy and save the key immediately — it cannot be retrieved later.
    """
    
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if current_user.plan != "api":
        raise HTTPException(status_code=403, detail="API key only available for API plan users")
    
    # Generate new key: plaintext (show once), hash (store), prefix (display)
    plaintext_key, key_hash, key_prefix = generate_api_key()
    current_user.api_key = key_hash
    current_user.api_key_prefix = key_prefix
    
    await db.commit()
    await db.refresh(current_user)
    
    # Return the plaintext key exactly once — it is never stored or retrievable
    return {
        "api_key": plaintext_key,
        "api_key_prefix": key_prefix,
        "warning": "Save this key now. It cannot be retrieved again.",
    }