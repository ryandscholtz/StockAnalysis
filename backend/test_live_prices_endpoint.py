#!/usr/bin/env python3
"""
Test the live-prices endpoint directly
"""
import requests
import json

def test_live_prices_endpoint():
    """Test the /api/watchlist/live-prices endpoint"""
    print("=== Testing Live Prices Endpoint ===\n")

    try:
        # Test the endpoint
        url = "http://127.0.0.1:8000/api/watchlist/live-prices"
        print(f"Making request to: {url}")

        response = requests.get(url, timeout=60)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("Response received successfully!")
            print(f"Number of tickers: {len(data.get('live_prices', {}))}")

            # Display detailed results
            for ticker, result in data.get('live_prices', {}).items():
                print(f"\n--- {ticker} ---")
                if result.get('success'):
                    print(f"✅ SUCCESS")
                    print(f"   Price: ${result.get('price', 'N/A')}")
                    print(f"   Company: {result.get('company_name', 'N/A')}")
                    print(f"   Comment: {result.get('comment', 'No comment')}")
                else:
                    print(f"❌ ERROR: {result.get('error', 'Unknown error')}")
                    print(f"   Comment: {result.get('comment', 'No comment')}")
        else:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - is the backend server running?")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_live_prices_endpoint()
