"""Check if specific templates exist in the database."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.session import AsyncSessionLocal, _init_engine
from models.models import MemeTemplate
from sqlalchemy import select


async def check_templates():
    _init_engine()
    
    template_names = [
        "It's a trap",
        "Nobody absolutely nobody",
        "Ancient aliens",
        "Two buttons",
        "Always has been",
        "coffin dance",
        "Panik Kalm Panik"
    ]
    
    async with AsyncSessionLocal() as db:
        # Check each template
        for name in template_names:
            result = await db.execute(
                select(MemeTemplate).where(MemeTemplate.name.ilike(f"%{name}%"))
            )
            templates = result.scalars().all()
            
            if templates:
                for t in templates:
                    print(f"✓ Found: {t.name} (ID: {t.id}, Source: {t.source}, Imgflip ID: {t.imgflip_id})")
            else:
                print(f"✗ NOT FOUND: {name}")
        
        # Also check total template count
        result = await db.execute(select(MemeTemplate))
        all_templates = result.scalars().all()
        print(f"\nTotal templates in database: {len(all_templates)}")


if __name__ == "__main__":
    asyncio.run(check_templates())
