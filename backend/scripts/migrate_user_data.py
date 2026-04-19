import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import AsyncSessionLocal, engine
from ..models.models import User, GeneratedMeme, MemeJob
from ..core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths for legacy data (if they exist)
LEGACY_DATA_DIR = Path("legacy")
USER_MIGRATION_FILE = LEGACY_DATA_DIR / "v1_users.json"
HISTORY_MIGRATION_FILE = LEGACY_DATA_DIR / "v1_history.json"

async def migrate_users(db: AsyncSession):
    """
    3.2.1 Create user accounts for existing session data
    3.2.3 Preserve user preferences and settings
    """
    logger.info("Starting user account migration...")
    
    if not USER_MIGRATION_FILE.exists():
        logger.warning(f"Legacy user data file {USER_MIGRATION_FILE} not found. Skipping user migration.")
        # Create a dummy user for testing if needed
        return

    try:
        with open(USER_MIGRATION_FILE, 'r', encoding='utf-8') as f:
            legacy_users = json.load(f)
            
        count = 0
        for u_data in legacy_users:
            email = u_data.get("email")
            if not email:
                continue
                
            # Check if user already exists
            result = await db.execute(select(User).where(User.email == email))
            existing_user = result.scalar_one_or_none()
            
            if not existing_user:
                new_user = User(
                    id=u_data.get("id", str(uuid4())),
                    email=email,
                    plan=u_data.get("plan", "free"),
                    daily_limit=u_data.get("daily_limit", settings.rate_limit_free),
                    daily_used=u_data.get("daily_used", 0),
                    created_at=datetime.fromisoformat(u_data.get("created_at")) if u_data.get("created_at") else datetime.now(timezone.utc),
                    preferences=u_data.get("preferences", {})
                )
                db.add(new_user)
                count += 1
            else:
                logger.info(f"User {email} already exists, skipping.")
                
        await db.commit()
        logger.info(f"Successfully migrated {count} users.")
    except Exception as e:
        logger.error(f"Error migrating users: {e}")
        await db.rollback()

async def migrate_history(db: AsyncSession):
    """
    3.2.2 Migrate meme generation history to new schema
    """
    logger.info("Starting meme history migration...")
    
    if not HISTORY_MIGRATION_FILE.exists():
        logger.warning(f"Legacy history data file {HISTORY_MIGRATION_FILE} not found. Skipping history migration.")
        return

    try:
        with open(HISTORY_MIGRATION_FILE, 'r', encoding='utf-8') as f:
            legacy_history = json.load(f)
            
        count = 0
        for h_data in legacy_history:
            meme_id = h_data.get("id", str(uuid4()))
            
            # Check if meme already exists
            result = await db.execute(select(GeneratedMeme).where(GeneratedMeme.id == meme_id))
            if result.scalar_one_or_none():
                continue
                
            new_meme = GeneratedMeme(
                id=meme_id,
                user_id=h_data.get("user_id"),
                prompt=h_data.get("prompt", ""),
                template_name=h_data.get("template_name", "unknown"),
                template_id=h_data.get("template_id", 0),
                meme_text=h_data.get("meme_text", []),
                image_url=h_data.get("image_url", ""),
                is_public=h_data.get("is_public", True),
                created_at=datetime.fromisoformat(h_data.get("created_at")) if h_data.get("created_at") else datetime.now(timezone.utc)
            )
            db.add(new_meme)
            count += 1
            
        await db.commit()
        logger.info(f"Successfully migrated {count} meme history records.")
    except Exception as e:
        logger.error(f"Error migrating history: {e}")
        await db.rollback()

async def handle_anonymous_sessions(db: AsyncSession):
    """
    3.2.4 Generate unique user IDs for anonymous sessions
    This utility tags anonymous memes with a generated session user if multiple memes share a common session trait.
    For now, it ensures all memes without a user_id are at least discoverable.
    """
    logger.info("Processing anonymous sessions...")
    
    # In v2, we want to group memes that belonged to the same anonymous session
    # For migration, if we can't find session logs, we'll generate unique IDs for them
    result = await db.execute(select(GeneratedMeme).where(GeneratedMeme.user_id == None))
    anon_memes = result.scalars().all()
    
    if not anon_memes:
        logger.info("No anonymous memes without IDs found.")
        return

    # 3.2.4 Generate unique user IDs for anonymous sessions
    for meme in anon_memes:
        # Generate a unique 'anon_' prefixed ID to track this session
        anon_id = f"anon_{uuid4().hex[:12]}"
        meme.user_id = anon_id
        logger.info(f"Generated anonymous ID {anon_id} for meme {meme.id}")
        
    await db.commit()
    logger.info(f"Successfully processed {len(anon_memes)} anonymous sessions.")
    
async def validate_data_integrity(db: AsyncSession):
    """
    3.2.5 Validate data integrity after migration
    """
    logger.info("Validating data integrity...")
    
    # 1. Check for memes with non-existent users
    result = await db.execute(
        select(GeneratedMeme).where(
            GeneratedMeme.user_id != None
        )
    )
    memes = result.scalars().all()
    
    invalid_memes = []
    for meme in memes:
        user_result = await db.execute(select(User).where(User.id == meme.user_id))
        if not user_result.scalar_one_or_none():
            invalid_memes.append(meme.id)
            
    if invalid_memes:
        logger.warning(f"Found {len(invalid_memes)} memes linked to non-existent users: {invalid_memes}")
    else:
        logger.info("Data integrity check passed: All user-linked memes have valid users.")

async def main():
    async with AsyncSessionLocal() as db:
        await migrate_users(db)
        await migrate_history(db)
        await handle_anonymous_sessions(db)
        await validate_data_integrity(db)

if __name__ == "__main__":
    asyncio.run(main())
