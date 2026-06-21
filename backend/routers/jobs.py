import asyncio
import json
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.worker import get_job_status, get_queue_stats, cleanup_old_jobs
from services.auth import get_current_user_optional, get_current_admin_user
from services.rate_limit import get_redis
from models.models import User

router = APIRouter()


class JobStatusResponse(BaseModel):
    id: str
    status: str  # "pending", "processing", "completed", "failed"
    created_at: str
    updated_at: str
    memes: Optional[list] = None
    error: Optional[str] = None


class QueueStatsResponse(BaseModel):
    queue_length: int
    pending_jobs: int
    processing_jobs: int
    completed_jobs: int
    failed_jobs: int
    total_jobs: int
    error: Optional[str] = None


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job(
    job_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get job status and results (Polling fallback)"""
    
    job_data = await get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(**job_data)


@router.get("/{job_id}/stream")
async def stream_job_status(
    job_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Stream job status updates via Server-Sent Events (SSE)"""
    
    async def event_generator():
        redis = await get_redis()
        pubsub = redis.pubsub()
        channel = f"job_status:{job_id}"
        await pubsub.subscribe(channel)
        
        try:
            # First, send current status immediately
            current_status = await get_job_status(job_id)
            if current_status:
                yield f"data: {json.dumps(current_status)}\n\n"
                if current_status["status"] in ["completed", "failed"]:
                    return

            # Then wait for updates
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    
                    # If completed, fetch full job data (including memes)
                    if data["status"] == "completed":
                        full_data = await get_job_status(job_id)
                        yield f"data: {json.dumps(full_data)}\n\n"
                        break
                    else:
                        yield f"data: {json.dumps(data)}\n\n"
                        
                    if data["status"] == "failed":
                        break
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/queue/stats", response_model=QueueStatsResponse)
async def get_queue_statistics():
    """Get ARQ queue statistics (for monitoring). Read-only counts, kept
    public-readable; the destructive cleanup endpoint below is admin-only."""
    
    stats = await get_queue_stats()
    return QueueStatsResponse(**stats)


@router.post("/queue/cleanup")
async def cleanup_old_jobs_endpoint(
    days_old: int = 7,
    _admin: User = Depends(get_current_admin_user),
):
    """
    Clean up old completed/failed jobs.

    SECURITY (Phase 1 remediation): this previously had no auth dependency
    at all — any unauthenticated caller could wipe job history. Admin-only now.
    """
    
    if days_old < 1:
        raise HTTPException(status_code=400, detail="days_old must be at least 1")
    
    deleted_count = await cleanup_old_jobs(days_old)
    
    return {
        "message": f"Cleaned up {deleted_count} old jobs",
        "deleted_count": deleted_count
    }
