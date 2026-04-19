import asyncio
import logging
from typing import Dict, Any, Optional
from uuid import uuid4
from datetime import datetime, timezone
from arq import create_pool, ArqRedis
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from ..core.config import settings
from ..db.session import AsyncSessionLocal
from ..models.models import MemeJob, GeneratedMeme, User
from .meme_generation import generate_memes

# Configure logging
logging.basicConfig(level=logging.INFO)
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


async def update_job_status(
    job_id: str, 
    status: str, 
    result_meme_ids: Optional[list] = None, 
    error_message: Optional[str] = None
) -> bool:
    """Update job status in database with error handling"""
    try:
        async with AsyncSessionLocal() as db:
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
            logger.info(f"Job {job_id} status updated to {status}")
            return True
            
    except SQLAlchemyError as e:
        logger.error(f"Database error updating job {job_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error updating job {job_id}: {e}")
        return False
async def process_meme_generation(ctx: Dict[str, Any], job_id: str, user_id: Optional[str], prompt: str) -> Dict[str, Any]:
    """ARQ worker function to process meme generation with improved error handling"""
    logger.info(f"Starting meme generation job {job_id} for prompt: {prompt[:50]}...")
    
    try:
        # Update job status to processing
        await update_job_status(job_id, "processing")
        
        # Validate inputs
        if not prompt or not prompt.strip():
            error_msg = "Empty or invalid prompt provided"
            logger.error(f"Job {job_id}: {error_msg}")
            await update_job_status(job_id, "failed", error_message=error_msg)
            return {"status": "failed", "error": error_msg}
        
        if len(prompt) > 1000:
            error_msg = "Prompt too long (max 1000 characters)"
            logger.error(f"Job {job_id}: {error_msg}")
            await update_job_status(job_id, "failed", error_message=error_msg)
            return {"status": "failed", "error": error_msg}
        
        # Generate memes
        logger.info(f"Job {job_id}: Calling meme generation service")
        generated_memes = await generate_memes(prompt)
        
        if not generated_memes:
            error_msg = "Failed to generate memes - no output from generation service"
            logger.error(f"Job {job_id}: {error_msg}")
            await update_job_status(job_id, "failed", error_message=error_msg)
            return {"status": "failed", "error": error_msg}
        
        logger.info(f"Job {job_id}: Generated {len(generated_memes)} memes")
        
        # Save generated memes to database
        meme_ids = []
        async with AsyncSessionLocal() as db:
            try:
                for meme_data in generated_memes:
                    meme = GeneratedMeme(
                        id=meme_data["id"],
                        user_id=user_id,
                        prompt=prompt,
                        template_name=meme_data["template_name"],
                        template_id=meme_data["template_id"],
                        meme_text=meme_data["meme_text"],
                        image_url=meme_data["image_url"],
                        is_public=True
                    )
                    db.add(meme)
                    meme_ids.append(meme.id)
                
                await db.commit()
                logger.info(f"Job {job_id}: Saved {len(meme_ids)} memes to database")
                
            except SQLAlchemyError as e:
                await db.rollback()
                error_msg = f"Database error saving memes: {str(e)}"
                logger.error(f"Job {job_id}: {error_msg}")
                await update_job_status(job_id, "failed", error_message=error_msg)
                return {"status": "failed", "error": error_msg}
        
        # Update job status to completed
        await update_job_status(job_id, "completed", result_meme_ids=meme_ids)
        
        logger.info(f"Job {job_id}: Completed successfully")
        return {
            "status": "completed",
            "meme_ids": meme_ids,
            "memes": generated_memes
        }
        
    except Exception as e:
        error_msg = f"Unexpected error in meme generation: {str(e)}"
        logger.error(f"Job {job_id}: {error_msg}", exc_info=True)
        await update_job_status(job_id, "failed", error_message=error_msg)
        return {"status": "failed", "error": error_msg}


async def enqueue_meme_generation(prompt: str, user: Optional[User] = None) -> str:
    """Enqueue a meme generation job with improved error handling"""
    job_id = str(uuid4())
    user_id = user.id if user else None
    
    logger.info(f"Enqueueing meme generation job {job_id} for user {user_id}")
    
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
            _job_timeout=300,  # 5 minutes timeout
            _defer_until=None,  # Process immediately
        )
        
        logger.info(f"Job {job_id} enqueued successfully")
        return job_id
        
    except SQLAlchemyError as e:
        logger.error(f"Database error creating job {job_id}: {e}")
        raise Exception(f"Failed to create job in database: {str(e)}")
    except Exception as e:
        logger.error(f"Error enqueueing job {job_id}: {e}")
        # Try to clean up database record if it was created
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(MemeJob)
                    .where(MemeJob.id == job_id)
                    .values(status="failed", error_message=f"Failed to enqueue: {str(e)}")
                )
                await db.commit()
        except Exception:
            pass  # Ignore cleanup errors
        raise Exception(f"Failed to enqueue job: {str(e)}")


