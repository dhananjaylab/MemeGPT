import asyncio
import json
from sqlalchemy import select
from db.session import AsyncSessionLocal, _init_engine
from models.models import MemeTemplate

async def check_templates():
    _init_engine()
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(MemeTemplate).where(MemeTemplate.name.ilike('%Panik%')))
        templates = result.scalars().all()
        for t in templates:
            print(f"ID: {t.id}, Name: {t.name}, Image URL: {t.image_url}, File Path: {t.file_path}")

if __name__ == "__main__":
    asyncio.run(check_templates())
