#!/usr/bin/env python3
"""
Test script to validate Alembic setup and migration files.

This script validates:
1. Alembic configuration is correct
2. Migration files are properly formatted
3. Models can be imported successfully
4. Migration scripts are syntactically correct

Usage:
    python test_alembic_setup.py
"""

import sys
import os
from pathlib import Path
import importlib.util

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))


def test_model_imports():
    """Test that all models can be imported successfully."""
    try:
        from models.models import User, GeneratedMeme, MemeJob, MemeTemplate
        from db.session import Base
        print("✅ All models imported successfully")
        
        # Test that models are properly registered with Base
        tables = Base.metadata.tables
        expected_tables = {'users', 'memes', 'meme_jobs', 'meme_templates'}
        actual_tables = set(tables.keys())
        
        if expected_tables.issubset(actual_tables):
            print("✅ All expected tables are registered with SQLAlchemy Base")
            for table in expected_tables:
                print(f"  - {table}")
        else:
            missing = expected_tables - actual_tables
            print(f"❌ Missing tables: {missing}")
            return False
            
        return True
    except Exception as e:
        print(f"❌ Model import failed: {e}")
        return False


def test_alembic_config():
    """Test that Alembic configuration is valid."""
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        
        # Load Alembic config
        alembic_cfg = Config("alembic.ini")
        script_dir = ScriptDirectory.from_config(alembic_cfg)
        
        print("✅ Alembic configuration loaded successfully")
        print(f"  - Script location: {script_dir.dir}")
        print(f"  - Version locations: {script_dir.version_locations}")
        
        return True
    except Exception as e:
        print(f"❌ Alembic configuration test failed: {e}")
        return False


def test_migration_files():
    """Test that migration files are valid."""
    try:
        versions_dir = Path("alembic/versions")
        migration_files = list(versions_dir.glob("*.py"))
        
        # Filter out __pycache__ and .gitkeep
        migration_files = [f for f in migration_files if f.name != "__init__.py"]
        
        print(f"✅ Found {len(migration_files)} migration file(s)")
        
        for migration_file in migration_files:
            print(f"  - {migration_file.name}")
            
            # Test that the migration file can be imported
            spec = importlib.util.spec_from_file_location("migration", migration_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Check required attributes
                required_attrs = ['revision', 'down_revision', 'upgrade', 'downgrade']
                for attr in required_attrs:
                    if not hasattr(module, attr):
                        print(f"❌ Migration {migration_file.name} missing required attribute: {attr}")
                        return False
                
                print(f"    ✅ Valid migration file")
            else:
                print(f"❌ Could not load migration file: {migration_file.name}")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Migration file test failed: {e}")
        return False


def test_env_py():
    """Test that env.py can be imported and executed."""
    try:
        # Test importing env.py components
        sys.path.insert(0, str(Path("alembic")))
        
        # Import the env module
        spec = importlib.util.spec_from_file_location("env", "alembic/env.py")
        if spec and spec.loader:
            # We can't actually execute it without a database, but we can check syntax
            with open("alembic/env.py", 'r') as f:
                env_content = f.read()
            
            # Compile to check syntax
            compile(env_content, "alembic/env.py", "exec")
            print("✅ env.py syntax is valid")
            
            # Check for required imports and functions
            required_elements = [
                "from alembic import context",
                "def run_migrations_offline",
                "def run_migrations_online",
                "target_metadata"
            ]
            
            for element in required_elements:
                if element not in env_content:
                    print(f"❌ env.py missing required element: {element}")
                    return False
            
            print("✅ env.py contains all required elements")
            return True
        else:
            print("❌ Could not load env.py")
            return False
            
    except Exception as e:
        print(f"❌ env.py test failed: {e}")
        return False


def test_database_url_config():
    """Test that database URL configuration is properly set."""
    try:
        from core.config import settings
        
        db_url = settings.database_url
        print(f"✅ Database URL configured: {db_url}")
        
        # Basic validation
        if not db_url.startswith(("postgresql://", "postgresql+asyncpg://")):
            print("⚠️  Warning: Database URL should use PostgreSQL")
        
        if "asyncpg" not in db_url:
            print("⚠️  Warning: Consider using asyncpg driver for better async performance")
        
        return True
    except Exception as e:
        print(f"❌ Database URL configuration test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Testing Alembic Setup for MemeGPT v2")
    print("=" * 50)
    
    tests = [
        ("Model Imports", test_model_imports),
        ("Alembic Configuration", test_alembic_config),
        ("Migration Files", test_migration_files),
        ("env.py Validation", test_env_py),
        ("Database URL Configuration", test_database_url_config),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 Testing: {test_name}")
        print("-" * 30)
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nTests passed: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("\n🎉 All tests passed! Alembic setup is ready.")
        print("\nNext steps:")
        print("1. Ensure PostgreSQL is running")
        print("2. Run: python init_db.py --test-connection")
        print("3. Run: python init_db.py (to create tables)")
        return True
    else:
        print(f"\n❌ {len(tests) - passed} test(s) failed. Please fix the issues above.")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
        sys.exit(1)