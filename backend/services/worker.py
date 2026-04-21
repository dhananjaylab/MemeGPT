import logging
from typing import Dict, Any, Optional, List
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, delete, and_, func
from arq import create_pool, ArqRedis
from arq.connections import RedisSettings

from core.config import settings
from db.session import AsyncSessionLocal
from models.models import MemeJob, GeneratedMeme, User

# Configure logging
logger = logging.getLogger(__name__)

# Redis settings for ARQ
redis_settings = RedisSettings.from_dsn(settings.redis_url)

# Global ARQ pool for reuse
_arq_pool: Optional[ArqRedis] = None

async def get_arq_pool() -> ArqRedis:
    """Get ARQ Redis pool with connection reuse"""
    global _arq_pool
    
    if _arq_pool is None:
        try:
            _arq_pool = await create_pool(redis_settings)
            logger.info("ARQ Redis pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create ARQ Redis pool: {e}")
            raise
    
    return _arq_pool

async def close_arq_pool():
    """Close ARQ Redis pool"""
    global _arq_pool
    
    if _arq_pool:
        await _arq_pool.close()
        _arq_pool = None
        logger.info("ARQ Redis pool closed")

async def enqueue_meme_generation(prompt: str, user: Optional[User] = None, ai_provider: str = "openai") -> str:
    """Enqueue a meme generation job"""
    job_id = str(uuid4())
    user_id = user.id if user else None
    
    logger.info(f"Enqueueing meme generation job {job_id} for user {user_id} with provider {ai_provider}")
    
    try:
        # Create job record in database
        async with AsyncSessionLocal() as db:
            job = MemeJob(
                id=job_id,
                user_id=user_id,
                prompt=prompt,
                status="pending"
            )
            db.add(job)
            await db.commit()
            logger.info(f"Job {job_id} created in database")
        
        # Enqueue job with ARQ
        pool = await get_arq_pool()
        await pool.enqueue_job(
            'process_meme_generation',
            job_id,
            user_id,
            prompt,
            ai_provider,
            _job_timeout=300,  # 5 minutes timeout
        )
        
        logger.info(f"Job {job_id} enqueued successfully")
        return job_id
        
    except Exception as e:
        logger.error(f"Error enqueueing job {job_id}: {e}")
        raise Exception(f"Failed to enqueue job: {str(e)}")

async def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job status and results"""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(MemeJob).where(MemeJob.id == job_id))
            job = result.scalar_one_or_none()
            
            if not job:
                return None
            
            job_data = {
                "id": job.id,
                "status": job.status,
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat()
            }
            
            if job.status == "completed" and job.result_meme_ids:
                meme_result = await db.execute(
                    select(GeneratedMeme).where(GeneratedMeme.id.in_(job.result_meme_ids))
                )
                memes = meme_result.scalars().all()
                
                job_data["memes"] = [
                    {
                        "id": meme.id,
                        "template_name": meme.template_name,
                        "template_id": meme.template_id,
                        "meme_text": meme.meme_text,
                        "image_url": meme.image_url,
                        "created_at": meme.created_at.isoformat()
                    }
                    for meme in memes
                ]
            elif job.status == "failed":
                job_data["error"] = job.error_message or "Unknown error"
            
            return job_data
    except Exception as e:
        logger.error(f"Error retrieving job {job_id}: {e}")
        return None

async def cleanup_old_jobs(days_old: int = 7) -> int:
    """Clean up old completed/failed jobs"""
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                delete(MemeJob).where(
                    and_(
                        MemeJob.updated_at < cutoff_date,
                        MemeJob.status.in_(["completed", "failed"])
                    )
                )
            )
            deleted_count = result.rowcount
            await db.commit()
            return deleted_count
    except Exception as e:
        logger.error(f"Error cleaning up old jobs: {e}")
        return 0

async def get_queue_stats() -> Dict[str, Any]:
    """Get ARQ queue statistics"""
    try:
        pool = await get_arq_pool()
        queue_length = await pool.llen('arq:queue')
        
        async with AsyncSessionLocal() as db:
            pending = await db.scalar(select(func.count(MemeJob.id)).where(MemeJob.status == "pending"))
            processing = await db.scalar(select(func.count(MemeJob.id)).where(MemeJob.status == "processing"))
            completed = await db.scalar(select(func.count(MemeJob.id)).where(MemeJob.status == "completed"))
            failed = await db.scalar(select(func.count(MemeJob.id)).where(MemeJob.status == "failed"))
        
        return {
            "queue_length": queue_length,
            "pending_jobs": pending or 0,
            "processing_jobs": processing or 0,
            "completed_jobs": completed or 0,
            "failed_jobs": failed or 0,
            "total_jobs": (pending or 0) + (processing or 0) + (completed or 0) + (failed or 0)
        }
    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        return {"error": str(e)}
