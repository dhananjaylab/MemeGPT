from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from db.session import get_db
from models.models import GeneratedMeme, User
from services.auth import get_current_user_optional
from services.rate_limit import rate_limit_request
from workers.meme_worker import enqueue_meme_generation

router = APIRouter()


class GenerateMemeRequest(BaseModel):
    prompt: str


class GenerateMemeResponse(BaseModel):
    job_id: str
    remaining_generations: int


class MemeResponse(BaseModel):
    id: str
    template_name: str
    template_id: int
    meme_text: List[str]
    image_url: str
    created_at: str
    share_count: int
    like_count: int


@router.post("/generate", response_model=GenerateMemeResponse)
async def generate_meme(
    request: Request,
    body: GenerateMemeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Generate memes from user prompt (async with job queue)"""
    
    # Rate limit check is now handled by middleware
    remaining = getattr(request.state, "rate_limit_remaining", 0)
    
    # Validate prompt
    if not body.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    
    if len(body.prompt) > 1000:
        raise HTTPException(status_code=400, detail="Prompt too long (max 1000 characters)")
    
    # Enqueue meme generation job
    job_id = await enqueue_meme_generation(body.prompt, current_user)
    
    return GenerateMemeResponse(
        job_id=job_id,
        remaining_generations=remaining
    )


@router.get("/public", response_model=List[MemeResponse])
async def get_public_memes(
    page: int = 1,
    limit: int = 20,
    sort: str = "recent",  # "recent", "top", "trending"
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get public memes for gallery"""
    
    # Validate pagination
    if page < 1:
        page = 1
    if limit > 100:
        limit = 100
    
    offset = (page - 1) * limit
    
    # Build query
    query = select(GeneratedMeme).where(GeneratedMeme.is_public == True)
    
    # Add search filter
    if search:
        search_term = f"%{search}%"
        query = query.where(
            GeneratedMeme.prompt.ilike(search_term) |
            GeneratedMeme.template_name.ilike(search_term)
        )
    
    # Add sorting
    if sort == "top":
        query = query.order_by(desc(GeneratedMeme.share_count))
    elif sort == "trending":
        # Simple trending: high share count + recent
        query = query.order_by(
            desc(GeneratedMeme.share_count * 0.7 + GeneratedMeme.created_at.timestamp() * 0.3)
        )
    else:  # recent
        query = query.order_by(desc(GeneratedMeme.created_at))
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    memes = result.scalars().all()
    
    return [
        MemeResponse(
            id=meme.id,
            template_name=meme.template_name,
            template_id=meme.template_id,
            meme_text=meme.meme_text,
            image_url=meme.image_url,
            created_at=meme.created_at.isoformat(),
            share_count=meme.share_count,
            like_count=meme.like_count
        )
        for meme in memes
    ]


@router.get("/my", response_model=List[MemeResponse])
async def get_my_memes(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get current user's memes"""
    
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Validate pagination
    if page < 1:
        page = 1
    if limit > 100:
        limit = 100
    
    offset = (page - 1) * limit
    
    # Get user's memes
    query = (
        select(GeneratedMeme)
        .where(GeneratedMeme.user_id == current_user.id)
        .order_by(desc(GeneratedMeme.created_at))
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(query)
    memes = result.scalars().all()
    
    return [
        MemeResponse(
            id=meme.id,
            template_name=meme.template_name,
            template_id=meme.template_id,
            meme_text=meme.meme_text,
            image_url=meme.image_url,
            created_at=meme.created_at.isoformat(),
            share_count=meme.share_count,
            like_count=meme.like_count
        )
        for meme in memes
    ]


@router.get("/{meme_id}", response_model=MemeResponse)
async def get_meme(
    meme_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get specific meme by ID"""
    
    result = await db.execute(select(GeneratedMeme).where(GeneratedMeme.id == meme_id))
    meme = result.scalar_one_or_none()
    
    if not meme:
        raise HTTPException(status_code=404, detail="Meme not found")
    
    if not meme.is_public:
        raise HTTPException(status_code=404, detail="Meme not found")
    
    return MemeResponse(
        id=meme.id,
        template_name=meme.template_name,
        template_id=meme.template_id,
        meme_text=meme.meme_text,
        image_url=meme.image_url,
        created_at=meme.created_at.isoformat(),
        share_count=meme.share_count,
        like_count=meme.like_count
    )


@router.post("/{meme_id}/share")
async def share_meme(
    meme_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Increment share count for a meme"""
    
    result = await db.execute(select(GeneratedMeme).where(GeneratedMeme.id == meme_id))
    meme = result.scalar_one_or_none()
    
    if not meme:
        raise HTTPException(status_code=404, detail="Meme not found")
    
    if not meme.is_public:
        raise HTTPException(status_code=404, detail="Meme not found")
    
    # Increment share count
    meme.share_count += 1
    await db.commit()
    
    return {"message": "Share count updated", "share_count": meme.share_count}


@router.post("/{meme_id}/like")
async def like_meme(
    meme_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Increment like count for a meme"""
    
    result = await db.execute(select(GeneratedMeme).where(GeneratedMeme.id == meme_id))
    meme = result.scalar_one_or_none()
    
    if not meme:
        raise HTTPException(status_code=404, detail="Meme not found")
    
    # Increment like count
    meme.like_count += 1
    await db.commit()
    
    return {"message": "Liked", "liked": True, "like_count": meme.like_count}


@router.delete("/{meme_id}")
async def delete_meme(
    meme_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Delete a meme (only by owner)"""
    
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    result = await db.execute(select(GeneratedMeme).where(GeneratedMeme.id == meme_id))
    meme = result.scalar_one_or_none()
    
    if not meme:
        raise HTTPException(status_code=404, detail="Meme not found")
    
    if meme.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this meme")
    
    await db.delete(meme)
    await db.commit()
    
    return {"message": "Meme deleted successfully"}