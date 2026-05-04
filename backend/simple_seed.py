"""
Simple script to seed templates using the existing database setup.
Run with: python simple_seed.py
"""
import asyncio
import json
from pathlib import Path

# Setup path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from db.session import get_db, _init_engine
from models.models import MemeTemplate
from core.config import settings


async def main():
    """Seed templates into database"""
    print("🚀 Seeding meme templates...\n")
    
    # Initialize engine
    _init_engine()
    
    # Load template data
    meme_data_path = Path(__file__).parent.parent / "public" / "meme_data.json"
    
    if not meme_data_path.exists():
        print(f"❌ Error: meme_data.json not found at {meme_data_path}")
        return
    
    with open(meme_data_path, 'r', encoding='utf-8') as f:
        templates_data = json.load(f)
    
    print(f"📄 Loaded {len(templates_data)} templates from JSON\n")
    
    # Get database session using the generator
    db_gen = get_db()
    db = await anext(db_gen)
    
    try:
        # Check existing
        result = await db.execute(select(MemeTemplate))
        existing = result.scalars().all()
        print(f"📊 Current database has {len(existing)} templates\n")
        
        added = 0
        updated = 0
        
        for template_data in templates_data:
            tid = template_data['id']
            
            # Check if exists
            result = await db.execute(
                select(MemeTemplate).where(MemeTemplate.id == tid)
            )
            existing_template = result.scalar_one_or_none()
            
            # Prepare data
            file_name = template_data['file_path']
            image_url = f"{settings.r2_public_url}/templates/{file_name}"
            
            if existing_template:
                # Update existing
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
                    id=tid,
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
                db.add(template)
                added += 1
                print(f"  ➕ Added: {template_data['name']}")
        
        # Commit
        await db.commit()
        
        print(f"\n✅ Success!")
        print(f"   Added: {added} templates")
        print(f"   Updated: {updated} templates")
        print(f"   Total in database: {added + updated}\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        await db.rollback()
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
