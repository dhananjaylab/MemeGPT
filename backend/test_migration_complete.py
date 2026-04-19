#!/usr/bin/env python3
"""
Complete migration test using SQLite for validation.

This script tests the complete migration process using an in-memory SQLite database
to validate that the migration logic works correctly with the actual database models.

Usage:
    python test_migration_complete.py
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from typing import List, Dict, Any

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select, func, text
from db.session import Base
from models.models import MemeTemplate


def load_meme_data_json() -> List[Dict[str, Any]]:
    """Load meme_data.json file."""
    meme_data_path = backend_dir.parent / "meme_data.json"
    
    with open(meme_data_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_meme_template(meme_data: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Validate and normalize a single meme template."""
    return {
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


async def test_complete_migration():
    """Test the complete migration process with SQLite."""
    print("🧪 Testing Complete Migration Process")
    print("=" * 50)
    
    # Create in-memory SQLite database for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    try:
        # Create tables
        print("📋 Creating database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Tables created successfully")
        
        # Load and validate meme data
        print("\n📄 Loading meme data...")
        meme_data = load_meme_data_json()
        print(f"✅ Loaded {len(meme_data)} templates")
        
        # Validate all templates
        print("\n🔍 Validating templates...")
        validated_templates = []
        for i, template_data in enumerate(meme_data):
            validated = validate_meme_template(template_data, i)
            validated_templates.append(validated)
        print(f"✅ All {len(validated_templates)} templates validated")
        
        # Perform migration
        print("\n🔄 Performing migration...")
        async with AsyncSession(engine) as db:
            # Insert templates
            for template_data in validated_templates:
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
            
            await db.commit()
            print(f"✅ Migrated {len(validated_templates)} templates to database")
        
        # Verify migration
        print("\n🔍 Verifying migration...")
        async with AsyncSession(engine) as db:
            # Check count
            result = await db.execute(select(func.count(MemeTemplate.id)))
            count = result.scalar()
            
            if count != len(meme_data):
                print(f"❌ Count mismatch: expected {len(meme_data)}, got {count}")
                return False
            
            print(f"✅ Template count correct: {count}")
            
            # Check individual templates
            result = await db.execute(select(MemeTemplate).order_by(MemeTemplate.id))
            db_templates = result.scalars().all()
            
            for i, (original, db_template) in enumerate(zip(validated_templates, db_templates)):
                # Check key fields
                if db_template.name != original['name']:
                    print(f"❌ Name mismatch for template {i}")
                    return False
                
                if db_template.number_of_text_fields != original['number_of_text_fields']:
                    print(f"❌ Text field count mismatch for template {i}")
                    return False
                
                if len(db_template.alternative_names) != len(original['alternative_names']):
                    print(f"❌ Alternative names count mismatch for template {i}")
                    return False
                
                if len(db_template.example_output) != len(original['example_output']):
                    print(f"❌ Example output count mismatch for template {i}")
                    return False
            
            print(f"✅ All template data verified correctly")
        
        # Test model methods
        print("\n🧪 Testing model methods...")
        async with AsyncSession(engine) as db:
            # Get a template and test methods
            result = await db.execute(select(MemeTemplate).limit(1))
            template = result.scalar_one()
            
            # Test properties and methods
            all_names = template.all_names
            if len(all_names) != len(template.alternative_names) + 1:
                print("❌ all_names property incorrect")
                return False
            
            # Test name matching
            if not template.matches_name(template.name.lower()):
                print("❌ matches_name method failed for primary name")
                return False
            
            if template.alternative_names and not template.matches_name(template.alternative_names[0].lower()):
                print("❌ matches_name method failed for alternative name")
                return False
            
            # Test text validation
            valid_text = ["test"] * template.number_of_text_fields
            if not template.validate_text_count(valid_text):
                print("❌ validate_text_count method failed for valid input")
                return False
            
            invalid_text = ["test"] * (template.number_of_text_fields + 1)
            if template.validate_text_count(invalid_text):
                print("❌ validate_text_count method failed for invalid input")
                return False
            
            print(f"✅ Model methods working correctly")
        
        # Test queries
        print("\n🔍 Testing database queries...")
        async with AsyncSession(engine) as db:
            # Test name search
            result = await db.execute(
                select(MemeTemplate).where(MemeTemplate.name.ilike("%drake%"))
            )
            drake_templates = result.scalars().all()
            
            if len(drake_templates) != 1:
                print(f"❌ Name search failed: expected 1 Drake template, got {len(drake_templates)}")
                return False
            
            # Test text field filtering
            result = await db.execute(
                select(MemeTemplate).where(MemeTemplate.number_of_text_fields == 2)
            )
            two_field_templates = result.scalars().all()
            
            expected_two_field = len([t for t in validated_templates if t['number_of_text_fields'] == 2])
            if len(two_field_templates) != expected_two_field:
                print(f"❌ Text field filtering failed")
                return False
            
            print(f"✅ Database queries working correctly")
        
        print(f"\n🎉 Complete migration test PASSED!")
        print(f"   - Data loading: ✅")
        print(f"   - Validation: ✅")
        print(f"   - Database insertion: ✅")
        print(f"   - Data verification: ✅")
        print(f"   - Model methods: ✅")
        print(f"   - Database queries: ✅")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration test failed: {e}")
        return False
    
    finally:
        await engine.dispose()


async def main():
    """Main test function."""
    print("🧙 MemeGPT Complete Migration Test")
    print("=" * 50)
    
    try:
        success = await test_complete_migration()
        
        if success:
            print(f"\n✅ ALL TESTS PASSED!")
            print(f"\nThe migration is ready for production use:")
            print(f"1. Database models are compatible")
            print(f"2. Data validation works correctly")
            print(f"3. Migration logic is sound")
            print(f"4. Model methods function properly")
            print(f"5. Database queries work as expected")
            print(f"\nNext step: Run the actual migration with PostgreSQL")
        else:
            print(f"\n❌ TESTS FAILED!")
            print(f"Please review and fix the issues before proceeding.")
        
        return success
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)