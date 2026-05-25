"""
Meme result caching service — Redis-backed.

Three cache layers:
  1. AI caption cache  — same prompt → same captions (1 h TTL)
  2. Meme image cache  — same template + texts → same image URL (24 h TTL)
  3. Template image cache — downloaded template bytes (6 h TTL)

All failures are soft: the generation pipeline simply skips the cache and
continues normally so a Redis outage never breaks meme creation.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis

from core.config import settings

logger = logging.getLogger(__name__)

# ── TTLs ────────────────────────────────────────────────────────────────────
CAPTION_TTL = 3_600          # 1 h  — AI output for a given prompt
MEME_URL_TTL = 86_400        # 24 h — final image URL for template+texts
TEMPLATE_IMG_TTL = 21_600    # 6 h  — raw bytes of a remote template image

# ── Singleton ────────────────────────────────────────────────────────────────
_redis: Optional[aioredis.Redis] = None


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(
            settings.redis_url,
            decode_responses=False,  # we handle encoding ourselves
            socket_connect_timeout=3,
            socket_timeout=3,
        )
    return _redis


# ── Key helpers ──────────────────────────────────────────────────────────────

def _h(value: str) -> str:
    """Return a 16-char hex digest of the given string."""
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def caption_key(prompt: str) -> str:
    return f"cap:{_h(prompt.lower().strip())}"


def meme_url_key(template_id: int, texts: List[str]) -> str:
    payload = f"{template_id}|{'|'.join(t.strip().lower() for t in texts)}"
    return f"meme:{_h(payload)}"


def template_img_key(url: str) -> str:
    return f"tpl:{_h(url)}"


# ── Caption cache ────────────────────────────────────────────────────────────

async def get_cached_captions(prompt: str) -> Optional[List[Dict[str, Any]]]:
    try:
        r = await _get_redis()
        raw = await r.get(caption_key(prompt))
        if raw:
            logger.debug("Caption cache HIT for prompt %r", prompt[:60])
            return json.loads(raw)
    except Exception as exc:
        logger.warning("Caption cache get failed: %s", exc)
    return None


async def set_cached_captions(
    prompt: str, captions: List[Dict[str, Any]]
) -> None:
    try:
        r = await _get_redis()
        await r.setex(caption_key(prompt), CAPTION_TTL, json.dumps(captions))
    except Exception as exc:
        logger.warning("Caption cache set failed: %s", exc)


# ── Meme URL cache ───────────────────────────────────────────────────────────

async def get_cached_meme_url(
    template_id: int, texts: List[str]
) -> Optional[str]:
    try:
        r = await _get_redis()
        raw = await r.get(meme_url_key(template_id, texts))
        if raw:
            logger.debug("Meme URL cache HIT for template %d", template_id)
            return raw.decode()
    except Exception as exc:
        logger.warning("Meme URL cache get failed: %s", exc)
    return None


async def set_cached_meme_url(
    template_id: int, texts: List[str], url: str
) -> None:
    try:
        r = await _get_redis()
        await r.setex(meme_url_key(template_id, texts), MEME_URL_TTL, url.encode())
    except Exception as exc:
        logger.warning("Meme URL cache set failed: %s", exc)


# ── Meme full metadata cache (eliminates DB query after cache hit) ────────────

async def get_cached_meme_metadata(
    template_id: int, texts: List[str]
) -> Optional[Dict[str, Any]]:
    """Return full meme metadata from cache (template_name, image_url, etc)."""
    try:
        r = await _get_redis()
        key = f"mem_meta:{meme_url_key(template_id, texts)[5:]}"  # mem_meta: prefix
        raw = await r.get(key)
        if raw:
            logger.debug("Meme metadata cache HIT for template %d", template_id)
            return json.loads(raw)
    except Exception as exc:
        logger.warning("Meme metadata cache get failed: %s", exc)
    return None


async def set_cached_meme_metadata(
    template_id: int, texts: List[str], metadata: Dict[str, Any]
) -> None:
    """Cache full meme metadata to eliminate DB query on cache hit."""
    try:
        r = await _get_redis()
        key = f"mem_meta:{meme_url_key(template_id, texts)[5:]}"  # mem_meta: prefix
        await r.setex(key, MEME_URL_TTL, json.dumps(metadata))
    except Exception as exc:
        logger.warning("Meme metadata cache set failed: %s", exc)


# ── Template image cache ─────────────────────────────────────────────────────

async def get_cached_template_image(url: str) -> Optional[bytes]:
    try:
        r = await _get_redis()
        data = await r.get(template_img_key(url))
        if data:
            logger.debug("Template image cache HIT for %s", url[:80])
            return data
    except Exception as exc:
        logger.warning("Template image cache get failed: %s", exc)
    return None


async def set_cached_template_image(url: str, image_bytes: bytes) -> None:
    try:
        r = await _get_redis()
        await r.setex(template_img_key(url), TEMPLATE_IMG_TTL, image_bytes)
    except Exception as exc:
        logger.warning("Template image cache set failed: %s", exc)


# ── Cache statistics (for the /health endpoint) ──────────────────────────────

async def get_cache_stats() -> Dict[str, Any]:
    try:
        r = await _get_redis()
        cap_keys = len(await r.keys("cap:*"))
        meme_keys = len(await r.keys("meme:*"))
        tpl_keys = len(await r.keys("tpl:*"))
        return {
            "caption_entries": cap_keys,
            "meme_url_entries": meme_keys,
            "template_image_entries": tpl_keys,
            "status": "ok",
        }
    except Exception as exc:
        return {"status": "unavailable", "error": str(exc)}
