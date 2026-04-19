#!/usr/bin/env python3
"""
Test script to verify ARQ worker queue setup for async meme generation.
This script tests the complete workflow from job enqueueing to completion.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.services.worker import (
    enqueue_meme_generation, 
    get_job_status, 
    get_arq_pool,
    process_meme_generation
)
from backend.models.models import User
from backend.core.config import settings


async def test_arq_connection():
    """Test Redis connection for ARQ"""
    print("🔍 Testing ARQ Redis connection...")
    try:
        pool = await get_arq_pool()
        await pool.ping()
        print("✅ ARQ Redis connection successful")
        return True
    except Exception as e:
        print(f"❌ ARQ Redis connection failed: {e}")
        return False


async def test_job_enqueueing():
    """Test job enqueueing functionality"""
    print("\n🔍 Testing job enqueueing...")
    try:
        # Create a test user (optional)
        test_user = None  # Anonymous user for testing
        
        # Enqueue a test job
        job_id = await enqueue_meme_generation(
            prompt="Testing ARQ worker with a simple meme about cats",
            user=test_user
        )
        
        print(f"✅ Job enqueued successfully with ID: {job_id}")
        return job_id
    except Exception as e:
        print(f"❌ Job enqueueing failed: {e}")
        return None


async def test_job_status_polling(job_id: str, max_wait: int = 60):
    """Test job status polling and completion"""
    print(f"\n🔍 Testing job status polling for job: {job_id}")
    
    start_time = asyncio.get_event_loop().time()
    
    while True:
        try:
            status = await get_job_status(job_id)
            
            if not status:
                print(f"❌ Job {job_id} not found")
                return False
            
            print(f"📊 Job status: {status['status']}")
            
            if status['status'] == 'completed':
                print("✅ Job completed successfully!")
                if 'memes' in status:
                    print(f"🎨 Generated {len(status['memes'])} memes:")
                    for i, meme in enumerate(status['memes'], 1):
                        print(f"   {i}. {meme['template_name']}: {meme['meme_text']}")
                return True
            
            elif status['status'] == 'failed':
                print(f"❌ Job failed: {status.get('error', 'Unknown error')}")
                return False
            
            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait:
                print(f"⏰ Timeout after {max_wait} seconds")
                return False
            
            # Wait before next poll
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"❌ Error polling job status: {e}")
            return False


async def test_worker_function_directly():
    """Test the worker function directly (without queue)"""
    print("\n🔍 Testing worker function directly...")
    try:
        # Test the worker function directly
        result = await process_meme_generation(
            ctx={},
            job_id="test-direct-job",
            user_id=None,
            prompt="Direct test of meme generation about dogs"
        )
        
        if result['status'] == 'completed':
            print("✅ Direct worker function test successful")
            print(f"🎨 Generated {len(result.get('memes', []))} memes")
            return True
        else:
            print(f"❌ Direct worker function failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Direct worker function test failed: {e}")
        return False


async def test_configuration():
    """Test ARQ configuration and settings"""
    print("\n🔍 Testing ARQ configuration...")
    
    # Check Redis URL
    redis_url = settings.redis_url
    print(f"📋 Redis URL: {redis_url}")
    
    # Check OpenAI API key
    openai_key = settings.openai_api_key
    if openai_key and openai_key != "":
        print("✅ OpenAI API key configured")
    else:
        print("❌ OpenAI API key not configured")
        return False
    
    # Check required directories
    required_dirs = [
        Path("templates"),
        Path("fonts"),
        Path("output")
    ]
    
    for dir_path in required_dirs:
        if dir_path.exists():
            print(f"✅ Directory exists: {dir_path}")
        else:
            print(f"❌ Directory missing: {dir_path}")
            # Create missing directories
            dir_path.mkdir(exist_ok=True)
            print(f"📁 Created directory: {dir_path}")
    
    # Check meme_data.json
    meme_data_path = Path("meme_data.json")
    if meme_data_path.exists():
        print("✅ meme_data.json exists")
        try:
            with open(meme_data_path) as f:
                data = json.load(f)
                print(f"📊 Found {len(data)} meme templates")
        except Exception as e:
            print(f"❌ Error reading meme_data.json: {e}")
            return False
    else:
        print("❌ meme_data.json not found")
        return False
    
    return True


async def main():
    """Main test function"""
    print("🚀 Starting ARQ Worker Queue Test Suite")
    print("=" * 50)
    
    # Test configuration
    config_ok = await test_configuration()
    if not config_ok:
        print("\n❌ Configuration test failed. Please fix configuration issues.")
        return
    
    # Test Redis connection
    redis_ok = await test_arq_connection()
    if not redis_ok:
        print("\n❌ Redis connection failed. Please ensure Redis is running.")
        return
    
    # Test direct worker function
    direct_ok = await test_worker_function_directly()
    if not direct_ok:
        print("\n❌ Direct worker function test failed.")
        return
    
    # Test full workflow (enqueueing + polling)
    print("\n🔄 Testing full ARQ workflow...")
    job_id = await test_job_enqueueing()
    
    if job_id:
        success = await test_job_status_polling(job_id)
        if success:
            print("\n🎉 All ARQ worker tests passed!")
        else:
            print("\n❌ Job processing test failed.")
    else:
        print("\n❌ Job enqueueing test failed.")


if __name__ == "__main__":
    # Set up environment
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()