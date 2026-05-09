"""Verify all templates are accessible via API."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.session import AsyncSessionLocal, _init_engine
from models.models import MemeTemplate
from sqlalchemy import select


async def verify_templates():
    """Check if all templates are properly configured."""
    _init_engine()
    
    missing_templates = [
        "It's a trap",
        "Nobody absolutely nobody",
        "Ancient aliens",
        "Two buttons",
        "Always has been",
        "coffin dance",
        "Panik"
    ]
    
    async with AsyncSessionLocal() as db:
        # Get all templates
        result = await db.execute(select(MemeTemplate))
        all_templates = result.scalars().all()
        
        print(f"Total templates in database: {len(all_templates)}\n")
        
        # Check each "missing" template
        print("Checking reported missing templates:")
        print("=" * 60)
        
        for search_name in missing_templates:
            found = False
            for template in all_templates:
                if search_name.lower() in template.name.lower():
                    found = True
                    print(f"\n✓ FOUND: {template.name}")
                    print(f"  ID: {template.id}")
                    print(f"  Source: {template.source}")
                    print(f"  Image URL: {template.image_url}")
                    print(f"  Text fields: {template.number_of_text_fields}")
                    
                    # Check if image URL is accessible
                    if template.image_url:
                        if template.image_url.startswith('/api/memes/proxy-image'):
                            print(f"  ⚠ Uses proxy (external image)")
                        elif template.image_url.startswith('/frames/'):
                            print(f"  ✓ Local image")
                        else:
                            print(f"  ? Unknown image source")
                    else:
                        print(f"  ✗ NO IMAGE URL")
                    break
            
            if not found:
                print(f"\n✗ NOT FOUND: {search_name}")
        
        print("\n" + "=" * 60)
        print("\nAll templates:")
        for t in sorted(all_templates, key=lambda x: x.id):
            print(f"  {t.id:2d}. {t.name}")


if __name__ == "__main__":
    asyncio.run(verify_templates())
