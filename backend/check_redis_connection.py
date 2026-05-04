import asyncio
import os
import sys
from dotenv import load_dotenv
from arq import create_pool
from arq.connections import RedisSettings

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

async def main():
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    print(f"Testing Redis connection to: {redis_url}")
    print("-" * 60)
    
    try:
        # Parse Redis URL
        settings = RedisSettings.from_dsn(redis_url)
        print(f"Host: {settings.host}")
        print(f"Port: {settings.port}")
        print(f"Database: {settings.database}")
        print("-" * 60)
        
        # Try to create pool
        print("Attempting to connect to Redis...")
        pool = await create_pool(settings)
        print("[SUCCESS] Connected to Redis!")
        
        # Test ping
        result = await pool.ping()
        print(f"[SUCCESS] Ping result: {result}")
        
        # Check available methods
        print("\nAvailable ARQ pool methods:")
        methods = [m for m in dir(pool) if not m.startswith('_') and callable(getattr(pool, m))]
        for method in sorted(methods):
            print(f"  - {method}")
        
        await pool.close()
        print("\n[SUCCESS] Connection test completed!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        print("\nPlease check:")
        print("1. Your REDIS_URL in .env file")
        print("2. Redis Cloud credentials are correct")
        print("3. Redis Cloud instance is running")
        print("4. Firewall/network allows connection")
        print("\nExpected format: redis://username:password@host:port/db")
        print("Or for Redis Cloud: redis://default:password@host:port")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

# Made with Bob
