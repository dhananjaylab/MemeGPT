"""
Simple script to seed meme templates into the database.
Run with: python seed_templates.py
"""
import asyncio
import json
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Import models
import sys
sys.path.insert(0, str(Path(__file__).parent))

from models.models import MemeTemplate, Base
from core.config import settings
from services.template_catalog import build_template_fields


async def seed_templates():
    """Seed meme templates from JSON file"""
    
    # Create engine
    engine = create_async_engine(settings.database_url, echo=True)
    
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Load meme data
    meme_data_path = Path(__file__).parent / "public" / "meme_data.json"
    
    if not meme_data_path.exists():
        print(f"❌ Error: meme_data.json not found at {meme_data_path}")
        return
    
    with open(meme_data_path, 'r', encoding='utf-8') as f:
        templates_data = json.load(f)
    
    print(f"\n📄 Loaded {len(templates_data)} templates from meme_data.json\n")
    
    async with async_session() as session:
        try:
            # Check existing templates
            result = await session.execute(select(MemeTemplate))
            existing = result.scalars().all()
            print(f"📊 Found {len(existing)} existing templates in database\n")
            
            added = 0
            updated = 0
            
            for template_data in templates_data:
                template_id = template_data['id']
                
                # Check if exists
                result = await session.execute(
                    select(MemeTemplate).where(MemeTemplate.id == template_id)
                )
                existing_template = result.scalar_one_or_none()
                
                fields = build_template_fields(template_data)
                
                if existing_template:
                    # Update
                    for key, value in fields.items():
                        setattr(existing_template, key, value)
                    updated += 1
                    print(f"  ✏️  Updated: {template_data['name']}")
                else:
                    # Create new
                    template = MemeTemplate(id=template_id, **fields)
                    session.add(template)
                    added += 1
                    print(f"  ➕ Added: {template_data['name']}")
            
            # Commit all changes
            await session.commit()
            
            print(f"\n✅ Success!")
            print(f"   Added: {added} templates")
            print(f"   Updated: {updated} templates")
            print(f"   Total: {added + updated} templates in database\n")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    print("🚀 Seeding meme templates into database...\n")
    asyncio.run(seed_templates())
    print("✨ Done!\n")

# Made with Bob
