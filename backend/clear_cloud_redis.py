#!/usr/bin/env python
"""Clear stuck jobs from cloud Redis"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from core.config import settings

def clear_cloud_redis():
    """Connect to cloud Redis and clear stuck jobs"""
    try:
        # Parse Redis URL - it's in format: redis://user:password@host:port
        redis_url = settings.redis_url
        print(f"Connecting to Redis: {redis_url.split('@')[1] if '@' in redis_url else redis_url}")
        
        # Use arq's built-in Redis connection
        import asyncio
        from arq.connections import RedisSettings
        from arq import create_pool
        
        redis_settings = RedisSettings.from_dsn(redis_url)
        
        async def do_clear():
            # Create a pool to clear
            pool = await create_pool(redis_settings)
            
            # The pool is the Redis connection, use it directly
            # Clear all keys
            await pool.flushdb()
            print(f"✅ Cleared cloud Redis database")
            
            # List remaining keys
            keys = await pool.keys('*')
            print(f"Remaining keys in Redis: {len(keys)}")
            
            await pool.aclose()
            return True
        
        result = asyncio.run(do_clear())
        if result:
            print("✅ Successfully cleared stuck jobs from cloud Redis")
            return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = clear_cloud_redis()
    sys.exit(0 if success else 1)
