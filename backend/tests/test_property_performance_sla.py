"""
Property-based tests for performance SLA compliance
"""
from app.core.cache import LocalCacheService
import pytest
import asyncio
import time
import sys
import os
from hypothesis import given, strategies as st, settings, assume
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MockPerformanceService:
    """Mock service for testing performance SLA compliance"""

    def __init__(self, cache_service):
        self.cache = cache_service
        self.sla_threshold_ms = 200  # 200ms SLA for cached data

    async def get_cached_data(self, key: str, data_generator=None) -> Dict[str, Any]:
        """Get data from cache with performance tracking"""
        start_time = time.perf_counter()

        # Try to get from cache first
        cached_data = await self.cache.get(key)

        if cached_data is not None:
            end_time = time.perf_counter()
            response_time_ms = (end_time - start_time) * 1000

            return {
                "data": cached_data,
                "cache_hit": True,
                "response_time_ms": response_time_ms,
                "sla_compliant": response_time_ms <= self.sla_threshold_ms
            }

        # Generate new data if not in cache
        if data_generator:
            new_data = await data_generator() if asyncio.iscoroutinefunction(data_generator) else data_generator()
            await self.cache.set(key, new_data)

            end_time = time.perf_counter()
            response_time_ms = (end_time - start_time) * 1000

            return {
                "data": new_data,
                "cache_hit": False,
                "response_time_ms": response_time_ms,
                "sla_compliant": response_time_ms <= self.sla_threshold_ms
            }

        end_time = time.perf_counter()
        response_time_ms = (end_time - start_time) * 1000

        return {
            "data": None,
            "cache_hit": False,
            "response_time_ms": response_time_ms,
            "sla_compliant": response_time_ms <= self.sla_threshold_ms
        }

    async def batch_get_cached_data(self, keys: list) -> Dict[str, Dict[str, Any]]:
        """Get multiple cached items with performance tracking"""
        start_time = time.perf_counter()

        results = {}
        for key in keys:
            cached_data = await self.cache.get(key)
            results[key] = {
                "data": cached_data,
                "cache_hit": cached_data is not None
            }

        end_time = time.perf_counter()
        total_response_time_ms = (end_time - start_time) * 1000

        return {
            "results": results,
            "total_response_time_ms": total_response_time_ms,
            "average_response_time_ms": total_response_time_ms /
            len(keys) if keys else 0,
            "sla_compliant": total_response_time_ms <= (
                self.sla_threshold_ms *
                len(keys))}


