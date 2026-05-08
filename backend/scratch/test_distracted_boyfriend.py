#!/usr/bin/env python3
"""
Test Distracted Boyfriend template caption order.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.meme_ai import get_caption_generator

async def test_distracted_boyfriend():
    """Test that Distracted Boyfriend captions are in correct order."""
    print("🧪 Testing Distracted Boyfriend Caption Order")
    print("=" * 60)
    
    prompt = "playing FIFA vs playing cricket in summer heat"
    
    print(f"Prompt: '{prompt}'")
    print()
    print("Expected order for Distracted Boyfriend:")
    print("  1. The tempting/new thing (left - other girl)")
    print("  2. The person (middle - boyfriend)")
    print("  3. The current commitment (right - girlfriend)")
    print()
    
    try:
        generator = await get_caption_generator("openai")
        result = await generator(prompt)
        
        if result:
            print(f"✅ Generated {len(result)} memes")
            
            # Find Distracted Boyfriend in results
            for meme in result:
                if "distracted" in meme.get('meme_name', '').lower():
                    print(f"\n📋 {meme['meme_name']} (ID: {meme['meme_id']})")
                    texts = meme.get('meme_text', [])
                    print(f"   1. Left (other girl): '{texts[0] if len(texts) > 0 else 'N/A'}'")
                    print(f"   2. Middle (boyfriend): '{texts[1] if len(texts) > 1 else 'N/A'}'")
                    print(f"   3. Right (girlfriend): '{texts[2] if len(texts) > 2 else 'N/A'}'")
                    print(f"   Reasoning: {meme.get('reasoning', 'N/A')}")
                    
                    # Validate order
                    if len(texts) >= 3:
                        if 'fifa' in texts[0].lower() or 'air' in texts[0].lower():
                            print("\n   ✅ ORDER CORRECT: Tempting thing is in position 1")
                        else:
                            print("\n   ❌ ORDER WRONG: Tempting thing should be in position 1")
        else:
            print("❌ No results returned")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_distracted_boyfriend())