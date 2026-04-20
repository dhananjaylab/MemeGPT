"""
CDN Configuration for Cloudflare R2
Handles cache policies, headers, and optimization settings
"""
import boto3
import logging
from typing import Dict, Optional, List
from enum import Enum
from ..core.config import settings

logger = logging.getLogger(__name__)

class CachePolicy(Enum):
    """Cache policy types for different content"""
    IMMUTABLE = "public, max-age=31536000, immutable"  # 1 year for versioned assets
    LONG_TERM = "public, max-age=2592000"  # 30 days for stable content
    MEDIUM_TERM = "public, max-age=86400"  # 1 day for dynamic content
    SHORT_TERM = "public, max-age=3600"    # 1 hour for frequently changing content
    NO_CACHE = "no-cache, no-store, must-revalidate"  # No caching

class CDNManager:
    """Manages CDN configuration and caching policies"""
    
    def __init__(self):
        if not settings.r2_access_key_id:
            raise ValueError("R2 credentials not configured")
            
        self.client = boto3.client(
            's3',
            endpoint_url=settings.r2_endpoint_url,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name=None  # Let boto3 handle region detection
        )
        self.bucket_name = settings.r2_bucket_name

    def get_cache_policy_for_path(self, object_key: str) -> str:
        """Determine appropriate cache policy based on file path and type"""
        # Versioned assets (with hash in filename) - immutable
        if any(pattern in object_key for pattern in ['-v', '_v', '.min.', 'hash-']):
            return CachePolicy.IMMUTABLE.value
            
        # Generated memes - long term caching
        if object_key.startswith(('memes/', 'generated/')):
            return CachePolicy.LONG_TERM.value
            
        # Template images - long term caching
        if object_key.startswith(('templates/', 'frames/')):
            return CachePolicy.LONG_TERM.value
            
        # User uploads - medium term caching
        if object_key.startswith(('uploads/', 'user-content/')):
            return CachePolicy.MEDIUM_TERM.value
            
        # Temporary files - short term caching
        if object_key.startswith(('temp/', 'tmp/')):
            return CachePolicy.SHORT_TERM.value
            
        # Default to medium term
        return CachePolicy.MEDIUM_TERM.value

    def get_content_type(self, object_key: str) -> str:
        """Determine content type based on file extension"""
        extension = object_key.lower().split('.')[-1]
        content_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
            'svg': 'image/svg+xml',
            'ico': 'image/x-icon',
            'bmp': 'image/bmp',
            'tiff': 'image/tiff',
            'tif': 'image/tiff'
        }
        return content_types.get(extension, 'application/octet-stream')

    def get_optimization_headers(self, object_key: str) -> Dict[str, str]:
        """Get optimization headers for the object"""
        headers = {}
        
        # Add compression hint for supported formats
        if any(ext in object_key.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
            headers['Content-Encoding'] = 'identity'  # Let CDN handle compression
            
        # Add security headers for images
        headers.update({
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'SAMEORIGIN',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        })
        
        # Add performance hints
        if object_key.startswith(('memes/', 'generated/')):
            headers['Link'] = '</css/critical.css>; rel=preload; as=style'
            
        return headers

    def upload_with_cdn_headers(self, file_data, object_key: str, 
                               custom_cache_policy: Optional[str] = None,
                               custom_headers: Optional[Dict[str, str]] = None) -> bool:
        """Upload file with appropriate CDN headers"""
        try:
            # Determine cache policy
            cache_control = custom_cache_policy or self.get_cache_policy_for_path(object_key)
            
            # Get content type
            content_type = self.get_content_type(object_key)
            
            # Get optimization headers
            headers = self.get_optimization_headers(object_key)
            
            # Add custom headers if provided
            if custom_headers:
                headers.update(custom_headers)
            
            # Prepare metadata
            metadata = {
                'uploaded-by': 'memegpt-api',
                'cache-policy': cache_control.split(',')[0].strip(),
                'optimization-level': 'standard'
            }
            
            # Add tags for public content
            tagging = "public=true&content-type=image"
            
            # Upload with all headers and metadata
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=file_data,
                ContentType=content_type,
                CacheControl=cache_control,
                Metadata=metadata,
                Tagging=tagging,
                **headers
            )
            
            logger.info(f"Uploaded {object_key} with CDN headers")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload {object_key} with CDN headers: {e}")
            return False

    def update_existing_object_headers(self, object_key: str) -> bool:
        """Update headers for existing object using copy operation"""
        try:
            # Get current object metadata
            self.client.head_object(Bucket=self.bucket_name, Key=object_key)
            
            # Prepare new headers
            cache_control = self.get_cache_policy_for_path(object_key)
            content_type = self.get_content_type(object_key)
            headers = self.get_optimization_headers(object_key)
            
            # Copy object to itself with new headers
            copy_source = {'Bucket': self.bucket_name, 'Key': object_key}
            
            self.client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=object_key,
                ContentType=content_type,
                CacheControl=cache_control,
                MetadataDirective='REPLACE',
                Metadata={
                    'updated-headers': 'true',
                    'cache-policy': cache_control.split(',')[0].strip()
                },
                **headers
            )
            
            logger.info(f"Updated headers for {object_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update headers for {object_key}: {e}")
            return False

    def bulk_update_cache_headers(self, prefix: str = "") -> Dict[str, int]:
        """Update cache headers for all objects with given prefix"""
        results = {'success': 0, 'failed': 0}
        
        try:
            paginator = self.client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
            
            for page in pages:
                if 'Contents' not in page:
                    continue
                    
                for obj in page['Contents']:
                    object_key = obj['Key']
                    if self.update_existing_object_headers(object_key):
                        results['success'] += 1
                    else:
                        results['failed'] += 1
                        
        except Exception as e:
            logger.error(f"Error during bulk header update: {e}")
            
        return results

    def configure_cloudflare_cache_rules(self) -> Dict[str, str]:
        """
        Generate Cloudflare cache rules configuration
        Note: This returns configuration that should be applied via Cloudflare dashboard or API
        """
        cache_rules = {
            "meme_images": {
                "expression": '(http.request.uri.path matches "^/.*\\.(jpg|jpeg|png|webp|gif)$") and (http.request.uri.path contains "/memes/" or http.request.uri.path contains "/generated/")',
                "action": "cache",
                "cache_level": "cache_everything",
                "edge_cache_ttl": 2592000,  # 30 days
                "browser_cache_ttl": 86400   # 1 day
            },
            "template_images": {
                "expression": '(http.request.uri.path matches "^/.*\\.(jpg|jpeg|png|webp|gif)$") and (http.request.uri.path contains "/templates/" or http.request.uri.path contains "/frames/")',
                "action": "cache",
                "cache_level": "cache_everything",
                "edge_cache_ttl": 31536000,  # 1 year
                "browser_cache_ttl": 2592000  # 30 days
            },
            "user_uploads": {
                "expression": '(http.request.uri.path matches "^/.*\\.(jpg|jpeg|png|webp|gif)$") and http.request.uri.path contains "/uploads/"',
                "action": "cache",
                "cache_level": "cache_everything",
                "edge_cache_ttl": 86400,    # 1 day
                "browser_cache_ttl": 3600   # 1 hour
            },
            "api_responses": {
                "expression": 'http.request.uri.path contains "/api/" and http.request.method eq "GET"',
                "action": "cache",
                "cache_level": "cache_everything",
                "edge_cache_ttl": 300,      # 5 minutes
                "browser_cache_ttl": 60     # 1 minute
            }
        }
        
        return cache_rules

def setup_cdn_caching() -> bool:
    """Setup CDN caching configuration"""
    try:
        manager = CDNManager()
        
        # Update headers for existing objects
        logger.info("Updating cache headers for existing objects...")
        results = manager.bulk_update_cache_headers()
        logger.info(f"Header update results: {results}")
        
        # Generate Cloudflare rules
        rules = manager.configure_cloudflare_cache_rules()
        logger.info("Cloudflare cache rules generated (apply via dashboard):")
        for rule_name, config in rules.items():
            logger.info(f"  {rule_name}: {config}")
            
        return True
        
    except Exception as e:
        logger.error(f"Failed to setup CDN caching: {e}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = setup_cdn_caching()
    exit(0 if success else 1)