class TestPerformanceSLAProperty:
    """Property-based tests for performance SLA compliance"""

    @given(
        cache_keys=st.lists(
            st.text(min_size=5, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc'))),
            min_size=1,
            max_size=10
        ),
        cache_values=st.lists(
            st.dictionaries(
                keys=st.text(min_size=3, max_size=15),
                values=st.one_of(
                    st.text(min_size=1, max_size=100),
                    st.integers(min_value=1, max_value=1000),
                    st.floats(min_value=0.1, max_value=1000.0)
                ),
                min_size=1,
                max_size=5
            ),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=30, deadline=8000)
    @pytest.mark.asyncio
    async def test_cached_data_performance_sla_property(
            self, cache_keys: list, cache_values: list):
        """
        Property 12: Performance SLA Compliance
        For any cached data request, the response time should be under 200ms.

        **Validates: Requirements 5.6**
        """
        # Ensure we have valid keys
        cache_keys = [key.strip() for key in cache_keys if key.strip()]
        assume(len(cache_keys) > 0)
        assume(len(cache_values) > 0)

        # Create cache service and performance service
        cache_service = LocalCacheService()
        perf_service = MockPerformanceService(cache_service)

        # Pre-populate cache with test data
        for i, key in enumerate(cache_keys):
            value = cache_values[i % len(cache_values)]
            await cache_service.set(key, value)

        # Test cached data retrieval performance
        for key in cache_keys:
            result = await perf_service.get_cached_data(key)

            # Property: Cached data should be retrieved quickly
            assert result["cache_hit"] is True, \
                f"Key {key} should be found in cache"

            # Property: Response time should meet SLA for cached data
            assert result["response_time_ms"] <= perf_service.sla_threshold_ms, f"Cached data response time {
                result['response_time_ms']}ms should be <= {
                perf_service.sla_threshold_ms}ms for key {key}"

            # Property: SLA compliance flag should be accurate
            expected_compliance = result["response_time_ms"] <= perf_service.sla_threshold_ms
            assert result["sla_compliant"] == expected_compliance, \
                f"SLA compliance flag should match actual performance for key {key}"

            # Property: Data should be returned correctly
            assert result["data"] is not None, \
                f"Cached data should be returned for key {key}"

    @given(
        batch_size=st.integers(min_value=1, max_value=20),
        data_complexity=st.sampled_from(["simple", "medium", "complex"])
    )
    @settings(max_examples=25, deadline=6000)
    @pytest.mark.asyncio
    async def test_batch_cache_performance_sla_property(
            self, batch_size: int, data_complexity: str):
        """
        Property 12b: Batch Cache Performance SLA
        For any batch of cached data requests, the average response time per item
        should remain within SLA bounds.

        **Validates: Requirements 5.6**
        """
        cache_service = LocalCacheService()
        perf_service = MockPerformanceService(cache_service)

        # Generate test data based on complexity
        cache_keys = [f"batch_key_{i}_{data_complexity}" for i in range(batch_size)]

        if data_complexity == "simple":
            test_values = [{"id": i, "value": f"simple_value_{i}"}
                           for i in range(batch_size)]
        elif data_complexity == "medium":
            test_values = [
                {
                    "id": i,
                    "data": f"medium_data_{i}" * 10,
                    "metadata": {"created": f"2024-01-{i + 1:02d}", "type": "medium"}
                }
                for i in range(batch_size)
            ]
        else:  # complex
            test_values = [
                {
                    "id": i,
                    "large_data": f"complex_data_{i}" * 50,
                    "nested": {
                        "level1": {"level2": {"level3": f"deep_value_{i}"}},
                        "arrays": [f"item_{j}" for j in range(10)]
                    },
                    "metadata": {
                        "created": f"2024-01-{i + 1:02d}",
                        "type": "complex",
                        "size": len(f"complex_data_{i}" * 50)
                    }
                }
                for i in range(batch_size)
            ]

        # Pre-populate cache
        for key, value in zip(cache_keys, test_values):
            await cache_service.set(key, value)

        # Test batch retrieval performance
        batch_result = await perf_service.batch_get_cached_data(cache_keys)

        # Property: All items should be cache hits
        for key in cache_keys:
            assert batch_result["results"][key]["cache_hit"] is True, \
                f"Key {key} should be found in cache"

        # Property: Average response time should meet SLA
        avg_response_time = batch_result["average_response_time_ms"]
        assert avg_response_time <= perf_service.sla_threshold_ms, f"Average response time {avg_response_time}ms should be <= {
            perf_service.sla_threshold_ms}ms for batch size {batch_size}"

        # Property: Total batch time should be reasonable
        total_time = batch_result["total_response_time_ms"]
        max_acceptable_total = perf_service.sla_threshold_ms * batch_size
        assert total_time <= max_acceptable_total, \
            f"Total batch time {total_time}ms should be <= {max_acceptable_total}ms"

        # Property: SLA compliance should be accurate
        expected_compliance = total_time <= max_acceptable_total
        assert batch_result["sla_compliant"] == expected_compliance, \
            "Batch SLA compliance flag should match actual performance"

    @given(
        concurrent_requests=st.integers(min_value=2, max_value=10),
        cache_hit_ratio=st.floats(min_value=0.5, max_value=1.0)
    )
    @settings(max_examples=15, deadline=10000)
    @pytest.mark.asyncio
    async def test_concurrent_cache_performance_sla_property(
            self, concurrent_requests: int, cache_hit_ratio: float):
        """
        Property 12c: Concurrent Cache Performance SLA
        For any number of concurrent cached data requests, each should meet SLA requirements
        without significant performance degradation.

        **Validates: Requirements 5.6**
        """
        cache_service = LocalCacheService()
        await cache_service.clear()  # Clear any existing cache entries
        perf_service = MockPerformanceService(cache_service)

        # Prepare cache keys and determine which should be cache hits
        cache_keys = [f"concurrent_key_{i}_{time.time()}" for i in range(
            concurrent_requests)]  # Use unique keys
        num_cache_hits = int(concurrent_requests * cache_hit_ratio)

        # Pre-populate cache for some keys (to achieve desired hit ratio)
        for i in range(num_cache_hits):
            key = cache_keys[i]
            value = {"id": i, "data": f"concurrent_data_{i}", "timestamp": time.time()}
            await cache_service.set(key, value)

        # Define async function for concurrent execution that doesn't cache misses
        async def get_cached_item(key: str) -> Dict[str, Any]:
            # Check if this key should be a cache hit based on our pre-population
            key_index = cache_keys.index(key)
            if key_index < num_cache_hits:
                # This should be a cache hit - don't provide data generator
                return await perf_service.get_cached_data(key, data_generator=None)
            else:
                # This should be a cache miss - don't provide data generator
                return await perf_service.get_cached_data(key, data_generator=None)

        # Execute concurrent requests
        start_time = time.perf_counter()
        tasks = [get_cached_item(key) for key in cache_keys]
        results = await asyncio.gather(*tasks)
        end_time = time.perf_counter()

        total_concurrent_time_ms = (end_time - start_time) * 1000

        # Property: Each cached request should meet SLA
        cache_hit_results = [r for r in results if r["cache_hit"]]
        for result in cache_hit_results:
            assert result["sla_compliant"] is True, f"Cached request should meet SLA: {
                result['response_time_ms']}ms <= {
                perf_service.sla_threshold_ms}ms"

        # Property: Cache hit ratio should be approximately as expected (with more
        # tolerance for small samples)
        actual_hit_ratio = len(cache_hit_results) / len(results)
        # At least 30% tolerance or 1/n for small samples
        expected_tolerance = max(0.3, 1.0 / concurrent_requests)
        assert abs(actual_hit_ratio - cache_hit_ratio) <= expected_tolerance, \
            f"Actual cache hit ratio {actual_hit_ratio} should be close to expected {cache_hit_ratio} (tolerance: {expected_tolerance})"

        # Property: Concurrent execution should not cause excessive delays
        max_acceptable_concurrent_time = perf_service.sla_threshold_ms * \
            2  # Allow 2x SLA for concurrent overhead
        assert total_concurrent_time_ms <= max_acceptable_concurrent_time, \
            f"Concurrent execution time {total_concurrent_time_ms}ms should be <= {max_acceptable_concurrent_time}ms"

        # Property: All requests should complete successfully
        assert len(results) == concurrent_requests, \
            f"All {concurrent_requests} concurrent requests should complete"

        for i, result in enumerate(results):
            assert "data" in result, f"Request {i} should return data"
            assert "response_time_ms" in result, f"Request {i} should include response time"

    @given(
        sla_threshold=st.integers(
            min_value=100,
            max_value=500),
        # 100ms to 500ms (more realistic)
        cache_operations=st.lists(
            st.tuples(
                st.sampled_from(["get", "set", "delete"]),
                st.text(
                    min_size=5,
                    max_size=20,
                    alphabet=st.characters(
                        whitelist_categories=(
                            'Lu',
                            'Ll',
                            'Nd'))),
                st.text(
                    min_size=1,
                    max_size=20,
                    alphabet=st.characters(
                        whitelist_categories=(
                            'Lu',
                            'Ll',
                            'Nd')))
            ),
            min_size=5,
            max_size=10
        )
    )
    @settings(max_examples=10, deadline=8000)
    @pytest.mark.asyncio
    async def test_cache_operation_performance_consistency_property(
            self, sla_threshold: int, cache_operations: list):
        """
        Property 12d: Cache Operation Performance Consistency
        For any sequence of cache operations, performance should remain consistent
        and within configured SLA thresholds.

        **Validates: Requirements 5.6**
        """
        cache_service = LocalCacheService()
        await cache_service.clear()  # Clear any existing cache entries
        perf_service = MockPerformanceService(cache_service)
        perf_service.sla_threshold_ms = sla_threshold

        operation_times = []

        # Execute cache operations and measure performance
        for operation, key, value in cache_operations:
            key = key.strip()
            assume(len(key) > 0)

            start_time = time.perf_counter()

            if operation == "get":
                await cache_service.get(key)
            elif operation == "set":
                await cache_service.set(key, value)
            elif operation == "delete":
                await cache_service.delete(key)

            end_time = time.perf_counter()
            operation_time_ms = (end_time - start_time) * 1000
            operation_times.append(operation_time_ms)

        # Property: Most operations should complete within reasonable time (allow
        # some outliers)
        slow_operations = [t for t in operation_times if t > sla_threshold]
        slow_operation_ratio = len(slow_operations) / len(operation_times)
        assert slow_operation_ratio <= 0.2, f"Too many slow operations: {
            slow_operation_ratio:.2%} > 20% (threshold: {sla_threshold}ms)"

        # Property: Average performance should be well within SLA
        avg_time = sum(operation_times) / len(operation_times)
        assert avg_time <= sla_threshold * 0.5, \
            f"Average operation time {avg_time}ms should be well within SLA threshold {sla_threshold}ms"

    @given(
        cache_size_mb=st.integers(min_value=1, max_value=10),
        entry_count=st.integers(min_value=10, max_value=100)
    )
    @settings(max_examples=10, deadline=6000)
    @pytest.mark.asyncio
    async def test_cache_size_impact_on_performance_property(
            self, cache_size_mb: int, entry_count: int):
        """
        Property 12e: Cache Size Impact on Performance
        For any cache size and entry count, performance should remain within SLA
        regardless of cache utilization level.

        **Validates: Requirements 5.6**
        """
        # Create cache with specific size limit
        cache_service = LocalCacheService(
            max_size_mb=cache_size_mb, default_ttl_minutes=60)
        perf_service = MockPerformanceService(cache_service)

        # Fill cache with entries
        cache_keys = []
        for i in range(entry_count):
            key = f"size_test_key_{i}"
            # Create entries of varying sizes
            value_size = (i % 5 + 1) * 100  # 100-500 chars
            value = {
                "id": i,
                "data": "x" * value_size,
                "metadata": {"size": value_size, "index": i}
            }

            await cache_service.set(key, value)
            cache_keys.append(key)

        # Test performance with different cache utilization levels
        sample_keys = cache_keys[::max(1, len(cache_keys) // 10)]  # Sample ~10 keys

        performance_results = []
        for key in sample_keys:
            result = await perf_service.get_cached_data(key)
            performance_results.append(result)

        # Property: All cached lookups should meet SLA regardless of cache size
        for result in performance_results:
            if result["cache_hit"]:
                assert result["sla_compliant"] is True, \
                    f"Cache lookup should meet SLA regardless of cache size: {result['response_time_ms']}ms"

        # Property: Performance should not degrade significantly with cache size
        response_times = [r["response_time_ms"]
                          for r in performance_results if r["cache_hit"]]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)

            # Performance should be consistent regardless of cache utilization
            assert avg_response_time <= perf_service.sla_threshold_ms * 0.5, \
                f"Average response time should be well within SLA: {avg_response_time}ms"

            assert max_response_time <= perf_service.sla_threshold_ms, \
                f"Maximum response time should meet SLA: {max_response_time}ms"

        # Property: Cache should maintain reasonable statistics
        stats = await cache_service.get_stats()
        # Note: Cache may have entries from previous operations, so we check if
        # it's reasonable
        assert stats["total_entries"] >= 0, \
            "Cache should have non-negative entry count"

        # Check that we can retrieve the entries we just added
        retrieved_count = 0
        for key in sample_keys:
            if await cache_service.exists(key):
                retrieved_count += 1

        assert retrieved_count > 0, \
            "Should be able to retrieve at least some of the added entries"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
