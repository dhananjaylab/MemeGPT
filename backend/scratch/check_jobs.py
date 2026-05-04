import asyncio
from db.session import AsyncSessionLocal, _init_engine
from sqlalchemy import select
from models.models import MemeJob

async def check():
    _init_engine()
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(MemeJob).where(MemeJob.status == 'processing'))
        jobs = res.scalars().all()
        print(f"Found {len(jobs)} processing jobs")
        for j in jobs:
            print(f"Job {j.id} updated at {j.updated_at}")

if __name__ == "__main__":
    asyncio.run(check())
