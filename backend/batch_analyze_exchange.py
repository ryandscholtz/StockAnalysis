"""
Script to batch analyze all stocks on an exchange
Usage: python batch_analyze_exchange.py <exchange> <ticker_list_file>
"""
import asyncio
import sys
import json
from pathlib import Path
from app.api.batch_analysis import BatchAnalyzer


async def main():
    if len(sys.argv) < 3:
        print("Usage: python batch_analyze_exchange.py <exchange_name> <ticker_list_file>")
        print("\nExample:")
        print("  python batch_analyze_exchange.py JSE jse_tickers.txt")
        print("\nTicker list file format: one ticker per line")
        print("Example tickers:")
        print("  MRF.JO")
        print("  NPN.JO")
        print("  BTI.JO")
        sys.exit(1)
    
    exchange_name = sys.argv[1]
    ticker_file = Path(sys.argv[2])
    
    if not ticker_file.exists():
        print(f"Error: Ticker list file not found: {ticker_file}")
        sys.exit(1)
    
    # Load tickers from file
    with open(ticker_file, 'r') as f:
        tickers = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    print(f"Loaded {len(tickers)} tickers from {ticker_file}")
    
    # Create batch analyzer
    # Will auto-detect DynamoDB if USE_DYNAMODB env var is set
    analyzer = BatchAnalyzer(
        max_concurrent=5,  # Process 5 stocks concurrently
        requests_per_minute=30,  # Rate limit: 30 requests/min = 1800/hour
        results_dir="batch_results",
        use_database=True,  # Use database for storage and caching
        db_path="stock_analysis.db",  # SQLite database file (if not using DynamoDB)
        use_dynamodb=None,  # None = auto-detect from USE_DYNAMODB env var
        dynamodb_table="stock-analyses",  # DynamoDB table name
        dynamodb_region="us-east-1"  # AWS region
    )
    
    # Run analysis
    summary = await analyzer.analyze_ticker_list(
        tickers=tickers,
        exchange_name=exchange_name,
        resume=True  # Resume if interrupted
    )
    
    print(f"\nSummary: {json.dumps(summary, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())

