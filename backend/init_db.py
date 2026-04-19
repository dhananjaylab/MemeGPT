#!/usr/bin/env python3
"""
Database initialization script for MemeGPT v2.

This script initializes the database by:
1. Creating all tables using Alembic migrations
2. Setting up initial data if needed
3. Validating the database schema

Usage:
    python init_db.py [--reset] [--test-connection]
    
Options:
    --reset: Drop all tables and recreate them
    --test-connection: Test database connection without making changes
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from alembic.config import Config
from alembic import command
from core.config import settings
from db.session import Base, engine
from models.models import User, GeneratedMeme, MemeJob, MemeTemplate


async def test_database_connection():
    """Test if we can connect to the database."""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def check_tables_exist():
    """Check if database tables exist."""
    try:
        async with engine.connect() as conn:
            # Check if users table exists
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'users'
                );
            """))
            users_exists = result.scalar()
            
            # Check if memes table exists
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'memes'
                );
            """))
            memes_exists = result.scalar()
            
            # Check if meme_jobs table exists
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'meme_jobs'
                );
            """))
            jobs_exists = result.scalar()
            
            # Check if meme_templates table exists
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'meme_templates'
                );
            """))
            templates_exists = result.scalar()
            
            return {
                'users': users_exists,
                'memes': memes_exists,
                'meme_jobs': jobs_exists,
                'meme_templates': templates_exists
            }
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        return None


def run_alembic_migrations():
    """Run Alembic migrations to create/update database schema."""
    try:
        # Create Alembic configuration
        alembic_cfg = Config("alembic.ini")
        
        # Run migrations
        print("🔄 Running Alembic migrations...")
        command.upgrade(alembic_cfg, "head")
        print("✅ Migrations completed successfully")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


async def reset_database():
    """Drop all tables and recreate them."""
    try:
        print("🔄 Dropping all tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        print("✅ All tables dropped")
        
        # Run migrations to recreate tables
        return run_alembic_migrations()
    except Exception as e:
        print(f"❌ Database reset failed: {e}")
        return False


async def validate_schema():
    """Validate that all expected tables and columns exist."""
    try:
        tables = await check_tables_exist()
        if not tables:
            return False
            
        all_exist = all(tables.values())
        if all_exist:
            print("✅ All required tables exist:")
            for table, exists in tables.items():
                print(f"  - {table}: {'✅' if exists else '❌'}")
        else:
            print("❌ Some tables are missing:")
            for table, exists in tables.items():
                print(f"  - {table}: {'✅' if exists else '❌'}")
                
        return all_exist
    except Exception as e:
        print(f"❌ Schema validation failed: {e}")
        return False


async def main():
    """Main initialization function."""
    parser = argparse.ArgumentParser(description="Initialize MemeGPT database")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables")
    parser.add_argument("--test-connection", action="store_true", help="Test database connection only")
    
    args = parser.parse_args()
    
    print("🚀 MemeGPT Database Initialization")
    print(f"Database URL: {settings.database_url}")
    print("-" * 50)
    
    # Test database connection
    if not await test_database_connection():
        print("\n❌ Cannot proceed without database connection.")
        print("Please ensure PostgreSQL is running and connection details are correct.")
        return False
    
    if args.test_connection:
        print("\n✅ Database connection test completed successfully!")
        return True
    
    # Check current state
    print("\n🔍 Checking current database state...")
    tables = await check_tables_exist()
    
    if args.reset:
        # Reset database
        if not await reset_database():
            return False
    else:
        # Check if we need to run migrations
        if not tables or not all(tables.values()):
            print("\n🔄 Some tables are missing. Running migrations...")
            if not run_alembic_migrations():
                return False
        else:
            print("\n✅ All tables already exist. Skipping migrations.")
    
    # Validate final state
    print("\n🔍 Validating database schema...")
    if await validate_schema():
        print("\n🎉 Database initialization completed successfully!")
        print("\nNext steps:")
        print("1. Start the FastAPI backend: python main.py")
        print("2. Start the ARQ worker: python worker.py")
        print("3. Access the API documentation at: http://localhost:8000/docs")
        return True
    else:
        print("\n❌ Database initialization failed!")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Initialization cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)