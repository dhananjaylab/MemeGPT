#!/usr/bin/env python3
"""
Debug OpenAI response format
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.meme_ai import generate_meme_captions

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    result = await generate_meme_captions("when you find a bug at 3am")
    print("Result:", result)

if __name__ == "__main__":
    asyncio.run(main())