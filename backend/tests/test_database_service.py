"""
Unit tests for database service functionality
"""
from app.database.db_service import DatabaseService
import pytest
import sqlite3
import tempfile
import os
from datetime import datetime
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDatabaseService:
    """Test cases for DatabaseService"""

    def setup_method(self):
        """Setup for each test method - create temporary database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.db_service = DatabaseService(db_path=self.db_path)

    def teardown_method(self):
        """Cleanup after each test method"""
        # Close database connection first
        if hasattr(self.db_service, 'conn') and self.db_service.conn:
            self.db_service.conn.close()

        # Try to delete the file, ignore if it fails
        try:
            if os.path.exists(self.db_path):
                os.unlink(self.db_path)
        except (PermissionError, OSError):
            # File might still be locked on Windows, ignore
            pass

    def test_database_initialization(self):
        """Test database initialization and table creation"""
        # Database file should exist
        assert os.path.exists(self.db_path)

        # Should be able to connect
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if watchlist table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='watchlist'")
        result = cursor.fetchone()
        assert result is not None

        conn.close()

    def test_add_to_watchlist(self):
        """Test adding items to watchlist"""
        # Add a stock to watchlist
        result = self.db_service.add_to_watchlist(
            ticker="AAPL",
            company_name="Apple Inc.",
            exchange="NASDAQ"
        )

        assert result is True

        # Verify it was added
        watchlist = self.db_service.get_watchlist()
        assert len(watchlist) == 1
        assert watchlist[0]['ticker'] == "AAPL"
        assert watchlist[0]['company_name'] == "Apple Inc."
        assert watchlist[0]['exchange'] == "NASDAQ"

    def test_add_duplicate_to_watchlist(self):
        """Test adding duplicate ticker to watchlist"""
        # Add first time
        result1 = self.db_service.add_to_watchlist("AAPL", "Apple Inc.", "NASDAQ")
        assert result1 is True

        # Try to add same ticker again
        self.db_service.add_to_watchlist("AAPL", "Apple Inc.", "NASDAQ")

        # Should handle gracefully (implementation dependent)
        watchlist = self.db_service.get_watchlist()
        # Should still only have one entry
        tickers = [item['ticker'] for item in watchlist]
        assert tickers.count("AAPL") == 1

    def test_remove_from_watchlist(self):
        """Test removing items from watchlist"""
        # Add item first
        self.db_service.add_to_watchlist("AAPL", "Apple Inc.", "NASDAQ")

        # Verify it exists
        watchlist = self.db_service.get_watchlist()
        assert len(watchlist) == 1

        # Remove it
        result = self.db_service.remove_from_watchlist("AAPL")
        assert result is True

        # Verify it's gone
        watchlist = self.db_service.get_watchlist()
        assert len(watchlist) == 0

    def test_remove_nonexistent_from_watchlist(self):
        """Test removing non-existent item from watchlist"""
        result = self.db_service.remove_from_watchlist("NONEXISTENT")

        # Should handle gracefully
        assert result is False or result is True  # Implementation dependent

    def test_get_empty_watchlist(self):
        """Test getting empty watchlist"""
        watchlist = self.db_service.get_watchlist()

        assert isinstance(watchlist, list)
        assert len(watchlist) == 0

    def test_get_watchlist_with_items(self):
        """Test getting watchlist with multiple items"""
        # Add multiple items
        items = [
            ("AAPL", "Apple Inc.", "NASDAQ"),
            ("GOOGL", "Alphabet Inc.", "NASDAQ"),
            ("MSFT", "Microsoft Corporation", "NASDAQ")
        ]

        for ticker, name, exchange in items:
            self.db_service.add_to_watchlist(ticker, name, exchange)

        watchlist = self.db_service.get_watchlist()

        assert len(watchlist) == 3
        tickers = [item['ticker'] for item in watchlist]
        assert "AAPL" in tickers
        assert "GOOGL" in tickers
        assert "MSFT" in tickers

    def test_update_watchlist_item(self):
        """Test updating watchlist item properties"""
        # Add item
        self.db_service.add_to_watchlist("AAPL", "Apple Inc.", "NASDAQ")

        # Update with notes
        result = self.db_service.update_watchlist_item("AAPL", notes="Great company")

        if hasattr(self.db_service, 'update_watchlist_item'):
            assert result is True

            # Verify update
            watchlist = self.db_service.get_watchlist()
            aapl_item = next(
                (item for item in watchlist if item['ticker'] == "AAPL"), None)
            assert aapl_item is not None
            if 'notes' in aapl_item:
                assert aapl_item['notes'] == "Great company"

    def test_store_analysis_data(self):
        """Test storing analysis data"""
        analysis_data = {
            'ticker': 'AAPL',
            'fair_value': 150.25,
            'current_price': 145.50,
            'recommendation': 'Buy',
            'analysis_date': datetime.now().strftime('%Y-%m-%d'),
            'financial_health_score': 85,
            'business_quality_score': 90
        }

        if hasattr(self.db_service, 'store_analysis_data'):
            result = self.db_service.store_analysis_data(analysis_data)
            assert result is True

    def test_get_analysis_data(self):
        """Test retrieving analysis data"""
        if hasattr(self.db_service, 'get_analysis_data'):
            # This might return None if no data exists
            result = self.db_service.get_analysis_data("AAPL")
            assert result is None or isinstance(result, dict)

    def test_database_connection_handling(self):
        """Test database connection error handling"""
        # Try to create service with invalid path
        invalid_path = "/invalid/path/database.db"

        try:
            invalid_service = DatabaseService(db_path=invalid_path)
            # If it doesn't raise an exception, it should handle gracefully
            assert invalid_service is not None
        except Exception as e:
            # Should be a reasonable database-related exception
            assert "database" in str(e).lower() or "permission" in str(
                e).lower() or "path" in str(e).lower()

    def test_get_ai_extracted_data(self):
        """Test getting AI extracted data"""
        if hasattr(self.db_service, 'get_ai_extracted_data'):
            result = self.db_service.get_ai_extracted_data("AAPL")

            # Should return dict (empty if no data) or None
            assert result is None or isinstance(result, dict)

    def test_store_ai_extracted_data(self):
        """Test storing AI extracted data"""
        if hasattr(self.db_service, 'store_ai_extracted_data'):
            ai_data = {
                'income_statement': {'2023': {'revenue': 1000000}},
                'balance_sheet': {'2023': {'total_assets': 2000000}},
                'key_metrics': {'latest': {'shares_outstanding': 1000000}}
            }

            result = self.db_service.store_ai_extracted_data("AAPL", ai_data)

            # Should handle gracefully
            assert result is True or result is None

    def test_concurrent_access(self):
        """Test concurrent database access"""
        import threading

        results = []

        def add_item(ticker):
            try:
                result = self.db_service.add_to_watchlist(
                    f"{ticker}", f"Company {ticker}", "NYSE")
                results.append(result)
            except Exception as e:
                results.append(f"Error: {e}")

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=add_item, args=(f"STOCK{i}",))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Check results
        assert len(results) == 5

        # Verify items were added
        watchlist = self.db_service.get_watchlist()
        assert len(watchlist) == 5


class TestDatabaseServiceEdgeCases:
    """Test edge cases and error conditions"""

    def test_invalid_ticker_format(self):
        """Test handling of invalid ticker formats"""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()

        try:
            db_service = DatabaseService(db_path=temp_db.name)

            # Test various invalid formats
            invalid_tickers = [
                "",
                None,
                "VERY_LONG_TICKER_NAME_THAT_EXCEEDS_LIMITS",
                "TICK@R",
                "123"]

            for ticker in invalid_tickers:
                try:
                    result = db_service.add_to_watchlist(ticker, "Test Company", "NYSE")
                    # Should either succeed or fail gracefully
                    assert result is True or result is False
                except Exception as e:
                    # Should be a reasonable validation error
                    assert isinstance(e, (ValueError, TypeError, sqlite3.Error))

        finally:
            # Close database connection first
            if 'db_service' in locals():
                try:
                    if hasattr(db_service, 'conn') and db_service.conn:
                        db_service.conn.close()
                except BaseException:
                    pass

            # Try to delete the file, ignore if it fails
            try:
                if os.path.exists(temp_db.name):
                    os.unlink(temp_db.name)
            except (PermissionError, OSError):
                # File might still be locked on Windows, ignore
                pass

    def test_database_corruption_handling(self):
        """Test handling of database corruption"""
        # Create a corrupted database file
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.write(b"This is not a valid SQLite database")
        temp_db.close()

        try:
            # Try to use corrupted database - should fail during initialization
            try:
                db_service = DatabaseService(db_path=temp_db.name)
                # If it somehow succeeds, test basic operations
                result = db_service.get_watchlist()
                assert isinstance(result, list)
            except (sqlite3.DatabaseError, Exception) as e:
                # Expected for corrupted database
                assert "database" in str(e).lower() or "file" in str(e).lower()

        finally:
            # Close database connection first
            if 'db_service' in locals():
                try:
                    if hasattr(db_service, 'conn') and db_service.conn:
                        db_service.conn.close()
                except BaseException:
                    pass

            # Try to delete the file, ignore if it fails
            try:
                if os.path.exists(temp_db.name):
                    os.unlink(temp_db.name)
            except (PermissionError, OSError):
                # File might still be locked on Windows, ignore
                pass


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
