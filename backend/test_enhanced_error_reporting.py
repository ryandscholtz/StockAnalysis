#!/usr/bin/env python3
"""
Test script for enhanced API error reporting
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.data.api_client import YahooFinanceClient

async def test_enhanced_error_reporting():
    """Test the enhanced error reporting functionality"""
    print("=== Testing Enhanced API Error Reporting ===\n")

    client = YahooFinanceClient()

    # Test cases
    test_cases = [
        ("AAPL", "Valid ticker - should succeed"),
        ("INVALID_TICKER_12345", "Invalid ticker - should provide detailed error"),
        ("PPE.JO", "International ticker - may succeed or fail with details"),
        ("COKE", "Valid ticker - should succeed"),
    ]

    for ticker, description in test_cases:
        print(f"Testing {ticker}: {description}")
        print("-" * 50)

        try:
            # Run in executor to match the API behavior
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, client.get_quote, ticker)

            if result:
                if result.get('success'):
                    print(f"✅ SUCCESS: {ticker}")
                    print(f"   Price: ${result.get('price', 'N/A')}")
                    print(f"   Company: {result.get('company_name', 'N/A')}")
                    print(f"   Comment: {result.get('error_detail', 'No comment')}")
                    if result.get('info_warning'):
                        print(f"   Warning: {result.get('info_warning')}")
                else:
                    print(f"❌ ERROR: {ticker}")
                    print(f"   Error: {result.get('error', 'Unknown error')}")
                    print(f"   Detail: {result.get('error_detail', 'No details')}")
            else:
                print(f"❌ FAILED: {ticker} - No result returned")

        except Exception as e:
            print(f"❌ EXCEPTION: {ticker} - {e}")

        print()

    print("=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_enhanced_error_reporting())
