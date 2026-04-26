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
    meme_data_path = Path(__file__).parent.parent / "public" / "meme_data.json"
    
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
                
                # Prepare image URL
                file_name = template_data['file_path']
                image_url = f"{settings.r2_public_url}/templates/{file_name}"
                
                if existing_template:
                    # Update
                    existing_template.name = template_data['name']
                    existing_template.alternative_names = template_data.get('alternative_names', [])
                    existing_template.file_path = template_data['file_path']
                    existing_template.font_path = template_data['font_path']
                    existing_template.text_color = template_data['text_color']
                    existing_template.text_stroke = template_data.get('text_stroke', False)
                    existing_template.usage_instructions = template_data['usage_instructions']
                    existing_template.number_of_text_fields = template_data['number_of_text_fields']
                    existing_template.text_coordinates_xy_wh = template_data['text_coordinates_xy_wh']
                    existing_template.text_coordinates = template_data['text_coordinates_xy_wh']
                    existing_template.example_output = template_data['example_output']
                    existing_template.image_url = image_url
                    existing_template.preview_image_url = image_url
                    updated += 1
                    print(f"  ✏️  Updated: {template_data['name']}")
                else:
                    # Create new
                    template = MemeTemplate(
                        id=template_id,
                        name=template_data['name'],
                        alternative_names=template_data.get('alternative_names', []),
                        file_path=template_data['file_path'],
                        font_path=template_data['font_path'],
                        text_color=template_data['text_color'],
                        text_stroke=template_data.get('text_stroke', False),
                        usage_instructions=template_data['usage_instructions'],
                        number_of_text_fields=template_data['number_of_text_fields'],
                        text_coordinates_xy_wh=template_data['text_coordinates_xy_wh'],
                        text_coordinates=template_data['text_coordinates_xy_wh'],
                        example_output=template_data['example_output'],
                        image_url=image_url,
                        preview_image_url=image_url
                    )
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
