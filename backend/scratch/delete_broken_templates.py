"""
Simple script to delete templates with broken proxy-image URLs
Run this from the backend directory
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Now we can import after path is set
import asyncio
from sqlalchemy import text
from db.session import engine


async def delete_broken_templates():
    """Delete templates using proxy-image URLs"""
    
    async with engine.begin() as conn:
        # First, show what we're about to delete
        result = await conn.execute(
            text("SELECT id, name, image_url FROM meme_templates WHERE image_url LIKE '%proxy-image%'")
        )
        templates = result.fetchall()
        
        if not templates:
            print("✅ No templates with proxy-image URLs found")
            return
        
        print(f"Found {len(templates)} templates with broken proxy-image URLs:")
        for row in templates:
            print(f"  - ID {row[0]}: {row[1]}")
        
        # Delete them
        result = await conn.execute(
            text("DELETE FROM meme_templates WHERE image_url LIKE '%proxy-image%'")
        )
        
        print(f"\n✅ Deleted {result.rowcount} templates")
        
        # Show remaining count
        result = await conn.execute(text("SELECT COUNT(*) FROM meme_templates"))
        count = result.scalar()
        print(f"✅ {count} templates remaining in database")


if __name__ == "__main__":
    asyncio.run(delete_broken_templates())

# Made with Bob
