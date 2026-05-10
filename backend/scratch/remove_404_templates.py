"""
Remove templates with 404 image URLs from the database.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from sqlalchemy import select
from db.session import async_session_maker
from models.models import MemeTemplate


async def check_url(url: str) -> bool:
    """Check if a URL returns 200 OK."""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            resp = await client.head(url, headers={"User-Agent": "MemeGPT/2.0"})
            return resp.status_code == 200
    except Exception as e:
        print(f"  Error checking {url}: {e}")
        return False


async def main():
    """Find and remove templates with broken image URLs."""
    
    # Known broken URLs from logs
    broken_urls = [
        "https://i.imgflip.com/1jgig.jpg",
        "https://i.imgflip.com/3bb4c7.jpg",
        "https://i.imgflip.com/6gg7y9.jpg",
    ]
    
    async with async_session_maker() as db:
        # Find all templates
        result = await db.execute(select(MemeTemplate))
        templates = result.scalars().all()
        
        print(f"Found {len(templates)} templates in database")
        print("\nChecking for broken URLs...\n")
        
        templates_to_remove = []
        
        for template in templates:
            # Check if image_url contains any of the broken URLs
            if template.image_url:
                for broken_url in broken_urls:
                    if broken_url in template.image_url:
                        print(f"❌ Template {template.id}: {template.name}")
                        print(f"   URL: {template.image_url}")
                        templates_to_remove.append(template)
                        break
        
        if not templates_to_remove:
            print("✅ No templates with broken URLs found!")
            return
        
        print(f"\n\nFound {len(templates_to_remove)} templates with broken URLs:")
        for t in templates_to_remove:
            print(f"  - ID {t.id}: {t.name}")
        
        # Ask for confirmation
        response = input(f"\nRemove these {len(templates_to_remove)} templates? (yes/no): ")
        
        if response.lower() in ['yes', 'y']:
            for template in templates_to_remove:
                await db.delete(template)
                print(f"  Removed: {template.name} (ID: {template.id})")
            
            await db.commit()
            print(f"\n✅ Successfully removed {len(templates_to_remove)} templates")
        else:
            print("\n❌ Cancelled - no templates removed")


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
