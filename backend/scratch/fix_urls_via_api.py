"""Fix template URLs by directly updating via HTTP requests."""
import httpx
import asyncio


# Template ID to Imgflip data mapping
TEMPLATE_UPDATES = [
    (0, '181913649', 'https://i.imgflip.com/30b1gx.jpg'),
    (1, '112126428', 'https://i.imgflip.com/1ur9b0.jpg'),
    (2, '124822590', 'https://i.imgflip.com/22bdq6.jpg'),
    (3, '217743513', 'https://i.imgflip.com/3lmzyx.jpg'),
    (4, '61579', 'https://i.imgflip.com/1bij.jpg'),
    (5, '93895088', 'https://i.imgflip.com/1jwhww.jpg'),
    (6, '27813981', 'https://i.imgflip.com/gk5el.jpg'),
    (7, '61544', 'https://i.imgflip.com/1bhk.jpg'),
    (8, '16464531', 'https://i.imgflip.com/6ew4g.jpg'),
    (9, '97984', 'https://i.imgflip.com/23ls.jpg'),
    (10, '89370399', 'https://i.imgflip.com/1h7in3.jpg'),
    (11, '55311130', 'https://i.imgflip.com/wxica.jpg'),
    (12, '155067746', 'https://i.imgflip.com/2kbn1e.jpg'),
    (13, '188390779', 'https://i.imgflip.com/345v97.jpg'),
    (14, '87743020', 'https://i.imgflip.com/1g8in9.jpg'),
    (15, '252600902', 'https://i.imgflip.com/46e43q.jpg'),
    (16, '131940431', 'https://i.imgflip.com/26am.jpg'),
    (17, '178591752', 'https://i.imgflip.com/3qqcml.jpg'),
    (18, '196652226', 'https://i.imgflip.com/3bb4c7.jpg'),
    (19, '110163934', 'https://i.imgflip.com/1o00in.jpg'),
    (20, '5677926', 'https://i.imgflip.com/1jgig.jpg'),
    (21, '102156234', 'https://i.imgflip.com/1otk96.jpg'),
    (22, '100947', 'https://i.imgflip.com/9ehk.jpg'),
    (23, '129242436', 'https://i.imgflip.com/24y43o.jpg'),
    (24, '101470', 'https://i.imgflip.com/kx0jh.jpg'),
    (25, '256616965', 'https://i.imgflip.com/6gg7y9.jpg'),
]


async def update_templates_via_db():
    """Update templates directly in the database using asyncpg."""
    import asyncpg
    
    # Get database URL from environment
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("✗ DATABASE_URL not found in environment")
        return
    
    # Convert asyncpg URL format
    database_url = database_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    print("Connecting to database...")
    conn = await asyncpg.connect(database_url)
    
    try:
        updated_count = 0
        
        print("Updating templates...")
        print("=" * 70)
        
        for template_id, imgflip_id, image_url in TEMPLATE_UPDATES:
            # Get template name first
            row = await conn.fetchrow(
                'SELECT name FROM meme_templates WHERE id = $1',
                template_id
            )
            
            if not row:
                print(f"⚠ Template ID {template_id} not found")
                continue
            
            template_name = row['name']
            
            # Update template
            await conn.execute('''
                UPDATE meme_templates 
                SET imgflip_id = $1,
                    image_url = $2,
                    preview_image_url = $2,
                    source = 'imgflip'
                WHERE id = $3
            ''', imgflip_id, image_url, template_id)
            
            print(f"✓ {template_name:40s} → {image_url}")
            updated_count += 1
        
        print("\n" + "=" * 70)
        print(f"\n✓ Updated {updated_count} templates successfully!")
        print("\nRefresh your browser to see the changes.")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(update_templates_via_db())
