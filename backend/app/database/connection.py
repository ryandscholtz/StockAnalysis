"""
Database connection management with pooling and retry logic
"""
import asyncio
import logging
from typing import Optional, Dict, Any, Callable, TypeVar, Generic
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import time
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ConnectionError(Exception):
    """Database connection error"""
    pass


class RetryPolicy:
    """Configuration for retry behavior"""
    
    def __init__(self, 
                 max_attempts: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 exponential_backoff: bool = True,
                 jitter: bool = True):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_backoff = exponential_backoff
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number"""
        if self.exponential_backoff:
            delay = self.base_delay * (2 ** (attempt - 1))
        else:
            delay = self.base_delay
        
        # Apply max delay limit
        delay = min(delay, self.max_delay)
        
        # Add jitter to avoid thundering herd
        if self.jitter:
            import random
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay


class ConnectionPool(ABC):
    """Abstract base class for connection pools"""
    
    @abstractmethod
    async def get_connection(self):
        """Get a connection from the pool"""
        pass
    
    @abstractmethod
    async def return_connection(self, connection):
        """Return a connection to the pool"""
        pass
    
    @abstractmethod
    async def close_all(self):
        """Close all connections in the pool"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        pass


class SimpleConnectionPool(ConnectionPool):
    """Simple connection pool implementation"""
    
    def __init__(self, 
                 connection_factory: Callable,
                 max_size: int = 10,
                 min_size: int = 1,
                 max_idle_time: float = 300.0):  # 5 minutes
        self.connection_factory = connection_factory
        self.max_size = max_size
        self.min_size = min_size
        self.max_idle_time = max_idle_time
        
        self._pool: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._active_connections = 0
        self._total_connections = 0
        self._connection_times: Dict[Any, datetime] = {}
        self._lock = asyncio.Lock()
    
    async def get_connection(self):
        """Get a connection from the pool"""
        async with self._lock:
            # Try to get existing connection from pool
            try:
                connection = self._pool.get_nowait()
                # Check if connection is still valid and not too old
                if self._is_connection_valid(connection):
                    self._active_connections += 1
                    return connection
                else:
                    # Connection is stale, close it
                    await self._close_connection(connection)
            except asyncio.QueueEmpty:
                pass
            
            # Create new connection if under max size
            if self._total_connections < self.max_size:
                connection = await self._create_connection()
                self._active_connections += 1
                self._total_connections += 1
                return connection
            
            # Wait for a connection to become available
            # In a real implementation, this would have a timeout
            raise ConnectionError("Connection pool exhausted")
    
    async def return_connection(self, connection):
        """Return a connection to the pool"""
        async with self._lock:
            if self._is_connection_valid(connection):
                try:
                    self._pool.put_nowait(connection)
                    self._connection_times[connection] = datetime.utcnow()
                except asyncio.QueueFull:
                    # Pool is full, close the connection
                    await self._close_connection(connection)
                    self._total_connections -= 1
            else:
                # Connection is invalid, close it
                await self._close_connection(connection)
                self._total_connections -= 1
            
            self._active_connections -= 1
    
    async def close_all(self):
        """Close all connections in the pool"""
        async with self._lock:
            # Close all pooled connections
            while not self._pool.empty():
                try:
                    connection = self._pool.get_nowait()
                    await self._close_connection(connection)
                except asyncio.QueueEmpty:
                    break
            
            self._total_connections = 0
            self._active_connections = 0
            self._connection_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        return {
            "total_connections": self._total_connections,
            "active_connections": self._active_connections,
            "pooled_connections": self._pool.qsize(),
            "max_size": self.max_size,
            "min_size": self.min_size
        }
    
    async def _create_connection(self):
        """Create a new connection"""
        try:
            connection = await self.connection_factory()
            self._connection_times[connection] = datetime.utcnow()
            return connection
        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            raise ConnectionError(f"Failed to create connection: {e}")
    
    async def _close_connection(self, connection):
        """Close a connection"""
        try:
            if hasattr(connection, 'close'):
                if asyncio.iscoroutinefunction(connection.close):
                    await connection.close()
                else:
                    connection.close()
            if connection in self._connection_times:
                del self._connection_times[connection]
        except Exception as e:
            logger.warning(f"Error closing connection: {e}")
    
    def _is_connection_valid(self, connection) -> bool:
        """Check if a connection is still valid"""
        if connection not in self._connection_times:
            return False
        
        # Check age
        age = datetime.utcnow() - self._connection_times[connection]
        if age.total_seconds() > self.max_idle_time:
            return False
        
        # In a real implementation, we might ping the connection
        return True


def with_retry(retry_policy: Optional[RetryPolicy] = None):
    """Decorator to add retry logic to database operations"""
    if retry_policy is None:
        retry_policy = RetryPolicy()
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, retry_policy.max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"Attempt {attempt} failed for {func.__name__}: {e}")
                    
                    if attempt < retry_policy.max_attempts:
                        delay = retry_policy.get_delay(attempt)
                        logger.info(f"Retrying {func.__name__} in {delay:.2f} seconds...")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"All {retry_policy.max_attempts} attempts failed for {func.__name__}")
            
            # All attempts failed, raise the last exception
            raise last_exception
        
        return wrapper
    return decorator


class ResilientDatabaseService:
    """Database service with connection pooling and retry logic"""
    
    def __init__(self, repository, connection_pool: Optional[ConnectionPool] = None, 
                 retry_policy: Optional[RetryPolicy] = None):
        self.repository = repository
        self.connection_pool = connection_pool
        self.retry_policy = retry_policy or RetryPolicy()
        self._operation_count = 0
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
    
    @with_retry()
    async def get_analysis(self, ticker: str, analysis_date: Optional[str] = None):
        """Get analysis with retry logic"""
        self._operation_count += 1
        try:
            return await self.repository.get_analysis(ticker, analysis_date)
        except Exception as e:
            self._failure_count += 1
            self._last_failure_time = datetime.utcnow()
            raise
    
    @with_retry()
    async def save_analysis(self, ticker: str, analysis_data: Dict, 
                           exchange: Optional[str] = None, analysis_date: Optional[str] = None):
        """Save analysis with retry logic"""
        self._operation_count += 1
        try:
            return await self.repository.save_analysis(ticker, analysis_data, exchange, analysis_date)
        except Exception as e:
            self._failure_count += 1
            self._last_failure_time = datetime.utcnow()
            raise
    
    @with_retry()
    async def get_watchlist(self):
        """Get watchlist with retry logic"""
        self._operation_count += 1
        try:
            return await self.repository.get_watchlist()
        except Exception as e:
            self._failure_count += 1
            self._last_failure_time = datetime.utcnow()
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        stats = {
            "operation_count": self._operation_count,
            "failure_count": self._failure_count,
            "success_rate": (self._operation_count - self._failure_count) / max(self._operation_count, 1),
            "last_failure_time": self._last_failure_time.isoformat() if self._last_failure_time else None
        }
        
        if self.connection_pool:
            stats["connection_pool"] = self.connection_pool.get_stats()
        
        return stats
    
    async def close(self):
        """Close the service and all connections"""
        if self.connection_pool:
            await self.connection_pool.close_all()
        
        if hasattr(self.repository, 'close'):
            await self.repository.close()