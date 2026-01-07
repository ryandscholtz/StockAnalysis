"""
Redis-based distributed caching service for production environments
"""
import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import asyncio
import hashlib

try:
    import redis.asyncio as redis
    from redis.asyncio import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    # Create dummy Redis class for type hints when Redis is not available
    class Redis:
        pass

from app.cache_manager import AdvancedCacheManager

logger = logging.getLogger(__name__)


class CacheService(ABC):
    """Abstract cache service interface"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL in seconds"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        pass
    
    @abstractmethod
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern"""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        pass


class RedisCacheService(CacheService):
    """Redis-based distributed cache service for production"""
    
    def __init__(self, redis_url: Optional[str] = None, **kwargs):
        if not REDIS_AVAILABLE:
            raise ImportError("redis package is required for RedisCacheService")
        
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_kwargs = kwargs
        self._redis: Optional[Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None
        
    async def _get_redis(self) -> Redis:
        """Get Redis connection with connection pooling"""
        if self._redis is None:
            if self._connection_pool is None:
                self._connection_pool = redis.ConnectionPool.from_url(
                    self.redis_url,
                    max_connections=20,
                    retry_on_timeout=True,
                    **self.redis_kwargs
                )
            
            self._redis = redis.Redis(connection_pool=self._connection_pool)
            
            # Test connection
            try:
                await self._redis.ping()
                logger.info("Redis connection established successfully")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        
        return self._redis
    
    def _serialize_value(self, value: Any) -> str:
        """Serialize value for Redis storage"""
        return json.dumps(value, default=str, ensure_ascii=False)
    
    def _deserialize_value(self, value: str) -> Any:
        """Deserialize value from Redis storage"""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        try:
            redis_client = await self._get_redis()
            value = await redis_client.get(key)
            
            if value is None:
                return None
            
            return self._deserialize_value(value.decode('utf-8'))
        
        except Exception as e:
            logger.error(f"Error getting key {key} from Redis: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis cache with optional TTL"""
        try:
            redis_client = await self._get_redis()
            serialized_value = self._serialize_value(value)
            
            if ttl is not None:
                result = await redis_client.setex(key, ttl, serialized_value)
            else:
                result = await redis_client.set(key, serialized_value)
            
            return bool(result)
        
        except Exception as e:
            logger.error(f"Error setting key {key} in Redis: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis cache"""
        try:
            redis_client = await self._get_redis()
            result = await redis_client.delete(key)
            return result > 0
        
        except Exception as e:
            logger.error(f"Error deleting key {key} from Redis: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern from Redis"""
        try:
            redis_client = await self._get_redis()
            
            # Get all keys matching pattern
            keys = await redis_client.keys(pattern)
            
            if not keys:
                return 0
            
            # Delete all matching keys
            result = await redis_client.delete(*keys)
            return result
        
        except Exception as e:
            logger.error(f"Error deleting pattern {pattern} from Redis: {e}")
            return 0
    
    async def clear(self) -> bool:
        """Clear all entries from Redis cache"""
        try:
            redis_client = await self._get_redis()
            result = await redis_client.flushdb()
            return bool(result)
        
        except Exception as e:
            logger.error(f"Error clearing Redis cache: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache"""
        try:
            redis_client = await self._get_redis()
            result = await redis_client.exists(key)
            return result > 0
        
        except Exception as e:
            logger.error(f"Error checking existence of key {key} in Redis: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics"""
        try:
            redis_client = await self._get_redis()
            info = await redis_client.info()
            
            return {
                "type": "redis",
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "redis_version": info.get("redis_version", "unknown")
            }
        
        except Exception as e:
            logger.error(f"Error getting Redis stats: {e}")
            return {"type": "redis", "error": str(e)}
    
    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            self._redis = None
        
        if self._connection_pool:
            await self._connection_pool.disconnect()
            self._connection_pool = None


class LocalCacheService(CacheService):
    """Local in-memory cache service for development"""
    
    def __init__(self, max_size_mb: int = 100, default_ttl_minutes: int = 60):
        self._cache = AdvancedCacheManager(max_size_mb, default_ttl_minutes)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from local cache"""
        return self._cache.get(key)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in local cache with optional TTL"""
        ttl_minutes = ttl / 60 if ttl is not None else None
        return self._cache.set(key, value, ttl_minutes)
    
    async def delete(self, key: str) -> bool:
        """Delete key from local cache"""
        return self._cache.delete(key)
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern from local cache"""
        # Simple pattern matching for local cache
        matching_keys = [
            key for key in self._cache.cache.keys()
            if self._matches_pattern(key, pattern)
        ]
        
        deleted_count = 0
        for key in matching_keys:
            if self._cache.delete(key):
                deleted_count += 1
        
        return deleted_count
    
    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """Simple pattern matching (supports * wildcard)"""
        if '*' not in pattern:
            return key == pattern
        
        # Convert Redis-style pattern to simple matching
        pattern_parts = pattern.split('*')
        
        if len(pattern_parts) == 2:
            prefix, suffix = pattern_parts
            # Both prefix and suffix must match, and if prefix is empty, any key matches
            if not prefix and not suffix:
                return True
            elif not prefix:
                return key.endswith(suffix)
            elif not suffix:
                return key.startswith(prefix)
            else:
                return key.startswith(prefix) and key.endswith(suffix)
        
        # For more complex patterns with multiple wildcards
        if not pattern_parts[0]:  # Pattern starts with *
            pattern_parts = pattern_parts[1:]
        if not pattern_parts[-1]:  # Pattern ends with *
            pattern_parts = pattern_parts[:-1]
        
        # Check that all non-empty parts appear in order in the key
        current_pos = 0
        for part in pattern_parts:
            if part:  # Skip empty parts
                pos = key.find(part, current_pos)
                if pos == -1:
                    return False
                current_pos = pos + len(part)
        
        return True
    
    async def clear(self) -> bool:
        """Clear all entries from local cache"""
        self._cache.clear()
        return True
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in local cache"""
        return self._cache.get(key) is not None
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get local cache statistics"""
        stats = self._cache.get_stats()
        stats["type"] = "local"
        return stats


class CacheInvalidationService:
    """Service for intelligent cache invalidation strategies"""
    
    def __init__(self, cache_service: CacheService):
        self.cache = cache_service
        self._invalidation_patterns = {
            "stock_analysis": [
                "analysis:{ticker}:*",
                "quote:{ticker}",
                "watchlist:*:{ticker}",
                "market:summary"
            ],
            "market_data": [
                "quote:*",
                "market:*",
                "sector:*"
            ],
            "user_data": [
                "user:{user_id}:*",
                "watchlist:{user_id}:*"
            ]
        }
    
    async def invalidate_stock_analysis(self, ticker: str) -> int:
        """Invalidate all cache entries related to a stock analysis"""
        total_deleted = 0
        
        for pattern_template in self._invalidation_patterns["stock_analysis"]:
            pattern = pattern_template.format(ticker=ticker)
            deleted = await self.cache.delete_pattern(pattern)
            total_deleted += deleted
            
            if deleted > 0:
                logger.info(f"Invalidated {deleted} cache entries for pattern: {pattern}")
        
        return total_deleted
    
    async def invalidate_market_data(self) -> int:
        """Invalidate all market-related cache entries"""
        total_deleted = 0
        
        for pattern in self._invalidation_patterns["market_data"]:
            deleted = await self.cache.delete_pattern(pattern)
            total_deleted += deleted
            
            if deleted > 0:
                logger.info(f"Invalidated {deleted} cache entries for pattern: {pattern}")
        
        return total_deleted
    
    async def invalidate_user_data(self, user_id: str) -> int:
        """Invalidate all cache entries for a specific user"""
        total_deleted = 0
        
        for pattern_template in self._invalidation_patterns["user_data"]:
            pattern = pattern_template.format(user_id=user_id)
            deleted = await self.cache.delete_pattern(pattern)
            total_deleted += deleted
            
            if deleted > 0:
                logger.info(f"Invalidated {deleted} cache entries for pattern: {pattern}")
        
        return total_deleted


def create_cache_service() -> CacheService:
    """Factory function to create appropriate cache service based on environment"""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        redis_url = os.getenv("REDIS_URL")
        if redis_url and REDIS_AVAILABLE:
            logger.info("Creating Redis cache service for production")
            return RedisCacheService(redis_url)
        else:
            logger.warning("Redis not available in production, falling back to local cache")
            return LocalCacheService()
    else:
        logger.info("Creating local cache service for development")
        return LocalCacheService()


# Global cache service instance
_cache_service: Optional[CacheService] = None


async def get_cache_service() -> CacheService:
    """Get the global cache service instance"""
    global _cache_service
    
    if _cache_service is None:
        _cache_service = create_cache_service()
    
    return _cache_service


async def get_cache_invalidation_service() -> CacheInvalidationService:
    """Get cache invalidation service"""
    cache_service = await get_cache_service()
    return CacheInvalidationService(cache_service)