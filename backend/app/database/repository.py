"""
Repository pattern for database abstraction
Provides a unified interface for both SQLite and DynamoDB
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any
from datetime import datetime, date


class DatabaseRepository(ABC):
    """Abstract base class for database repositories"""

    @abstractmethod
    async def has_analysis_today(self, ticker: str, analysis_date: Optional[str] = None) -> bool:
        """Check if stock has been analyzed today"""
        pass

    @abstractmethod
    async def get_analysis(self, ticker: str, analysis_date: Optional[str] = None) -> Optional[Dict]:
        """Get analysis for a ticker"""
        pass

    @abstractmethod
    async def get_latest_analysis(self, ticker: str) -> Optional[Dict]:
        """Get the latest analysis for a ticker"""
        pass

    @abstractmethod
    async def save_analysis(self,
                           ticker: str,
                           analysis_data: Dict,
                           exchange: Optional[str] = None,
                           analysis_date: Optional[str] = None) -> bool:
        """Save analysis to database"""
        pass

    @abstractmethod
    async def save_error(self,
                        ticker: str,
                        error_message: str,
                        exchange: Optional[str] = None,
                        analysis_date: Optional[str] = None) -> bool:
        """Save error record for a ticker"""
        pass

    @abstractmethod
    async def get_exchange_analyses(self,
                                   exchange: str,
                                   analysis_date: Optional[str] = None,
                                   limit: Optional[int] = None) -> List[Dict]:
        """Get all analyses for an exchange"""
        pass

    @abstractmethod
    async def add_to_watchlist(self, ticker: str, company_name: Optional[str] = None,
                              exchange: Optional[str] = None, notes: Optional[str] = None) -> bool:
        """Add a stock to the watchlist"""
        pass

    @abstractmethod
    async def remove_from_watchlist(self, ticker: str) -> bool:
        """Remove a stock from the watchlist"""
        pass

    @abstractmethod
    async def get_watchlist(self) -> List[Dict]:
        """Get all stocks in the watchlist"""
        pass

    @abstractmethod
    async def close(self):
        """Close database connections"""
        pass


class SQLiteRepository(DatabaseRepository):
    """SQLite implementation of the repository pattern"""

    def __init__(self, db_path: str = "stock_analysis.db"):
        from app.database.db_service import DatabaseService
        self.db_service = DatabaseService(db_path=db_path)

    async def has_analysis_today(self, ticker: str, analysis_date: Optional[str] = None) -> bool:
        return self.db_service.has_analysis_today(ticker, analysis_date)

    async def get_analysis(self, ticker: str, analysis_date: Optional[str] = None) -> Optional[Dict]:
        return self.db_service.get_analysis(ticker, analysis_date)

    async def get_latest_analysis(self, ticker: str) -> Optional[Dict]:
        return self.db_service.get_latest_analysis(ticker)

    async def save_analysis(self,
                           ticker: str,
                           analysis_data: Dict,
                           exchange: Optional[str] = None,
                           analysis_date: Optional[str] = None) -> bool:
        return self.db_service.save_analysis(ticker, analysis_data, exchange, analysis_date)

    async def save_error(self,
                        ticker: str,
                        error_message: str,
                        exchange: Optional[str] = None,
                        analysis_date: Optional[str] = None) -> bool:
        return self.db_service.save_error(ticker, error_message, exchange, analysis_date)

    async def get_exchange_analyses(self,
                                   exchange: str,
                                   analysis_date: Optional[str] = None,
                                   limit: Optional[int] = None) -> List[Dict]:
        return self.db_service.get_exchange_analyses(exchange, analysis_date, limit)

    async def add_to_watchlist(self, ticker: str, company_name: Optional[str] = None,
                              exchange: Optional[str] = None, notes: Optional[str] = None) -> bool:
        return self.db_service.add_to_watchlist(ticker, company_name, exchange, notes)

    async def remove_from_watchlist(self, ticker: str) -> bool:
        return self.db_service.remove_from_watchlist(ticker)

    async def get_watchlist(self) -> List[Dict]:
        return self.db_service.get_watchlist()

    async def close(self):
        # SQLite connections are managed per-session, no persistent connection to close
        pass


class DynamoDBRepository(DatabaseRepository):
    """DynamoDB implementation of the repository pattern"""

    def __init__(self, table_name: Optional[str] = None, region: Optional[str] = None):
        from app.database.dynamodb_service import DynamoDBService
        self.db_service = DynamoDBService(table_name=table_name, region=region)

    async def has_analysis_today(self, ticker: str, analysis_date: Optional[str] = None) -> bool:
        return self.db_service.has_analysis_today(ticker, analysis_date)

    async def get_analysis(self, ticker: str, analysis_date: Optional[str] = None) -> Optional[Dict]:
        return self.db_service.get_analysis(ticker, analysis_date)

    async def get_latest_analysis(self, ticker: str) -> Optional[Dict]:
        # DynamoDB service doesn't have this method yet, implement basic version
        if analysis_date is None:
            analysis_date = date.today().isoformat()
        return self.db_service.get_analysis(ticker, analysis_date)

    async def save_analysis(self,
                           ticker: str,
                           analysis_data: Dict,
                           exchange: Optional[str] = None,
                           analysis_date: Optional[str] = None) -> bool:
        return self.db_service.save_analysis(ticker, analysis_data, exchange, analysis_date)

    async def save_error(self,
                        ticker: str,
                        error_message: str,
                        exchange: Optional[str] = None,
                        analysis_date: Optional[str] = None) -> bool:
        return self.db_service.save_error(ticker, error_message, exchange, analysis_date)

    async def get_exchange_analyses(self,
                                   exchange: str,
                                   analysis_date: Optional[str] = None,
                                   limit: Optional[int] = None) -> List[Dict]:
        return self.db_service.get_exchange_analyses(exchange, analysis_date, limit)

    async def add_to_watchlist(self, ticker: str, company_name: Optional[str] = None,
                              exchange: Optional[str] = None, notes: Optional[str] = None) -> bool:
        # DynamoDB service doesn't have watchlist methods yet, return False for now
        return False

    async def remove_from_watchlist(self, ticker: str) -> bool:
        # DynamoDB service doesn't have watchlist methods yet, return False for now
        return False

    async def get_watchlist(self) -> List[Dict]:
        # DynamoDB service doesn't have watchlist methods yet, return empty list for now
        return []

    async def close(self):
        # DynamoDB connections are managed by boto3, no persistent connection to close
        pass
