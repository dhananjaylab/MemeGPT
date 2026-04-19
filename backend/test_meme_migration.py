#!/usr/bin/env python3
"""
Test script for meme template migration logic.

This script validates the migration logic without requiring a database connection.
It tests the JSON parsing, validation, and transformation logic.

Usage:
    python test_meme_migration.py
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Import the migration functions
from migrate_meme_templates import load_meme_data_json, validate_meme_template


def test_load_meme_data():
    """Test loading meme_data.json file."""
    print("🧪 Testing meme_data.json loading...")
    
    try:
        meme_data = load_meme_data_json()
        print(f"✅ Successfully loaded {len(meme_data)} templates")
        
        # Check that it's a list
        if not isinstance(meme_data, list):
            print("❌ meme_data should be a list")
            return False
        
        # Check that we have some templates
        if len(meme_data) == 0:
            print("❌ No templates found in meme_data.json")
            return False
        
        print(f"✅ Found {len(meme_data)} templates in meme_data.json")
        return True
        
    except Exception as e:
        print(f"❌ Failed to load meme_data.json: {e}")
        return False


def test_template_validation():
    """Test template validation logic."""
    print("\n🧪 Testing template validation...")
    
    try:
        meme_data = load_meme_data_json()
        
        valid_count = 0
        for i, template_data in enumerate(meme_data):
            try:
                validated = validate_meme_template(template_data, i)
                
                # Check that all required fields are present
                required_fields = [
                    'id', 'name', 'alternative_names', 'file_path', 'font_path',
                    'text_color', 'text_stroke', 'usage_instructions',
                    'number_of_text_fields', 'text_coordinates_xy_wh', 'example_output'
                ]
                
                for field in required_fields:
                    if field not in validated:
                        print(f"❌ Template {i}: Missing field '{field}' after validation")
                        return False
                
                # Check data types
                if not isinstance(validated['alternative_names'], list):
                    print(f"❌ Template {i}: alternative_names should be a list")
                    return False
                
                if not isinstance(validated['text_coordinates_xy_wh'], list):
                    print(f"❌ Template {i}: text_coordinates_xy_wh should be a list")
                    return False
                
                if not isinstance(validated['example_output'], list):
                    print(f"❌ Template {i}: example_output should be a list")
                    return False
                
                # Check coordinate structure
                coords = validated['text_coordinates_xy_wh']
                if len(coords) != validated['number_of_text_fields']:
                    print(f"❌ Template {i}: coordinate count mismatch")
                    return False
                
                for j, coord in enumerate(coords):
                    if not isinstance(coord, list) or len(coord) != 4:
                        print(f"❌ Template {i}: coordinate {j} should be [x, y, w, h]")
                        return False
                
                # Check example output
                if len(validated['example_output']) != validated['number_of_text_fields']:
                    print(f"❌ Template {i}: example output count mismatch")
                    return False
                
                valid_count += 1
                print(f"✅ Template {i}: {validated['name']} - validation passed")
                
            except ValueError as e:
                print(f"❌ Template {i}: Validation failed - {e}")
                return False
        
        print(f"\n✅ All {valid_count} templates passed validation")
        return True
        
    except Exception as e:
        print(f"❌ Template validation test failed: {e}")
        return False


def test_template_details():
    """Test and display template details."""
    print("\n🧪 Testing template details...")
    
    try:
        meme_data = load_meme_data_json()
        
        print(f"\n📋 Template Summary:")
        print("-" * 60)
        
        for i, template_data in enumerate(meme_data):
            validated = validate_meme_template(template_data, i)
            
            print(f"Template {validated['id']}: {validated['name']}")
            print(f"  Alternative names: {validated['alternative_names']}")
            print(f"  File: {validated['file_path']}")
            print(f"  Font: {validated['font_path']}")
            print(f"  Text fields: {validated['number_of_text_fields']}")
            print(f"  Text color: {validated['text_color']}")
            print(f"  Text stroke: {validated['text_stroke']}")
            print(f"  Example: {validated['example_output']}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Template details test failed: {e}")
        return False


def test_migration_data_structure():
    """Test that the migration data structure matches the database model."""
    print("\n🧪 Testing migration data structure compatibility...")
    
    try:
        meme_data = load_meme_data_json()
        
        # Test creating model-like objects
        for i, template_data in enumerate(meme_data):
            validated = validate_meme_template(template_data, i)
            
            # Simulate creating a MemeTemplate object
            model_data = {
                'id': validated['id'],
                'name': validated['name'],
                'alternative_names': validated['alternative_names'],
                'file_path': validated['file_path'],
                'font_path': validated['font_path'],
                'text_color': validated['text_color'],
                'text_stroke': validated['text_stroke'],
                'usage_instructions': validated['usage_instructions'],
                'number_of_text_fields': validated['number_of_text_fields'],
                'text_coordinates_xy_wh': validated['text_coordinates_xy_wh'],
                'example_output': validated['example_output']
            }
            
            # Validate that all fields are JSON serializable
            try:
                json.dumps(model_data)
            except TypeError as e:
                print(f"❌ Template {i}: Data not JSON serializable - {e}")
                return False
        
        print(f"✅ All {len(meme_data)} templates are compatible with database model")
        return True
        
    except Exception as e:
        print(f"❌ Migration data structure test failed: {e}")
        return False


def main():
    """Run all migration tests."""
    print("🧙 MemeGPT Template Migration Tests")
    print("=" * 50)
    
    tests = [
        ("Load meme_data.json", test_load_meme_data),
        ("Validate templates", test_template_validation),
        ("Check template details", test_template_details),
        ("Test data structure compatibility", test_migration_data_structure)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Migration logic is ready.")
        print("\nNext steps:")
        print("1. Ensure PostgreSQL database is running")
        print("2. Run Alembic migrations: alembic upgrade head")
        print("3. Run the actual migration: python migrate_meme_templates.py")
        return True
    else:
        print("❌ Some tests failed. Please fix the issues before running migration.")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)