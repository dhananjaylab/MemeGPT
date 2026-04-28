import asyncio
import logging
import json
from typing import Dict, Any, Optional, List
from uuid import uuid4
from datetime import datetime, timezone
from arq import create_pool, ArqRedis
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.exc import SQLAlchemyError
from pathlib import Path

from core.config import settings
from db import session as db_session
from models.models import MemeJob, GeneratedMeme, User, MemeTemplate
from services.meme_ai import get_caption_generator, AIProvider
from services.compositor import overlay_text_on_image
from services.storage import upload_to_r2

from services.worker import get_arq_pool, close_arq_pool

# Configure logging
logger = logging.getLogger(__name__)

async def update_job_status(
    job_id: str, 
    status: str, 
    result_meme_ids: Optional[list] = None, 
    error_message: Optional[str] = None
) -> bool:
    """Update job status in database"""
    try:
        async with db_session.AsyncSessionLocal() as db:
            update_data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc)
            }
            
            if result_meme_ids is not None:
                update_data["result_meme_ids"] = result_meme_ids
            
            if error_message is not None:
                update_data["error_message"] = error_message
            
            await db.execute(
                update(MemeJob)
                .where(MemeJob.id == job_id)
                .values(**update_data)
            )
            await db.commit()
            return True
    except Exception as e:
        logger.error(f"Error updating job {job_id}: {e}")
        return False

async def get_template_by_id(db: AsyncSession, template_id: int) -> Optional[Dict[str, Any]]:
    """Get meme template from DB"""
    result = await db.execute(select(MemeTemplate).where(MemeTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if template:
        return {
            "id": template.id,
            "name": template.name,
            "file_path": template.file_path,
            "font_path": template.font_path,
            "text_color": template.text_color,
            "text_stroke": template.text_stroke,
            "text_coordinates_xy_wh": template.text_coordinates_xy_wh,
            "number_of_text_fields": template.number_of_text_fields
        }
    return None

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
    """Full pipeline: AI -> Compositor -> Storage -> DB"""
    logger.info(f"Processing job {job_id} with provider={ai_provider}, mode={generation_mode}")
    await update_job_status(job_id, "processing")
    
    try:
        # 1. Caption generation
        if generation_mode.lower() == "manual":
            if manual_template_id is None or not manual_captions:
                await update_job_status(
                    job_id,
                    "failed",
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
            provider = ai_provider.lower()
            if provider not in {AIProvider.OPENAI.value, AIProvider.GEMINI.value}:
                provider = AIProvider.OPENAI.value
            generator = await get_caption_generator(provider)
            captions = await generator(prompt)
        
        if not captions:
            await update_job_status(job_id, "failed", error_message=f"AI ({ai_provider}) failed to generate captions")
            return {"status": "failed"}

        meme_ids = []
        async with db_session.AsyncSessionLocal() as db:
            for ai_meme in captions:
                try:
                    template_id = int(ai_meme["meme_id"])
                    template = await get_template_by_id(db, template_id)
                    if not template:
                        logger.warning(f"Template {template_id} not found")
                        continue

                    # 2. Image Composition
                    image_path = overlay_text_on_image(template, ai_meme["meme_text"])
                    
                    # 3. Storage Upload
                    object_key = f"memes/{uuid4()}.png"
                    image_url = await upload_to_r2(image_path, object_key)
                    if not image_url:
                        # Fallback to local path (relative to static)
                        image_url = f"/static/output/{image_path.name}"

                    # 4. Save to DB
                    meme_id = str(uuid4())
                    new_meme = GeneratedMeme(
                        id=meme_id,
                        user_id=user_id,
                        prompt=prompt,
                        template_name=template["name"],
                        template_id=template_id,
                        meme_text=ai_meme["meme_text"],
                        image_url=image_url,
                        is_public=True
                    )
                    db.add(new_meme)
                    meme_ids.append(meme_id)
                except Exception as e:
                    logger.error(f"Error in single meme processing: {e}")
            await db.commit()

        if not meme_ids:
            await update_job_status(job_id, "failed", error_message="Failed to generate any memes")
            return {"status": "failed"}

        await update_job_status(job_id, "completed", result_meme_ids=meme_ids)
        return {"status": "completed", "meme_ids": meme_ids}

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        await update_job_status(job_id, "failed", error_message=str(e))
        return {"status": "failed"}

class WorkerSettings:
    functions = [process_meme_generation]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    queue_name = settings.arq_queue_name
    
    @staticmethod
    async def on_startup(ctx):
        logger.info("Worker starting up")
        db_session._init_engine()
        logger.info("Database engine initialized in worker")
        
    @staticmethod
    async def on_shutdown(ctx):
        logger.info("Worker shutting down")
        await close_arq_pool()