"""
Batch stock analysis for entire exchanges
Handles rate limiting, error recovery, and progress tracking
"""
import asyncio
import json
import os
from datetime import datetime, date
from typing import List, Dict, Optional
from pathlib import Path
from app.api.progress import ProgressTracker
from app.data.api_client import YahooFinanceClient
from app.database.db_service import DatabaseService
from app.database.dynamodb_service import DynamoDBService


class BatchAnalyzer:
    """Analyze all stocks on an exchange with rate limiting and error handling"""

    def __init__(self,
                 max_concurrent: int = 5,
                 requests_per_minute: int = 30,
                 results_dir: str = "batch_results",
                 use_database: bool = True,
                 db_path: str = "stock_analysis.db",
                 use_dynamodb: Optional[bool] = None,
                 dynamodb_table: str = "stock-analyses",
                 dynamodb_region: str = "us-east-1"):
        """
        Args:
            max_concurrent: Maximum concurrent analyses
            requests_per_minute: Rate limit for Yahoo Finance (default 30/min = 1800/hour)
            results_dir: Directory to save results
            use_database: Whether to use database for storage and caching
            db_path: Path to SQLite database file (if using SQLite)
            use_dynamodb: Whether to use DynamoDB (None = auto-detect from env)
            dynamodb_table: DynamoDB table name
            dynamodb_region: AWS region for DynamoDB
        """
        self.max_concurrent = max_concurrent
        self.requests_per_minute = requests_per_minute
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        self.yahoo_client = YahooFinanceClient()
        self.use_database = use_database

        # Determine which database backend to use
        if not use_database:
            self.db_service = None
        else:
            # Auto-detect DynamoDB if env var is set, otherwise use SQLite
            if use_dynamodb is None:
                use_dynamodb = os.getenv('USE_DYNAMODB', 'false').lower() == 'true'

            if use_dynamodb:
                try:
                    self.db_service = DynamoDBService(
                        table_name=dynamodb_table,
                        region=dynamodb_region
                    )
                    print(f"Using DynamoDB: {dynamodb_table} in {dynamodb_region}")
                except Exception as e:
                    print(f"Warning: Failed to initialize DynamoDB ({e}), falling back to SQLite")
                    self.db_service = DatabaseService(db_path=db_path)
            else:
                self.db_service = DatabaseService(db_path=db_path)
                print(f"Using SQLite: {db_path}")

    async def get_exchange_tickers(self, exchange: str) -> List[str]:
        """
        Get list of tickers for an exchange

        Args:
            exchange: Exchange code (e.g., 'NYSE', 'NASDAQ', 'JSE', 'LSE')

        Returns:
            List of ticker symbols
        """
        # Note: yfinance doesn't have a direct API to get all tickers for an exchange
        # This is a placeholder - you may need to use a different data source
        # Options:
        # 1. Use a stock list API (e.g., Financial Modeling Prep, Alpha Vantage)
        # 2. Scrape exchange websites
        # 3. Use pre-compiled lists

        # For now, return empty list - user will need to provide ticker list
        return []

    async def analyze_ticker_list(self,
                                  tickers: List[str],
                                  exchange_name: str,
                                  resume: bool = True,
                                  skip_existing: bool = True,
                                  analysis_date: Optional[str] = None) -> Dict:
        """
        Analyze a list of tickers with rate limiting and error handling

        Args:
            tickers: List of ticker symbols to analyze
            exchange_name: Name of exchange (for file naming)
            resume: If True, skip already processed tickers (from JSON files)
            skip_existing: If True, skip tickers already analyzed today (from database)
            analysis_date: Date in YYYY-MM-DD format (defaults to today)

        Returns:
            Summary dictionary with results
        """
        if analysis_date is None:
            analysis_date = date.today().isoformat()

        results_file = self.results_dir / f"{exchange_name}_{analysis_date.replace('-', '')}.json"
        progress_file = self.results_dir / f"{exchange_name}_progress_{analysis_date.replace('-', '')}.json"

        # Load existing results if resuming
        completed_tickers = set()
        results = {}
        if resume and results_file.exists():
            try:
                with open(results_file, 'r') as f:
                    results = json.load(f)
                    completed_tickers = set(results.keys())
                print(f"Resuming from JSON: Found {len(completed_tickers)} already processed tickers")
            except Exception as e:
                print(f"Error loading existing results: {e}")

        # Check database for existing analyses
        skipped_from_db = 0
        if skip_existing and self.use_database:
            for ticker in tickers:
                if self.db_service.has_analysis_today(ticker, analysis_date):
                    if ticker not in completed_tickers:
                        # Load from database
                        db_analysis = self.db_service.get_analysis(ticker, analysis_date)
                        if db_analysis:
                            results[ticker] = {
                                'ticker': ticker,
                                'timestamp': db_analysis.get('analyzed_at'),
                                'analysis': db_analysis.get('analysis_data', {}),
                                'status': 'success',
                                'source': 'database'
                            }
                            completed_tickers.add(ticker)
                            skipped_from_db += 1

        if skipped_from_db > 0:
            print(f"Skipped {skipped_from_db} tickers already analyzed today (from database)")

        # Filter out already completed tickers
        remaining_tickers = [t for t in tickers if t not in completed_tickers]
        total_tickers = len(tickers)
        completed_count = len(completed_tickers)

        print(f"\n=== Batch Analysis: {exchange_name} ===")
        print(f"Analysis date: {analysis_date}")
        print(f"Total tickers: {total_tickers}")
        print(f"Already completed: {completed_count} ({skipped_from_db} from database)")
        print(f"Remaining: {len(remaining_tickers)}")
        print(f"Results file: {results_file}")
        print(f"Using database: {self.use_database}")
        print("=" * 50)

        # Create batch job record
        batch_job_id = None
        if self.use_database:
            batch_job_id = self.db_service.create_batch_job(exchange_name, tickers)
            print(f"Batch job ID: {batch_job_id}")

        # Rate limiting: process in batches with delays
        semaphore = asyncio.Semaphore(self.max_concurrent)
        rate_limit_delay = 60 / self.requests_per_minute  # seconds between requests

        async def analyze_with_rate_limit(ticker: str):
            """Analyze a single ticker with rate limiting"""
            # Import here to avoid circular import
            from app.api.routes import _analyze_stock_with_progress

            async with semaphore:
                try:
                    # Rate limiting delay
                    await asyncio.sleep(rate_limit_delay)

                    # Create a progress tracker (simplified for batch processing)
                    progress_tracker = ProgressTracker()

                    # Perform analysis
                    analysis = await _analyze_stock_with_progress(ticker, progress_tracker)

                    # Convert to dict for JSON serialization
                    if hasattr(analysis, 'dict'):
                        analysis_dict = analysis.dict()
                    elif hasattr(analysis, '__dict__'):
                        analysis_dict = analysis.__dict__
                    else:
                        analysis_dict = str(analysis)

                    # Save to database if enabled
                    if self.use_database:
                        self.db_service.save_analysis(
                            ticker=ticker,
                            analysis_data=analysis_dict,
                            exchange=exchange_name,
                            analysis_date=analysis_date
                        )

                    result = {
                        'ticker': ticker,
                        'timestamp': datetime.now().isoformat(),
                        'analysis': analysis_dict,
                        'status': 'success',
                        'source': 'new_analysis'
                    }

                    return ticker, result

                except Exception as e:
                    # Save error to database if enabled
                    if self.use_database:
                        self.db_service.save_error(
                            ticker=ticker,
                            error_message=str(e),
                            exchange=exchange_name,
                            analysis_date=analysis_date
                        )

                    error_result = {
                        'ticker': ticker,
                        'timestamp': datetime.now().isoformat(),
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'status': 'error',
                        'source': 'new_analysis'
                    }
                    return ticker, error_result

        # Process tickers in batches
        batch_size = 50  # Save progress every N tickers
        successful = 0
        failed = 0

        for i in range(0, len(remaining_tickers), batch_size):
            batch = remaining_tickers[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(remaining_tickers) + batch_size - 1) // batch_size

            print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} tickers)...")

            # Process batch concurrently
            tasks = [analyze_with_rate_limit(ticker) for ticker in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for result in batch_results:
                if isinstance(result, Exception):
                    failed += 1
                    print(f"  Error in batch processing: {result}")
                    continue

                ticker, analysis_result = result
                results[ticker] = analysis_result

                if analysis_result.get('status') == 'success':
                    successful += 1
                else:
                    failed += 1

                completed_count += 1

                # Update batch job progress
                if self.use_database and batch_job_id:
                    self.db_service.update_batch_job(
                        batch_job_id,
                        processed_tickers=completed_count,
                        successful_tickers=successful,
                        failed_tickers=failed
                    )

                # Print progress
                if completed_count % 10 == 0:
                    print(f"  Progress: {completed_count}/{total_tickers} "
                          f"(✓ {successful} | ✗ {failed})")

            # Save progress after each batch
            try:
                with open(results_file, 'w') as f:
                    json.dump(results, f, indent=2, default=str)

                # Save progress summary
                progress_summary = {
                    'exchange': exchange_name,
                    'total_tickers': total_tickers,
                    'completed': completed_count,
                    'successful': successful,
                    'failed': failed,
                    'remaining': total_tickers - completed_count,
                    'last_updated': datetime.now().isoformat()
                }
                with open(progress_file, 'w') as f:
                    json.dump(progress_summary, f, indent=2)

            except Exception as e:
                print(f"  Warning: Could not save progress: {e}")

        # Complete batch job
        if self.use_database and batch_job_id:
            self.db_service.complete_batch_job(batch_job_id)

        # Final summary
        summary = {
            'exchange': exchange_name,
            'analysis_date': analysis_date,
            'total_tickers': total_tickers,
            'successful': successful,
            'failed': failed,
            'completed': completed_count,
            'skipped_from_db': skipped_from_db,
            'results_file': str(results_file),
            'database_used': self.use_database,
            'batch_job_id': batch_job_id,
            'timestamp': datetime.now().isoformat()
        }

        print(f"\n=== Batch Analysis Complete ===")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Skipped (from DB): {skipped_from_db}")
        print(f"Results saved to: {results_file}")
        if self.use_database:
            print(f"Results also saved to database: {self.db_service.db_path}")

        return summary
