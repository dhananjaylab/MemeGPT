import asyncio
import json
from pathlib import Path
import sys
sys.path.insert(0, '.')
from sqlalchemy import select
from db.session import get_db, _init_engine
from models.models import MemeTemplate
from core.config import settings

async def seed():
    print("🚀 Seeding templates...")
    _init_engine()
    meme_data_path = Path('../public/meme_data.json')
    with open(meme_data_path, 'r') as f:
        templates_data = json.load(f)
    
    print(f"📄 Loaded {len(templates_data)} templates\n")
    
    db_gen = get_db()
    db = await db_gen.__anext__()
    
    try:
        added = 0
        updated = 0
        
        # Fallback image URLs using imgflip API (publicly available meme templates)
        fallback_images = {
            0: "https://i.imgflip.com/30b1gx.jpg",  # Drake
            1: "https://i.imgflip.com/1ur9b0.jpg",  # Distracted Boyfriend
            2: "https://i.imgflip.com/22bdq6.jpg",  # Left Exit
            3: "https://i.imgflip.com/26am.jpg",    # One Does Not Simply
            4: "https://i.imgflip.com/1bij.jpg",    # Success Kid
            5: "https://i.imgflip.com/1g8my4.jpg",  # Disaster Girl
            6: "https://i.imgflip.com/gk5el.jpg",   # Hide the Pain Harold
            7: "https://i.imgflip.com/1ihzfe.jpg",  # Surprised Pikachu
            8: "https://i.imgflip.com/261o3j.jpg",  # Change My Mind
            9: "https://i.imgflip.com/1c1uej.jpg",  # Leonardo Dicaprio Cheers
            10: "https://i.imgflip.com/1otk96.jpg", # Trump Bill Signing
        }
        
        for t in templates_data:
            result = await db.execute(select(MemeTemplate).where(MemeTemplate.id == t['id']))
            existing = result.scalar_one_or_none()
            
            # Use fallback image if available, otherwise use R2 URL
            image_url = fallback_images.get(t['id'], f"{settings.r2_public_url}/templates/{t['file_path']}")
            
            if existing:
                # Update existing template with new image URL
                existing.name = t['name']
                existing.alternative_names = t.get('alternative_names', [])
                existing.file_path = t['file_path']
                existing.font_path = t['font_path']
                existing.text_color = t['text_color']
                existing.text_stroke = t.get('text_stroke', False)
                existing.usage_instructions = t['usage_instructions']
                existing.number_of_text_fields = t['number_of_text_fields']
                existing.text_coordinates_xy_wh = t['text_coordinates_xy_wh']
                existing.text_coordinates = t['text_coordinates_xy_wh']
                existing.example_output = t['example_output']
                existing.image_url = image_url
                existing.preview_image_url = image_url
                updated += 1
                print(f"  ✏️  Updated: {t['name']}")
            else:
                template = MemeTemplate(
                    id=t['id'],
                    name=t['name'],
                    alternative_names=t.get('alternative_names', []),
                    file_path=t['file_path'],
                    font_path=t['font_path'],
                    text_color=t['text_color'],
                    text_stroke=t.get('text_stroke', False),
                    usage_instructions=t['usage_instructions'],
                    number_of_text_fields=t['number_of_text_fields'],
                    text_coordinates_xy_wh=t['text_coordinates_xy_wh'],
                    text_coordinates=t['text_coordinates_xy_wh'],
                    example_output=t['example_output'],
                    image_url=image_url,
                    preview_image_url=image_url
                )
                db.add(template)
                added += 1
                print(f"  ➕ Added: {t['name']}")
        
        await db.commit()
        print(f"\n✅ Success! Added {added} templates, Updated {updated} templates")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(seed())

# Made with Bob
