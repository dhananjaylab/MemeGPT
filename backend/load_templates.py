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


async def load_templates():
    """Load meme templates from JSON file into database"""
    
    # Initialize database engine
    _init_engine()
    
    # Load meme data
    meme_data_path = Path(__file__).parent.parent / "public" / "meme_data.json"
    
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
            existing_ids = {t.id for t in existing_templates}
            
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
                
                if existing:
                    # Update existing template
                    existing.name = template_data['name']
                    existing.alternative_names = template_data.get('alternative_names', [])
                    existing.file_path = template_data['file_path']
                    existing.font_path = template_data['font_path']
                    existing.text_color = template_data['text_color']
                    existing.text_stroke = template_data.get('text_stroke', False)
                    existing.usage_instructions = template_data['usage_instructions']
                    existing.number_of_text_fields = template_data['number_of_text_fields']
                    existing.text_coordinates_xy_wh = template_data['text_coordinates_xy_wh']
                    existing.example_output = template_data['example_output']
                    
                    # Set image URLs (assuming R2 public URL structure)
                    file_name = template_data['file_path']
                    existing.image_url = f"https://pub-85d20eba57fa4492b8ee36240e8c5b22.r2.dev/templates/{file_name}"
                    existing.preview_image_url = existing.image_url
                    
                    updated += 1
                    print(f"  ✏️  Updated: {template_data['name']}")
                else:
                    # Create new template
                    file_name = template_data['file_path']
                    image_url = f"https://pub-85d20eba57fa4492b8ee36240e8c5b22.r2.dev/templates/{file_name}"
                    
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
                        text_coordinates=template_data['text_coordinates_xy_wh'],  # Same as xy_wh
                        example_output=template_data['example_output'],
                        image_url=image_url,
                        preview_image_url=image_url
                    )
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
