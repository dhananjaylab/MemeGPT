#!/usr/bin/env python3
"""
Check Imgflip API requirements and test without credentials.
"""

import asyncio
import httpx

async def test_imgflip_api():
    """Test Imgflip API to understand requirements."""
    print("🧪 Testing Imgflip API Requirements")
    print("=" * 60)
    
    # Test 1: Get memes (should work without credentials)
    print("\n1. Testing GET /get_memes (should work without credentials)")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get("https://api.imgflip.com/get_memes")
            data = response.json()
            if data.get("success"):
                memes = data.get("data", {}).get("memes", [])
                print(f"✅ SUCCESS - Got {len(memes)} templates")
                if memes:
                    print(f"   Example: {memes[0]['name']} (ID: {memes[0]['id']})")
            else:
                print(f"❌ FAILED - {data.get('error_message')}")
    except Exception as e:
        print(f"❌ ERROR - {e}")
    
    # Test 2: Caption image without credentials
    print("\n2. Testing POST /caption_image WITHOUT credentials")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.imgflip.com/caption_image",
                data={
                    "template_id": "87743020",  # Two Buttons
                    "text0": "Option A",
                    "text1": "Option B",
                }
            )
            data = response.json()
            if data.get("success"):
                print(f"✅ SUCCESS - {data.get('data', {}).get('url')}")
            else:
                print(f"❌ FAILED - {data.get('error_message')}")
    except Exception as e:
        print(f"❌ ERROR - {e}")
    
    # Test 3: Caption image with empty credentials
    print("\n3. Testing POST /caption_image WITH empty credentials")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.imgflip.com/caption_image",
                data={
                    "template_id": "87743020",
                    "text0": "Option A",
                    "text1": "Option B",
                    "username": "",
                    "password": "",
                }
            )
            data = response.json()
            if data.get("success"):
                print(f"✅ SUCCESS - {data.get('data', {}).get('url')}")
            else:
                print(f"❌ FAILED - {data.get('error_message')}")
    except Exception as e:
        print(f"❌ ERROR - {e}")

if __name__ == "__main__":
    asyncio.run(test_imgflip_api())