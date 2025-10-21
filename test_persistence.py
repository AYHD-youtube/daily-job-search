#!/usr/bin/env python3
"""
Test script to verify API key persistence
"""

import requests
import json

# Test API key persistence
def test_api_persistence():
    base_url = "http://localhost:5001"
    
    # Test data
    test_api_key = "test-api-key-12345"
    test_search_engine_id = "test-search-engine-67890"
    
    print("🧪 Testing API Key Persistence...")
    
    # Test saving API keys
    save_data = {
        "custom_search_api_key": test_api_key,
        "search_engine_id": test_search_engine_id
    }
    
    try:
        # Note: This would require authentication in a real test
        # For now, just verify the endpoint exists
        response = requests.post(f"{base_url}/api/save-api-keys", 
                               json=save_data, 
                               headers={'Content-Type': 'application/json'})
        
        print(f"✅ Save API keys endpoint: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API keys saved successfully")
        else:
            print(f"❌ API keys save failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing API persistence: {e}")

if __name__ == "__main__":
    test_api_persistence()
