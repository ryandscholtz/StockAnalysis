"""
Unified database service that combines repository pattern, connection pooling, and migration support
"""
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime

from app.database.factory import DatabaseFactory, get_database_repository
from app.database.repository import DatabaseRepository
from app.database.connection import ResilientDatabaseService, RetryPolicy, SimpleConnectionPool
from app.database.migration import MigrationRunner, create_migration_runner

logger = logging.getLogger(__name__)


class UnifiedDatabaseService:
    """
    Unified database service that provides:
    - Environment-specific database selection (SQLite/DynamoDB)
    - Connection pooling and retry logic
    - Database migration support
    - Consistent API across all database backends
    """
    
    def __init__(self, 
                 environment: Optional[str] = None,
                 retry_policy: Optional[RetryPolicy] = None,
                 enable_connection_pooling: bool = True):
        """
        Initialize unified database service
        
        Args:
            environment: Environment name (production, development, test)
            retry_policy: Retry policy for failed operations
            enable_connection_pooling: Whether to enable connection pooling
        """
        self.environment = environment
        self.retry_policy = retry_policy or RetryPolicy()
        self.enable_connection_pooling = enable_connection_pooling
        
        # Initialize repository
        self.repository = get_database_repository(environment)
        
        # Initialize resilient service wrapper
        connection_pool = None
        if enable_connection_pooling:
            # Note: Connection pooling is more relevant for traditional databases
            # For SQLite and DynamoDB, the underlying services handle connections
            pass
        
        self.resilient_service = ResilientDatabaseService(
            repository=self.repository,
            connection_pool=connection_pool,
            retry_policy=self.retry_policy
        )
        
        # Initialize migration runner
        self.migration_runner = create_migration_runner(self.repository)
        
        logger.info(f"Initialized unified database service for environment: {environment}")
    
    # Analysis operations
    async def has_analysis_today(self, ticker: str, analysis_date: Optional[str] = None) -> bool:
        """Check if stock has been analyzed today"""
        return await self.resilient_service.repository.has_analysis_today(ticker, analysis_date)
    
    async def get_analysis(self, ticker: str, analysis_date: Optional[str] = None) -> Optional[Dict]:
        """Get analysis for a ticker with retry logic"""
        return await self.resilient_service.get_analysis(ticker, analysis_date)
    
    async def get_latest_analysis(self, ticker: str) -> Optional[Dict]:
        """Get the latest analysis for a ticker"""
        return await self.resilient_service.repository.get_latest_analysis(ticker)
    
    async def save_analysis(self, 
                           ticker: str,
                           analysis_data: Dict,
                           exchange: Optional[str] = None,
                           analysis_date: Optional[str] = None) -> bool:
        """Save analysis with retry logic"""
        return await self.resilient_service.save_analysis(ticker, analysis_data, exchange, analysis_date)
    
    async def save_error(self,
                        ticker: str,
                        error_message: str,
                        exchange: Optional[str] = None,
                        analysis_date: Optional[str] = None) -> bool:
        """Save error record for a ticker"""
        return await self.resilient_service.repository.save_error(ticker, error_message, exchange, analysis_date)
    
    async def get_exchange_analyses(self, 
                                   exchange: str,
                                   analysis_date: Optional[str] = None,
                                   limit: Optional[int] = None) -> List[Dict]:
        """Get all analyses for an exchange"""
        return await self.resilient_service.repository.get_exchange_analyses(exchange, analysis_date, limit)
    
    # Watchlist operations
    async def add_to_watchlist(self, ticker: str, company_name: Optional[str] = None, 
                              exchange: Optional[str] = None, notes: Optional[str] = None) -> bool:
        """Add a stock to the watchlist"""
        return await self.resilient_service.repository.add_to_watchlist(ticker, company_name, exchange, notes)
    
    async def remove_from_watchlist(self, ticker: str) -> bool:
        """Remove a stock from the watchlist"""
        return await self.resilient_service.repository.remove_from_watchlist(ticker)
    
    async def get_watchlist(self) -> List[Dict]:
        """Get all stocks in the watchlist with retry logic"""
        return await self.resilient_service.get_watchlist()
    
    # Migration operations
    async def run_migrations(self) -> bool:
        """Run all pending database migrations"""
        try:
            logger.info("Running database migrations...")
            result = await self.migration_runner.run_migrations()
            if result:
                logger.info("All migrations completed successfully")
            else:
                logger.error("Some migrations failed")
            return result
        except Exception as e:
            logger.error(f"Error running migrations: {e}")
            return False
    
    async def rollback_migration(self, version: str) -> bool:
        """Rollback a specific migration"""
        try:
            logger.info(f"Rolling back migration {version}...")
            result = await self.migration_runner.rollback_migration(version)
            if result:
                logger.info(f"Migration {version} rolled back successfully")
            else:
                logger.error(f"Failed to rollback migration {version}")
            return result
        except Exception as e:
            logger.error(f"Error rolling back migration {version}: {e}")
            return False
    
    async def get_applied_migrations(self) -> Dict[str, datetime]:
        """Get list of applied migrations"""
        return await self.migration_runner.get_applied_migrations()
    
    # Service management
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive service statistics"""
        stats = {
            "environment": self.environment,
            "repository_type": type(self.repository).__name__,
            "retry_policy": {
                "max_attempts": self.retry_policy.max_attempts,
                "base_delay": self.retry_policy.base_delay,
                "max_delay": self.retry_policy.max_delay,
                "exponential_backoff": self.retry_policy.exponential_backoff,
                "jitter": self.retry_policy.jitter
            },
            "connection_pooling_enabled": self.enable_connection_pooling
        }
        
        # Add resilient service stats
        resilient_stats = self.resilient_service.get_stats()
        stats.update(resilient_stats)
        
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the database service"""
        try:
            # Test basic operation
            start_time = datetime.utcnow()
            await self.get_watchlist()
            end_time = datetime.utcnow()
            
            response_time = (end_time - start_time).total_seconds()
            
            return {
                "status": "healthy",
                "response_time_seconds": response_time,
                "timestamp": datetime.utcnow().isoformat(),
                "environment": self.environment,
                "repository_type": type(self.repository).__name__
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "environment": self.environment,
                "repository_type": type(self.repository).__name__
            }
    
    async def close(self):
        """Close the database service and all connections"""
        try:
            await self.resilient_service.close()
            logger.info("Database service closed successfully")
        except Exception as e:
            logger.error(f"Error closing database service: {e}")


# Global service instance
_unified_service: Optional[UnifiedDatabaseService] = None


def get_unified_database_service(environment: Optional[str] = None) -> UnifiedDatabaseService:
    """Get or create the global unified database service instance"""
    global _unified_service
    
    if _unified_service is None:
        _unified_service = UnifiedDatabaseService(environment=environment)
    
    return _unified_service


async def initialize_database_service(environment: Optional[str] = None, 
                                     run_migrations: bool = True) -> UnifiedDatabaseService:
    """
    Initialize the database service and optionally run migrations
    
    Args:
        environment: Environment name
        run_migrations: Whether to run pending migrations
    
    Returns:
        Initialized UnifiedDatabaseService
    """
    service = get_unified_database_service(environment)
    
    if run_migrations:
        await service.run_migrations()
    
    return service


async def shutdown_database_service():
    """Shutdown the global database service"""
    global _unified_service
    
    if _unified_service is not None:
        await _unified_service.close()
        _unified_service = None