async def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job status and results with improved error handling"""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(MemeJob).where(MemeJob.id == job_id))
            job = result.scalar_one_or_none()
            
            if not job:
                logger.warning(f"Job {job_id} not found")
                return None
            
            job_data = {
                "id": job.id,
                "status": job.status,
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat()
            }
            
            if job.status == "completed" and job.result_meme_ids:
                # Get the generated memes
                try:
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
                    logger.debug(f"Job {job_id}: Retrieved {len(memes)} memes")
                    
                except Exception as e:
                    logger.error(f"Error retrieving memes for job {job_id}: {e}")
                    job_data["memes"] = []
                    
            elif job.status == "failed":
                job_data["error"] = job.error_message or "Unknown error"
            
            return job_data
            
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving job {job_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error retrieving job {job_id}: {e}")
        return None


async def cleanup_old_jobs(days_old: int = 7) -> int:
    """Clean up old completed/failed jobs from database"""
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        
        async with AsyncSessionLocal() as db:
            # Delete old jobs
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
            
            logger.info(f"Cleaned up {deleted_count} old jobs")
            return deleted_count
            
    except Exception as e:
        logger.error(f"Error cleaning up old jobs: {e}")
        return 0


async def get_queue_stats() -> Dict[str, Any]:
    """Get ARQ queue statistics"""
    try:
        pool = await get_arq_pool()
        
        # Get queue length
        queue_length = await pool.llen('arq:queue')
        
        # Get job counts by status
        async with AsyncSessionLocal() as db:
            pending_jobs = await db.scalar(
                select(func.count(MemeJob.id)).where(MemeJob.status == "pending")
            )
            processing_jobs = await db.scalar(
                select(func.count(MemeJob.id)).where(MemeJob.status == "processing")
            )
            completed_jobs = await db.scalar(
                select(func.count(MemeJob.id)).where(MemeJob.status == "completed")
            )
            failed_jobs = await db.scalar(
                select(func.count(MemeJob.id)).where(MemeJob.status == "failed")
            )
        
        return {
            "queue_length": queue_length,
            "pending_jobs": pending_jobs or 0,
            "processing_jobs": processing_jobs or 0,
            "completed_jobs": completed_jobs or 0,
            "failed_jobs": failed_jobs or 0,
            "total_jobs": (pending_jobs or 0) + (processing_jobs or 0) + (completed_jobs or 0) + (failed_jobs or 0)
        }
        
    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        return {
            "queue_length": -1,
            "pending_jobs": -1,
            "processing_jobs": -1,
            "completed_jobs": -1,
            "failed_jobs": -1,
            "total_jobs": -1,
            "error": str(e)
        }


# ARQ worker configuration
class WorkerSettings:
    functions = [process_meme_generation]
    redis_settings = redis_settings
    max_jobs = 10
    job_timeout = 300  # 5 minutes
    keep_result = 3600  # Keep results for 1 hour
    queue_name = 'meme_generation'
    
    # Health check function
    health_check_interval = 60  # Check every minute
    
    # Logging configuration
    log_results = True
    
    # Retry configuration
    max_tries = 3
    retry_delay = 30  # 30 seconds between retries
    
    # Worker lifecycle hooks
    @staticmethod
    async def startup(ctx):
        """Worker startup hook"""
        logger.info("ARQ worker starting up...")
        
    @staticmethod
    async def shutdown(ctx):
        """Worker shutdown hook"""
        logger.info("ARQ worker shutting down...")
        await close_arq_pool()
        
    @staticmethod
    async def on_job_start(ctx):
        """Called when a job starts"""
        job_id = ctx.get('job_id', 'unknown')
        logger.info(f"Starting job: {job_id}")
        
    @staticmethod
    async def on_job_end(ctx):
        """Called when a job ends"""
        job_id = ctx.get('job_id', 'unknown')
        logger.info(f"Finished job: {job_id}")


# Additional imports for cleanup function
from datetime import timedelta
from sqlalchemy import delete, and_, func