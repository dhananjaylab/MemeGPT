"""Remove templates that don't have working Imgflip mappings."""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv


async def remove_broken_templates():
    """Remove templates that couldn't be synced with Imgflip."""
    
    # Templates to remove (by name)
    TEMPLATES_TO_REMOVE = [
        "But That's None Of My Business",
        "Nobody Absolutely Nobody",
        "It's A Trap",
        "Bike Fall",
        "Coffin Dance"
    ]
    
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
        removed_count = 0
        
        print("Removing templates without working Imgflip URLs...")
        print("=" * 70)
        
        for template_name in TEMPLATES_TO_REMOVE:
            # Check if template exists
            row = await conn.fetchrow(
                'SELECT id, name FROM meme_templates WHERE name LIKE $1',
                f'%{template_name}%'
            )
            
            if row:
                template_id = row['id']
                actual_name = row['name']
                
                # Delete the template
                await conn.execute(
                    'DELETE FROM meme_templates WHERE id = $1',
                    template_id
                )
                
                print(f"✗ Removed: {actual_name} (ID: {template_id})")
                removed_count += 1
            else:
                print(f"⚠ Not found: {template_name}")
        
        print("\n" + "=" * 70)
        print(f"\n✓ Removed {removed_count} templates")
        
        # Show remaining template count
        total = await conn.fetchval('SELECT COUNT(*) FROM meme_templates')
        print(f"✓ {total} templates remaining in database")
        print("\nRefresh your browser to see the changes!")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(remove_broken_templates())
