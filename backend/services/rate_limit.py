"""
Rate limiting — sliding window per IP / user, backed by Redis.
Tiers:
  anonymous  → 5  generations / day
  free user  → 5  generations / day
  pro user   → 500 generations / day
  api key    → 500 generations / day (or custom)
"""
import time
import hashlib
from typing import Tuple, Optional

import redis.asyncio as aioredis
from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.config import settings
from models.models import User

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def _window_key(identifier: str) -> str:
    """Build a deterministic Redis key for the sliding window."""
    safe = hashlib.md5(identifier.encode()).hexdigest()[:16]
    return f"rl:sliding:{safe}"


async def check_rate_limit(
    identifier: str,
    limit: int,
    window_seconds: int = 86400,  # 24 hour window
) -> Tuple[int, int]:
    """
    Increment the counter and check against limit using a sliding window.
    Returns (current_count, remaining).
    Raises HTTP 429 if over limit.
    """
    redis = await get_redis()
    key = _window_key(identifier)
    now = time.time()
    cutoff = now - window_seconds

    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, 0, cutoff)
    member = f"{now}:{hashlib.md5(str(now).encode()).hexdigest()[:8]}"
    pipe.zadd(key, {member: now})
    pipe.zcard(key)
    pipe.expire(key, window_seconds + 3600)
    
    results = await pipe.execute()
    
    current_count = results[2]
    remaining = max(0, limit - current_count)

    if current_count > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. You can generate {limit} memes per day on this plan.",
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(now + window_seconds)),
                "Retry-After": str(window_seconds),
            },
        )

    return current_count, remaining


async def rate_limit_request(
    request: Request, 
    user: Optional[User] = None,
    user_id: Optional[str] = None,
    db: Optional[AsyncSession] = None,
    custom_limit: Optional[int] = None,
) -> Tuple[int, int]:
    """
    Determine the rate limit identifier and ceiling for a request,
    then check + increment.
    """
    limit = settings.rate_limit_free
    identifier = ""

    # Case 1: Full user object provided (Router level)
    if user is not None:
        limit = user.daily_limit or settings.rate_limit_free
        identifier = f"user:{user.id}"
    
    # Case 2: User ID provided but no User object (Middleware level)
    elif user_id is not None:
        identifier = f"user:{user_id}"
        if db:
            result = await db.execute(select(User).where(User.id == user_id))
            db_user = result.scalar_one_or_none()
            if db_user:
                limit = db_user.daily_limit or settings.rate_limit_free
        else:
            # Fallback if no DB session in middleware
            # This could be improved by caching user tiers in Redis
            limit = settings.rate_limit_free

    # Case 3: API Key check (Middleware level)
    elif request.headers.get("X-API-Key"):
        api_key = request.headers.get("X-API-Key")
        identifier = f"api:{hashlib.md5(api_key.encode()).hexdigest()[:16]}"
        if db:
            result = await db.execute(select(User).where(User.api_key == api_key))
            db_user = result.scalar_one_or_none()
            if db_user:
                limit = db_user.daily_limit or settings.rate_limit_api
        else:
            limit = settings.rate_limit_api

    # Case 4: Anonymous — use IP
    else:
        ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        identifier = f"ip:{ip}"
        limit = settings.rate_limit_free

    if custom_limit is not None:
        limit = custom_limit

    return await check_rate_limit(identifier, limit)