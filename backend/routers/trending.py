from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from datetime import datetime, timedelta

from db.session import get_db
from models.models import GeneratedMeme
from routers.memes import MemeResponse

import json
from services.rate_limit import get_redis

router = APIRouter()

# Phase 2 honesty fix: this was previously labeled "source": "mock" in the
# API response but presented to users via TrendingTopics.tsx and the
# Footer's "Reddit"/"Discord Bot"/"Slack App" links as if it were a live
# integration. It is curated, hand-picked seed data, not a live feed — the
# response now says "curated" and the frontend surfaces that honestly
# instead of implying real-time Reddit/Twitter scraping that doesn't exist.
# Wiring this up to the real Reddit/News APIs (praw + newsapi-python are
# already in requirements.txt) is a good Phase 3 candidate once you have
# API credentials provisioned for them.
CURATED_TRENDING_TOPICS = [
    {"name": "Monday Motivation", "source": "Twitter", "count": 1250, "trend_direction": "up"},
    {"name": "AI Generated Memes", "source": "Reddit", "count": 892, "trend_direction": "up"},
    {"name": "Office Vibes", "source": "Twitter", "count": 756, "trend_direction": "steady"},
    {"name": "Weekend Plans", "source": "Reddit", "count": 645, "trend_direction": "up"},
    {"name": "Tech Fails", "source": "Hacker News", "count": 521, "trend_direction": "down"},
    {"name": "Motivation Quotes", "source": "Twitter", "count": 412, "trend_direction": "steady"},
    {"name": "Funny Cats", "source": "Reddit", "count": 389, "trend_direction": "up"},
    {"name": "Programming Humor", "source": "GitHub Trending", "count": 356, "trend_direction": "up"},
]


@router.get("/topics")
async def get_trending_topics(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """Get curated topic suggestions for meme generation inspiration.

    NOTE: this is hand-curated seed data, not a live Reddit/Twitter/News
    feed — see CURATED_TRENDING_TOPICS above. The "source" field on each
    topic indicates where that *kind* of content typically comes from, not
    that this endpoint scraped it live.
    """
    
    redis = await get_redis()
    cache_key = f"trending:topics:{limit}"
    
    # Try to get from cache
    cached_data = await redis.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    
    response_data = {
        "topics": CURATED_TRENDING_TOPICS[:limit],
        "source": "curated",
        "updated_at": datetime.utcnow().isoformat(),
        "refresh_interval_seconds": 3600
    }
    
    # Cache for 1 hour
    await redis.setex(cache_key, 3600, json.dumps(response_data))
    
    return response_data


@router.get("/topics/real")
async def get_trending_topics_from_db(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """Get trending topics based on recent meme prompts from database.

    Unlike /topics above, this one is genuinely live — it's derived from
    your own users' actual recent prompts, not external curated seed data.
    """
    
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
    
    topics = []
    for template_name, count in trending_templates:
        topics.append({
            "name": template_name,
            "source": "MemeGPT",
            "count": count,
            "trend_direction": "up"
        })
    
    return {
        "topics": topics,
        "source": "database",
        "updated_at": datetime.utcnow().isoformat(),
        "refresh_interval_seconds": 600
    }


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
            prompt=meme.prompt,
            meme_text=meme.meme_text,
            image_url=meme.image_url,
            created_at=meme.created_at.isoformat(),
            share_count=meme.share_count,
            like_count=meme.like_count,
            is_public=meme.is_public,
        )
        for meme in memes
    ]
