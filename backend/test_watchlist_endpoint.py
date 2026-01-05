#!/usr/bin/env python3
"""
Test the watchlist endpoint
"""
import requests

def test_watchlist_endpoint():
    """Test the /api/watchlist endpoint"""
    print("=== Testing Watchlist Endpoint ===\n")
    
    try:
        # Test the watchlist endpoint
        url = "http://127.0.0.1:8000/api/watchlist"
        print(f"Making request to: {url}")
        
        response = requests.get(url, timeout=15)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Watchlist endpoint working!")
            print(f"Number of items: {len(data.get('items', []))}")
            for item in data.get('items', [])[:3]:  # Show first 3 items
                print(f"  - {item.get('ticker', 'N/A')}: {item.get('company_name', 'N/A')}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed")
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_watchlist_endpoint()