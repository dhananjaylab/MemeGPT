"""
Imgflip API integration service for fetching popular meme templates.
"""
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from core.config import settings
from models.models import MemeTemplate


IMGFLIP_API_URL = "https://api.imgflip.com/get_memes"
IMGFLIP_CAPTION_URL = "https://api.imgflip.com/caption_image"
CACHE_DURATION_HOURS = 24


class ImgflipService:
    """Service for interacting with Imgflip API"""
    
    @staticmethod
    async def fetch_popular_templates() -> List[Dict[str, Any]]:
        """
        Fetch popular meme templates from Imgflip API.
        
        Returns:
            List of template dictionaries with keys: id, name, url, width, height, box_count
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(IMGFLIP_API_URL)
                response.raise_for_status()
                
                data = response.json()
                if not data.get("success"):
                    raise Exception("Imgflip API returned unsuccessful response")
                
                memes = data.get("data", {}).get("memes", [])
                return memes[:100]  # Return top 100 templates
                
        except httpx.HTTPError as e:
            raise Exception(f"Failed to fetch Imgflip templates: {str(e)}")
        except Exception as e:
            raise Exception(f"Error processing Imgflip response: {str(e)}")
    
    @staticmethod
    def generate_text_coordinates(box_count: int) -> List[List[int]]:
        """
        Generate default text coordinates for Imgflip templates based on box count.
        
        Args:
            box_count: Number of text boxes in the template
            
        Returns:
            List of [x, y, width, height] coordinates in percentage
        """
        if box_count == 1:
            # Single text box at top
            return [[10, 5, 80, 20]]
        elif box_count == 2:
            # Two text boxes: top and bottom
            return [
                [10, 5, 80, 20],   # Top
                [10, 75, 80, 20]   # Bottom
            ]
        elif box_count == 3:
            # Three text boxes: top, middle, bottom
            return [
                [10, 5, 80, 15],   # Top
                [10, 42, 80, 15],  # Middle
                [10, 80, 80, 15]   # Bottom
            ]
        else:
            # For 4+ boxes, distribute evenly
            coords = []
            spacing = 100 / (box_count + 1)
            for i in range(box_count):
                y = spacing * (i + 1) - 10
                coords.append([10, int(y), 80, 15])
            return coords
    
    @staticmethod
    async def sync_templates_to_db(db: AsyncSession) -> Dict[str, Any]:
        """
        Fetch Imgflip templates and sync them to the database.
        Updates existing templates or creates new ones.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with sync statistics
        """
        try:
            # Fetch templates from Imgflip
            imgflip_templates = await ImgflipService.fetch_popular_templates()
            
            stats = {
                "fetched": len(imgflip_templates),
                "created": 0,
                "updated": 0,
                "errors": 0
            }
            
            current_time = datetime.utcnow()
            
            for template_data in imgflip_templates:
                try:
                    imgflip_id = str(template_data.get("id"))
                    name = template_data.get("name", "Unknown Template")
                    url = template_data.get("url", "")
                    box_count = template_data.get("box_count", 2)
                    
                    # Check if template already exists
                    result = await db.execute(
                        select(MemeTemplate).where(MemeTemplate.imgflip_id == imgflip_id)
                    )
                    existing_template = result.scalar_one_or_none()
                    
                    # Generate text coordinates
                    text_coords = ImgflipService.generate_text_coordinates(box_count)
                    
                    if existing_template:
                        # Update existing template
                        existing_template.name = name
                        existing_template.image_url = url
                        existing_template.preview_image_url = url
                        existing_template.box_count = box_count
                        existing_template.number_of_text_fields = box_count
                        existing_template.text_coordinates = text_coords
                        existing_template.last_synced_at = current_time
                        existing_template.updated_at = current_time
                        stats["updated"] += 1
                    else:
                        # Create new template
                        new_template = MemeTemplate(
                            name=name,
                            alternative_names=[],
                            file_path="",  # Not used for Imgflip templates
                            font_path="fonts/impact.ttf",  # Default font
                            text_color="#FFFFFF",
                            text_stroke=True,
                            usage_instructions=f"Imgflip template: {name}",
                            number_of_text_fields=box_count,
                            text_coordinates=text_coords,
                            text_coordinates_xy_wh=text_coords,
                            example_output=[],
                            image_url=url,
                            preview_image_url=url,
                            source="imgflip",
                            imgflip_id=imgflip_id,
                            box_count=box_count,
                            last_synced_at=current_time
                        )
                        db.add(new_template)
                        stats["created"] += 1
                        
                except Exception as e:
                    print(f"Error syncing template {template_data.get('name', 'unknown')}: {str(e)}")
                    stats["errors"] += 1
                    continue
            
            await db.commit()
            return stats
            
        except Exception as e:
            await db.rollback()
            raise Exception(f"Failed to sync Imgflip templates: {str(e)}")
    
    @staticmethod
    async def should_sync(db: AsyncSession) -> bool:
        """
        Check if Imgflip templates should be synced based on last sync time.
        
        Args:
            db: Database session
            
        Returns:
            True if sync is needed, False otherwise
        """
        try:
            # Get the most recent Imgflip template sync time
            result = await db.execute(
                select(MemeTemplate.last_synced_at)
                .where(MemeTemplate.source == "imgflip")
                .order_by(MemeTemplate.last_synced_at.desc())
                .limit(1)
            )
            last_sync = result.scalar_one_or_none()
            
            if not last_sync:
                return True  # Never synced before
            
            # Check if cache has expired
            cache_expiry = last_sync + timedelta(hours=CACHE_DURATION_HOURS)
            return datetime.utcnow() > cache_expiry
            
        except Exception:
            return True  # Sync on error to be safe
    
    @staticmethod
    async def get_template_by_imgflip_id(db: AsyncSession, imgflip_id: str) -> Optional[MemeTemplate]:
        """
        Get a template by its Imgflip ID.
        
        Args:
            db: Database session
            imgflip_id: Imgflip template ID
            
        Returns:
            MemeTemplate if found, None otherwise
        """
        result = await db.execute(
            select(MemeTemplate).where(MemeTemplate.imgflip_id == imgflip_id)
        )
        return result.scalar_one_or_none()


# Singleton instance
imgflip_service = ImgflipService()

# Made with Bob
