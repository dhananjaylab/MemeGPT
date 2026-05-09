"""Fix broken template image URLs by syncing with Imgflip."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.session import AsyncSessionLocal, _init_engine
from services.imgflip import imgflip_service


async def fix_template_urls():
    """Sync templates with Imgflip to get correct image URLs."""
    _init_engine()
    
    print("Syncing templates with Imgflip API...")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        try:
            stats = await imgflip_service.sync_templates_to_db(db)
            
            print(f"\n✓ Sync completed successfully!")
            print(f"  Fetched: {stats['fetched']} templates from Imgflip")
            print(f"  Created: {stats['created']} new templates")
            print(f"  Updated: {stats['updated']} existing templates")
            print(f"  Errors: {stats['errors']}")
            
            if stats['errors'] > 0:
                print(f"\n⚠ Some templates had errors during sync")
            
            print("\n" + "=" * 60)
            print("Templates should now have correct image URLs!")
            print("Refresh your browser to see the changes.")
            
        except Exception as e:
            print(f"\n✗ Error during sync: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(fix_template_urls())
