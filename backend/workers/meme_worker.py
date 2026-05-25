"""
ARQ meme worker — processes generation jobs asynchronously.

v2 enhancements:
  • Caption cache: identical prompts skip the AI call
  • Image URL cache: identical template+texts skip image composition
  • Async compositor for remote (Gen-Z) template images
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4
from datetime import datetime, timezone

from arq import ArqRedis
from arq.connections import RedisSettings
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db import session as db_session
from models.models import GeneratedMeme, MemeJob, MemeTemplate
from services.cache import (
    get_cached_captions, set_cached_captions,
    get_cached_meme_url, set_cached_meme_url,
)
from services.compositor import overlay_text_on_image_async
from services.imgflip import imgflip_service
from services.meme_ai import get_caption_generator, AIProvider
from services.storage import upload_to_r2
from services.worker import close_arq_pool, get_arq_pool
from services.rate_limit import get_redis

logger = logging.getLogger(__name__)


# ── DB helpers ────────────────────────────────────────────────────────────────

async def update_job_status(
    job_id: str,
    status: str,
    result_meme_ids: Optional[List[str]] = None,
    error_message: Optional[str] = None,
) -> bool:
    try:
        async with db_session.AsyncSessionLocal() as db:
            data: Dict[str, Any] = {
                "status": status,
                "updated_at": datetime.now(timezone.utc),
            }
            if result_meme_ids is not None:
                data["result_meme_ids"] = result_meme_ids
            if error_message is not None:
                data["error_message"] = error_message

            await db.execute(update(MemeJob).where(MemeJob.id == job_id).values(**data))
            await db.commit()

            # Publish status to Redis pubsub for SSE streams
            try:
                redis = await get_redis()
                msg = {
                    "id": job_id,
                    "status": status,
                }
                if error_message:
                    msg["error"] = error_message
                await redis.publish(f"job_status:{job_id}", json.dumps(msg))
            except Exception as redis_exc:
                logger.error("Failed to publish job status to Redis: %s", redis_exc)

            return True
    except Exception as exc:
        logger.error("Failed to update job %s: %s", job_id, exc)
        return False


async def get_templates_by_ids(
    db: AsyncSession, template_ids: List[int]
) -> Dict[int, Dict[str, Any]]:
    """Batch-fetch all templates in a single query — avoids N sequential round-trips."""
    if not template_ids:
        return {}
    result = await db.execute(
        select(MemeTemplate).where(MemeTemplate.id.in_(template_ids))
    )
    templates = result.scalars().all()
    return {
        t.id: {
            "id": t.id,
            "name": t.name,
            "file_path": t.file_path,
            "font_path": t.font_path,
            "text_color": t.text_color,
            "text_stroke": t.text_stroke,
            "text_coordinates_xy_wh": t.text_coordinates_xy_wh,
            "number_of_text_fields": t.number_of_text_fields,
            "image_url": t.image_url,
            "source": t.source,
            "imgflip_id": t.imgflip_id,
        }
        for t in templates
    }


async def _resolve_image_url(template: Dict[str, Any], texts: List[str], job_id: str) -> Optional[str]:
    template_id = template["id"]
    cached_url = await get_cached_meme_url(template_id, texts)
    if cached_url:
        logger.info(
            "Meme URL cache HIT for template %d job %s",
            template_id, job_id,
        )
        return cached_url

    image_path = await overlay_text_on_image_async(template, texts)
    object_key = f"memes/{uuid4()}{image_path.suffix}"
    upload_result = await upload_to_r2(image_path, object_key, optimize=False, create_variants=False)
    image_url = upload_result.get("primary") if isinstance(upload_result, dict) else None

    if image_url:
        await set_cached_meme_url(template_id, texts, image_url)
    return image_url


# ── Core job handler ─────────────────────────────────────────────────────────

async def process_meme_generation(
    ctx: Dict[str, Any],
    job_id: str,
    user_id: Optional[str],
    prompt: str,
    ai_provider: str = "openai",
    generation_mode: str = "auto",
    manual_template_id: Optional[int] = None,
    manual_captions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    logger.info(
        "Processing job %s provider=%s mode=%s", job_id, ai_provider, generation_mode
    )
    # Fire-and-forget: don't await status update — start AI immediately
    asyncio.create_task(update_job_status(job_id, "processing"))

    try:
        # ── 1. Generate / retrieve captions ──────────────────────────────────
        if generation_mode.lower() == "manual":
            if manual_template_id is None or not manual_captions:
                await update_job_status(
                    job_id, "failed",
                    error_message="Manual mode requires template_id and captions",
                )
                return {"status": "failed"}
            captions = [
                {
                    "meme_id": int(manual_template_id),
                    "meme_name": "manual",
                    "meme_text": manual_captions,
                }
            ]
        else:
            # Check caption cache first
            cached_caps = await get_cached_captions(prompt)
            if cached_caps:
                logger.info("Caption cache HIT for job %s", job_id)
                captions = cached_caps
            else:
                provider = ai_provider.lower()
                if provider not in {AIProvider.OPENAI.value, AIProvider.GEMINI.value}:
                    provider = AIProvider.OPENAI.value
                generator = await get_caption_generator(provider)
                captions = await generator(prompt)

                if captions:
                    await set_cached_captions(prompt, captions)

        if not captions:
            await update_job_status(
                job_id, "failed",
                error_message=f"AI ({ai_provider}) failed to generate captions",
            )
            return {"status": "failed"}

        # ── 2. Compose meme images (fully parallel pipeline) ──────────────────
        # Each meme: resolve_image_url → db_save runs concurrently
        meme_ids: List[str] = []

        async with db_session.AsyncSessionLocal() as db:
            # Batch-fetch all templates in a single DB query
            template_id_list = []
            for ai_meme in captions:
                try:
                    template_id_list.append(int(ai_meme["meme_id"]))
                except (KeyError, ValueError, TypeError):
                    pass

            templates_map = await get_templates_by_ids(db, template_id_list)

            async def _compose_one_meme(
                ai_meme: Dict[str, Any],
            ) -> Optional[str]:
                """Resolve image URL for one meme and persist it; returns meme_id or None."""
                try:
                    template_id = int(ai_meme["meme_id"])
                    template = templates_map.get(template_id)
                    if not template:
                        logger.warning("Template %d not found — skipping", template_id)
                        return None

                    texts: List[str] = ai_meme["meme_text"]
                    image_url = await _resolve_image_url(template, texts, job_id)
                    if not image_url:
                        logger.error("Failed to resolve image URL for template %d job %s", template_id, job_id)
                        return None

                    meme_id = str(uuid4())
                    db.add(
                        GeneratedMeme(
                            id=meme_id,
                            user_id=user_id,
                            prompt=prompt,
                            template_name=template["name"],
                            template_id=template["id"],
                            meme_text=texts,
                            image_url=image_url,
                            is_public=True,
                        )
                    )
                    return meme_id

                except Exception as exc:
                    logger.error("Error composing meme for job %s: %s", job_id, exc, exc_info=True)
                    return None

            # Run all meme compositions concurrently
            results = await asyncio.gather(
                *[_compose_one_meme(m) for m in captions],
                return_exceptions=True,
            )
            meme_ids = [r for r in results if isinstance(r, str)]

            # Single commit for all memes
            await db.commit()

        if not meme_ids:
            await update_job_status(
                job_id, "failed",
                error_message="Failed to generate any memes",
            )
            return {"status": "failed"}

        await update_job_status(job_id, "completed", result_meme_ids=meme_ids)
        logger.info("Job %s completed with %d memes", job_id, len(meme_ids))
        return {"status": "completed", "meme_ids": meme_ids}

    except Exception as exc:
        logger.error("Job %s failed: %s", job_id, exc, exc_info=True)
        await update_job_status(job_id, "failed", error_message=str(exc))
        return {"status": "failed"}


# ── Worker settings ───────────────────────────────────────────────────────────

class WorkerSettings:
    functions = [process_meme_generation]
    redis_settings = RedisSettings.from_dsn(settings.arq_redis_url)
    queue_name = settings.arq_queue_name
    max_jobs = 20          # allow more concurrent jobs
    job_timeout = 120      # 2-minute hard cap per job

    @staticmethod
    async def on_startup(ctx: Dict[str, Any]) -> None:
        logger.info("Worker starting up")
        db_session._init_engine()
        logger.info("Database engine initialised in worker")

    @staticmethod
    async def on_shutdown(ctx: Dict[str, Any]) -> None:
        logger.info("Worker shutting down")
        await close_arq_pool()
