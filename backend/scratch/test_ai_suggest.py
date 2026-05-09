#!/usr/bin/env python3
"""
Test script for AI suggestion endpoint.
"""

import urllib.request
import json

def test_ai_suggest():
    """Test the AI suggestion endpoint."""
    url = 'http://127.0.0.1:8000/api/ai/suggest'
    data = {
        'prompt': 'when you realize it\'s Monday tomorrow',
        'provider': 'openai'
    }
    
    req = urllib.request.Request(
        url, 
        data=json.dumps(data).encode('utf-8'), 
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        response = urllib.request.urlopen(req)
        result = response.read().decode('utf-8')
        print("✅ AI Suggest Test SUCCESS")
        print("Response:", result[:500] + "..." if len(result) > 500 else result)
    except Exception as e:
        print("❌ AI Suggest Test FAILED")
        if hasattr(e, 'read'):
            error_response = e.read().decode('utf-8')
            print("Error response:", error_response)
        else:
            print("Error:", str(e))

if __name__ == "__main__":
    test_ai_suggest()