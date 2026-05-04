import asyncio
from sqlalchemy import select
from db import session as db_session
from models.models import GeneratedMeme

async def check_memes():
    db_session._init_engine()
    async with db_session.AsyncSessionLocal() as db:
        result = await db.execute(select(GeneratedMeme))
        memes = result.scalars().all()
        print(f"Total memes in DB: {len(memes)}")
        for meme in memes:
            print(f"Meme ID: {meme.id}, Prompt: {meme.prompt[:30]}, Is Public: {meme.is_public}, User ID: {meme.user_id}, Image URL: {meme.image_url}")

if __name__ == "__main__":
    asyncio.run(check_memes())
