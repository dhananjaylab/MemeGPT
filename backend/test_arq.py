import asyncio
from arq import create_pool
from arq.connections import RedisSettings

async def main():
    settings = RedisSettings(host='localhost', port=6379)
    pool = await create_pool(settings)
    
    print("ARQ Pool methods:")
    methods = [m for m in dir(pool) if not m.startswith('_')]
    for method in methods:
        print(f"  - {method}")
    
    await pool.close()

if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
