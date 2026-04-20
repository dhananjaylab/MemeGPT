"""
Cloudflare R2 Configuration and Setup
Handles bucket creation, permissions, and CORS configuration
"""
import boto3
import json
import logging
from botocore.exceptions import ClientError, BotoCoreError
from typing import Dict, List, Optional
from ..core.config import settings

logger = logging.getLogger(__name__)

class R2ConfigManager:
    """Manages Cloudflare R2 bucket configuration and permissions"""
    
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

    def create_bucket_if_not_exists(self) -> bool:
        """Create R2 bucket if it doesn't exist"""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket {self.bucket_name} already exists")
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                try:
                    self.client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"Created bucket {self.bucket_name}")
                    return True
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
                    return False
            else:
                logger.error(f"Error checking bucket: {e}")
                return False

    def configure_cors(self) -> bool:
        """Configure CORS for the R2 bucket"""
        cors_configuration = {
            'CORSRules': [
                {
                    'AllowedHeaders': ['*'],
                    'AllowedMethods': ['GET', 'HEAD'],
                    'AllowedOrigins': settings.cors_origins + ['*'],  # Allow all origins for public assets
                    'ExposeHeaders': ['ETag', 'Content-Length', 'Content-Type'],
                    'MaxAgeSeconds': 3600
                }
            ]
        }
        
        try:
            self.client.put_bucket_cors(
                Bucket=self.bucket_name,
                CORSConfiguration=cors_configuration
            )
            logger.info(f"CORS configured for bucket {self.bucket_name}")
            return True
        except ClientError as e:
            logger.error(f"Failed to configure CORS: {e}")
            return False

    def configure_public_access_policy(self) -> bool:
        """Configure bucket policy for public read access to images"""
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{self.bucket_name}/*",
                    "Condition": {
                        "StringLike": {
                            "s3:ExistingObjectTag/public": "true"
                        }
                    }
                },
                {
                    "Sid": "PublicReadMemes",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{self.bucket_name}/memes/*"
                },
                {
                    "Sid": "PublicReadTemplates",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{self.bucket_name}/templates/*"
                },
                {
                    "Sid": "DenyDirectAccess",
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{self.bucket_name}/private/*"
                }
            ]
        }
        
        try:
            self.client.put_bucket_policy(
                Bucket=self.bucket_name,
                Policy=json.dumps(policy)
            )
            logger.info(f"Public access policy configured for bucket {self.bucket_name}")
            return True
        except ClientError as e:
            logger.error(f"Failed to configure bucket policy: {e}")
            return False

    def configure_lifecycle_policy(self) -> bool:
        """Configure lifecycle policy for automatic cleanup of temporary files"""
        lifecycle_configuration = {
            'Rules': [
                {
                    'ID': 'DeleteTempFiles',
                    'Status': 'Enabled',
                    'Filter': {
                        'Prefix': 'temp/'
                    },
                    'Expiration': {
                        'Days': 7
                    }
                },
                {
                    'ID': 'DeleteFailedUploads',
                    'Status': 'Enabled',
                    'Filter': {
                        'Prefix': 'uploads/failed/'
                    },
                    'Expiration': {
                        'Days': 1
                    }
                },
                {
                    'ID': 'TransitionToIA',
                    'Status': 'Enabled',
                    'Filter': {
                        'Prefix': 'archive/'
                    },
                    'Transitions': [
                        {
                            'Days': 30,
                            'StorageClass': 'STANDARD_IA'
                        }
                    ]
                },
                {
                    'ID': 'CleanupOldVersions',
                    'Status': 'Enabled',
                    'NoncurrentVersionExpiration': {
                        'NoncurrentDays': 30
                    }
                }
            ]
        }
        
        try:
            self.client.put_bucket_lifecycle_configuration(
                Bucket=self.bucket_name,
                LifecycleConfiguration=lifecycle_configuration
            )
            logger.info(f"Lifecycle policy configured for bucket {self.bucket_name}")
            return True
        except ClientError as e:
            logger.error(f"Failed to configure lifecycle policy: {e}")
            return False

    def setup_bucket(self) -> bool:
        """Complete bucket setup with all configurations"""
        try:
            success = True
            success &= self.create_bucket_if_not_exists()
            success &= self.configure_cors()
            success &= self.configure_public_access_policy()
            success &= self.configure_lifecycle_policy()
            
            if success:
                logger.info("R2 bucket setup completed successfully")
            else:
                logger.error("R2 bucket setup completed with errors")
                
            return success
        except Exception as e:
            logger.error(f"Unexpected error during bucket setup: {e}")
            return False

    def verify_configuration(self) -> Dict[str, bool]:
        """Verify all bucket configurations are in place"""
        results = {
            'bucket_exists': False,
            'cors_configured': False,
            'policy_configured': False,
            'lifecycle_configured': False
        }
        
        try:
            # Check bucket exists
            self.client.head_bucket(Bucket=self.bucket_name)
            results['bucket_exists'] = True
            
            # Check CORS
            try:
                self.client.get_bucket_cors(Bucket=self.bucket_name)
                results['cors_configured'] = True
            except ClientError:
                pass
                
            # Check policy
            try:
                self.client.get_bucket_policy(Bucket=self.bucket_name)
                results['policy_configured'] = True
            except ClientError:
                pass
                
            # Check lifecycle
            try:
                self.client.get_bucket_lifecycle_configuration(Bucket=self.bucket_name)
                results['lifecycle_configured'] = True
            except ClientError:
                pass
                
        except ClientError as e:
            logger.error(f"Error verifying configuration: {e}")
            
        return results

class CDNCachingPolicy:
    """Manages CDN caching policies for Cloudflare R2"""
    
    # Default cache control headers for different content types
    CACHE_RULES = {
        # Meme images - cache aggressively
        "memes/": {
            "cache_control": "public, max-age=31536000, immutable",  # 1 year
            "content_types": ["image/jpeg", "image/png", "image/webp"],
        },
        # Templates - cache long term
        "templates/": {
            "cache_control": "public, max-age=2592000, immutable",  # 30 days
            "content_types": ["image/jpeg", "image/png", "image/webp"],
        },
        # User uploads - cache medium term
        "uploads/": {
            "cache_control": "public, max-age=604800",  # 7 days
            "content_types": ["image/jpeg", "image/png", "image/webp"],
        },
        # API responses - no cache
        "api/": {
            "cache_control": "no-cache, no-store, must-revalidate",
            "content_types": ["application/json"],
        },
        # Default for everything else
        "default": {
            "cache_control": "public, max-age=3600",  # 1 hour
            "content_types": [],
        }
    }
    
    @staticmethod
    def get_cache_control_header(object_key: str) -> str:
        """Get cache control header for an object"""
        for prefix, rule in CDNCachingPolicy.CACHE_RULES.items():
            if prefix != "default" and object_key.startswith(prefix):
                return rule["cache_control"]
        
        return CDNCachingPolicy.CACHE_RULES["default"]["cache_control"]
    
    @staticmethod
    def get_cache_ttl_seconds(object_key: str) -> int:
        """Extract TTL in seconds from cache rule"""
        cache_header = CDNCachingPolicy.get_cache_control_header(object_key)
        
        # Parse max-age from cache control header
        for part in cache_header.split(","):
            part = part.strip()
            if part.startswith("max-age="):
                try:
                    return int(part.split("=")[1])
                except (ValueError, IndexError):
                    pass
        
        return 3600  # Default 1 hour


def setup_r2_bucket() -> bool:
    """Convenience function to setup R2 bucket"""
    try:
        manager = R2ConfigManager()
        return manager.setup_bucket()
    except Exception as e:
        logger.error(f"Failed to setup R2 bucket: {e}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = setup_r2_bucket()
    exit(0 if success else 1)