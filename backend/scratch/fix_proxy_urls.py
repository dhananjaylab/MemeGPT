"""
Fix broken proxy-image URLs by fetching fresh URLs from Imgflip API
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import select
from db.session import get_db
from models.models import MemeTemplate
from services.imgflip import ImgflipService


async def fix_proxy_urls():
    """Update templates with broken proxy URLs to use fresh Imgflip URLs"""
    
    db_gen = get_db()
    db = await db_gen.__anext__()
    
    try:
        # Fetch fresh templates from Imgflip
        print("Fetching fresh templates from Imgflip API...")
        imgflip_templates = await ImgflipService.fetch_popular_templates()
        
        # Create a mapping of template names to URLs
        imgflip_map = {t['name']: t['url'] for t in imgflip_templates}
        print(f"Fetched {len(imgflip_map)} templates from Imgflip")
        
        # Find all templates using proxy-image URLs
        result = await db.execute(
            select(MemeTemplate).where(
                MemeTemplate.image_url.like('%proxy-image%')
            )
        )
        templates = result.scalars().all()
        
        print(f"\nFound {len(templates)} templates using proxy-image URLs")
        
        updated = 0
        for template in templates:
            # Try to find matching Imgflip template by name
            if template.name in imgflip_map:
                new_url = imgflip_map[template.name]
                print(f"  Updating {template.name} (ID {template.id})")
                print(f"    Old: {template.image_url}")
                print(f"    New: {new_url}")
                
                template.image_url = new_url
                template.preview_image_url = new_url
                template.fallback_url = new_url
                updated += 1
            else:
                print(f"  ⚠️  No match found for: {template.name}")
        
        await db.commit()
        print(f"\n✅ Updated {updated} templates")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        await db.rollback()
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(fix_proxy_urls())

# Made with Bob
