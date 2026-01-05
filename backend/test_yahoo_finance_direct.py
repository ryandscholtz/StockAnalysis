#!/usr/bin/env python3
"""
Test Yahoo Finance API directly to see what's causing the hang
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.data.api_client import YahooFinanceClient
import asyncio
import time

async def test_yahoo_finance_direct():
    """Test Yahoo Finance API directly"""
    print("=== Testing Yahoo Finance API Directly ===\n")
    
    client = YahooFinanceClient()
    
    # Test with a simple ticker
    ticker = "AAPL"
    print(f"Testing {ticker}...")
    
    try:
        start_time = time.time()
        
        # Test the get_quote method directly
        result = client.get_quote(ticker)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"⏱️  Operation took {duration:.2f} seconds")
        
        if result:
            print(f"✅ Result received:")
            print(f"   Success: {result.get('success', 'N/A')}")
            print(f"   Price: {result.get('price', 'N/A')}")
            print(f"   Error: {result.get('error', 'N/A')}")
            print(f"   Detail: {result.get('error_detail', 'N/A')}")
        else:
            print("❌ No result returned")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_yahoo_finance_direct())