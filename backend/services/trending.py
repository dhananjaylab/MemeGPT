"""
Trending meme leaderboard — Redis Sorted Sets.

Uses ZADD / ZREVRANGE to maintain a real-time trending ranking so the
``GET /memes?sort=trending`` endpoint never hits a full table scan.

The sorted-set score is: ``share_count * 0.7 + like_count * 0.3``
(the same formula previously computed inline in the SQL ORDER BY).

Two update paths:
  1. **Inline** — called from share / like endpoints after incrementing
     counters.  A single ZADD is O(log N).
  2. **Bulk rebuild** — ``rebuild_trending_leaderboard()`` can be called
     from a periodic background task (e.g. every 5 min) to reconcile
     the sorted set with the database.

Graceful degradation: every public function catches Redis errors so a
Redis outage never breaks the meme endpoints — the router falls back to
a simple indexed SQL query on the ``trending_score`` column.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import redis.asyncio as aioredis

from core.config import settings

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

TRENDING_KEY = "trending:memes"
TRENDING_MAX_SIZE = 5_000  # trim to top-N after each update

# ── Redis singleton (shared with cache.py) ───────────────────────────────────

_redis: Optional[aioredis.Redis] = None


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
    return _redis


# ── Score formula ────────────────────────────────────────────────────────────

def compute_trending_score(share_count: int, like_count: int) -> float:
    """Weighted trending formula — keep in sync with the SQL migration."""
    return (share_count or 0) * 0.7 + (like_count or 0) * 0.3


# ── Inline update (called from share / like endpoints) ───────────────────────

async def update_trending_score(
    meme_id: str,
    share_count: int,
    like_count: int,
) -> None:
    """Set *meme_id*'s score in the sorted set.  O(log N)."""
    try:
        r = await _get_redis()
        score = compute_trending_score(share_count, like_count)
        await r.zadd(TRENDING_KEY, {meme_id: score})
        # Periodically trim to keep memory bounded
        await r.zremrangebyrank(TRENDING_KEY, 0, -(TRENDING_MAX_SIZE + 1))
    except Exception as exc:
        logger.warning("Trending leaderboard update failed: %s", exc)


async def remove_from_trending(meme_id: str) -> None:
    """Remove a deleted meme from the leaderboard."""
    try:
        r = await _get_redis()
        await r.zrem(TRENDING_KEY, meme_id)
    except Exception as exc:
        logger.warning("Trending leaderboard remove failed: %s", exc)


# ── Read (called from router) ───────────────────────────────────────────────

async def get_trending_meme_ids(
    offset: int = 0,
    limit: int = 20,
) -> Optional[List[str]]:
    """Return the top trending meme IDs from Redis, or *None* on failure."""
    try:
        r = await _get_redis()
        # ZREVRANGE returns highest-score first
        ids: List[str] = await r.zrevrange(
            TRENDING_KEY, offset, offset + limit - 1,
        )
        return ids if ids else None
    except Exception as exc:
        logger.warning("Trending leaderboard read failed: %s", exc)
        return None


# ── Bulk rebuild (for periodic background tasks) ─────────────────────────────

async def rebuild_trending_leaderboard(
    meme_rows: List[Tuple[str, int, int]],
) -> int:
    """Re-populate the sorted set from a list of ``(id, share_count, like_count)``.

    Returns the number of entries written.
    """
    try:
        r = await _get_redis()
        pipe = r.pipeline()
        pipe.delete(TRENDING_KEY)
        mapping = {
            mid: compute_trending_score(sc, lc)
            for mid, sc, lc in meme_rows
        }
        if mapping:
            pipe.zadd(TRENDING_KEY, mapping)
        await pipe.execute()
        logger.info("Trending leaderboard rebuilt with %d entries", len(mapping))
        return len(mapping)
    except Exception as exc:
        logger.error("Trending leaderboard rebuild failed: %s", exc)
        return 0
