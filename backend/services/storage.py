import asyncio
import boto3
from botocore.exceptions import ClientError
from pathlib import Path
from typing import Optional, Tuple, Dict, List
from PIL import Image, ImageOps, ImageFilter
import io
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from ..core.config import settings
from .cdn_config import CDNManager

logger = logging.getLogger(__name__)

# Initialize R2 client
r2_client = boto3.client(
    's3',
    endpoint_url=settings.r2_endpoint_url,
    aws_access_key_id=settings.r2_access_key,
    aws_secret_access_key=settings.r2_secret_key,
    region_name='auto'
) if settings.r2_access_key else None

# Initialize CDN manager
cdn_manager = CDNManager() if settings.r2_access_key else None

class ImageOptimizer:
    """Advanced image optimization pipeline"""
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.supported_formats = {
            'webp': {'quality': 90, 'method': 6},
            'jpeg': {'quality': 85, 'progressive': True},
            'png': {'optimize': True, 'compress_level': 6}
        }
        
    @staticmethod
    def calculate_file_hash(file_data: bytes) -> str:
        """Calculate SHA-256 hash of file data"""
        return hashlib.sha256(file_data).hexdigest()[:16]
    
    @staticmethod
    def get_optimal_dimensions(width: int, height: int, max_size: int = 2048) -> Tuple[int, int]:
        """Calculate optimal dimensions while maintaining aspect ratio"""
        if width <= max_size and height <= max_size:
            return width, height
            
        ratio = min(max_size / width, max_size / height)
        return int(width * ratio), int(height * ratio)
    
    def detect_image_quality(self, image: Image.Image) -> Dict[str, any]:
        """Analyze image to determine optimal compression settings"""
        width, height = image.size
        pixel_count = width * height
        
        # Analyze image complexity
        grayscale = image.convert('L')
        histogram = grayscale.histogram()
        
        # Calculate entropy (complexity measure)
        total_pixels = sum(histogram)
        entropy = -sum((count/total_pixels) * (count/total_pixels).bit_length() 
                      for count in histogram if count > 0)
        
        # Determine quality based on image characteristics
        if pixel_count > 1000000:  # Large images
            base_quality = 80
        elif entropy > 7:  # High complexity
            base_quality = 90
        else:  # Simple images
            base_quality = 75
            
        return {
            'recommended_quality': base_quality,
            'complexity': entropy,
            'pixel_count': pixel_count,
            'is_high_detail': entropy > 7
        }
    
    def optimize_for_web(self, image: Image.Image, quality: int = None, 
                        format_preference: str = "webp") -> Tuple[io.BytesIO, str, Dict[str, any]]:
        """
        Optimize image for web delivery with adaptive quality
        Returns optimized image data, content type, and metadata
        """
        # Analyze image for optimal settings
        analysis = self.detect_image_quality(image)
        if quality is None:
            quality = analysis['recommended_quality']
        
        # Convert to RGB if necessary
        if image.mode in ("RGBA", "P"):
            # Preserve transparency for WebP and PNG
            if format_preference.lower() in ["webp", "png"]:
                image = image.convert("RGBA")
            else:
                # Create white background for JPEG
                background = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "RGBA":
                    background.paste(image, mask=image.split()[-1])
                else:
                    background.paste(image)
                image = background
        else:
            image = image.convert("RGB")
        
        # Apply auto-orientation
        image = ImageOps.exif_transpose(image)
        
        # Get original dimensions
        original_width, original_height = image.size
        
        # Optimize dimensions
        new_width, new_height = self.get_optimal_dimensions(original_width, original_height)
        if (new_width, new_height) != (original_width, original_height):
            # Use high-quality resampling
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Apply subtle sharpening for resized images
        if (new_width, new_height) != (original_width, original_height):
            image = image.filter(ImageFilter.UnsharpMask(radius=0.5, percent=50, threshold=3))
        
        output = io.BytesIO()
        metadata = {
            'original_size': f"{original_width}x{original_height}",
            'optimized_size': f"{new_width}x{new_height}",
            'optimization_applied': True,
            'quality_used': quality,
            'complexity_score': analysis['complexity']
        }
        
        # Choose format and optimize with adaptive settings
        if format_preference.lower() == "webp":
            webp_settings = self.supported_formats['webp'].copy()
            webp_settings['quality'] = quality
            image.save(output, format="WEBP", **webp_settings, optimize=True)
            content_type = "image/webp"
            metadata['format'] = 'webp'
        elif format_preference.lower() == "png":
            png_settings = self.supported_formats['png'].copy()
            image.save(output, format="PNG", **png_settings)
            content_type = "image/png"
            metadata['format'] = 'png'
        else:  # JPEG
            jpeg_settings = self.supported_formats['jpeg'].copy()
            jpeg_settings['quality'] = quality
            image.save(output, format="JPEG", **jpeg_settings, optimize=True)
            content_type = "image/jpeg"
            metadata['format'] = 'jpeg'
        
        output.seek(0)
        metadata['file_size'] = len(output.getvalue())
        metadata['compression_ratio'] = round(metadata['file_size'] / (original_width * original_height * 3), 4)
        
        return output, content_type, metadata
    
    def create_multiple_variants(self, image: Image.Image) -> Dict[str, Tuple[io.BytesIO, str, Dict]]:
        """Create multiple optimized variants of an image"""
        variants = {}
        
        # High quality WebP (primary)
        webp_data, webp_type, webp_meta = self.optimize_for_web(image, quality=90, format_preference="webp")
        variants['webp'] = (webp_data, webp_type, webp_meta)
        
        # Fallback JPEG
        jpeg_data, jpeg_type, jpeg_meta = self.optimize_for_web(image, quality=85, format_preference="jpeg")
        variants['jpeg'] = (jpeg_data, jpeg_type, jpeg_meta)
        
        # Thumbnail (WebP, 300px max)
        thumb_image = image.copy()
        thumb_width, thumb_height = self.get_optimal_dimensions(image.width, image.height, max_size=300)
        thumb_image = thumb_image.resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)
        thumb_data, thumb_type, thumb_meta = self.optimize_for_web(thumb_image, quality=80, format_preference="webp")
        variants['thumbnail'] = (thumb_data, thumb_type, thumb_meta)
        
        return variants

