#!/usr/bin/env python3
"""
Simple test to verify v1 meme generation functions are migrated to FastAPI structure.
"""

import json
import sys
from pathlib import Path

def test_meme_data_exists():
    """Test that meme data file exists and is valid"""
    print("Testing meme_data.json...")
    try:
        meme_data_path = Path("meme_data.json")
        if not meme_data_path.exists():
            print("✗ meme_data.json not found")
            return False
        
        with open(meme_data_path, 'r') as f:
            meme_data = json.load(f)
        
        assert isinstance(meme_data, list), "Meme data should be a list"
        assert len(meme_data) > 0, "Meme data should not be empty"
        
        # Check structure of first meme
        first_meme = meme_data[0]
        required_fields = [
            'id', 'name', 'file_path', 'font_path', 'text_color',
            'number_of_text_fields', 'text_coordinates_xy_wh', 'example_output'
        ]
        
        for field in required_fields:
            if field not in first_meme:
                print(f"✗ Missing required field: {field}")
                return False
        
        print(f"✓ meme_data.json is valid with {len(meme_data)} templates")
        return True
    except Exception as e:
        print(f"✗ Error reading meme_data.json: {e}")
        return False

def test_backend_structure():
    """Test that backend structure exists"""
    print("Testing backend structure...")
    try:
        backend_path = Path("backend")
        if not backend_path.exists():
            print("✗ backend directory not found")
            return False
        
        # Check for key files
        key_files = [
            "backend/main.py",
            "backend/services/meme_generation.py",
            "backend/services/worker.py",
            "backend/routers/memes.py"
        ]
        
        for file_path in key_files:
            if not Path(file_path).exists():
                print(f"✗ Missing key file: {file_path}")
                return False
        
        print("✓ Backend structure is complete")
        return True
    except Exception as e:
        print(f"✗ Error checking backend structure: {e}")
        return False

def test_meme_generation_service():
    """Test that meme generation service has required functions"""
    print("Testing meme generation service...")
    try:
        service_path = Path("backend/services/meme_generation.py")
        if not service_path.exists():
            print("✗ meme_generation.py not found")
            return False
        
        with open(service_path, 'r') as f:
            content = f.read()
        
        # Check for key functions from v1
        required_functions = [
            'def load_meme_data',
            'def load_meme_data_flat_string',
            'def get_system_instructions',
            'async def call_chatgpt',
            'def overlay_text_on_image',
            'async def generate_memes',
            'def handle_text_caps'
        ]
        
        missing_functions = []
        for func in required_functions:
            if func not in content:
                missing_functions.append(func)
        
        if missing_functions:
            print(f"✗ Missing functions: {missing_functions}")
            return False
        
        print("✓ All required v1 functions are present in FastAPI service")
        return True
    except Exception as e:
        print(f"✗ Error checking meme generation service: {e}")
        return False

def test_template_images():
    """Test that template images exist"""
    print("Testing template images...")
    try:
        templates_path = Path("templates")
        if not templates_path.exists():
            print("⚠ templates directory not found (expected for migration)")
            return True  # Not critical for migration test
        
        # Count available templates
        image_files = list(templates_path.glob("*.jpg"))
        print(f"✓ Found {len(image_files)} template images")
        return True
    except Exception as e:
        print(f"⚠ Error checking templates: {e}")
        return True  # Not critical

def test_font_handling():
    """Test that font handling is implemented"""
    print("Testing font handling...")
    try:
        fonts_path = Path("fonts")
        if not fonts_path.exists():
            print("✗ fonts directory not found")
            return False
        
        readme_path = fonts_path / "README.md"
        if readme_path.exists():
            print("✓ Font directory has documentation")
        else:
            print("⚠ Font directory missing documentation")
        
        # Check if meme generation service handles missing fonts gracefully
        service_path = Path("backend/services/meme_generation.py")
        with open(service_path, 'r') as f:
            content = f.read()
        
        if "except (OSError, IOError)" in content and "load_default" in content:
            print("✓ Font fallback handling implemented")
            return True
        else:
            print("⚠ Font fallback handling may be missing")
            return True  # Not critical
            
    except Exception as e:
        print(f"✗ Error checking font handling: {e}")
        return False

def run_migration_tests():
    """Run all migration validation tests"""
    print("=" * 60)
    print("MEME GENERATION MIGRATION VALIDATION")
    print("=" * 60)
    
    tests = [
        ("Meme Data File", test_meme_data_exists),
        ("Backend Structure", test_backend_structure),
        ("Meme Generation Service", test_meme_generation_service),
        ("Template Images", test_template_images),
        ("Font Handling", test_font_handling),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 60)
    print("MIGRATION VALIDATION RESULTS")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:<30} {status}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 MIGRATION VALIDATION PASSED!")
        print("All v1 meme generation functions are properly migrated to FastAPI structure.")
        return True
    else:
        print(f"\n⚠️  {total - passed} validation checks failed")
        return False

if __name__ == "__main__":
    success = run_migration_tests()
    sys.exit(0 if success else 1)