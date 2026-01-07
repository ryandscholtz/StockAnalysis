"""
Property-based tests for cache invalidation correctness
"""
import pytest
import asyncio
import os
import sys
import logging
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from unittest.mock import AsyncMock, MagicMock

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.cache import LocalCacheService, CacheInvalidationService

logger = logging.getLogger(__name__)


class TestCacheInvalidationProperty:
    """Property-based tests for cache invalidation correctness"""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test to ensure clean cache state"""
        # This fixture will ensure each test gets a clean environment
        # The actual cache clearing is done in each test method
        yield
    
    @given(
        ticker=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        cache_data=st.dictionaries(
            keys=st.text(min_size=5, max_size=50),
            values=st.text(min_size=1, max_size=100),
            min_size=1,
            max_size=20
        )
    )
    @settings(max_examples=50, deadline=10000)
    @pytest.mark.asyncio
    async def test_cache_invalidation_correctness_property(self, ticker: str, cache_data: dict):
        """
        Property 10: Cache Invalidation Correctness
        For any cached data, when the underlying data changes, the cache entry should be 
        invalidated and subsequent requests should return fresh data.
        
        **Validates: Requirements 5.2**
        """
        # Ensure ticker is valid
        assume(len(ticker.strip()) > 0)
        ticker = ticker.upper().strip()
        
        # Create fresh cache service and invalidation service instances
        cache_service = LocalCacheService()
        invalidation_service = CacheInvalidationService(cache_service)
        
        # Ensure completely clean state
        await cache_service.clear()
        
        # Populate cache with data related to the ticker
        cache_keys = []
        for key_suffix, value in cache_data.items():
            # Create cache keys that would be affected by ticker invalidation
            cache_key = f"analysis:{ticker}:{key_suffix}"
            await cache_service.set(cache_key, value)
            cache_keys.append(cache_key)
        
        # Also add some unrelated cache entries that should NOT be invalidated
        unrelated_keys = []
        for i, (key_suffix, value) in enumerate(list(cache_data.items())[:3]):
            unrelated_key = f"analysis:OTHER{i}:{key_suffix}"
            await cache_service.set(unrelated_key, value)
            unrelated_keys.append(unrelated_key)
        
        # Add quote cache entry for the ticker
        quote_key = f"quote:{ticker}"
        await cache_service.set(quote_key, {"price": 100.0, "volume": 1000})
        cache_keys.append(quote_key)
        
        # Add watchlist entries
        watchlist_key = f"watchlist:user123:{ticker}"
        await cache_service.set(watchlist_key, {"added_at": "2024-01-01"})
        cache_keys.append(watchlist_key)
        
        # Add market summary (should be invalidated for any ticker)
        market_key = "market:summary"
        await cache_service.set(market_key, {"status": "open"})
        cache_keys.append(market_key)
        
        # Verify all cache entries exist before invalidation
        for key in cache_keys:
            cached_value = await cache_service.get(key)
            assert cached_value is not None, f"Cache key {key} should exist before invalidation"
        
        # Verify unrelated entries exist
        for key in unrelated_keys:
            cached_value = await cache_service.get(key)
            assert cached_value is not None, f"Unrelated key {key} should exist before invalidation"
        
        # Perform cache invalidation for the ticker
        invalidated_count = await invalidation_service.invalidate_stock_analysis(ticker)
        
        # Property: After invalidation, all ticker-related cache entries should be removed
        for key in cache_keys:
            cached_value = await cache_service.get(key)
            assert cached_value is None, f"Cache key {key} should be invalidated after ticker update"
        
        # Property: Unrelated cache entries should remain intact
        for key in unrelated_keys:
            cached_value = await cache_service.get(key)
            assert cached_value is not None, f"Unrelated key {key} should NOT be invalidated"
        
        # Property: Invalidation should report correct count
        assert invalidated_count >= len([k for k in cache_keys if k.startswith(f"analysis:{ticker}:") or k == f"quote:{ticker}" or k.startswith("watchlist:") or k == "market:summary"]), \
            "Invalidation count should reflect actual invalidated entries"
    
    @given(
        cache_entries=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),  # cache key
                st.text(min_size=1, max_size=30)   # cache value
            ),
            min_size=1,
            max_size=10
        ),
        invalidation_pattern=st.sampled_from(["analysis:*", "quote:*", "market:*", "user:*"])
    )
    @settings(max_examples=20, deadline=8000, suppress_health_check=[HealthCheck.filter_too_much])
    @pytest.mark.asyncio
    async def test_pattern_invalidation_correctness_property(self, cache_entries: list, invalidation_pattern: str):
        """
        Property 10b: Pattern Invalidation Correctness
        For any cache invalidation pattern, only entries matching the pattern should be removed,
        and all matching entries should be removed.
        
        **Validates: Requirements 5.2**
        """
        # Create a fresh cache service instance for this test
        cache_service = LocalCacheService()
        
        # Ensure completely clean state
        await cache_service.clear()
        
        # Populate cache with entries
        matching_keys = []
        non_matching_keys = []
        valid_entries = []
        
        for key, value in cache_entries:
            # Clean and validate key
            key = key.strip()
            if len(key) == 0:
                continue  # Skip empty keys instead of using assume
            
            # Ensure key is ASCII for consistent behavior
            try:
                key.encode('ascii')
            except UnicodeEncodeError:
                continue  # Skip non-ASCII keys
            
            valid_entries.append((key, value))
            
            # Determine if key matches pattern
            pattern_prefix = invalidation_pattern.replace("*", "")
            if key.startswith(pattern_prefix):
                matching_keys.append(key)
            else:
                non_matching_keys.append(key)
        
        # Skip test if no valid entries (but don't use assume to avoid filtering)
        if len(valid_entries) == 0:
            return
        
        # Set cache entries
        for key, value in valid_entries:
            success = await cache_service.set(key, value)
            assert success, f"Failed to set cache entry for key {key}"
        
        # Verify all entries exist before invalidation
        for key, _ in valid_entries:
            cached_value = await cache_service.get(key)
            assert cached_value is not None, f"Cache key {key} should exist before invalidation"
        
        # Get initial cache stats to verify state
        initial_stats = await cache_service.get_stats()
        logger.info(f"Cache state before invalidation: {initial_stats}")
        
        # Perform pattern-based invalidation
        deleted_count = await cache_service.delete_pattern(invalidation_pattern)
        
        # Log for debugging
        logger.info(f"Pattern: {invalidation_pattern}, Matching keys: {matching_keys}, "
                   f"Non-matching keys: {non_matching_keys}, Deleted count: {deleted_count}")
        
        # Property: All matching keys should be invalidated
        for key in matching_keys:
            cached_value = await cache_service.get(key)
            assert cached_value is None, f"Matching key {key} should be invalidated by pattern {invalidation_pattern}"
        
        # Property: Non-matching keys should remain
        for key in non_matching_keys:
            cached_value = await cache_service.get(key)
            assert cached_value is not None, f"Non-matching key {key} should NOT be invalidated by pattern {invalidation_pattern}"
        
        # Property: Deleted count should match number of matching keys
        assert deleted_count == len(matching_keys), \
            f"Deleted count {deleted_count} should equal matching keys count {len(matching_keys)}. " \
            f"Matching keys: {matching_keys}, Non-matching keys: {non_matching_keys}"
    
    @given(
        initial_data=st.dictionaries(
            keys=st.text(min_size=3, max_size=20),
            values=st.text(min_size=1, max_size=30),
            min_size=1,
            max_size=10
        ),
        updated_data=st.dictionaries(
            keys=st.text(min_size=3, max_size=20),
            values=st.text(min_size=1, max_size=30),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=25, deadline=8000)
    @pytest.mark.asyncio
    async def test_cache_freshness_after_invalidation_property(self, initial_data: dict, updated_data: dict):
        """
        Property 10c: Cache Freshness After Invalidation
        For any cache invalidation, subsequent cache sets should store fresh data
        and not be affected by previous cached values.
        
        **Validates: Requirements 5.2**
        """
        cache_service = LocalCacheService()
        
        # Clear any existing cache entries to ensure clean state
        await cache_service.clear()
        
        # Set initial cache data
        cache_keys = []
        for key, value in initial_data.items():
            key = key.strip()
            assume(len(key) > 0)
            cache_key = f"test:{key}"
            await cache_service.set(cache_key, value)
            cache_keys.append(cache_key)
        
        # Verify initial data is cached
        for key in cache_keys:
            cached_value = await cache_service.get(key)
            assert cached_value is not None, f"Initial data should be cached for key {key}"
        
        # Invalidate all test data
        deleted_count = await cache_service.delete_pattern("test:*")
        
        # Property: All cache entries should be invalidated
        for key in cache_keys:
            cached_value = await cache_service.get(key)
            assert cached_value is None, f"Cache key {key} should be invalidated"
        
        # Set updated data with same keys
        updated_keys = []
        for key, value in updated_data.items():
            key = key.strip()
            if len(key) > 0:
                cache_key = f"test:{key}"
                await cache_service.set(cache_key, value)
                updated_keys.append((cache_key, value))
        
        # Property: Fresh data should be retrievable and correct
        for cache_key, expected_value in updated_keys:
            cached_value = await cache_service.get(cache_key)
            assert cached_value == expected_value, \
                f"Fresh data should be correctly cached for key {cache_key}"
        
        # Property: Only updated keys should exist, no stale data
        for original_key in cache_keys:
            if original_key not in [k for k, _ in updated_keys]:
                cached_value = await cache_service.get(original_key)
                assert cached_value is None, \
                    f"Non-updated key {original_key} should remain invalidated"
    
    @given(
        user_id=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        user_data=st.dictionaries(
            keys=st.text(min_size=3, max_size=15),
            values=st.integers(min_value=1, max_value=1000),
            min_size=1,
            max_size=8
        )
    )
    @settings(max_examples=20, deadline=6000)
    @pytest.mark.asyncio
    async def test_user_specific_invalidation_property(self, user_id: str, user_data: dict):
        """
        Property 10d: User-Specific Invalidation
        For any user-specific cache invalidation, only that user's data should be affected,
        other users' data should remain intact.
        
        **Validates: Requirements 5.2**
        """
        # Ensure user_id is valid
        user_id = user_id.strip()
        assume(len(user_id) > 0)
        
        cache_service = LocalCacheService()
        invalidation_service = CacheInvalidationService(cache_service)
        
        # Clear any existing cache entries to ensure clean state
        await cache_service.clear()
        
        # Create cache entries for target user
        target_user_keys = []
        for key, value in user_data.items():
            cache_key = f"user:{user_id}:{key}"
            await cache_service.set(cache_key, value)
            target_user_keys.append(cache_key)
        
        # Create cache entries for other users
        other_user_keys = []
        for i in range(3):  # Create 3 other users
            other_user_id = f"other_user_{i}"
            for key, value in list(user_data.items())[:3]:  # Use subset of data
                cache_key = f"user:{other_user_id}:{key}"
                await cache_service.set(cache_key, value)
                other_user_keys.append(cache_key)
        
        # Verify all data exists before invalidation
        all_keys = target_user_keys + other_user_keys
        for key in all_keys:
            cached_value = await cache_service.get(key)
            assert cached_value is not None, f"Cache key {key} should exist before invalidation"
        
        # Invalidate target user's data
        invalidated_count = await invalidation_service.invalidate_user_data(user_id)
        
        # Property: Target user's data should be invalidated
        for key in target_user_keys:
            cached_value = await cache_service.get(key)
            assert cached_value is None, f"Target user key {key} should be invalidated"
        
        # Property: Other users' data should remain intact
        for key in other_user_keys:
            cached_value = await cache_service.get(key)
            assert cached_value is not None, f"Other user key {key} should NOT be invalidated"
        
        # Property: Invalidation count should be positive if target user had data
        if target_user_keys:
            assert invalidated_count > 0, "Invalidation should report positive count when data exists"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])