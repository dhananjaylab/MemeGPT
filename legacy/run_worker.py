#!/usr/bin/env python3
"""
Enhanced startup script for ARQ worker with health checks and monitoring
"""
import asyncio
import os
import signal
import sys
from pathlib import Path
from typing import Optional
import logging

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.services.worker import WorkerSettings, get_arq_pool, close_arq_pool
from backend.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global worker reference for graceful shutdown
worker_task: Optional[asyncio.Task] = None


async def check_dependencies():
    """Check if all required dependencies are available"""
    logger.info("Checking dependencies...")
    
    # Check Redis connection
    try:
        pool = await get_arq_pool()
        await pool.ping()
        logger.info("✅ Redis connection successful")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return False
    
    # Check required directories
    required_dirs = [
        Path("templates"),
        Path("fonts"),
        Path("output")
    ]
    
    for dir_path in required_dirs:
        if not dir_path.exists():
            logger.warning(f"Creating missing directory: {dir_path}")
            dir_path.mkdir(exist_ok=True)
        logger.info(f"✅ Directory available: {dir_path}")
    
    # Check meme_data.json
    meme_data_path = Path("meme_data.json")
    if not meme_data_path.exists():
        logger.error("❌ meme_data.json not found")
        return False
    logger.info("✅ meme_data.json found")
    
    # Check OpenAI API key
    if not settings.openai_api_key or settings.openai_api_key == "":
        logger.error("❌ OpenAI API key not configured")
        return False
    logger.info("✅ OpenAI API key configured")
    
    return True


async def run_worker():
    """Run the ARQ worker with proper error handling"""
    from arq import run_worker
    
    logger.info("Starting ARQ worker...")
    logger.info(f"Redis URL: {settings.redis_url}")
    logger.info(f"Max jobs: {WorkerSettings.max_jobs}")
    logger.info(f"Job timeout: {WorkerSettings.job_timeout}s")
    
    try:
        await run_worker(WorkerSettings)
    except Exception as e:
        logger.error(f"Worker error: {e}")
        raise


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    
    if worker_task and not worker_task.done():
        worker_task.cancel()
    
    # Close ARQ pool
    asyncio.create_task(close_arq_pool())
    
    sys.exit(0)


async def main():
    """Main function with dependency checks and graceful shutdown"""
    global worker_task
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Ensure we're in the right directory
    os.chdir(Path(__file__).parent)
    
    # Check dependencies
    if not await check_dependencies():
        logger.error("Dependency check failed. Please fix the issues above.")
        sys.exit(1)
    
    # Run worker
    try:
        worker_task = asyncio.create_task(run_worker())
        await worker_task
    except asyncio.CancelledError:
        logger.info("Worker task cancelled")
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        sys.exit(1)
    finally:
        await close_arq_pool()
        logger.info("Worker shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker interrupted")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)