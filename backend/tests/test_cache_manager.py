"""
Unit tests for cache manager functionality
"""
from app.cache_manager import AdvancedCacheManager
import pytest
import asyncio
import time
from datetime import timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAdvancedCacheManager:
    """Test cases for AdvancedCacheManager"""

    def setup_method(self):
        """Setup for each test method"""
        self.cache = AdvancedCacheManager(max_size_mb=1, default_ttl_minutes=1)
        # Clear any existing cache
        self.cache.clear()

    def test_cache_initialization(self):
        """Test cache manager initialization"""
        assert self.cache.max_size_bytes == 1024 * 1024  # 1MB
        assert self.cache.current_size_bytes == 0
        assert len(self.cache.cache) == 0
        assert self.cache.default_ttl == timedelta(minutes=1)

    def test_set_and_get_basic(self):
        """Test basic set and get operations"""
        # Test string value
        result = self.cache.set("test_key", "test_value")
        assert result is True

        retrieved = self.cache.get("test_key")
        assert retrieved == "test_value"

        # Test dict value
        test_dict = {"name": "John", "age": 30}
        self.cache.set("dict_key", test_dict)
        retrieved_dict = self.cache.get("dict_key")
        assert retrieved_dict == test_dict

    def test_ttl_expiration(self):
        """Test TTL expiration functionality"""
        # Set with very short TTL
        self.cache.set("expire_key", "expire_value", ttl_minutes=0.01)  # 0.6 seconds

        # Should be available immediately
        assert self.cache.get("expire_key") == "expire_value"

        # Wait for expiration
        time.sleep(1)

        # Should be expired now
        assert self.cache.get("expire_key") is None

    def test_cache_size_tracking(self):
        """Test cache size tracking and calculation"""
        initial_size = self.cache.current_size_bytes

        # Add some data
        self.cache.set("size_test", "x" * 1000)  # ~1KB

        # Size should have increased
        assert self.cache.current_size_bytes > initial_size

        # Remove the entry
        self.cache.delete("size_test")

        # Size should be back to initial
        assert self.cache.current_size_bytes == initial_size

    def test_lru_eviction(self):
        """Test LRU eviction when cache is full"""
        # Fill cache to near capacity with small entries
        for i in range(100):
            self.cache.set(f"key_{i}", "x" * 10000)  # ~10KB each

        # Add one more large entry that should trigger eviction
        self.cache.set("large_key", "x" * 500000)  # ~500KB

        # Some earlier entries should have been evicted
        assert self.cache.get("key_0") is None  # First entry should be evicted
        assert self.cache.get("large_key") == "x" * 500000  # New entry should exist

    def test_access_count_tracking(self):
        """Test access count and last accessed tracking"""
        self.cache.set("access_test", "value")

        # Get initial entry
        entry = self.cache.cache["access_test"]
        initial_count = entry.access_count
        initial_accessed = entry.last_accessed

        # Access the value
        self.cache.get("access_test")

        # Check that access count increased and last_accessed updated
        assert entry.access_count == initial_count + 1
        # last_accessed should be set after first access
        assert entry.last_accessed is not None
        if initial_accessed is not None:
            assert entry.last_accessed > initial_accessed

    def test_delete_operation(self):
        """Test cache deletion"""
        self.cache.set("delete_test", "value")
        assert self.cache.get("delete_test") == "value"

        # Delete the entry
        result = self.cache.delete("delete_test")
        assert result is True

        # Should not exist anymore
        assert self.cache.get("delete_test") is None

        # Deleting non-existent key should return False
        result = self.cache.delete("non_existent")
        assert result is False

    def test_clear_operation(self):
        """Test cache clear operation"""
        # Add multiple entries
        for i in range(5):
            self.cache.set(f"clear_test_{i}", f"value_{i}")

        assert len(self.cache.cache) == 5

        # Clear cache
        self.cache.clear()

        assert len(self.cache.cache) == 0
        assert self.cache.current_size_bytes == 0

    def test_get_stats(self):
        """Test cache statistics"""
        # Add some entries
        self.cache.set("stats_1", "value1")
        self.cache.set("stats_2", "value2", ttl_minutes=0.01)  # Will expire soon

        stats = self.cache.get_stats()

        assert "total_entries" in stats
        assert "active_entries" in stats
        assert "current_size_mb" in stats
        assert "max_size_mb" in stats
        assert "utilization_percent" in stats

        assert stats["total_entries"] >= 2
        assert stats["max_size_mb"] == 1.0  # We set 1MB limit

    def test_generate_key(self):
        """Test cache key generation"""
        key1 = self.cache._generate_key("prefix", param1="value1", param2="value2")
        key2 = self.cache._generate_key("prefix", param1="value1", param2="value2")
        key3 = self.cache._generate_key("prefix", param1="different", param2="value2")

        # Same parameters should generate same key
        assert key1 == key2

        # Different parameters should generate different key
        assert key1 != key3

        # Key should start with prefix
        assert key1.startswith("prefix:")

    def test_get_or_set_sync(self):
        """Test get_or_set with synchronous factory function"""
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return f"generated_value_{call_count}"

        # First call should use factory
        result1 = self.cache.get_or_set("factory_test", factory)
        assert result1 == "generated_value_1"
        assert call_count == 1

        # Second call should use cached value
        result2 = self.cache.get_or_set("factory_test", factory)
        assert result2 == "generated_value_1"  # Same value
        assert call_count == 1  # Factory not called again

    @pytest.mark.asyncio
    async def test_get_or_set_async(self):
        """Test get_or_set with async factory function"""
        call_count = 0

        async def async_factory():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Simulate async work
            return f"async_generated_{call_count}"

        # First call should use factory
        result1 = await self.cache.get_or_set_async("async_factory_test", async_factory)
        assert result1 == "async_generated_1"
        assert call_count == 1

        # Second call should use cached value
        result2 = await self.cache.get_or_set_async("async_factory_test", async_factory)
        assert result2 == "async_generated_1"  # Same value
        assert call_count == 1  # Factory not called again


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