# Initialize optimizer
image_optimizer = ImageOptimizer()

def optimize_image(file_path: Path, quality: int = 85) -> Tuple[io.BytesIO, str]:
    """
    Legacy function for backward compatibility
    Optimizes the image for web use.
    Returns a BytesIO object and the content type.
    """
    img = Image.open(file_path)
    data, content_type, _ = image_optimizer.optimize_for_web(img, quality=quality)
    return data, content_type

async def upload_to_r2(file_path: Path, object_key: str, optimize: bool = True, 
                  create_variants: bool = False) -> Optional[Dict[str, str]]:
    """
    Upload image to Cloudflare R2 with optimization and CDN configuration
    Returns dictionary with URLs for different variants
    """
    if not r2_client or not cdn_manager:
        logger.error("R2 client or CDN manager not initialized. Check your credentials.")
        return None
        
    try:
        # Load image
        img = Image.open(file_path)
        
        # Generate file hash for cache busting
        with open(file_path, 'rb') as f:
            file_hash = image_optimizer.calculate_file_hash(f.read())
        
        # Prepare object key with hash
        base_key = object_key.rsplit('.', 1)[0] if '.' in object_key else object_key
        
        urls = {}
        
        if create_variants:
            # Create multiple optimized variants
            variants = image_optimizer.create_multiple_variants(img)
            
            for variant_name, (data, content_type, metadata) in variants.items():
                variant_key = f"{base_key}-{file_hash}.{variant_name}.{metadata['format']}"
                
                success = await _upload_variant(variant_key, data, content_type, metadata)
                if success:
                    urls[variant_name] = f"{settings.r2_public_url}/{variant_key}"
                    
        else:
            # Single optimized upload
            if optimize:
                data, content_type, metadata = image_optimizer.optimize_for_web(img)
                final_key = f"{base_key}-{file_hash}.webp"
            else:
                with open(file_path, 'rb') as f:
                    data = io.BytesIO(f.read())
                content_type = cdn_manager.get_content_type(object_key)
                metadata = {'optimization_applied': False}
                final_key = f"{base_key}-{file_hash}.{object_key.split('.')[-1]}"
            
            success = await _upload_variant(final_key, data, content_type, metadata)
            if success:
                urls['primary'] = f"{settings.r2_public_url}/{final_key}"
        
        return urls if urls else None
        
    except Exception as e:
        logger.error(f"Unexpected error uploading to R2: {e}")
        return None

