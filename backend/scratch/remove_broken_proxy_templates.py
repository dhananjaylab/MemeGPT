"""
Remove templates with broken proxy-image URLs
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import select, delete
from db.session import get_db
from models.models import MemeTemplate


async def remove_broken_templates():
    """Remove templates using proxy-image URLs (broken imgflip links)"""
    
    db_gen = get_db()
    db = await db_gen.__anext__()
    
    try:
        # Find all templates using proxy-image URLs
        result = await db.execute(
            select(MemeTemplate).where(
                MemeTemplate.image_url.like('%proxy-image%')
            )
        )
        templates = result.scalars().all()
        
        print(f"Found {len(templates)} templates with proxy-image URLs:")
        for template in templates:
            print(f"  - ID {template.id}: {template.name}")
        
        if templates:
            # Delete them
            await db.execute(
                delete(MemeTemplate).where(
                    MemeTemplate.image_url.like('%proxy-image%')
                )
            )
            await db.commit()
            print(f"\n✅ Removed {len(templates)} templates with broken URLs")
        else:
            print("\n✅ No templates with proxy-image URLs found")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        await db.rollback()
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(remove_broken_templates())

# Made with Bob
