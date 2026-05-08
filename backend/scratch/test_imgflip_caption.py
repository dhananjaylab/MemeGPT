#!/usr/bin/env python3
"""
Test script for Imgflip caption API integration.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.imgflip import imgflip_service

async def test_imgflip_caption():
    """Test the Imgflip caption API."""
    print("🧪 Testing Imgflip Caption API")
    print("=" * 60)
    
    # Test with "Two Buttons" meme (Imgflip ID: 87743020)
    template_id = "87743020"
    texts = [
        "Use local compositor",
        "Use Imgflip API",
        "Smart meme generator"
    ]
    
    try:
        print(f"Generating meme with template ID: {template_id}")
        print(f"Texts: {texts}")
        print()
        
        result = await imgflip_service.caption_image(template_id, texts)
        
        if result.get("success"):
            meme_url = result.get("data", {}).get("url")
            print("✅ Imgflip Caption API SUCCESS")
            print(f"Generated meme URL: {meme_url}")
            print()
            print("Note: If you have Imgflip credentials configured,")
            print("the meme will be watermark-free. Otherwise, it will")
            print("have an Imgflip watermark.")
        else:
            print("❌ Imgflip Caption API FAILED")
            print(f"Error: {result.get('error_message', 'Unknown error')}")
            
    except Exception as e:
        print("❌ Imgflip Caption API ERROR")
        print(f"Exception: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_imgflip_caption())