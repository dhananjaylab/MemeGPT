#!/usr/bin/env python3
"""
Simple ARQ worker test that doesn't require database dependencies.
This test verifies the core ARQ configuration and Redis connectivity.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Test Redis connectivity without importing backend modules
async def test_redis_connection():
    """Test basic Redis connection"""
    print("🔍 Testing Redis connection...")
    try:
        import redis.asyncio as redis
        
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        r = redis.from_url(redis_url)
        
        await r.ping()
        print("✅ Redis connection successful")
        await r.close()
        return True
    except ImportError:
        print("❌ Redis library not installed")
        return False
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False


async def test_arq_import():
    """Test ARQ library import"""
    print("\n🔍 Testing ARQ library import...")
    try:
        import arq
        from arq import create_pool, ArqRedis
        from arq.connections import RedisSettings
        
        print("✅ ARQ library imported successfully")
        print(f"📦 ARQ version: {arq.__version__}")
        return True
    except ImportError as e:
        print(f"❌ ARQ library import failed: {e}")
        return False


async def test_arq_pool():
    """Test ARQ Redis pool creation"""
    print("\n🔍 Testing ARQ Redis pool creation...")
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis_settings = RedisSettings.from_dsn(redis_url)
        
        pool = await create_pool(redis_settings)
        await pool.ping()
        print("✅ ARQ Redis pool created and tested successfully")
        await pool.close()
        return True
    except Exception as e:
        print(f"❌ ARQ Redis pool test failed: {e}")
        return False


def test_file_structure():
    """Test required file structure"""
    print("\n🔍 Testing file structure...")
    
    required_files = [
        "meme_data.json",
        "backend/services/worker.py",
        "backend/models/models.py",
        "run_worker.py"
    ]
    
    required_dirs = [
        "templates",
        "fonts",
        "output"
    ]
    
    all_good = True
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ File exists: {file_path}")
        else:
            print(f"❌ File missing: {file_path}")
            all_good = False
    
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✅ Directory exists: {dir_path}")
        else:
            print(f"📁 Creating directory: {dir_path}")
            Path(dir_path).mkdir(exist_ok=True)
    
    # Test meme_data.json content
    try:
        with open("meme_data.json") as f:
            data = json.load(f)
            print(f"✅ meme_data.json contains {len(data)} templates")
    except Exception as e:
        print(f"❌ Error reading meme_data.json: {e}")
        all_good = False
    
    return all_good


def test_environment():
    """Test environment configuration"""
    print("\n🔍 Testing environment configuration...")
    
    required_env = {
        "REDIS_URL": "redis://localhost:6379",
        "DATABASE_URL": "postgresql+asyncpg://user:password@localhost/memegpt",
        "OPENAI_API_KEY": ""
    }
    
    all_good = True
    
    for env_var, default in required_env.items():
        value = os.getenv(env_var, default)
        if value and value != "":
            if env_var == "OPENAI_API_KEY":
                # Don't print the actual key
                print(f"✅ {env_var}: configured (hidden)")
            else:
                print(f"✅ {env_var}: {value}")
        else:
            print(f"❌ {env_var}: not configured")
            if env_var == "OPENAI_API_KEY":
                all_good = False
    
    return all_good


async def test_worker_config():
    """Test worker configuration without importing backend"""
    print("\n🔍 Testing worker configuration...")
    
    try:
        # Set minimal environment for testing
        os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
        os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
        
        # Try to import worker settings
        sys.path.insert(0, str(Path(__file__).parent))
        
        # This will fail if dependencies are missing, but we can catch it
        try:
            from backend.services.worker import WorkerSettings
            print("✅ Worker configuration imported successfully")
            print(f"📊 Max jobs: {WorkerSettings.max_jobs}")
            print(f"⏱️  Job timeout: {WorkerSettings.job_timeout}s")
            return True
        except ImportError as e:
            print(f"⚠️  Worker configuration import failed (missing dependencies): {e}")
            print("   This is expected if database dependencies are not installed")
            return False
            
    except Exception as e:
        print(f"❌ Worker configuration test failed: {e}")
        return False


async def main():
    """Main test function"""
    print("🚀 Starting Simple ARQ Worker Test")
    print("=" * 50)
    
    # Test file structure
    files_ok = test_file_structure()
    
    # Test environment
    env_ok = test_environment()
    
    # Test Redis connection
    redis_ok = await test_redis_connection()
    
    # Test ARQ import
    arq_ok = await test_arq_import()
    
    # Test ARQ pool (only if Redis is working)
    pool_ok = False
    if redis_ok and arq_ok:
        pool_ok = await test_arq_pool()
    
    # Test worker config (may fail due to missing deps)
    worker_ok = await test_worker_config()
    
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    print(f"   File structure: {'✅' if files_ok else '❌'}")
    print(f"   Environment: {'✅' if env_ok else '❌'}")
    print(f"   Redis connection: {'✅' if redis_ok else '❌'}")
    print(f"   ARQ library: {'✅' if arq_ok else '❌'}")
    print(f"   ARQ pool: {'✅' if pool_ok else '❌'}")
    print(f"   Worker config: {'✅' if worker_ok else '⚠️ '}")
    
    if files_ok and redis_ok and arq_ok and pool_ok:
        print("\n🎉 Core ARQ setup is working! Worker should be able to start.")
        if not worker_ok:
            print("💡 Install missing dependencies to fully test worker configuration:")
            print("   pip install asyncpg sqlalchemy[asyncio] fastapi")
    else:
        print("\n❌ Some core components are not working. Please fix the issues above.")
    
    return files_ok and redis_ok and arq_ok and pool_ok


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)