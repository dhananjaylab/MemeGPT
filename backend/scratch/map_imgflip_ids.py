"""Map local templates to Imgflip IDs and update with fresh URLs."""
import asyncio
import httpx
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Template name to Imgflip ID mapping (from Imgflip API)
# These are the most popular templates that match our local ones
TEMPLATE_MAPPING = {
    "Drake Hotline Bling": "181913649",
    "Distracted Boyfriend": "112126428",
    "Left Exit 12 Off Ramp": "124822590",
    "One Does Not Simply": "61579",
    "UNO Draw 25 Cards": "217743513",
    "Expanding Brain": "93895088",
    "Hide the Pain Harold": "27813981",
    "Success Kid": "61544",
    "But That's None Of My Business": "16464531",
    "Disaster Girl": "97984",
    "Roll Safe Think About It": "89370399",
    "This Is Fine": "55311130",
    "Surprised Pikachu": "155067746",
    "Woman Yelling At Cat": "188390779",
    "Two Buttons": "87743020",
    "Always Has Been": "252600902",
    "Gru's Plan": "131940431",
    "Panik Kalm Panik": "178591752",
    "Nobody Absolutely Nobody": "196652226",
    "Me Explaining To My Mom": "110163934",
    "It's A Trap": "5677926",
    "Mocking SpongeBob": "102156234",
    "Bike Fall": "100947",
    "Change My Mind": "129242436",
    "Ancient Aliens": "101470",
    "Coffin Dance": "256616965",
}


async def fetch_imgflip_templates():
    """Fetch current templates from Imgflip API."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get("https://api.imgflip.com/get_memes")
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success"):
                raise Exception("Imgflip API returned unsuccessful response")
            
            memes = data.get("data", {}).get("memes", [])
            return {str(m["id"]): m for m in memes}
    except Exception as e:
        print(f"Error fetching Imgflip templates: {e}")
        return {}


async def update_template_urls():
    """Update local templates with Imgflip IDs and fresh URLs."""
    from db.session import AsyncSessionLocal, _init_engine
    from models.models import MemeTemplate
    from sqlalchemy import select
    
    _init_engine()
    
    print("Fetching fresh templates from Imgflip...")
    imgflip_templates = await fetch_imgflip_templates()
    
    if not imgflip_templates:
        print("✗ Failed to fetch Imgflip templates")
        return
    
    print(f"✓ Fetched {len(imgflip_templates)} templates from Imgflip\n")
    
    async with AsyncSessionLocal() as db:
        # Get all local templates
        result = await db.execute(select(MemeTemplate))
        local_templates = result.scalars().all()
        
        updated_count = 0
        not_found_count = 0
        
        print("Updating templates...")
        print("=" * 70)
        
        for template in local_templates:
            # Try to find Imgflip ID for this template
            imgflip_id = None
            
            # First, check our manual mapping
            for name_pattern, mapped_id in TEMPLATE_MAPPING.items():
                if name_pattern.lower() in template.name.lower() or template.name.lower() in name_pattern.lower():
                    imgflip_id = mapped_id
                    break
            
            if imgflip_id and imgflip_id in imgflip_templates:
                imgflip_data = imgflip_templates[imgflip_id]
                
                # Update template with Imgflip data
                template.imgflip_id = imgflip_id
                template.image_url = imgflip_data["url"]
                template.preview_image_url = imgflip_data["url"]
                template.source = "imgflip"
                template.box_count = imgflip_data.get("box_count", template.number_of_text_fields)
                
                print(f"✓ {template.name:40s} → Imgflip ID: {imgflip_id}")
                print(f"  URL: {imgflip_data['url']}")
                updated_count += 1
            else:
                print(f"⚠ {template.name:40s} → No Imgflip mapping found")
                not_found_count += 1
        
        # Commit changes
        await db.commit()
        
        print("\n" + "=" * 70)
        print(f"\n✓ Updated {updated_count} templates")
        print(f"⚠ {not_found_count} templates not mapped")
        print("\nRefresh your browser to see the updated templates!")


if __name__ == "__main__":
    asyncio.run(update_template_urls())
