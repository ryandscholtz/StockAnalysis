#!/usr/bin/env python3
"""
Test the optimized endpoints for instant responses
"""
import requests
import time

def test_optimized_endpoints():
    """Test the new optimized endpoints"""
    print("=== Testing Optimized Endpoints ===\n")

    base_url = "http://127.0.0.1:8000/api"

    # Test 1: Cached watchlist (should be instant)
    print("1. Testing cached watchlist endpoint...")
    start_time = time.time()
    try:
        response = requests.get(f"{base_url}/watchlist/cached", timeout=5)
        end_time = time.time()

        print(f"   Response time: {(end_time - start_time)*1000:.0f}ms")
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ SUCCESS: Found {data.get('total', 0)} watchlist items")
            print(f"   Cached: {data.get('cached', False)}")
        else:
            print(f"   ❌ ERROR: {response.text}")
    except Exception as e:
        print(f"   ❌ EXCEPTION: {e}")

    print()

    # Test 2: Async live prices (should return task ID immediately)
    print("2. Testing async live prices endpoint...")
    start_time = time.time()
    try:
        response = requests.get(f"{base_url}/watchlist/live-prices-async", timeout=5)
        end_time = time.time()

        print(f"   Response time: {(end_time - start_time)*1000:.0f}ms")
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if 'task_id' in data:
                print(f"   ✅ SUCCESS: Got task ID {data['task_id']}")
                print(f"   Message: {data.get('message', 'No message')}")

                # Test task status endpoint
                task_id = data['task_id']
                print(f"\n   Testing task status for {task_id}...")

                status_response = requests.get(f"{base_url}/tasks/{task_id}", timeout=5)
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"   Task status: {status_data.get('status', 'unknown')}")
                    print(f"   Progress: {status_data.get('progress', 0)}%")
                else:
                    print(f"   ❌ Task status error: {status_response.text}")

            elif 'live_prices' in data:
                print(f"   ✅ SUCCESS: Got cached live prices immediately")
                print(f"   Cached: {data.get('cached', False)}")
            else:
                print(f"   ❌ UNEXPECTED RESPONSE: {data}")
        else:
            print(f"   ❌ ERROR: {response.text}")
    except Exception as e:
        print(f"   ❌ EXCEPTION: {e}")

    print()

    # Test 3: Health check
    print("3. Testing detailed health check...")
    start_time = time.time()
    try:
        response = requests.get(f"{base_url}/health/detailed", timeout=5)
        end_time = time.time()

        print(f"   Response time: {(end_time - start_time)*1000:.0f}ms")
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ SUCCESS: System status: {data.get('status', 'unknown')}")

            # Show key metrics
            if 'background_tasks' in data:
                tasks = data['background_tasks']
                print(f"   Background tasks: {tasks.get('running', 0)} running, {tasks.get('total', 0)} total")

            if 'cache' in data:
                cache = data['cache']
                print(f"   Cache: {cache.get('active_entries', 0)} entries, {cache.get('current_size_mb', 0)}MB used")

        else:
            print(f"   ❌ ERROR: {response.text}")
    except Exception as e:
        print(f"   ❌ EXCEPTION: {e}")

    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_optimized_endpoints()
