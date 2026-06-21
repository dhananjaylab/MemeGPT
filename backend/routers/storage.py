"""
Storage management endpoints for monitoring and cleanup.

Provides admin endpoints for:
- Storage metrics and monitoring
- Manual cleanup operations
- R2 migration utilities

SECURITY (Phase 1 remediation): every endpoint in this router is
destructive or discloses internal operational data, and previously had
no authorization check at all — `current_user` was typed `Optional[User]`
and never inspected, so any unauthenticated caller could trigger
permanent deletion of generated meme files or kick off a full R2
migration. All endpoints now require an authenticated admin account via
get_current_admin_user.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from models.models import User
from services.auth import get_current_admin_user
from services.storage_cleanup import cleanup_service, run_scheduled_cleanup

router = APIRouter()


class StorageMetricsResponse(BaseModel):
    exists: bool
    file_count: int
    total_size_bytes: int
    total_size_mb: float
    oldest_file_age_hours: float
    newest_file_age_hours: float
    average_file_size_kb: float


class CleanupRequest(BaseModel):
    max_age_days: Optional[int] = None
    target_size_mb: Optional[int] = None
    dry_run: bool = True


class CleanupResponse(BaseModel):
    deleted_count: int
    freed_bytes: int
    freed_mb: float
    dry_run: bool
    errors: list


class MigrationRequest(BaseModel):
    delete_after_upload: bool = False


@router.get("/metrics", response_model=StorageMetricsResponse)
async def get_storage_metrics(
    _admin: User = Depends(get_current_admin_user),
):
    """
    Get current storage metrics for the output directory.
    
    Returns information about:
    - Number of files
    - Total storage size
    - File age statistics
    - Average file size
    """
    metrics = cleanup_service.get_storage_metrics()
    return StorageMetricsResponse(**metrics)


@router.post("/cleanup/age", response_model=CleanupResponse)
async def cleanup_by_age(
    request: CleanupRequest,
    _admin: User = Depends(get_current_admin_user),
):
    """
    Remove files older than specified age.
    
    Args:
        max_age_days: Maximum age in days (default: 7)
        dry_run: If true, only report what would be deleted (default: true)
    
    Note: This endpoint is safe to call with dry_run=true to preview changes.
    Destructive when dry_run=false — admin-only.
    """
    result = cleanup_service.cleanup_old_files(
        max_age_days=request.max_age_days,
        dry_run=request.dry_run
    )
    return CleanupResponse(**result)


@router.post("/cleanup/size", response_model=CleanupResponse)
async def cleanup_by_size(
    request: CleanupRequest,
    _admin: User = Depends(get_current_admin_user),
):
    """
    Remove oldest files until total size is below target.
    
    Args:
        target_size_mb: Target size in MB (default: 1000)
        dry_run: If true, only report what would be deleted (default: true)
    
    Files are deleted in order of oldest first until target size is reached.
    Destructive when dry_run=false — admin-only.
    """
    result = cleanup_service.cleanup_by_size(
        target_size_mb=request.target_size_mb,
        dry_run=request.dry_run
    )
    return CleanupResponse(**result)


@router.post("/migrate-to-r2")
async def migrate_to_r2(
    request: MigrationRequest,
    _admin: User = Depends(get_current_admin_user),
):
    """
    Migrate local files to R2 storage.
    
    Args:
        delete_after_upload: If true, delete local files after successful upload
    
    This operation:
    1. Uploads all local files to R2
    2. Optionally deletes local files after successful upload
    3. Returns migration statistics
    
    Warning: This operation may take a long time for large numbers of files.
    Admin-only.
    """
    result = await cleanup_service.migrate_to_r2(
        delete_after_upload=request.delete_after_upload
    )
    return result


@router.post("/cleanup/scheduled")
async def run_cleanup(
    _admin: User = Depends(get_current_admin_user),
):
    """
    Run the scheduled cleanup routine.
    
    This performs:
    1. Age-based cleanup (removes files older than 7 days)
    2. Size-based cleanup (if total size exceeds 1000 MB)
    3. Returns before/after metrics
    
    This is the same routine that should be run periodically via cron.
    Admin-only — if you need this on an automated cron/Action, mint a
    long-lived admin API key for that job rather than relaxing this check.
    """
    result = await run_scheduled_cleanup()
    return result

# Made with Bob
