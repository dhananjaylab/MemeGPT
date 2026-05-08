import asyncio
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from models.models import MemeTemplate
from core.config import settings

async def check_templates():
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as session:
        result = await session.execute(select(MemeTemplate))
        templates = result.scalars().all()
        
        for t in templates:
            print(f"ID: {t.id} | Name: {t.name} | URL: {t.image_url}")

if __name__ == "__main__":
    asyncio.run(check_templates())
