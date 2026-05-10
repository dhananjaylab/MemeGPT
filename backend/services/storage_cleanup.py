"""
Storage cleanup service for managing local output directory.

Provides utilities to:
- Remove old generated memes from local storage
- Monitor disk usage
- Generate storage metrics
- Migrate files to R2 storage
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.config import settings

logger = logging.getLogger(__name__)

# Constants
OUTPUT_DIR = Path(__file__).parent.parent / "public" / "output"
DEFAULT_MAX_AGE_DAYS = 7
DEFAULT_MAX_SIZE_MB = 1000


class StorageCleanupService:
    """Service for managing local storage cleanup and monitoring"""
    
    def __init__(
        self,
        output_dir: Path = OUTPUT_DIR,
        max_age_days: int = DEFAULT_MAX_AGE_DAYS,
        max_size_mb: int = DEFAULT_MAX_SIZE_MB,
    ):
        self.output_dir = output_dir
        self.max_age_days = max_age_days
        self.max_size_mb = max_size_mb
        self.max_size_bytes = max_size_mb * 1024 * 1024
        
    def get_storage_metrics(self) -> Dict[str, Any]:
        """
        Get current storage metrics for the output directory.
        
        Returns:
            Dictionary with metrics including file count, total size, oldest file age
        """
        if not self.output_dir.exists():
            return {
                "exists": False,
                "file_count": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0,
                "oldest_file_age_hours": 0,
                "newest_file_age_hours": 0,
            }
        
        files = list(self.output_dir.glob("*.png"))
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        
        now = time.time()
        file_ages = [now - f.stat().st_mtime for f in files if f.is_file()]
        
        return {
            "exists": True,
            "file_count": len(files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest_file_age_hours": round(max(file_ages) / 3600, 2) if file_ages else 0,
            "newest_file_age_hours": round(min(file_ages) / 3600, 2) if file_ages else 0,
            "average_file_size_kb": round(total_size / len(files) / 1024, 2) if files else 0,
        }
    
    def find_old_files(self, max_age_days: Optional[int] = None) -> List[Path]:
        """
        Find files older than the specified age.
        
        Args:
            max_age_days: Maximum age in days (uses instance default if not provided)
            
        Returns:
            List of Path objects for files exceeding the age threshold
        """
        if not self.output_dir.exists():
            return []
        
        age_days = max_age_days or self.max_age_days
        cutoff_time = time.time() - (age_days * 24 * 3600)
        
        old_files = []
        for file_path in self.output_dir.glob("*.png"):
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                old_files.append(file_path)
        
        return old_files
    
    def cleanup_old_files(self, max_age_days: Optional[int] = None, dry_run: bool = False) -> Dict[str, Any]:
        """
        Remove files older than the specified age.
        
        Args:
            max_age_days: Maximum age in days (uses instance default if not provided)
            dry_run: If True, only report what would be deleted without actually deleting
            
        Returns:
            Dictionary with cleanup results
        """
        old_files = self.find_old_files(max_age_days)
        
        if not old_files:
            return {
                "deleted_count": 0,
                "freed_bytes": 0,
                "freed_mb": 0,
                "dry_run": dry_run,
                "errors": [],
            }
        
        deleted_count = 0
        freed_bytes = 0
        errors = []
        
        for file_path in old_files:
            try:
                file_size = file_path.stat().st_size
                
                if not dry_run:
                    file_path.unlink()
                    logger.info(f"Deleted old file: {file_path.name} ({file_size} bytes)")
                else:
                    logger.info(f"[DRY RUN] Would delete: {file_path.name} ({file_size} bytes)")
                
                deleted_count += 1
                freed_bytes += file_size
                
            except Exception as e:
                error_msg = f"Failed to delete {file_path.name}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        return {
            "deleted_count": deleted_count,
            "freed_bytes": freed_bytes,
            "freed_mb": round(freed_bytes / (1024 * 1024), 2),
            "dry_run": dry_run,
            "errors": errors,
        }
    
    def cleanup_by_size(self, target_size_mb: Optional[int] = None, dry_run: bool = False) -> Dict[str, Any]:
        """
        Remove oldest files until total size is below target.
        
        Args:
            target_size_mb: Target size in MB (uses instance default if not provided)
            dry_run: If True, only report what would be deleted without actually deleting
            
        Returns:
            Dictionary with cleanup results
        """
        if not self.output_dir.exists():
            return {
                "deleted_count": 0,
                "freed_bytes": 0,
                "freed_mb": 0,
                "dry_run": dry_run,
                "errors": [],
            }
        
        target_bytes = (target_size_mb or self.max_size_mb) * 1024 * 1024
        
        # Get all files sorted by modification time (oldest first)
        files = sorted(
            [f for f in self.output_dir.glob("*.png") if f.is_file()],
            key=lambda f: f.stat().st_mtime
        )
        
        current_size = sum(f.stat().st_size for f in files)
        
        if current_size <= target_bytes:
            return {
                "deleted_count": 0,
                "freed_bytes": 0,
                "freed_mb": 0,
                "current_size_mb": round(current_size / (1024 * 1024), 2),
                "target_size_mb": target_size_mb or self.max_size_mb,
                "dry_run": dry_run,
                "message": "Current size is already below target",
            }
        
        deleted_count = 0
        freed_bytes = 0
        errors = []
        
        for file_path in files:
            if current_size <= target_bytes:
                break
            
            try:
                file_size = file_path.stat().st_size
                
                if not dry_run:
                    file_path.unlink()
                    logger.info(f"Deleted file to reduce size: {file_path.name} ({file_size} bytes)")
                else:
                    logger.info(f"[DRY RUN] Would delete: {file_path.name} ({file_size} bytes)")
                
                current_size -= file_size
                freed_bytes += file_size
                deleted_count += 1
                
            except Exception as e:
                error_msg = f"Failed to delete {file_path.name}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        return {
            "deleted_count": deleted_count,
            "freed_bytes": freed_bytes,
            "freed_mb": round(freed_bytes / (1024 * 1024), 2),
            "final_size_mb": round(current_size / (1024 * 1024), 2),
            "target_size_mb": target_size_mb or self.max_size_mb,
            "dry_run": dry_run,
            "errors": errors,
        }
    
    async def migrate_to_r2(self, delete_after_upload: bool = False) -> Dict[str, Any]:
        """
        Migrate local files to R2 storage.
        
        Args:
            delete_after_upload: If True, delete local files after successful upload
            
        Returns:
            Dictionary with migration results
        """
        from services.storage import upload_to_r2
        
        if not self.output_dir.exists():
            return {
                "migrated_count": 0,
                "failed_count": 0,
                "deleted_count": 0,
                "errors": [],
            }
        
        files = list(self.output_dir.glob("*.png"))
        
        migrated_count = 0
        failed_count = 0
        deleted_count = 0
        errors = []
        
        for file_path in files:
            try:
                # Upload to R2
                object_key = f"migrated/{file_path.name}"
                result = await upload_to_r2(file_path, object_key, optimize=True)
                
                if result and result.get("primary"):
                    migrated_count += 1
                    logger.info(f"Migrated to R2: {file_path.name} -> {result['primary']}")
                    
                    # Delete local file if requested
                    if delete_after_upload:
                        file_path.unlink()
                        deleted_count += 1
                        logger.info(f"Deleted local file after migration: {file_path.name}")
                else:
                    failed_count += 1
                    error_msg = f"Failed to migrate {file_path.name}: No URL returned"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    
            except Exception as e:
                failed_count += 1
                error_msg = f"Failed to migrate {file_path.name}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        return {
            "total_files": len(files),
            "migrated_count": migrated_count,
            "failed_count": failed_count,
            "deleted_count": deleted_count,
            "errors": errors,
        }


# Global instance
cleanup_service = StorageCleanupService()


async def run_scheduled_cleanup():
    """
    Run scheduled cleanup task.
    Should be called periodically (e.g., daily via cron or background worker).
    """
    logger.info("Starting scheduled storage cleanup")
    
    # Get current metrics
    metrics = cleanup_service.get_storage_metrics()
    logger.info(f"Storage metrics before cleanup: {metrics}")
    
    # Cleanup old files
    cleanup_result = cleanup_service.cleanup_old_files(dry_run=False)
    logger.info(f"Cleanup result: {cleanup_result}")
    
    # Check if size is still too large
    if metrics["total_size_mb"] > cleanup_service.max_size_mb:
        size_cleanup = cleanup_service.cleanup_by_size(dry_run=False)
        logger.info(f"Size-based cleanup result: {size_cleanup}")
    
    # Get final metrics
    final_metrics = cleanup_service.get_storage_metrics()
    logger.info(f"Storage metrics after cleanup: {final_metrics}")
    
    return {
        "before": metrics,
        "cleanup": cleanup_result,
        "after": final_metrics,
    }

# Made with Bob
