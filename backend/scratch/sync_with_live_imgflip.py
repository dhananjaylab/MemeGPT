"""Sync templates with live Imgflip API data."""
import httpx
import asyncio
import asyncpg
import os
from dotenv import load_dotenv


async def sync_with_imgflip():
    """Fetch fresh templates from Imgflip and update database."""
    
    # Fetch current templates from Imgflip
    print("Fetching templates from Imgflip API...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get("https://api.imgflip.com/get_memes")
        response.raise_for_status()
        data = response.json()
        
        if not data.get("success"):
            print("✗ Imgflip API returned unsuccessful response")
            return
        
        imgflip_templates = {str(m["id"]): m for m in data["data"]["memes"]}
    
    print(f"✓ Fetched {len(imgflip_templates)} templates from Imgflip\n")
    
    # Template name to Imgflip ID mapping
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
    
    # Connect to database
    load_dotenv()
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("✗ DATABASE_URL not found")
        return
    
    database_url = database_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    print("Connecting to database...")
    conn = await asyncpg.connect(database_url)
    
    try:
        # Get all local templates
        rows = await conn.fetch('SELECT id, name FROM meme_templates ORDER BY id')
        
        updated_count = 0
        not_found_count = 0
        
        print("Updating templates with fresh Imgflip data...")
        print("=" * 70)
        
        for row in rows:
            template_id = row['id']
            template_name = row['name']
            
            # Find Imgflip ID for this template
            imgflip_id = None
            for name_pattern, mapped_id in TEMPLATE_MAPPING.items():
                if name_pattern.lower() in template_name.lower() or template_name.lower() in name_pattern.lower():
                    imgflip_id = mapped_id
                    break
            
            if imgflip_id and imgflip_id in imgflip_templates:
                imgflip_data = imgflip_templates[imgflip_id]
                image_url = imgflip_data["url"]
                box_count = imgflip_data["box_count"]
                
                # Update template
                await conn.execute('''
                    UPDATE meme_templates 
                    SET imgflip_id = $1,
                        image_url = $2,
                        preview_image_url = $2,
                        source = 'imgflip',
                        box_count = $3
                    WHERE id = $4
                ''', imgflip_id, image_url, box_count, template_id)
                
                print(f"✓ {template_name:40s} → {image_url}")
                updated_count += 1
            else:
                print(f"⚠ {template_name:40s} → No Imgflip mapping")
                not_found_count += 1
        
        print("\n" + "=" * 70)
        print(f"\n✓ Updated {updated_count} templates with fresh Imgflip URLs")
        print(f"⚠ {not_found_count} templates not mapped to Imgflip")
        print("\nRefresh your browser to see the changes!")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(sync_with_imgflip())
