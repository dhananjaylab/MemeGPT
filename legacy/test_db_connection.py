#!/usr/bin/env python3
"""Test database connection."""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from db.session import engine
from sqlalchemy import text

async def test_connection():
    """Test database connection."""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text('SELECT 1'))
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)