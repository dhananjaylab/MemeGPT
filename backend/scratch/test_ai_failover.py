#!/usr/bin/env python3
"""
Test script for AI suggestion endpoint failover.
"""

import urllib.request
import json

def test_ai_failover():
    """Test the AI suggestion endpoint failover by requesting a provider that might fail."""
    url = 'http://127.0.0.1:8000/api/ai/suggest'
    data = {
        'prompt': 'when your code works on the first try',
        # Don't specify provider to test default behavior and failover
    }
    
    req = urllib.request.Request(
        url, 
        data=json.dumps(data).encode('utf-8'), 
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        response = urllib.request.urlopen(req)
        result = response.read().decode('utf-8')
        print("✅ AI Failover Test SUCCESS")
        
        # Parse response to see which provider was used
        response_data = json.loads(result)
        provider_used = response_data.get('provider_used', 'unknown')
        num_options = len(response_data.get('options', []))
        
        print(f"Provider used: {provider_used}")
        print(f"Number of options: {num_options}")
        print("Response preview:", result[:300] + "..." if len(result) > 300 else result)
        
    except Exception as e:
        print("❌ AI Failover Test FAILED")
        if hasattr(e, 'read'):
            error_response = e.read().decode('utf-8')
            print("Error response:", error_response)
        else:
            print("Error:", str(e))

if __name__ == "__main__":
    test_ai_failover()