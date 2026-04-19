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
from functools import wraps
from typing import Callable

import redis.asyncio as aioredis
from fastapi import HTTPException, Request

from .config import settings

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def _window_key(identifier: str, window: str = "day") -> str:
    """Build a deterministic Redis key for the current time window."""
    if window == "day":
        slot = int(time.time()) // 86400        # resets at midnight UTC
    elif window == "hour":
        slot = int(time.time()) // 3600
    else:
        slot = int(time.time()) // 60

    safe = hashlib.md5(identifier.encode()).hexdigest()[:16]
    return f"rl:{window}:{safe}:{slot}"


async def check_rate_limit(
    identifier: str,
    limit: int,
    window: str = "day",
) -> tuple[int, int]:
    """
    Increment the counter and check against limit.
    Returns (current_count, remaining).
    Raises HTTP 429 if over limit.
    """
    redis = await get_redis()
    key = _window_key(identifier, window)

    pipe = redis.pipeline()
    pipe.incr(key)
    # TTL slightly longer than window so keys self-clean
    pipe.expire(key, 86400 + 3600 if window == "day" else 7200)
    results = await pipe.execute()

    current: int = results[0]
    remaining = max(0, limit - current)

    if current > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. You can generate {limit} memes per day on this plan.",
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str((_window_key_reset(window))),
                "Retry-After": str(_window_key_reset(window) - int(time.time())),
            },
        )

    return current, remaining


def _window_key_reset(window: str) -> int:
    """Unix timestamp when current window resets."""
    if window == "day":
        slot = int(time.time()) // 86400
        return (slot + 1) * 86400
    slot = int(time.time()) // 3600
    return (slot + 1) * 3600


async def rate_limit_request(request: Request, user=None) -> tuple[int, int]:
    """
    Determine the rate limit identifier and ceiling for a request,
    then check + increment. Call this at the top of generation endpoints.
    """
    if user is not None:
        # Authenticated — use user ID, apply plan-based limit
        limit = user.daily_limit  # set when user upgrades plan
        identifier = f"user:{user.id}"
    else:
        # Anonymous — use IP
        limit = settings.rate_limit_free
        ip = request.client.host if request.client else "unknown"
        # Trust X-Forwarded-For if behind a reverse proxy
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        identifier = f"ip:{ip}"

    return await check_rate_limit(identifier, limit)
