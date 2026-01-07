"""
Unit tests for Redis caching in production environment
"""
import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock, AsyncMock
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.cache import (
    create_cache_service,
    RedisCacheService,
    LocalCacheService,
    get_cache_service,
    CacheInvalidationService
)


class TestRedisCachingProduction:
    """Test Redis caching functionality in production environment"""
    
    def test_production_environment_uses_redis_cache(self):
        """
        Test that production environment uses Redis for caching
        Requirements: 5.1
        """
        # Mock Redis availability
        with patch('app.core.cache.REDIS_AVAILABLE', True):
            # Test production environment with Redis URL
            with patch.dict(os.environ, {
                'ENVIRONMENT': 'production',
                'REDIS_URL': 'redis://localhost:6379/0'
            }, clear=False):
                cache_service = create_cache_service()
                
                # Should create Redis cache service in production
                assert isinstance(cache_service, RedisCacheService)
                assert cache_service.redis_url == 'redis://localhost:6379/0'
    
    def test_production_fallback_to_local_when_redis_unavailable(self):
        """
        Test fallback to local cache when Redis is not available in production
        Requirements: 5.1
        """
        # Mock Redis as unavailable
        with patch('app.core.cache.REDIS_AVAILABLE', False):
            with patch.dict(os.environ, {
                'ENVIRONMENT': 'production',
                'REDIS_URL': 'redis://localhost:6379/0'
            }, clear=False):
                cache_service = create_cache_service()
                
                # Should fall back to local cache when Redis unavailable
                assert isinstance(cache_service, LocalCacheService)
    
    def test_development_environment_uses_local_cache(self):
        """
        Test that development environment uses local cache
        Requirements: 5.1
        """
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development'
        }, clear=False):
            cache_service = create_cache_service()
            
            # Should use local cache in development
            assert isinstance(cache_service, LocalCacheService)
    
    def test_default_environment_uses_local_cache(self):
        """
        Test that default (unspecified) environment uses local cache
        Requirements: 5.1
        """
        # Remove ENVIRONMENT variable if it exists
        env_backup = os.environ.get('ENVIRONMENT')
        if 'ENVIRONMENT' in os.environ:
            del os.environ['ENVIRONMENT']
        
        try:
            cache_service = create_cache_service()
            
            # Should use local cache by default
            assert isinstance(cache_service, LocalCacheService)
        finally:
            # Restore environment variable
            if env_backup is not None:
                os.environ['ENVIRONMENT'] = env_backup
    
    def test_redis_cache_service_configuration(self):
        """
        Test Redis cache service configuration and initialization
        Requirements: 5.1
        """
        with patch('app.core.cache.REDIS_AVAILABLE', True):
            # Test with custom Redis URL
            cache_service = RedisCacheService("redis://custom-host:6380/1")
            assert cache_service.redis_url == "redis://custom-host:6380/1"
            
            # Test with default Redis URL from environment
            with patch.dict(os.environ, {'REDIS_URL': 'redis://env-host:6379/2'}, clear=False):
                cache_service = RedisCacheService()
                assert cache_service.redis_url == "redis://env-host:6379/2"
    
    def test_redis_cache_service_without_redis_package(self):
        """
        Test Redis cache service raises error when Redis package not available
        Requirements: 5.1
        """
        with patch('app.core.cache.REDIS_AVAILABLE', False):
            with pytest.raises(ImportError, match="redis package is required"):
                RedisCacheService("redis://localhost:6379/0")
    
    @pytest.mark.asyncio
    async def test_local_cache_service_operations(self):
        """
        Test local cache service basic operations
        Requirements: 5.1
        """
        cache_service = LocalCacheService(max_size_mb=1, default_ttl_minutes=1)
        
        # Test set and get
        result = await cache_service.set("test_key", {"test": "value"})
        assert result is True
        
        value = await cache_service.get("test_key")
        assert value == {"test": "value"}
        
        # Test exists
        exists = await cache_service.exists("test_key")
        assert exists is True
        
        # Test delete
        deleted = await cache_service.delete("test_key")
        assert deleted is True
        
        # Test key no longer exists
        value = await cache_service.get("test_key")
        assert value is None
        
        exists = await cache_service.exists("test_key")
        assert exists is False
    
    @pytest.mark.asyncio
    async def test_local_cache_pattern_deletion(self):
        """
        Test local cache pattern-based deletion
        Requirements: 5.1
        """
        cache_service = LocalCacheService()
        
        # Set multiple keys with pattern
        await cache_service.set("test:key1", "value1")
        await cache_service.set("test:key2", "value2")
        await cache_service.set("other:key3", "value3")
        
        # Delete keys matching pattern
        deleted_count = await cache_service.delete_pattern("test:*")
        assert deleted_count == 2
        
        # Verify correct keys were deleted
        assert await cache_service.get("test:key1") is None
        assert await cache_service.get("test:key2") is None
        assert await cache_service.get("other:key3") == "value3"
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_service(self):
        """
        Test cache invalidation service functionality
        Requirements: 5.1
        """
        # Mock cache service
        mock_cache = AsyncMock()
        mock_cache.delete_pattern = AsyncMock(return_value=5)
        
        invalidation_service = CacheInvalidationService(mock_cache)
        
        # Test stock analysis invalidation
        result = await invalidation_service.invalidate_stock_analysis("AAPL")
        
        # Should have called delete_pattern for each pattern
        expected_calls = [
            "analysis:AAPL:*",
            "quote:AAPL", 
            "watchlist:*:AAPL",
            "market:summary"
        ]
        
        assert mock_cache.delete_pattern.call_count == len(expected_calls)
        
        # Verify each pattern was called
        for expected_pattern in expected_calls:
            mock_cache.delete_pattern.assert_any_call(expected_pattern)
        
        # Should return total deleted count
        assert result == 5 * len(expected_calls)  # 5 deletions per pattern
    
    @pytest.mark.asyncio
    async def test_global_cache_service_singleton(self):
        """
        Test that global cache service maintains singleton pattern
        Requirements: 5.1
        """
        # Clear any existing global cache service
        import app.core.cache
        app.core.cache._cache_service = None
        
        with patch('app.core.cache.create_cache_service') as mock_create:
            mock_cache = MagicMock()
            mock_create.return_value = mock_cache
            
            # First call should create cache service
            cache1 = await get_cache_service()
            assert cache1 == mock_cache
            mock_create.assert_called_once()
            
            # Second call should return same instance
            cache2 = await get_cache_service()
            assert cache2 == mock_cache
            assert cache1 is cache2
            
            # create_cache_service should only be called once
            assert mock_create.call_count == 1
    
    @pytest.mark.asyncio
    async def test_cache_service_stats(self):
        """
        Test cache service statistics functionality
        Requirements: 5.1
        """
        cache_service = LocalCacheService()
        
        # Add some test data
        await cache_service.set("stats_test_1", "value1")
        await cache_service.set("stats_test_2", "value2")
        
        # Get stats
        stats = await cache_service.get_stats()
        
        # Verify stats structure
        assert "type" in stats
        assert stats["type"] == "local"
        assert "total_entries" in stats
        assert "active_entries" in stats
        assert "current_size_mb" in stats
        assert "max_size_mb" in stats
        
        # Should have at least 2 entries
        assert stats["total_entries"] >= 2


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])