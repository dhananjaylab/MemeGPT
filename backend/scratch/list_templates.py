import asyncio
from db import session as db_session
from sqlalchemy import select
from models.models import MemeTemplate

async def list_templates():
    db_session._init_engine()
    async with db_session.AsyncSessionLocal() as db:
        result = await db.execute(select(MemeTemplate))
        templates = result.scalars().all()
        print(f"Total templates: {len(templates)}")
        for t in templates:
            print(f"ID: {t.id}, Name: {t.name}, ImgflipID: {t.imgflip_id}")

if __name__ == "__main__":
    asyncio.run(list_templates())
