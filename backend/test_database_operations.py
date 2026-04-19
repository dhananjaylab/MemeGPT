#!/usr/bin/env python3
"""
Test script to demonstrate database operations with the new models.

This script shows how to:
1. Create users with different plans
2. Create meme templates
3. Generate memes and jobs
4. Query data with relationships

Usage:
    python test_database_operations.py
"""

import asyncio
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from db.session import get_db, engine
from models.models import User, GeneratedMeme, MemeJob, MemeTemplate


async def create_sample_user(db: AsyncSession) -> User:
    """Create a sample user for testing."""
    user = User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        plan="free",
        daily_limit=5,
        daily_used=0
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    print(f"✅ Created user: {user.email} (Plan: {user.plan})")
    return user


async def create_sample_template(db: AsyncSession) -> MemeTemplate:
    """Create a sample meme template for testing."""
    template = MemeTemplate(
        name="Drake Pointing",
        alternative_names=["Drake", "Drake Hotline Bling"],
        file_path="/templates/drake.jpg",
        font_path="/fonts/impact.ttf",
        text_color="#FFFFFF",
        text_stroke=True,
        usage_instructions="Two text fields: top (rejection) and bottom (approval)",
        number_of_text_fields=2,
        text_coordinates_xy_wh=[[10, 10, 300, 100], [10, 200, 300, 100]],
        example_output=["Old way of doing things", "New improved way"]
    )
    
    db.add(template)
    await db.commit()
    await db.refresh(template)
    
    print(f"✅ Created template: {template.name}")
    return template


async def create_sample_meme(db: AsyncSession, user: User, template: MemeTemplate) -> GeneratedMeme:
    """Create a sample generated meme for testing."""
    meme = GeneratedMeme(
        id=str(uuid.uuid4()),
        user_id=user.id,
        prompt="Make a meme about learning Python",
        template_name=template.name,
        template_id=template.id,
        meme_text=["Learning Python the hard way", "Using MemeGPT to learn Python"],
        image_url="https://example.com/memes/sample.jpg",
        thumbnail_url="https://example.com/memes/sample_thumb.jpg",
        share_count=0,
        is_public=True
    )
    
    db.add(meme)
    await db.commit()
    await db.refresh(meme)
    
    print(f"✅ Created meme: {meme.id} for user {user.email}")
    return meme


async def create_sample_job(db: AsyncSession, user: User) -> MemeJob:
    """Create a sample meme generation job for testing."""
    job = MemeJob(
        id=str(uuid.uuid4()),
        user_id=user.id,
        prompt="Create a funny meme about debugging code",
        status="pending"
    )
    
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    print(f"✅ Created job: {job.id} with status {job.status}")
    return job


async def demonstrate_queries(db: AsyncSession):
    """Demonstrate various database queries."""
    print("\n🔍 Demonstrating Database Queries")
    print("-" * 40)
    
    # Count users by plan
    result = await db.execute(
        select(User.plan, func.count(User.id).label('count'))
        .group_by(User.plan)
    )
    user_counts = result.all()
    
    print("User counts by plan:")
    for plan, count in user_counts:
        print(f"  - {plan}: {count}")
    
    # Get memes with user information
    result = await db.execute(
        select(GeneratedMeme, User.email)
        .join(User, GeneratedMeme.user_id == User.id)
        .where(GeneratedMeme.is_public == True)
    )
    memes_with_users = result.all()
    
    print(f"\nPublic memes ({len(memes_with_users)}):")
    for meme, user_email in memes_with_users:
        print(f"  - {meme.template_name} by {user_email}")
    
    # Get pending jobs
    result = await db.execute(
        select(MemeJob)
        .where(MemeJob.status == "pending")
    )
    pending_jobs = result.scalars().all()
    
    print(f"\nPending jobs: {len(pending_jobs)}")
    for job in pending_jobs:
        print(f"  - Job {job.id}: {job.prompt[:50]}...")
    
    # Get templates with usage count
    result = await db.execute(
        select(
            MemeTemplate.name,
            func.count(GeneratedMeme.id).label('usage_count')
        )
        .outerjoin(GeneratedMeme, MemeTemplate.name == GeneratedMeme.template_name)
        .group_by(MemeTemplate.name)
    )
    template_usage = result.all()
    
    print(f"\nTemplate usage:")
    for template_name, usage_count in template_usage:
        print(f"  - {template_name}: {usage_count} memes")


async def demonstrate_model_methods(db: AsyncSession):
    """Demonstrate model methods and properties."""
    print("\n🧪 Demonstrating Model Methods")
    print("-" * 40)
    
    # Get a user and demonstrate methods
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    
    if user:
        print(f"User: {user.email}")
        print(f"  - Is premium: {user.is_premium}")
        print(f"  - Has API access: {user.has_api_access}")
        print(f"  - Can generate: {user.can_generate()}")
        print(f"  - Remaining generations: {user.remaining_generations}")
    
    # Get a meme and demonstrate methods
    result = await db.execute(select(GeneratedMeme).limit(1))
    meme = result.scalar_one_or_none()
    
    if meme:
        print(f"\nMeme: {meme.id}")
        print(f"  - Is anonymous: {meme.is_anonymous}")
        print(f"  - Display URL: {meme.display_url}")
        print(f"  - Share count: {meme.share_count}")
    
    # Get a job and demonstrate methods
    result = await db.execute(select(MemeJob).limit(1))
    job = result.scalar_one_or_none()
    
    if job:
        print(f"\nJob: {job.id}")
        print(f"  - Is completed: {job.is_completed}")
        print(f"  - Is failed: {job.is_failed}")
        print(f"  - Is processing: {job.is_processing}")


async def cleanup_test_data(db: AsyncSession):
    """Clean up test data."""
    print("\n🧹 Cleaning up test data...")
    
    # Delete in correct order due to foreign key constraints
    await db.execute("DELETE FROM meme_jobs WHERE prompt LIKE '%debugging code%'")
    await db.execute("DELETE FROM memes WHERE prompt LIKE '%learning Python%'")
    await db.execute("DELETE FROM meme_templates WHERE name = 'Drake Pointing'")
    await db.execute("DELETE FROM users WHERE email = 'test@example.com'")
    
    await db.commit()
    print("✅ Test data cleaned up")


async def main():
    """Main test function."""
    print("🧪 Testing Database Operations for MemeGPT v2")
    print("=" * 50)
    
    # Test database connection
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Please ensure PostgreSQL is running and migrations have been applied.")
        return False
    
    # Get database session
    async with AsyncSession(engine) as db:
        try:
            # Create sample data
            print("\n📝 Creating Sample Data")
            print("-" * 30)
            
            user = await create_sample_user(db)
            template = await create_sample_template(db)
            meme = await create_sample_meme(db, user, template)
            job = await create_sample_job(db, user)
            
            # Demonstrate queries
            await demonstrate_queries(db)
            
            # Demonstrate model methods
            await demonstrate_model_methods(db)
            
            # Clean up
            await cleanup_test_data(db)
            
            print("\n🎉 All database operations completed successfully!")
            return True
            
        except Exception as e:
            print(f"\n❌ Database operation failed: {e}")
            await db.rollback()
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