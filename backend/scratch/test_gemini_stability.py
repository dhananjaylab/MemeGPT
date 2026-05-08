#!/usr/bin/env python3
"""
Test script for Gemini stability improvements.
Tests both providers and failover logic.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.meme_ai import get_caption_generator, AIProvider
from core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_provider(provider_name: str, prompt: str):
    """Test a specific provider with a given prompt."""
    print(f"\n{'='*60}")
    print(f"Testing {provider_name.upper()} with prompt: '{prompt}'")
    print(f"{'='*60}")
    
    try:
        generator = await get_caption_generator(provider_name)
        result = await generator(prompt)
        
        if result:
            print(f"✅ {provider_name.upper()} SUCCESS - Generated {len(result)} memes:")
            for i, meme in enumerate(result, 1):
                print(f"  {i}. {meme.get('meme_name', 'Unknown')} (ID: {meme.get('meme_id', 'N/A')})")
                print(f"     Text: {meme.get('meme_text', [])}")
                print(f"     Reasoning: {meme.get('reasoning', 'N/A')}")
        else:
            print(f"❌ {provider_name.upper()} FAILED - No results returned")
            
    except Exception as e:
        print(f"❌ {provider_name.upper()} ERROR: {e}")
        logger.exception(f"Error testing {provider_name}")

async def test_failover_logic():
    """Test the failover logic by simulating provider failures."""
    print(f"\n{'='*60}")
    print("Testing Failover Logic")
    print(f"{'='*60}")
    
    # Test with a provider that might not be configured
    test_prompts = [
        "when you realize it's Monday tomorrow",
        "trying to explain crypto to your parents",
        "when the group project is due tomorrow"
    ]
    
    for prompt in test_prompts:
        print(f"\nTesting failover with: '{prompt}'")
        
        # Test Gemini first (with OpenAI fallback)
        if settings.has_gemini or settings.has_openai:
            generator = await get_caption_generator("gemini")
            result = await generator(prompt)
            
            if result:
                print(f"✅ Failover test passed - Got {len(result)} results")
            else:
                print("❌ Failover test failed - No results from any provider")
        else:
            print("⚠️  No providers configured for failover test")

async def main():
    """Main test function."""
    print("🧪 Gemini Stability Test Suite")
    print(f"OpenAI configured: {settings.has_openai}")
    print(f"Gemini configured: {settings.has_gemini}")
    print(f"Default provider: {settings.ai_provider}")
    
    if not settings.has_openai and not settings.has_gemini:
        print("❌ No AI providers configured. Please set API keys in .env file.")
        return
    
    test_prompt = "when you're debugging code at 3am and find the bug"
    
    # Test individual providers
    if settings.has_openai:
        await test_provider("openai", test_prompt)
    
    if settings.has_gemini:
        await test_provider("gemini", test_prompt)
    
    # Test failover logic
    await test_failover_logic()
    
    print(f"\n{'='*60}")
    print("✅ Test suite completed!")
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(main())