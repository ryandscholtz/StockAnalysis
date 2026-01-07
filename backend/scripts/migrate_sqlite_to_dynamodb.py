"""
Migrate data from SQLite to DynamoDB
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.db_service import DatabaseService
from app.database.dynamodb_service import DynamoDBService
from datetime import date, timedelta


def migrate_all_data():
    """Migrate all data from SQLite to DynamoDB"""
    print("Initializing databases...")
    sqlite_db = DatabaseService(db_path="stock_analysis.db")
    dynamodb = DynamoDBService(table_name="stock-analyses")

    print("Querying SQLite for all analyses...")
    session = sqlite_db.get_session()

    try:
        # Get all analyses
        from app.database.models import StockAnalysis
        all_analyses = session.query(StockAnalysis).all()

        print(f"Found {len(all_analyses)} analyses to migrate")

        migrated = 0
        failed = 0

        for analysis in all_analyses:
            try:
                # Convert SQLAlchemy model to dict
                analysis_dict = analysis.to_dict()

                # Extract analysis_data
                analysis_data = analysis_dict.get('analysis_data', {})

                # Save to DynamoDB
                success = dynamodb.save_analysis(
                    ticker=analysis.ticker,
                    analysis_data=analysis_data,
                    exchange=analysis.exchange,
                    analysis_date=analysis.analysis_date
                )

                if success:
                    migrated += 1
                    if migrated % 10 == 0:
                        print(f"  Migrated {migrated}/{len(all_analyses)}...")
                else:
                    failed += 1
                    print(f"  Failed to migrate {analysis.ticker} ({analysis.analysis_date})")

            except Exception as e:
                failed += 1
                print(f"  Error migrating {analysis.ticker}: {e}")

        print(f"\n=== Migration Complete ===")
        print(f"Migrated: {migrated}")
        print(f"Failed: {failed}")
        print(f"Total: {len(all_analyses)}")

    finally:
        session.close()


def migrate_date_range(start_date: str, end_date: str):
    """Migrate analyses for a specific date range"""
    print(f"Migrating analyses from {start_date} to {end_date}...")

    sqlite_db = DatabaseService(db_path="stock_analysis.db")
    dynamodb = DynamoDBService(table_name="stock-analyses")

    session = sqlite_db.get_session()

    try:
        from app.database.models import StockAnalysis
        from sqlalchemy import and_

        analyses = session.query(StockAnalysis).filter(
            and_(
                StockAnalysis.analysis_date >= start_date,
                StockAnalysis.analysis_date <= end_date
            )
        ).all()

        print(f"Found {len(analyses)} analyses in date range")

        migrated = 0
        for analysis in analyses:
            analysis_dict = analysis.to_dict()
            analysis_data = analysis_dict.get('analysis_data', {})

            if dynamodb.save_analysis(
                ticker=analysis.ticker,
                analysis_data=analysis_data,
                exchange=analysis.exchange,
                analysis_date=analysis.analysis_date
            ):
                migrated += 1

        print(f"Migrated {migrated}/{len(analyses)}")

    finally:
        session.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Migrate SQLite data to DynamoDB')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)', default=None)
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)', default=None)

    args = parser.parse_args()

    if args.start_date and args.end_date:
        migrate_date_range(args.start_date, args.end_date)
    else:
        migrate_all_data()
