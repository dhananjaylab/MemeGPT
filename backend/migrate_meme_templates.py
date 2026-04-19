#!/usr/bin/env python3
"""
Migrate existing meme_data.json to new database format.

This script reads the existing meme_data.json file and migrates all meme template
data to the new MemeTemplate database table, preserving all metadata and configuration.

Usage:
    python migrate_meme_templates.py [--dry-run] [--backup]
    
Options:
    --dry-run: Show what would be migrated without making changes
    --backup: Create a backup of existing data before migration
"""

import asyncio
import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, text
from db.session import engine
from models.models import MemeTemplate


async def load_meme_data_json() -> List[Dict[str, Any]]:
    """Load and validate meme_data.json file."""
    # Look for meme_data.json in the project root (parent directory)
    meme_data_path = backend_dir.parent / "meme_data.json"
    
    if not meme_data_path.exists():
        raise FileNotFoundError(f"meme_data.json not found at {meme_data_path}")
    
    print(f"📄 Loading meme data from: {meme_data_path}")
    
    try:
        with open(meme_data_path, 'r', encoding='utf-8') as f:
            meme_data = json.load(f)
        
        if not isinstance(meme_data, list):
            raise ValueError("meme_data.json must contain a list of meme templates")
        
        print(f"✅ Loaded {len(meme_data)} meme templates from JSON")
        return meme_data
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in meme_data.json: {e}")


