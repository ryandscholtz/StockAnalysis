#!/usr/bin/env python3
"""
Simple test script to debug the cached quote endpoint issue
"""
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_cached_quote():
    """Test the cached quote functionality directly"""
    try:
        # Import the dependencies
        from app.core.dependencies import get_service_container
        from app.data.api_client import YahooFinanceClient
        
        print("Testing cached quote functionality...")
        
        # Test 1: Create YahooFinanceClient directly
        print("\n1. Testing YahooFinanceClient creation...")
        try:
            yahoo_client = YahooFinanceClient()
            print("✓ YahooFinanceClient created successfully")
        except Exception as e:
            print(f"✗ Failed to create YahooFinanceClient: {e}")
            return
        
        # Test 2: Test get_quote method
        print("\n2. Testing get_quote method...")
        try:
            quote = yahoo_client.get_quote("AAPL")
            print(f"✓ get_quote returned: {quote}")
        except Exception as e:
            print(f"✗ get_quote failed: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Test 3: Test service container
        print("\n3. Testing service container...")
        try:
            container = get_service_container()
            yahoo_from_container = container.yahoo_client
            print("✓ Service container created YahooFinanceClient successfully")
        except Exception as e:
            print(f"✗ Service container failed: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Test 4: Test cache manager
        print("\n4. Testing cache manager...")
        try:
            from app.cache_manager import cache_manager
            cache_manager.set("test_key", {"test": "value"}, 1)
            result = cache_manager.get("test_key")
            print(f"✓ Cache manager working: {result}")
        except Exception as e:
            print(f"✗ Cache manager failed: {e}")
            import traceback
            traceback.print_exc()
        
        print("\nAll tests completed!")
        
    except Exception as e:
        print(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_cached_quote())