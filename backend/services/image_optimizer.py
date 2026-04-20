"""
Image Optimization Service
Handles image compression, resizing, and format conversion for CDN delivery
"""
import io
import logging
from pathlib import Path
from typing import Optional, Tuple
from enum import Enum
import asyncio

from PIL import Image, ImageOps
import aiofiles

logger = logging.getLogger(__name__)


class ImageFormat(str, Enum):
    """Supported image formats"""
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    AVIF = "avif"


class ImageOptimizer:
    """Optimizes images for CDN delivery with multiple formats and sizes"""
    
    # Image quality presets
    QUALITY_PRESETS = {
        "high": 90,
        "medium": 75,
        "low": 60,
    }
    
    # Standard responsive sizes for images
    RESPONSIVE_SIZES = {
        "thumbnail": 150,
        "small": 300,
        "medium": 600,
        "large": 1200,
        "original": None,  # Keep original size
    }
    
    def __init__(self, max_width: int = 2048, max_height: int = 2048):
        """
        Initialize image optimizer
        
        Args:
            max_width: Maximum width for images
            max_height: Maximum height for images
        """
        self.max_width = max_width
        self.max_height = max_height
    
    @staticmethod
    def _get_optimal_format(original_format: str) -> ImageFormat:
        """Determine optimal output format based on input"""
        format_map = {
            "jpg": ImageFormat.JPEG,
            "jpeg": ImageFormat.JPEG,
            "png": ImageFormat.PNG,
            "webp": ImageFormat.WEBP,
            "gif": ImageFormat.JPEG,  # Convert GIF to JPEG
        }
        return format_map.get(original_format.lower(), ImageFormat.JPEG)
    
    def optimize_image(
        self,
        image_data: bytes,
        target_size: Optional[str] = "medium",
        quality: str = "medium",
        target_format: Optional[ImageFormat] = None,
    ) -> bytes:
        """
        Optimize a single image
        
        Args:
            image_data: Raw image bytes
            target_size: Target size preset (thumbnail, small, medium, large, original)
            quality: Quality preset (high, medium, low)
            target_format: Output format (auto-detect if None)
            
        Returns:
            Optimized image bytes
        """
        try:
            # Open image
            img = Image.open(io.BytesIO(image_data))
            
            # Convert RGBA to RGB if needed (for JPEG compatibility)
            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = background
            
            # Determine format
            if not target_format:
                original_format = img.format or "jpeg"
                target_format = self._get_optimal_format(original_format)
            
            # Resize if target size specified
            if target_size and target_size != "original":
                max_dimension = self.RESPONSIVE_SIZES.get(target_size, 600)
                if max_dimension:
                    img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            
            # Apply dimension limits
            if img.width > self.max_width or img.height > self.max_height:
                img.thumbnail((self.max_width, self.max_height), Image.Resampling.LANCZOS)
            
            # Get quality level
            quality_level = self.QUALITY_PRESETS.get(quality, 75)
            
            # Save optimized image
            output = io.BytesIO()
            save_kwargs = {
                "format": target_format.value.upper(),
                "optimize": True,
            }
            
            if target_format in (ImageFormat.JPEG, ImageFormat.WEBP):
                save_kwargs["quality"] = quality_level
            elif target_format == ImageFormat.PNG:
                save_kwargs["compress_level"] = 9
            
            img.save(output, **save_kwargs)
            output.seek(0)
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error optimizing image: {e}")
            raise
    
    def generate_responsive_images(
        self,
        image_data: bytes,
        quality: str = "medium",
        include_formats: Optional[list] = None,
    ) -> dict:
        """
        Generate multiple sizes and formats for responsive delivery
        
        Args:
            image_data: Raw image bytes
            quality: Quality preset
            include_formats: List of formats to generate (default: [JPEG, WEBP])
            
        Returns:
            Dictionary mapping size/format combinations to optimized image bytes
        """
        if not include_formats:
            include_formats = [ImageFormat.JPEG, ImageFormat.WEBP]
        
        result = {}
        
        try:
            for size_name in ["thumbnail", "small", "medium", "large", "original"]:
                for fmt in include_formats:
                    key = f"{size_name}_{fmt.value}"
                    optimized = self.optimize_image(
                        image_data,
                        target_size=size_name,
                        quality=quality,
                        target_format=fmt,
                    )
                    result[key] = optimized
                    logger.debug(f"Generated {key}: {len(optimized)} bytes")
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating responsive images: {e}")
            raise
    
    def get_optimization_stats(self, original_data: bytes, optimized_data: bytes) -> dict:
        """
        Calculate optimization statistics
        
        Args:
            original_data: Original image bytes
            optimized_data: Optimized image bytes
            
        Returns:
            Dictionary with optimization stats
        """
        original_size = len(original_data)
        optimized_size = len(optimized_data)
        reduction_percent = ((original_size - optimized_size) / original_size * 100) if original_size > 0 else 0
        
        return {
            "original_size_bytes": original_size,
            "optimized_size_bytes": optimized_size,
            "reduction_bytes": original_size - optimized_size,
            "reduction_percent": round(reduction_percent, 2),
            "compression_ratio": round(original_size / optimized_size, 2) if optimized_size > 0 else 0,
        }


class AsyncImageOptimizer(ImageOptimizer):
    """Async wrapper for image optimization"""
    
    async def optimize_image_async(
        self,
        image_data: bytes,
        target_size: Optional[str] = "medium",
        quality: str = "medium",
        target_format: Optional[ImageFormat] = None,
    ) -> bytes:
        """Async image optimization"""
        return await asyncio.to_thread(
            self.optimize_image,
            image_data,
            target_size,
            quality,
            target_format,
        )
    
    async def generate_responsive_images_async(
        self,
        image_data: bytes,
        quality: str = "medium",
        include_formats: Optional[list] = None,
    ) -> dict:
        """Async responsive image generation"""
        return await asyncio.to_thread(
            self.generate_responsive_images,
            image_data,
            quality,
            include_formats,
        )
