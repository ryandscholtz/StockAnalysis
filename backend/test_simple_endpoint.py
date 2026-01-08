#!/usr/bin/env python3
"""
Test a simple endpoint to check if server is working
"""
import requests

def test_simple_endpoint():
    """Test the /api/version endpoint"""
    print("=== Testing Simple Endpoint ===\n")

    try:
        # Test the version endpoint (should be fast)
        url = "http://127.0.0.1:8000/api/version"
        print(f"Making request to: {url}")

        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Server is working!")
            print(f"Response: {data}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - server not running or not accessible")
    except requests.exceptions.Timeout:
        print("❌ Request timed out - server may be hanging")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_simple_endpoint()
