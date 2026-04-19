from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from datetime import datetime, timedelta

from ..db.session import get_db
from ..models.models import GeneratedMeme
from ..routers.memes import MemeResponse

router = APIRouter()


@router.get("/topics")
async def get_trending_topics(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """Get trending topics based on recent meme prompts"""
    
    # Get memes from last 7 days
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    # This is a simplified trending algorithm
    # In production, you might want more sophisticated text analysis
    result = await db.execute(
        select(GeneratedMeme.template_name, func.count(GeneratedMeme.id).label('count'))
        .where(GeneratedMeme.created_at >= week_ago)
        .where(GeneratedMeme.is_public == True)
        .group_by(GeneratedMeme.template_name)
        .order_by(desc('count'))
        .limit(limit)
    )
    
    trending_templates = result.all()
    
    return [
        {
            "template_name": template_name,
            "usage_count": count
        }
        for template_name, count in trending_templates
    ]


@router.get("/memes", response_model=List[MemeResponse])
async def get_trending_memes(
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Get trending memes based on share count and recency"""
    
    # Simple trending algorithm: high share count + recent
    # You might want to implement a more sophisticated algorithm
    result = await db.execute(
        select(GeneratedMeme)
        .where(GeneratedMeme.is_public == True)
        .order_by(desc(GeneratedMeme.share_count), desc(GeneratedMeme.created_at))
        .limit(limit)
    )
    
    memes = result.scalars().all()
    
    return [
        MemeResponse(
            id=meme.id,
            template_name=meme.template_name,
            template_id=meme.template_id,
            meme_text=meme.meme_text,
            image_url=meme.image_url,
            created_at=meme.created_at.isoformat(),
            share_count=meme.share_count
        )
        for meme in memes
    ]