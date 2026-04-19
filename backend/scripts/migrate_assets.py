#!/usr/bin/env python3
"""
MemeGPT Template and Asset Migration Script.

This script migrates existing meme templates from meme_data.json to the database
and uploads template images to Cloudflare R2 storage.

Tasks implemented:
3.1.1 Migrate existing meme templates to new format
3.1.2 Upload existing images to Cloudflare R2 storage
3.1.3 Update image URLs to point to R2 CDN
3.1.4 Validate all template metadata after migration
3.1.5 Create backup of original template files
"""

import asyncio
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add project root and backend to path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from db.session import engine, AsyncSessionLocal
from models.models import MemeTemplate
from services.storage import upload_to_r2
from core.config import settings

# Paths
MEME_DATA_PATH = ROOT_DIR / "meme_data.json"
FRAMES_DIR = ROOT_DIR / "public" / "frames"
BACKUP_DIR = ROOT_DIR / "legacy" / "backups" / f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

async def backup_files():
    """Step 3.1.5: Create backup of original template files and metadata."""
    print(f"📦 Creating backup in {BACKUP_DIR}...")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    # Backup JSON
    if MEME_DATA_PATH.exists():
        shutil.copy2(MEME_DATA_PATH, BACKUP_DIR / "meme_data.json.bak")
        print("✅ Backed up meme_data.json")
    
    # Backup Images
    if FRAMES_DIR.exists():
        frames_backup = BACKUP_DIR / "frames"
        shutil.copytree(FRAMES_DIR, frames_backup)
        print(f"✅ Backed up {len(list(FRAMES_DIR.glob('*')))} frame images")

def load_and_validate_json() -> List[Dict[str, Any]]:
    """Step 3.1.4: Validate all template metadata."""
    if not MEME_DATA_PATH.exists():
        print(f"❌ Could not find {MEME_DATA_PATH}")
        sys.exit(1)
        
    with open(MEME_DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    if not isinstance(data, list):
        print("❌ Invalid data format: expected a list of templates")
        sys.exit(1)
        
    print(f"✅ Loaded {len(data)} templates from JSON")
    
    # Basic validation
    required_keys = ['name', 'file_path', 'number_of_text_fields', 'text_coordinates_xy_wh']
    for i, item in enumerate(data):
        for key in required_keys:
            if key not in item:
                print(f"❌ Template {i} ({item.get('name', 'Unknown')}) missing required key: {key}")
                sys.exit(1)
                
    print("✅ Metadata validation successful")
    return data

async def migrate_data(templates_data: List[Dict[str, Any]]):
    """Steps 3.1.1, 3.1.2, 3.1.3: Migrate templates and upload assets."""
    print("\n🚀 Starting data and asset migration...")
    
    async with AsyncSessionLocal() as db:
        # Clear existing templates first (re-migration safety)
        await db.execute(delete(MemeTemplate))
        await db.commit()
        
        migrated_count = 0
        for i, item in enumerate(templates_data):
            template_name = item['name']
            file_path_str = item['file_path']
            local_image_path = FRAMES_DIR / file_path_str
            
            print(f"Processing ({i+1}/{len(templates_data)}): {template_name}")
            
            image_url = None
            if local_image_path.exists():
                # Step 3.1.2: Upload to R2
                object_key = f"templates/{file_path_str}"
                print(f"  Uploading {file_path_str} to R2...")
                image_url = await upload_to_r2(local_image_path, object_key)
                if image_url:
                    print(f"  ✅ Uploaded: {image_url}")
                else:
                    print(f"  ⚠️  R2 upload failed for {template_name}, will proceed without URL")
            else:
                print(f"  ❌ Local image not found: {local_image_path}")
            
            # Step 3.1.1 & 3.1.3: Create DB entry with CDN URL
            template = MemeTemplate(
                name=template_name,
                alternative_names=item.get('alternative_names', []),
                file_path=file_path_str,
                font_path=item.get('font_path', 'Inter-SemiBold.ttf'),
                text_color=item.get('text_color', 'white'),
                text_stroke=item.get('text_stroke', True),
                usage_instructions=item.get('usage_instructions', ''),
                number_of_text_fields=item['number_of_text_fields'],
                text_coordinates_xy_wh=item['text_coordinates_xy_wh'],
                example_output=item.get('example_output', []),
                image_url=image_url # The R2 URL
            )
            
            db.add(template)
            migrated_count += 1
            
        await db.commit()
        print(f"\n🎉 Successfully migrated {migrated_count} templates to database.")

async def main():
    print("MemeGPT Data & Asset Migration Tool")
    print("=" * 40)
    
    # 1. Backup
    await backup_files()
    
    # 2. Validate
    templates = load_and_validate_json()
    
    # 3. Migrate & Upload
    await migrate_data(templates)
    
    print("\n✅ Migration complete!")

if __name__ == "__main__":
    asyncio.run(main())
