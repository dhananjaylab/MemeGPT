import asyncio
import sys, os, logging
logging.basicConfig(level=logging.DEBUG)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.session import get_db
from routers.memes import generate_meme_quick, GenerateMemeRequest

async def main():
    async for db in get_db():
        req = GenerateMemeRequest(prompt="when the wifi drops during a ranked match 2", ai_provider="gemini")
        try:
            res = await generate_meme_quick(req, db, current_user=None)
            print("Success:", res)
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
