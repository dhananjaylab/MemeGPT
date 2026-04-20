import boto3
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class R2BackupManager:
    """Comprehensive backup strategy for Cloudflare R2 storage"""
    
    def __init__(self):
        self.r2_account_id = os.getenv("R2_ACCOUNT_ID")
        self.r2_access_key_id = os.getenv("R2_ACCESS_KEY_ID")
        self.r2_secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY")
        self.r2_bucket_name = os.getenv("R2_BUCKET_NAME", "memegpt-images")
        self.backup_bucket_name = os.getenv("R2_BACKUP_BUCKET_NAME", f"{self.r2_bucket_name}-backup")
        
        if not all([self.r2_account_id, self.r2_access_key_id, self.r2_secret_access_key]):
            raise ValueError("R2 credentials not found in environment variables")
        
        self.client = boto3.client(
            's3',
            endpoint_url=f"https://{self.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=self.r2_access_key_id,
            aws_secret_access_key=self.r2_secret_access_key,
            region_name=None
        )
        
        self.backup_dir = Path("backups/r2")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup_bucket(self) -> bool:
        """Create dedicated backup bucket if it doesn't exist"""
        try:
            self.client.head_bucket(Bucket=self.backup_bucket_name)
            logger.info(f"Backup bucket {self.backup_bucket_name} already exists")
            return True
        except Exception:
            try:
                self.client.create_bucket(Bucket=self.backup_bucket_name)
                
                # Configure backup bucket with versioning
                self.client.put_bucket_versioning(
                    Bucket=self.backup_bucket_name,
                    VersioningConfiguration={'Status': 'Enabled'}
                )
                
                # Set lifecycle policy for backup retention
                lifecycle_config = {
                    'Rules': [
                        {
                            'ID': 'BackupRetention',
                            'Status': 'Enabled',
                            'NoncurrentVersionExpiration': {
                                'NoncurrentDays': 90  # Keep backups for 90 days
                            }
                        }
                    ]
                }
                
                self.client.put_bucket_lifecycle_configuration(
                    Bucket=self.backup_bucket_name,
                    LifecycleConfiguration=lifecycle_config
                )
                
                logger.info(f"Created backup bucket {self.backup_bucket_name} with versioning and lifecycle")
                return True
                
            except Exception as e:
                logger.error(f"Failed to create backup bucket: {e}")
                return False
    
    def backup_to_local(self, prefix: str = "", max_workers: int = 5) -> Dict[str, int]:
        """Backup R2 objects to local storage with parallel downloads"""
        results = {'success': 0, 'failed': 0, 'total_size': 0}
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_{timestamp}"
        backup_path.mkdir(exist_ok=True)
        
        # Create backup manifest
        manifest = {
            'timestamp': timestamp,
            'bucket': self.r2_bucket_name,
            'prefix': prefix,
            'files': []
        }
        
        def download_object(obj_info):
            key, size = obj_info
            local_path = backup_path / key
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                self.client.download_file(self.r2_bucket_name, key, str(local_path))
                logger.info(f"Downloaded {key} ({size} bytes)")
                return {'key': key, 'size': size, 'status': 'success'}
            except Exception as e:
                logger.error(f"Failed to download {key}: {e}")
                return {'key': key, 'size': size, 'status': 'failed', 'error': str(e)}
        
        try:
            # List all objects
            paginator = self.client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.r2_bucket_name, Prefix=prefix)
            
            objects_to_download = []
            for page in pages:
                if 'Contents' not in page:
                    continue
                for obj in page['Contents']:
                    objects_to_download.append((obj['Key'], obj['Size']))
            
            # Download objects in parallel
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_obj = {executor.submit(download_object, obj): obj for obj in objects_to_download}
                
                for future in as_completed(future_to_obj):
                    result = future.result()
                    manifest['files'].append(result)
                    
                    if result['status'] == 'success':
                        results['success'] += 1
                        results['total_size'] += result['size']
                    else:
                        results['failed'] += 1
            
            # Save manifest
            manifest_path = backup_path / 'manifest.json'
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            logger.info(f"Local backup completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            results['failed'] = len(objects_to_download) if 'objects_to_download' in locals() else 0
            return results
    
    def backup_to_r2_bucket(self, prefix: str = "") -> Dict[str, int]:
        """Cross-bucket backup within R2"""
        if not self.create_backup_bucket():
            return {'success': 0, 'failed': 0}
        
        results = {'success': 0, 'failed': 0}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            paginator = self.client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.r2_bucket_name, Prefix=prefix)
            
            for page in pages:
                if 'Contents' not in page:
                    continue
                    
                for obj in page['Contents']:
                    source_key = obj['Key']
                    backup_key = f"{timestamp}/{source_key}"
                    
                    try:
                        # Copy object to backup bucket
                        copy_source = {'Bucket': self.r2_bucket_name, 'Key': source_key}
                        self.client.copy_object(
                            CopySource=copy_source,
                            Bucket=self.backup_bucket_name,
                            Key=backup_key,
                            MetadataDirective='COPY'
                        )
                        
                        results['success'] += 1
                        logger.info(f"Backed up {source_key} to {backup_key}")
                        
                    except Exception as e:
                        results['failed'] += 1
                        logger.error(f"Failed to backup {source_key}: {e}")
            
            logger.info(f"R2 cross-bucket backup completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"R2 backup failed: {e}")
            return results
    
    def incremental_backup(self, since_hours: int = 24) -> Dict[str, int]:
        """Perform incremental backup of objects modified in the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=since_hours)
        results = {'success': 0, 'failed': 0, 'skipped': 0}
        
        try:
            paginator = self.client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.r2_bucket_name)
            
            for page in pages:
                if 'Contents' not in page:
                    continue
                    
                for obj in page['Contents']:
                    # Check if object was modified recently
                    if obj['LastModified'].replace(tzinfo=None) > cutoff_time:
                        # Backup this object
                        source_key = obj['Key']
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        backup_key = f"incremental/{timestamp}/{source_key}"
                        
                        try:
                            copy_source = {'Bucket': self.r2_bucket_name, 'Key': source_key}
                            self.client.copy_object(
                                CopySource=copy_source,
                                Bucket=self.backup_bucket_name,
                                Key=backup_key,
                                MetadataDirective='COPY'
                            )
                            
                            results['success'] += 1
                            logger.info(f"Incremental backup: {source_key}")
                            
                        except Exception as e:
                            results['failed'] += 1
                            logger.error(f"Failed incremental backup of {source_key}: {e}")
                    else:
                        results['skipped'] += 1
            
            logger.info(f"Incremental backup completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Incremental backup failed: {e}")
            return results
    
    def restore_from_backup(self, backup_timestamp: str, target_prefix: str = "restored/") -> Dict[str, int]:
        """Restore objects from backup"""
        results = {'success': 0, 'failed': 0}
        
        try:
            # List backup objects
            backup_prefix = f"{backup_timestamp}/"
            paginator = self.client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.backup_bucket_name, Prefix=backup_prefix)
            
            for page in pages:
                if 'Contents' not in page:
                    continue
                    
                for obj in page['Contents']:
                    backup_key = obj['Key']
                    # Remove timestamp prefix to get original key
                    original_key = backup_key[len(backup_prefix):]
                    restore_key = f"{target_prefix}{original_key}"
                    
                    try:
                        copy_source = {'Bucket': self.backup_bucket_name, 'Key': backup_key}
                        self.client.copy_object(
                            CopySource=copy_source,
                            Bucket=self.r2_bucket_name,
                            Key=restore_key,
                            MetadataDirective='COPY'
                        )
                        
                        results['success'] += 1
                        logger.info(f"Restored {original_key} to {restore_key}")
                        
                    except Exception as e:
                        results['failed'] += 1
                        logger.error(f"Failed to restore {original_key}: {e}")
            
            logger.info(f"Restore completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return results
    
    def cleanup_old_backups(self, days_to_keep: int = 30) -> Dict[str, int]:
        """Clean up old backup files"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        results = {'deleted': 0, 'failed': 0}
        
        try:
            # Clean up local backups
            for backup_dir in self.backup_dir.glob("backup_*"):
                if backup_dir.is_dir():
                    # Parse timestamp from directory name
                    timestamp_str = backup_dir.name.replace("backup_", "")
                    try:
                        backup_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                        if backup_date < cutoff_date:
                            import shutil
                            shutil.rmtree(backup_dir)
                            results['deleted'] += 1
                            logger.info(f"Deleted old local backup: {backup_dir}")
                    except ValueError:
                        logger.warning(f"Could not parse backup timestamp: {timestamp_str}")
            
            logger.info(f"Backup cleanup completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
            return results

def backup_r2():
    """Main backup function with comprehensive strategy"""
    try:
        backup_manager = R2BackupManager()
        
        print("Starting comprehensive R2 backup...")
        
        # 1. Incremental backup (last 24 hours)
        print("Performing incremental backup...")
        incremental_results = backup_manager.incremental_backup(since_hours=24)
        print(f"Incremental backup: {incremental_results}")
        
        # 2. Full backup to backup bucket (weekly)
        if datetime.now().weekday() == 0:  # Monday
            print("Performing weekly full backup to R2...")
            full_backup_results = backup_manager.backup_to_r2_bucket()
            print(f"Full R2 backup: {full_backup_results}")
        
        # 3. Local backup (monthly)
        if datetime.now().day == 1:  # First day of month
            print("Performing monthly local backup...")
            local_backup_results = backup_manager.backup_to_local()
            print(f"Local backup: {local_backup_results}")
        
        # 4. Cleanup old backups
        print("Cleaning up old backups...")
        cleanup_results = backup_manager.cleanup_old_backups(days_to_keep=30)
        print(f"Cleanup: {cleanup_results}")
        
        print("Backup strategy completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Backup strategy failed: {e}")
        print(f"Backup failed: {e}")
        return False

if __name__ == "__main__":
    backup_r2()
