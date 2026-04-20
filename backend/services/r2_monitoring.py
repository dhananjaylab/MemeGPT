"""
R2 Storage Backup and Monitoring Service
Handles backup strategies, monitoring, and cost tracking for Cloudflare R2
"""
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import boto3
from botocore.exceptions import ClientError

from core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class StorageMetrics:
    """Storage metrics snapshot"""
    timestamp: str
    total_objects: int
    total_size_bytes: int
    total_size_gb: float
    meme_objects: int
    meme_size_bytes: int
    template_objects: int
    template_size_bytes: int
    backup_objects: int
    backup_size_bytes: int
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BackupMetadata:
    """Backup metadata"""
    backup_id: str
    timestamp: str
    source_bucket: str
    object_count: int
    total_size_bytes: int
    status: str  # pending, in_progress, completed, failed
    error_message: Optional[str] = None
    completed_at: Optional[str] = None


class R2BackupManager:
    """Manages R2 bucket backup strategy"""
    
    def __init__(self):
        if not all([settings.r2_account_id, settings.r2_access_key_id, settings.r2_secret_access_key]):
            raise ValueError("R2 credentials not properly configured")
        
        self.client = boto3.client(
            's3',
            endpoint_url=settings.r2_endpoint_url,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name='auto'
        )
        self.bucket_name = settings.r2_bucket_name
        self.backup_prefix = "backups/"
    
    def create_backup_metadata(self) -> BackupMetadata:
        """Create backup metadata entry"""
        backup_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        return BackupMetadata(
            backup_id=backup_id,
            timestamp=datetime.utcnow().isoformat(),
            source_bucket=self.bucket_name,
            object_count=0,
            total_size_bytes=0,
            status="pending",
        )
    
    def backup_bucket_versioning(self, enable: bool = True) -> bool:
        """Enable or disable bucket versioning for backup protection"""
        try:
            if enable:
                self.client.put_bucket_versioning(
                    Bucket=self.bucket_name,
                    VersioningConfiguration={'Status': 'Enabled'}
                )
                logger.info(f"Versioning enabled for bucket {self.bucket_name}")
            else:
                self.client.put_bucket_versioning(
                    Bucket=self.bucket_name,
                    VersioningConfiguration={'Status': 'Suspended'}
                )
                logger.info(f"Versioning suspended for bucket {self.bucket_name}")
            return True
        except ClientError as e:
            logger.error(f"Failed to configure versioning: {e}")
            return False
    
    def list_backup_manifests(self, limit: int = 10) -> List[dict]:
        """List recent backup manifests"""
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=self.backup_prefix,
                MaxKeys=limit
            )
            
            manifests = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    if obj['Key'].endswith('_manifest.json'):
                        try:
                            obj_response = self.client.get_object(
                                Bucket=self.bucket_name,
                                Key=obj['Key']
                            )
                            manifest = json.loads(obj_response['Body'].read().decode())
                            manifests.append(manifest)
                        except Exception as e:
                            logger.error(f"Failed to read manifest {obj['Key']}: {e}")
            
            return sorted(manifests, key=lambda x: x['timestamp'], reverse=True)
            
        except ClientError as e:
            logger.error(f"Failed to list backup manifests: {e}")
            return []
    
    def backup_object(self, source_key: str, backup_id: str) -> bool:
        """Backup a single object to backup prefix"""
        try:
            backup_key = f"{self.backup_prefix}{backup_id}/{source_key}"
            
            copy_source = {'Bucket': self.bucket_name, 'Key': source_key}
            self.client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=backup_key
            )
            
            logger.debug(f"Backed up {source_key} to {backup_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to backup object {source_key}: {e}")
            return False
    
    def backup_bucket_snapshot(self, backup_id: Optional[str] = None) -> BackupMetadata:
        """Create a snapshot backup of the entire bucket"""
        if not backup_id:
            backup_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        metadata = BackupMetadata(
            backup_id=backup_id,
            timestamp=datetime.utcnow().isoformat(),
            source_bucket=self.bucket_name,
            object_count=0,
            total_size_bytes=0,
            status="in_progress",
        )
        
        try:
            paginator = self.client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name)
            
            for page in pages:
                if 'Contents' not in page:
                    continue
                
                for obj in page['Contents']:
                    # Skip backup objects to avoid backup loops
                    if obj['Key'].startswith(self.backup_prefix):
                        continue
                    
                    if self.backup_object(obj['Key'], backup_id):
                        metadata.object_count += 1
                        metadata.total_size_bytes += obj['Size']
            
            # Save manifest
            manifest_key = f"{self.backup_prefix}{backup_id}/_manifest.json"
            manifest_data = {
                **asdict(metadata),
                "completed_at": datetime.utcnow().isoformat(),
            }
            manifest_data['status'] = 'completed'
            
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=manifest_key,
                Body=json.dumps(manifest_data, indent=2),
                ContentType='application/json'
            )
            
            metadata.status = 'completed'
            metadata.completed_at = datetime.utcnow().isoformat()
            logger.info(f"Backup {backup_id} completed: {metadata.object_count} objects, {metadata.total_size_bytes} bytes")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            metadata.status = 'failed'
            metadata.error_message = str(e)
            return metadata
    
    def restore_from_backup(self, backup_id: str, restore_prefix: str = "") -> bool:
        """Restore objects from a backup"""
        try:
            paginator = self.client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=f"{self.backup_prefix}{backup_id}/"
            )
            
            restored_count = 0
            for page in pages:
                if 'Contents' not in page:
                    continue
                
                for obj in page['Contents']:
                    # Skip manifest file
                    if obj['Key'].endswith('_manifest.json'):
                        continue
                    
                    # Extract original key
                    original_key = obj['Key'].replace(f"{self.backup_prefix}{backup_id}/", "", 1)
                    restore_key = f"{restore_prefix}{original_key}" if restore_prefix else original_key
                    
                    copy_source = {'Bucket': self.bucket_name, 'Key': obj['Key']}
                    self.client.copy_object(
                        CopySource=copy_source,
                        Bucket=self.bucket_name,
                        Key=restore_key
                    )
                    restored_count += 1
            
            logger.info(f"Restored {restored_count} objects from backup {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            return False
    
    def cleanup_old_backups(self, retention_days: int = 30) -> int:
        """Remove backups older than retention period"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            deleted_count = 0
            
            paginator = self.client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=self.backup_prefix
            )
            
            for page in pages:
                if 'Contents' not in page:
                    continue
                
                for obj in page['Contents']:
                    if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                        self.client.delete_object(
                            Bucket=self.bucket_name,
                            Key=obj['Key']
                        )
                        deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old backup objects")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
            return 0


class R2MonitoringService:
    """Monitors R2 storage usage and costs"""
    
    def __init__(self):
        if not all([settings.r2_account_id, settings.r2_access_key_id, settings.r2_secret_access_key]):
            raise ValueError("R2 credentials not properly configured")
        
        self.client = boto3.client(
            's3',
            endpoint_url=settings.r2_endpoint_url,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name='auto'
        )
        self.bucket_name = settings.r2_bucket_name
    
    def get_storage_metrics(self) -> StorageMetrics:
        """Get current storage metrics"""
        try:
            total_objects = 0
            total_size = 0
            category_stats = {
                "meme": {"objects": 0, "size": 0},
                "template": {"objects": 0, "size": 0},
                "backup": {"objects": 0, "size": 0},
                "other": {"objects": 0, "size": 0},
            }
            
            paginator = self.client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name)
            
            for page in pages:
                if 'Contents' not in page:
                    continue
                
                for obj in page['Contents']:
                    total_objects += 1
                    total_size += obj['Size']
                    
                    # Categorize
                    key = obj['Key']
                    if key.startswith('memes/'):
                        category_stats['meme']['objects'] += 1
                        category_stats['meme']['size'] += obj['Size']
                    elif key.startswith('templates/'):
                        category_stats['template']['objects'] += 1
                        category_stats['template']['size'] += obj['Size']
                    elif key.startswith('backups/'):
                        category_stats['backup']['objects'] += 1
                        category_stats['backup']['size'] += obj['Size']
                    else:
                        category_stats['other']['objects'] += 1
                        category_stats['other']['size'] += obj['Size']
            
            metrics = StorageMetrics(
                timestamp=datetime.utcnow().isoformat(),
                total_objects=total_objects,
                total_size_bytes=total_size,
                total_size_gb=round(total_size / (1024 ** 3), 2),
                meme_objects=category_stats['meme']['objects'],
                meme_size_bytes=category_stats['meme']['size'],
                template_objects=category_stats['template']['objects'],
                template_size_bytes=category_stats['template']['size'],
                backup_objects=category_stats['backup']['objects'],
                backup_size_bytes=category_stats['backup']['size'],
            )
            
            logger.info(f"Storage metrics: {metrics.total_objects} objects, {metrics.total_size_gb} GB")
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get storage metrics: {e}")
            raise
    
    def estimate_monthly_cost(self, metrics: StorageMetrics) -> dict:
        """Estimate monthly R2 storage cost"""
        # Cloudflare R2 pricing (as of 2024)
        storage_cost_per_gb_per_month = 0.015  # $0.015 per GB/month
        api_request_cost = 0.0000036  # $0.0000036 per API request
        estimated_requests_per_day = 10000  # Conservative estimate
        
        monthly_storage_cost = (metrics.total_size_gb * storage_cost_per_gb_per_month)
        daily_api_costs = (estimated_requests_per_day * api_request_cost)
        monthly_api_costs = daily_api_costs * 30
        
        return {
            "total_size_gb": metrics.total_size_gb,
            "monthly_storage_cost": round(monthly_storage_cost, 2),
            "estimated_daily_requests": estimated_requests_per_day,
            "monthly_api_costs": round(monthly_api_costs, 2),
            "total_estimated_monthly_cost": round(monthly_storage_cost + monthly_api_costs, 2),
            "cost_breakdown": {
                "storage": round(monthly_storage_cost, 2),
                "api_requests": round(monthly_api_costs, 2),
            }
        }
    
    def get_storage_trends(self, metrics_list: List[StorageMetrics]) -> dict:
        """Analyze storage growth trends"""
        if len(metrics_list) < 2:
            return {"error": "Need at least 2 metrics to calculate trends"}
        
        sorted_metrics = sorted(metrics_list, key=lambda m: m.timestamp)
        first = sorted_metrics[0]
        last = sorted_metrics[-1]
        
        size_growth = last.total_size_bytes - first.total_size_bytes
        object_growth = last.total_objects - first.total_objects
        
        return {
            "size_growth_bytes": size_growth,
            "size_growth_gb": round(size_growth / (1024 ** 3), 2),
            "object_growth": object_growth,
            "average_object_size_bytes": round(last.total_size_bytes / last.total_objects) if last.total_objects > 0 else 0,
        }
