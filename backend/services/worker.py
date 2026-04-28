import logging
from typing import Dict, Any, Optional, List
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, delete, and_, func
from arq import create_pool, ArqRedis
from arq.connections import RedisSettings

from core.config import settings
from db import session as db_session
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
            logger.info(f"Creating ARQ pool with settings: {redis_settings}")
            logger.info(f"create_pool function: {create_pool}")
            _arq_pool = await create_pool(
                redis_settings,
                default_queue_name=settings.arq_queue_name
            )
            logger.info(f"ARQ Redis pool created successfully on queue {settings.arq_queue_name}: {_arq_pool}")
            logger.info(f"Pool type: {type(_arq_pool)}")
        except Exception as e:
            logger.error(f"Failed to create ARQ Redis pool: {e}", exc_info=True)
            raise
    
    return _arq_pool

async def close_arq_pool():
    """Close ARQ Redis pool"""
    global _arq_pool
    
    if _arq_pool:
        await _arq_pool.aclose()
        _arq_pool = None
        logger.info("ARQ Redis pool closed")

async def enqueue_meme_generation(
    prompt: str,
    user: Optional[User] = None,
    ai_provider: str = "openai",
    generation_mode: str = "auto",
    manual_template_id: Optional[int] = None,
    manual_captions: Optional[List[str]] = None,
) -> str:
    """Enqueue a meme generation job"""
    print("[DEBUG] === enqueue_meme_generation CALLED ===")
    job_id = str(uuid4())
    user_id = user.id if user else None
    
    print(f"[DEBUG] job_id={job_id}, user_id={user_id}")
    logger.info(
        f"Enqueueing meme generation job {job_id} for user {user_id} with "
        f"provider={ai_provider} mode={generation_mode}"
    )
    
    try:
        print("[DEBUG] About to create job in database...")
        # Ensure database engine is initialized
        db_session._init_engine()
        print("[DEBUG] Database engine initialized")
        # Create job record in database
        async with db_session.AsyncSessionLocal() as db:
            print("[DEBUG] Got database session")
            job = MemeJob(
                id=job_id,
                user_id=user_id,
                prompt=prompt,
                ai_provider=ai_provider,
                generation_mode=generation_mode,
                manual_template_id=manual_template_id,
                manual_captions=manual_captions,
                status="pending"
            )
            print("[DEBUG] Created MemeJob object")
            db.add(job)
            print("[DEBUG] Added job to session")
            await db.commit()
            print(f"[DEBUG] Job {job_id} committed to database")
            logger.info(f"Job {job_id} created in database")
        
        print("[DEBUG] Database operations complete, now enqueueing with ARQ...")
        # Enqueue job with ARQ
        try:
            print(f"[DEBUG] About to get ARQ pool...")
            pool = await get_arq_pool()
            print(f"[DEBUG] Got ARQ pool: {pool}")
            print(f"[DEBUG] Pool type: {type(pool)}")
            print(f"[DEBUG] Has enqueue_job: {hasattr(pool, 'enqueue_job')}")
            
            if pool is None:
                raise Exception("ARQ pool is None")
            
            # Check if enqueue_job method exists and is callable
            enqueue_method = getattr(pool, 'enqueue_job', None)
            print(f"[DEBUG] enqueue_job method: {enqueue_method}")
            print(f"[DEBUG] enqueue_job callable: {callable(enqueue_method)}")
            
            if enqueue_method is None:
                raise Exception("enqueue_job method not found on pool")
            
            print(f"[DEBUG] About to call enqueue_job...")
            # Use function name string for ARQ enqueue_job
            result = await pool.enqueue_job(
                'process_meme_generation',
                job_id,
                prompt,
                ai_provider,
                generation_mode,
                manual_template_id,
                manual_captions,
                _job_id=job_id,
                _queue_name=settings.arq_queue_name,
            )
            
            print(f"[DEBUG] Job {job_id} enqueued successfully with result: {result}")
            logger.info(f"Job {job_id} enqueued successfully with result: {result}")
            return job_id
        except Exception as e:
            print(f"[DEBUG] Exception caught: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            logger.error(f"Failed to enqueue job {job_id}: {e}", exc_info=True)
            raise
        
    except Exception as e:
        logger.error(f"Error enqueueing job {job_id}: {e}")
        raise Exception(f"Failed to enqueue job: {str(e)}")

async def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job status and results"""
    try:
        async with db_session.AsyncSessionLocal() as db:
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
        
        async with db_session.AsyncSessionLocal() as db:
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
    # Safely get the ARQ pool
    try:
        pool = await get_arq_pool()
        if pool is None:
            return {"error": "ARQ pool not initialized", "queue_length": 0}
        
        # ARQ uses the queue name as the key for the zset
        queue_length = await pool.zcard(settings.arq_queue_name)
    except Exception as e:
        logger.warning(f"Could not get ARQ queue stats: {e}")
        queue_length = 0
        
        # Get database stats
        try:
            async with db_session.AsyncSessionLocal() as db:
                pending = await db.scalar(select(func.count(MemeJob.id)).where(MemeJob.status == "pending"))
                processing = await db.scalar(select(func.count(MemeJob.id)).where(MemeJob.status == "processing"))
                completed = await db.scalar(select(func.count(MemeJob.id)).where(MemeJob.status == "completed"))
                failed = await db.scalar(select(func.count(MemeJob.id)).where(MemeJob.status == "failed"))
        except Exception as e:
            logger.warning(f"Could not get database stats: {e}")
            pending = processing = completed = failed = 0
        
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
