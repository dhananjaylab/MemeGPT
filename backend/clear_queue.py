#!/usr/bin/env python
import sys
import asyncio
from core.config import settings
from services.worker import get_arq_pool

async def clear_queue():
    try:
        pool = await get_arq_pool()
        # Clear all jobs
        await pool.aclose()
        print("Queue cleared - pool closed")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(clear_queue())
