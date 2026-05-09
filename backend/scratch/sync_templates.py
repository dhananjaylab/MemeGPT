import asyncio
from db import session as db_session
from services.imgflip import imgflip_service

async def sync():
    db_session._init_engine()
    async with db_session.AsyncSessionLocal() as db:
        print("Syncing templates from Imgflip...")
        stats = await imgflip_service.sync_templates_to_db(db)
        print(f"Sync complete: {stats}")

if __name__ == "__main__":
    asyncio.run(sync())