async def _upload_variant(object_key: str, data: io.BytesIO, content_type: str, 
                         metadata: Dict[str, any]) -> bool:
    """Upload a single image variant with CDN headers"""
    def _upload():
        try:
            # Use CDN manager for upload with proper headers
            return cdn_manager.upload_with_cdn_headers(
                file_data=data,
                object_key=object_key,
                custom_headers={
                    'Content-Type': content_type,
                    'X-Optimization-Applied': str(metadata.get('optimization_applied', False)),
                    'X-Original-Size': metadata.get('original_size', 'unknown'),
                    'X-File-Size': str(metadata.get('file_size', 0))
                }
            )
        except Exception as e:
            logger.error(f"Error uploading variant {object_key}: {e}")
            return False
    
    # Run upload in thread pool to avoid blocking
    return await asyncio.get_event_loop().run_in_executor(
        image_optimizer.executor, _upload
    )

async def upload_optimized_meme(file_path: Path, meme_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, str]]:
    """
    Upload a generated meme with full optimization pipeline
    Creates multiple variants for different use cases
    """
    # Determine object key structure
    if user_id:
        object_key = f"memes/{user_id}/{meme_id}"
    else:
        object_key = f"memes/public/{meme_id}"
    
    return await upload_to_r2(file_path, object_key, optimize=True, create_variants=True)

async def upload_template_image(file_path: Path, template_name: str) -> Optional[str]:
    """Upload template image with long-term caching"""
    object_key = f"templates/{template_name}"
    
    urls = await upload_to_r2(file_path, object_key, optimize=True, create_variants=False)
    return urls.get('primary') if urls else None

async def batch_optimize_existing_images(prefix: str = "", max_concurrent: int = 5) -> Dict[str, int]:
    """
    Batch optimize existing images in R2 storage
    Downloads, optimizes, and re-uploads with proper CDN headers
    """
    if not r2_client:
        logger.error("R2 client not initialized")
        return {'success': 0, 'failed': 0, 'skipped': 0}
    
    results = {'success': 0, 'failed': 0, 'skipped': 0}
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def optimize_single_image(object_key: str):
        async with semaphore:
            try:
                # Check if already optimized
                response = r2_client.head_object(Bucket=settings.r2_bucket_name, Key=object_key)
                if response.get('Metadata', {}).get('optimization-applied') == 'true':
                    results['skipped'] += 1
                    return
                
                # Download image
                obj = r2_client.get_object(Bucket=settings.r2_bucket_name, Key=object_key)
                image_data = obj['Body'].read()
                
                # Optimize
                img = Image.open(io.BytesIO(image_data))
                optimized_data, content_type, metadata = image_optimizer.optimize_for_web(img)
                
                # Re-upload with optimization
                success = cdn_manager.upload_with_cdn_headers(
                    file_data=optimized_data,
                    object_key=object_key,
                    custom_headers={
                        'Content-Type': content_type,
                        'X-Optimization-Applied': 'true',
                        'X-Batch-Optimized': 'true'
                    }
                )
                
                if success:
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    
            except Exception as e:
                logger.error(f"Failed to optimize {object_key}: {e}")
                results['failed'] += 1
    
    try:
        # List all images with prefix
        paginator = r2_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=settings.r2_bucket_name, Prefix=prefix)
        
        tasks = []
        for page in pages:
            if 'Contents' not in page:
                continue
                
            for obj in page['Contents']:
                object_key = obj['Key']
                # Only process image files
                if any(ext in object_key.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                    tasks.append(optimize_single_image(object_key))
        
        # Execute all optimization tasks
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
    except Exception as e:
        logger.error(f"Error during batch optimization: {e}")
    
    return results

