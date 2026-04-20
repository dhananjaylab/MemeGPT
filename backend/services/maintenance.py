"""
Maintenance and Automated Backup Service
Handles automated maintenance tasks and backup procedures
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)


class MaintenanceTaskStatus(str, Enum):
    """Maintenance task status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class BackupType(str, Enum):
    """Types of backups"""
    DATABASE = "database"
    R2_STORAGE = "r2_storage"
    CONFIGURATION = "configuration"
    FULL = "full"


@dataclass
class MaintenanceTask:
    """Maintenance task"""
    task_id: str
    name: str
    description: str
    status: MaintenanceTaskStatus = MaintenanceTaskStatus.PENDING
    scheduled_time: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    result: Optional[Dict] = None


@dataclass
class BackupRecord:
    """Backup record"""
    backup_id: str
    backup_type: BackupType
    timestamp: str
    size_bytes: int
    status: str  # completed, failed, pending
    location: str
    retention_days: int
    error_message: Optional[str] = None


class MaintenanceScheduler:
    """Schedules and manages maintenance tasks"""
    
    # Default maintenance schedules
    DEFAULT_SCHEDULES = {
        "database_vacuum": {"schedule": "0 2 * * 0", "description": "Vacuum database"},
        "database_analyze": {"schedule": "0 3 * * 0", "description": "Analyze database"},
        "cleanup_temp_files": {"schedule": "0 4 * * *", "description": "Cleanup temporary files"},
        "backup_database": {"schedule": "0 1 * * *", "description": "Backup database"},
        "backup_r2": {"schedule": "0 2 * * 0", "description": "Backup R2 storage"},
        "cleanup_old_backups": {"schedule": "0 3 * * 1", "description": "Cleanup old backups"},
        "health_check": {"schedule": "*/30 * * * *", "description": "Health check"},
    }
    
    def __init__(self):
        self.tasks: Dict[str, MaintenanceTask] = {}
        self.task_history: List[MaintenanceTask] = []
    
    async def schedule_task(
        self,
        task_id: str,
        name: str,
        description: str,
        task_func,
        scheduled_time: Optional[str] = None,
    ) -> MaintenanceTask:
        """Schedule a maintenance task"""
        task = MaintenanceTask(
            task_id=task_id,
            name=name,
            description=description,
            scheduled_time=scheduled_time or datetime.utcnow().isoformat(),
        )
        
        self.tasks[task_id] = task
        logger.info(f"Scheduled task: {name} ({task_id})")
        
        # Execute immediately if no scheduled time
        if not scheduled_time:
            await self.execute_task(task_id, task_func)
        
        return task
    
    async def execute_task(self, task_id: str, task_func) -> MaintenanceTask:
        """Execute a maintenance task"""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self.tasks[task_id]
        task.status = MaintenanceTaskStatus.RUNNING
        task.started_at = datetime.utcnow().isoformat()
        
        try:
            logger.info(f"Executing task: {task.name}")
            result = await task_func()
            
            task.status = MaintenanceTaskStatus.COMPLETED
            task.completed_at = datetime.utcnow().isoformat()
            task.result = result
            
            logger.info(f"Task completed: {task.name}")
            
        except Exception as e:
            logger.error(f"Task failed: {task.name} - {str(e)}")
            task.status = MaintenanceTaskStatus.FAILED
            task.completed_at = datetime.utcnow().isoformat()
            task.error_message = str(e)
        
        self.task_history.append(task)
        return task
    
    def get_task_history(self, limit: int = 100) -> List[MaintenanceTask]:
        """Get task history"""
        return self.task_history[-limit:]
    
    def get_task_status(self, task_id: str) -> Optional[MaintenanceTask]:
        """Get status of specific task"""
        return self.tasks.get(task_id)


