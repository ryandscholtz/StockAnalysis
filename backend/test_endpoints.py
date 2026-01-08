#!/usr/bin/env python3
"""
Test script to verify API endpoints are working after dependency injection fixes
"""
import requests
import json

def test_endpoints():
    base_url = "http://localhost:8000/api"
    
    endpoints = [
        ("/version", "Version endpoint"),
        ("/analysis-presets", "Analysis presets endpoint"),
        ("/search?q=AAPL", "Search endpoint"),
        ("/cache/watchlist", "Cached watchlist endpoint"),
        ("/quote/AAPL/cached", "Cached quote endpoint")
    ]
    
    for endpoint, name in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✓ {name}: {response.status_code} - OK")
            else:
                print(f"✗ {name}: {response.status_code} - {response.text[:100]}")
        except Exception as e:
            print(f"✗ {name}: Error - {e}")

if __name__ == "__main__":
    test_endpoints()