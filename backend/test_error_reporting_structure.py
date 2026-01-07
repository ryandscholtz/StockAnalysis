#!/usr/bin/env python3
"""
Test the error reporting structure without actually calling slow APIs
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_error_reporting_structure():
    """Test the error reporting structure"""
    print("=== Testing Error Reporting Structure ===\n")

    # Mock API attempts data structure
    mock_api_attempts = [
        {
            'api': 'Yahoo Finance',
            'method': 'yf.Ticker() creation',
            'status': 'success',
            'details': 'Successfully created ticker object for AAPL'
        },
        {
            'api': 'Yahoo Finance',
            'method': 'ticker.history(period="5d")',
            'status': 'failed',
            'error': 'Expecting value: line 1 column 1 (char 0)',
            'details': 'Exception during 5-day history: JSON parsing error'
        },
        {
            'api': 'Yahoo Finance',
            'method': 'ticker.history(period="1mo")',
            'status': 'failed',
            'error': 'Expecting value: line 1 column 1 (char 0)',
            'details': 'Exception during 1-month history: JSON parsing error'
        },
        {
            'api': 'Yahoo Finance',
            'method': 'ticker.fast_info.lastPrice',
            'status': 'failed',
            'error': 'No lastPrice attribute',
            'details': 'fast_info object does not have lastPrice attribute or it is None'
        },
        {
            'api': 'Yahoo Finance',
            'method': 'ticker.info (attempt 1/3)',
            'status': 'failed',
            'error': 'Rate limited',
            'details': 'Rate limited during ticker.info attempt 1: 429 Too Many Requests'
        },
        {
            'api': 'Alpha Vantage',
            'method': 'get_quote()',
            'status': 'failed',
            'error': 'No price data returned',
            'details': 'Alpha Vantage returned empty or invalid quote data'
        },
        {
            'api': 'Financial Modeling Prep',
            'method': 'get_quote()',
            'status': 'failed',
            'error': 'No price data returned',
            'details': 'Financial Modeling Prep returned empty or invalid quote data'
        },
        {
            'api': 'Google Finance',
            'method': 'web_scraping',
            'status': 'failed',
            'error': 'No price data returned',
            'details': 'Google Finance web scraping returned empty or invalid quote data'
        },
        {
            'api': 'MarketStack',
            'method': 'get_intraday()',
            'status': 'failed',
            'error': 'No price data returned',
            'details': 'MarketStack returned empty or invalid intraday data'
        }
    ]

    # Test the formatting function
    from app.api.routes import _format_api_attempts_comment

    # Test failure case
    failure_comment = _format_api_attempts_comment(mock_api_attempts, success=False)
    print("Failure Comment:")
    print(failure_comment)
    print()

    # Test success case (modify one attempt to be successful)
    mock_api_attempts_success = mock_api_attempts.copy()
    mock_api_attempts_success[1] = {
        'api': 'Yahoo Finance',
        'method': 'ticker.history(period="5d")',
        'status': 'success',
        'price': 150.25,
        'details': 'Successfully retrieved price 150.25 from 5-day history'
    }

    success_comment = _format_api_attempts_comment(mock_api_attempts_success, success=True)
    print("Success Comment:")
    print(success_comment)
    print()

    # Test the structure
    print("API Attempts Structure:")
    for i, attempt in enumerate(mock_api_attempts):
        print(f"{i+1}. {attempt['api']} - {attempt['method']}: {attempt['status']}")
        if attempt['status'] == 'failed':
            print(f"   Error: {attempt['error']}")
            print(f"   Details: {attempt['details']}")
        print()

if __name__ == "__main__":
    test_error_reporting_structure()
