"""
Dependency injection container and FastAPI dependencies
"""
from typing import Optional, AsyncGenerator
from fastapi import Depends, Request
from functools import lru_cache
import logging

from app.core.logging import set_correlation_id, generate_correlation_id
from app.core.exceptions import DatabaseError, ExternalAPIError
from app.data.data_fetcher import DataFetcher
from app.data.api_client import YahooFinanceClient
from app.cache_manager import AdvancedCacheManager
from app.database.db_service import DatabaseService

logger = logging.getLogger(__name__)


class ServiceContainer:
    """Dependency injection container for application services"""

    def __init__(self):
        self._data_fetcher: Optional[DataFetcher] = None
        self._yahoo_client: Optional[YahooFinanceClient] = None
        self._cache_manager: Optional[AdvancedCacheManager] = None
        self._database_service: Optional[DatabaseService] = None

    @property
    def data_fetcher(self) -> DataFetcher:
        """Get or create DataFetcher instance"""
        if self._data_fetcher is None:
            self._data_fetcher = DataFetcher()
        return self._data_fetcher

    @property
    def yahoo_client(self) -> YahooFinanceClient:
        """Get or create YahooFinanceClient instance"""
        if self._yahoo_client is None:
            self._yahoo_client = YahooFinanceClient()
        return self._yahoo_client

    @property
    def cache_manager(self) -> AdvancedCacheManager:
        """Get or create CacheManager instance"""
        if self._cache_manager is None:
            self._cache_manager = AdvancedCacheManager()
        return self._cache_manager

    @property
    def database_service(self) -> DatabaseService:
        """Get or create DatabaseService instance"""
        if self._database_service is None:
            try:
                self._database_service = DatabaseService(db_path="stock_analysis.db")
            except Exception as e:
                logger.error(f"Failed to initialize database service: {e}")
                raise DatabaseError(
                    message="Failed to initialize database connection",
                    operation="initialization"
                )
        return self._database_service

    async def cleanup(self):
        """Cleanup resources"""
        # Close database connections, cache connections, etc.
        if self._database_service:
            # Add cleanup logic if needed
            pass
        if self._cache_manager:
            # Add cleanup logic if needed
            pass


# Global service container instance
_service_container: Optional[ServiceContainer] = None


@lru_cache()
def get_service_container() -> ServiceContainer:
    """Get the global service container instance"""
    global _service_container
    if _service_container is None:
        _service_container = ServiceContainer()
    return _service_container


async def get_correlation_id(request: Request) -> str:
    """Extract or generate correlation ID for request tracking"""
    correlation_id = request.headers.get("x-correlation-id")
    if not correlation_id:
        correlation_id = generate_correlation_id()

    # Set in context for logging
    set_correlation_id(correlation_id)
    return correlation_id


async def get_data_fetcher(
    container: ServiceContainer = Depends(get_service_container)
) -> DataFetcher:
    """Get DataFetcher dependency"""
    try:
        return container.data_fetcher
    except Exception as e:
        logger.error(f"Failed to get data fetcher: {e}")
        raise ExternalAPIError(
            message="Data fetcher service unavailable",
            service="DataFetcher"
        )


async def get_yahoo_client(
    container: ServiceContainer = Depends(get_service_container)
) -> YahooFinanceClient:
    """Get YahooFinanceClient dependency"""
    try:
        return container.yahoo_client
    except Exception as e:
        logger.error(f"Failed to get Yahoo Finance client: {e}")
        raise ExternalAPIError(
            message="Yahoo Finance service unavailable",
            service="YahooFinance"
        )


async def get_cache_manager(
    container: ServiceContainer = Depends(get_service_container)
) -> AdvancedCacheManager:
    """Get CacheManager dependency"""
    try:
        return container.cache_manager
    except Exception as e:
        logger.error(f"Failed to get cache manager: {e}")
        # Cache is not critical, return None or a no-op cache
        return AdvancedCacheManager()  # This should handle failures gracefully


async def get_database_service(
    container: ServiceContainer = Depends(get_service_container)
) -> DatabaseService:
    """Get DatabaseService dependency"""
    try:
        return container.database_service
    except Exception as e:
        logger.error(f"Failed to get database service: {e}")
        raise DatabaseError(
            message="Database service unavailable",
            operation="dependency_injection"
        )


# Lifespan management
async def startup_services():
    """Initialize services on application startup"""
    logger.info("Initializing application services...")
    container = get_service_container()

    # Pre-initialize critical services to catch errors early
    try:
        _ = container.database_service
        logger.info("Database service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database service: {e}")
        # Don't raise here - let individual requests handle the error

    try:
        _ = container.cache_manager
        logger.info("Cache manager initialized")
    except Exception as e:
        logger.warning(f"Cache manager initialization failed: {e}")
        # Cache is not critical for startup

    logger.info("Service initialization complete")


async def shutdown_services():
    """Cleanup services on application shutdown"""
    logger.info("Shutting down application services...")
    global _service_container

    if _service_container:
        await _service_container.cleanup()
        _service_container = None

    logger.info("Service shutdown complete")
