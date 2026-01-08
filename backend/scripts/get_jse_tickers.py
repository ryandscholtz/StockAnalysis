"""
Helper script to get JSE ticker list
This is an example - you may need to adapt for other exchanges
"""
import yfinance as yf
import requests
from typing import List


def get_jse_tickers() -> List[str]:
    """
    Get list of JSE (Johannesburg Stock Exchange) tickers

    Note: This is a simplified example. For production, you may want to:
    1. Use a paid API (Financial Modeling Prep, Alpha Vantage)
    2. Scrape the exchange website
    3. Use a pre-compiled list
    """
    # Common JSE tickers (you'll need to expand this list)
    # Option 1: Use a known list
    common_jse_tickers = [
        "MRF.JO", "NPN.JO", "BTI.JO", "AGL.JO", "SHP.JO",
        "FSR.JO", "SOL.JO", "BID.JO", "NED.JO", "SBK.JO",
        # Add more tickers here
    ]

    # Option 2: Try to fetch from Yahoo Finance (limited)
    # This won't get all tickers, but can help discover some
    try:
        # Search for JSE stocks
        from yfinance import Search
        search = Search("JSE", max_results=100)
        if hasattr(search, 'quotes') and search.quotes:
            for quote in search.quotes:
                symbol = getattr(quote, 'symbol', '') or (quote.get('symbol') if isinstance(quote, dict) else '')
                if symbol and '.JO' in symbol:
                    if symbol not in common_jse_tickers:
                        common_jse_tickers.append(symbol)
    except Exception as e:
        print(f"Error searching for JSE tickers: {e}")

    return sorted(set(common_jse_tickers))


def save_ticker_list(tickers: List[str], filename: str = "jse_tickers.txt"):
    """Save ticker list to file"""
    with open(filename, 'w') as f:
        f.write("# JSE Ticker List\n")
        f.write("# Generated automatically\n\n")
        for ticker in tickers:
            f.write(f"{ticker}\n")
    print(f"Saved {len(tickers)} tickers to {filename}")


if __name__ == "__main__":
    tickers = get_jse_tickers()
    print(f"Found {len(tickers)} JSE tickers")
    save_ticker_list(tickers)
    print("\nFirst 10 tickers:")
    for ticker in tickers[:10]:
        print(f"  {ticker}")
