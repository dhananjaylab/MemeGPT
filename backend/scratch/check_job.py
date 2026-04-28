import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add current directory to path to import models
sys.path.append(os.getcwd())
from models.models import MemeJob

async def check():
    engine = create_async_engine('postgresql+asyncpg://neondb_owner:npg_EwQCSO4MfDl9@ep-raspy-firefly-a7li2pgc-pooler.ap-southeast-2.aws.neon.tech/neondb?ssl=require')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        # Check all pending/failed jobs
        res = await session.execute(select(MemeJob).order_by(MemeJob.created_at.desc()).limit(5))
        jobs = res.scalars().all()
        for job in jobs:
            print(f"ID: {job.id}")
            print(f"  Status: {job.status}")
            print(f"  Error: {job.error_message}")
            print("-" * 20)
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
