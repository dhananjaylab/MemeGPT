"""
Script to load meme templates from meme_data.json into the database.
Run this script to populate the database with meme templates.

Usage:
    python load_templates.py
"""
import asyncio
import json
import sys
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from db.session import _init_engine, engine
from models.models import MemeTemplate
from services.template_catalog import build_template_fields


async def load_templates():
    """Load meme templates from JSON file into database"""
    
    # Initialize database engine
    _init_engine()
    
    # Load meme data
    meme_data_path = Path(__file__).parent / "public" / "meme_data.json"
    
    if not meme_data_path.exists():
        print(f"❌ Error: meme_data.json not found at {meme_data_path}")
        return
    
    with open(meme_data_path, 'r', encoding='utf-8') as f:
        templates_data = json.load(f)
    
    print(f"📄 Loaded {len(templates_data)} templates from meme_data.json")
    
    # Create database session
    async with AsyncSession(engine) as db:
        try:
            # Check existing templates
            result = await db.execute(select(MemeTemplate))
            existing_templates = result.scalars().all()
            
            print(f"📊 Found {len(existing_templates)} existing templates in database")
            
            added = 0
            updated = 0
            
            for template_data in templates_data:
                template_id = template_data['id']
                
                # Check if template exists
                result = await db.execute(
                    select(MemeTemplate).where(MemeTemplate.id == template_id)
                )
                existing = result.scalar_one_or_none()
                
                fields = build_template_fields(template_data)

                if existing:
                    # Update existing template
                    for key, value in fields.items():
                        setattr(existing, key, value)
                    updated += 1
                    print(f"  ✏️  Updated: {template_data['name']}")
                else:
                    # Create new template
                    template = MemeTemplate(id=template_id, **fields)
                    db.add(template)
                    added += 1
                    print(f"  ➕ Added: {template_data['name']}")
            
            # Commit changes
            await db.commit()
            
            print(f"\n✅ Success!")
            print(f"   Added: {added} templates")
            print(f"   Updated: {updated} templates")
            print(f"   Total: {len(templates_data)} templates in database")
            
        except Exception as e:
            print(f"\n❌ Error loading templates: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            raise


if __name__ == "__main__":
    print("🚀 Loading meme templates into database...\n")
    asyncio.run(load_templates())

# Made with Bob
