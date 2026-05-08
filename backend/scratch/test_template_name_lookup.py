#!/usr/bin/env python3
"""
Test template name lookup functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.meme_ai import get_caption_generator

async def test_template_lookup():
    """Test AI generation with template name lookup."""
    print("🧪 Testing Template Name Lookup")
    print("=" * 60)
    
    prompt = "when you see a polar bear hunting a seal"
    
    try:
        print(f"Testing with prompt: '{prompt}'")
        print()
        
        # Test with OpenAI
        generator = await get_caption_generator("openai")
        result = await generator(prompt)
        
        if result:
            print(f"✅ SUCCESS - Generated {len(result)} memes:")
            for i, meme in enumerate(result, 1):
                print(f"\n  {i}. {meme.get('meme_name')} (ID: {meme.get('meme_id')})")
                print(f"     Text: {meme.get('meme_text')}")
                print(f"     Reasoning: {meme.get('reasoning', 'N/A')}")
        else:
            print("❌ FAILED - No results returned")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_template_lookup())