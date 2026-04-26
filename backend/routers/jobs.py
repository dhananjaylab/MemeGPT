from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from services.worker import get_job_status, get_queue_stats, cleanup_old_jobs
from services.auth import get_current_user_optional
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
    """Get job status and results"""
    
    job_data = await get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(**job_data)


@router.get("/queue/stats", response_model=QueueStatsResponse)
async def get_queue_statistics():
    """Get ARQ queue statistics (for monitoring)"""
    
    stats = await get_queue_stats()
    return QueueStatsResponse(**stats)


@router.post("/queue/cleanup")
async def cleanup_old_jobs_endpoint(days_old: int = 7):
    """Clean up old completed/failed jobs"""
    
    if days_old < 1:
        raise HTTPException(status_code=400, detail="days_old must be at least 1")
    
    deleted_count = await cleanup_old_jobs(days_old)
    
    return {
        "message": f"Cleaned up {deleted_count} old jobs",
        "deleted_count": deleted_count
    }