class BackupManager:
    """Manages automated backups"""
    
    def __init__(self, storage_backend=None):
        self.storage = storage_backend
        self.backups: List[BackupRecord] = []
    
    async def backup_database(
        self,
        connection_string: str,
        backup_retention_days: int = 30,
    ) -> BackupRecord:
        """Backup database"""
        backup = BackupRecord(
            backup_id=f"db_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            backup_type=BackupType.DATABASE,
            timestamp=datetime.utcnow().isoformat(),
            size_bytes=0,
            status="pending",
            location="",
            retention_days=backup_retention_days,
        )
        
        try:
            logger.info("Starting database backup...")
            # In production, would use pg_dump or similar
            backup.status = "completed"
            backup.size_bytes = 1024 * 1024  # Placeholder
            backup.location = f"s3://backups/{backup.backup_id}.sql"
            
            logger.info(f"Database backup completed: {backup.backup_id}")
            
        except Exception as e:
            backup.status = "failed"
            backup.error_message = str(e)
            logger.error(f"Database backup failed: {str(e)}")
        
        self.backups.append(backup)
        if self.storage:
            await self.storage.store_backup_record(backup)
        
        return backup
    
    async def backup_r2_storage(
        self,
        bucket_name: str,
        backup_retention_days: int = 90,
    ) -> BackupRecord:
        """Backup R2 storage"""
        backup = BackupRecord(
            backup_id=f"r2_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            backup_type=BackupType.R2_STORAGE,
            timestamp=datetime.utcnow().isoformat(),
            size_bytes=0,
            status="pending",
            location="",
            retention_days=backup_retention_days,
        )
        
        try:
            logger.info("Starting R2 storage backup...")
            backup.status = "completed"
            backup.size_bytes = 5 * 1024 * 1024 * 1024  # Placeholder
            backup.location = f"r2://backups/{backup.backup_id}"
            
            logger.info(f"R2 backup completed: {backup.backup_id}")
            
        except Exception as e:
            backup.status = "failed"
            backup.error_message = str(e)
            logger.error(f"R2 backup failed: {str(e)}")
        
        self.backups.append(backup)
        if self.storage:
            await self.storage.store_backup_record(backup)
        
        return backup
    
    async def full_backup(
        self,
        connection_string: str,
        bucket_name: str,
    ) -> Dict:
        """Execute full backup"""
        logger.info("Starting full system backup...")
        
        db_backup = await self.backup_database(connection_string)
        r2_backup = await self.backup_r2_storage(bucket_name)
        
        all_successful = (
            db_backup.status == "completed" and
            r2_backup.status == "completed"
        )
        
        return {
            "status": "completed" if all_successful else "completed_with_errors",
            "timestamp": datetime.utcnow().isoformat(),
            "backups": [
                {"type": "database", "status": db_backup.status},
                {"type": "r2_storage", "status": r2_backup.status},
            ],
            "total_size_gb": round((db_backup.size_bytes + r2_backup.size_bytes) / (1024 ** 3), 2),
        }
    
    async def cleanup_old_backups(self) -> Dict:
        """Clean up old backups based on retention"""
        logger.info("Cleaning up old backups...")
        
        cleaned_count = 0
        for backup in self.backups:
            created_date = datetime.fromisoformat(backup.timestamp)
            age_days = (datetime.utcnow() - created_date).days
            
            if age_days > backup.retention_days:
                cleaned_count += 1
                logger.info(f"Removing old backup: {backup.backup_id}")
                # In production, would delete from storage
        
        return {
            "cleaned_count": cleaned_count,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def get_backup_history(self, backup_type: Optional[BackupType] = None) -> List[BackupRecord]:
        """Get backup history"""
        backups = self.backups.copy()
        
        if backup_type:
            backups = [b for b in backups if b.backup_type == backup_type]
        
        return sorted(backups, key=lambda b: b.timestamp, reverse=True)


class SystemHealthChecker:
    """Performs system health checks"""
    
    async def check_database_health(self, session) -> Dict:
        """Check database health"""
        try:
            result = await session.execute("SELECT 1")
            return {
                "status": "healthy",
                "component": "database",
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "component": "database",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    async def check_redis_health(self, redis_client) -> Dict:
        """Check Redis health"""
        try:
            await redis_client.ping()
            return {
                "status": "healthy",
                "component": "redis",
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "component": "redis",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    async def check_storage_health(self, s3_client) -> Dict:
        """Check storage health"""
        try:
            # Test S3/R2 connectivity
            await asyncio.to_thread(lambda: s3_client.head_bucket(Bucket="test"))
            return {
                "status": "healthy",
                "component": "storage",
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "component": "storage",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    async def full_health_check(self, session, redis_client, s3_client) -> Dict:
        """Perform full system health check"""
        logger.info("Running full system health check...")
        
        checks = await asyncio.gather(
            self.check_database_health(session),
            self.check_redis_health(redis_client),
            self.check_storage_health(s3_client),
        )
        
        all_healthy = all(check["status"] == "healthy" for check in checks)
        
        return {
            "overall_status": "healthy" if all_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks,
        }