def validate_meme_template(meme_data: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Validate and normalize a single meme template."""
    required_fields = [
        'name', 'file_path', 'font_path', 'text_color', 'usage_instructions',
        'number_of_text_fields', 'text_coordinates_xy_wh', 'example_output'
    ]
    
    # Check required fields
    for field in required_fields:
        if field not in meme_data:
            raise ValueError(f"Template {index}: Missing required field '{field}'")
    
    # Validate and normalize data
    validated = {
        'id': meme_data.get('id', index),
        'name': str(meme_data['name']).strip(),
        'alternative_names': meme_data.get('alternative_names', []),
        'file_path': str(meme_data['file_path']).strip(),
        'font_path': str(meme_data['font_path']).strip(),
        'text_color': str(meme_data['text_color']).strip(),
        'text_stroke': bool(meme_data.get('text_stroke', False)),
        'usage_instructions': str(meme_data['usage_instructions']).strip(),
        'number_of_text_fields': int(meme_data['number_of_text_fields']),
        'text_coordinates_xy_wh': meme_data['text_coordinates_xy_wh'],
        'example_output': meme_data['example_output']
    }
    
    # Validate alternative_names is a list
    if not isinstance(validated['alternative_names'], list):
        raise ValueError(f"Template {index}: alternative_names must be a list")
    
    # Validate text_coordinates_xy_wh structure
    coords = validated['text_coordinates_xy_wh']
    if not isinstance(coords, list):
        raise ValueError(f"Template {index}: text_coordinates_xy_wh must be a list")
    
    if len(coords) != validated['number_of_text_fields']:
        raise ValueError(f"Template {index}: text_coordinates_xy_wh length ({len(coords)}) "
                        f"doesn't match number_of_text_fields ({validated['number_of_text_fields']})")
    
    for i, coord in enumerate(coords):
        if not isinstance(coord, list) or len(coord) != 4:
            raise ValueError(f"Template {index}: text_coordinates_xy_wh[{i}] must be [x, y, w, h]")
        if not all(isinstance(x, (int, float)) for x in coord):
            raise ValueError(f"Template {index}: text_coordinates_xy_wh[{i}] must contain numbers")
    
    # Validate example_output
    example = validated['example_output']
    if not isinstance(example, list):
        raise ValueError(f"Template {index}: example_output must be a list")
    
    if len(example) != validated['number_of_text_fields']:
        raise ValueError(f"Template {index}: example_output length ({len(example)}) "
                        f"doesn't match number_of_text_fields ({validated['number_of_text_fields']})")
    
    return validated


async def check_existing_templates(db: AsyncSession) -> List[MemeTemplate]:
    """Check for existing templates in the database."""
    result = await db.execute(select(MemeTemplate))
    existing_templates = result.scalars().all()
    
    if existing_templates:
        print(f"⚠️  Found {len(existing_templates)} existing templates in database:")
        for template in existing_templates:
            print(f"   - ID {template.id}: {template.name}")
    
    return existing_templates


async def backup_existing_templates(db: AsyncSession, backup_path: Path) -> None:
    """Create a backup of existing templates."""
    existing_templates = await check_existing_templates(db)
    
    if not existing_templates:
        print("ℹ️  No existing templates to backup")
        return
    
    backup_data = []
    for template in existing_templates:
        backup_data.append({
            'id': template.id,
            'name': template.name,
            'alternative_names': template.alternative_names,
            'file_path': template.file_path,
            'font_path': template.font_path,
            'text_color': template.text_color,
            'text_stroke': template.text_stroke,
            'usage_instructions': template.usage_instructions,
            'number_of_text_fields': template.number_of_text_fields,
            'text_coordinates_xy_wh': template.text_coordinates_xy_wh,
            'example_output': template.example_output,
            'created_at': template.created_at.isoformat() if template.created_at else None,
            'updated_at': template.updated_at.isoformat() if template.updated_at else None
        })
    
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Backed up {len(backup_data)} existing templates to: {backup_path}")


async def migrate_templates(db: AsyncSession, meme_data: List[Dict[str, Any]], dry_run: bool = False) -> bool:
    """Migrate meme templates to the database."""
    print(f"\n🔄 {'Simulating' if dry_run else 'Starting'} template migration...")
    
    # Validate all templates first
    validated_templates = []
    for i, template_data in enumerate(meme_data):
        try:
            validated = validate_meme_template(template_data, i)
            validated_templates.append(validated)
            print(f"✅ Validated template {i}: {validated['name']}")
        except ValueError as e:
            print(f"❌ Validation failed for template {i}: {e}")
            return False
    
    if dry_run:
        print(f"\n🔍 DRY RUN: Would migrate {len(validated_templates)} templates:")
        for template in validated_templates:
            print(f"   - ID {template['id']}: {template['name']}")
            print(f"     Alternative names: {template['alternative_names']}")
            print(f"     Text fields: {template['number_of_text_fields']}")
            print(f"     File: {template['file_path']}")
        return True
    
    # Clear existing templates
    existing_count = await db.scalar(select(func.count(MemeTemplate.id)))
    if existing_count > 0:
        print(f"🗑️  Removing {existing_count} existing templates...")
        await db.execute(delete(MemeTemplate))
        await db.commit()
    
    # Insert new templates
    success_count = 0
    for template_data in validated_templates:
        try:
            template = MemeTemplate(
                id=template_data['id'],
                name=template_data['name'],
                alternative_names=template_data['alternative_names'],
                file_path=template_data['file_path'],
                font_path=template_data['font_path'],
                text_color=template_data['text_color'],
                text_stroke=template_data['text_stroke'],
                usage_instructions=template_data['usage_instructions'],
                number_of_text_fields=template_data['number_of_text_fields'],
                text_coordinates_xy_wh=template_data['text_coordinates_xy_wh'],
                example_output=template_data['example_output']
            )
            
            db.add(template)
            success_count += 1
            print(f"✅ Added template: {template.name}")
            
        except Exception as e:
            print(f"❌ Failed to add template {template_data['name']}: {e}")
            await db.rollback()
            return False
    
    # Commit all changes
    try:
        await db.commit()
        print(f"\n🎉 Successfully migrated {success_count} templates to database!")
        return True
    except Exception as e:
        print(f"❌ Failed to commit migration: {e}")
        await db.rollback()
        return False


async def verify_migration(db: AsyncSession, original_data: List[Dict[str, Any]]) -> bool:
    """Verify that migration was successful."""
    print("\n🔍 Verifying migration...")
    
    # Check template count
    result = await db.execute(select(func.count(MemeTemplate.id)))
    db_count = result.scalar()
    
    if db_count != len(original_data):
        print(f"❌ Template count mismatch: expected {len(original_data)}, got {db_count}")
        return False
    
    # Check each template
    result = await db.execute(select(MemeTemplate).order_by(MemeTemplate.id))
    db_templates = result.scalars().all()
    
    for i, (original, db_template) in enumerate(zip(original_data, db_templates)):
        # Validate key fields
        if db_template.name != original['name']:
            print(f"❌ Name mismatch for template {i}: expected '{original['name']}', got '{db_template.name}'")
            return False
        
        if db_template.number_of_text_fields != original['number_of_text_fields']:
            print(f"❌ Text field count mismatch for template {i}")
            return False
        
        if len(db_template.example_output) != len(original['example_output']):
            print(f"❌ Example output length mismatch for template {i}")
            return False
    
    print(f"✅ Migration verification successful: {db_count} templates migrated correctly")
    return True


async def test_database_connection() -> bool:
    """Test if we can connect to the database."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Please ensure PostgreSQL is running and migrations have been applied.")
        return False


async def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description="Migrate meme_data.json to database")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated without making changes")
    parser.add_argument("--backup", action="store_true", help="Create backup of existing data before migration")
    
    args = parser.parse_args()
    
    print("🧙 MemeGPT Template Migration Tool")
    print("=" * 50)
    
    # Test database connection
    if not await test_database_connection():
        return False
    
    try:
        # Load meme data from JSON
        meme_data = load_meme_data_json()
        
        async with AsyncSession(engine) as db:
            # Create backup if requested
            if args.backup and not args.dry_run:
                backup_path = backend_dir / f"meme_templates_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                await backup_existing_templates(db, backup_path)
            
            # Perform migration
            success = await migrate_templates(db, meme_data, dry_run=args.dry_run)
            
            if not success:
                print("\n❌ Migration failed!")
                return False
            
            # Verify migration (only for actual migration, not dry run)
            if not args.dry_run:
                if not await verify_migration(db, meme_data):
                    print("\n❌ Migration verification failed!")
                    return False
            
            if args.dry_run:
                print(f"\n✅ Dry run completed successfully!")
                print("Run without --dry-run to perform the actual migration.")
            else:
                print(f"\n🎉 Migration completed successfully!")
                print(f"Migrated {len(meme_data)} meme templates to the database.")
            
            return True
            
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)