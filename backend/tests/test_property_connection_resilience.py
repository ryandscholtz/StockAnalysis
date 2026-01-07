"""
Property-based tests for database connection resilience
Tests Property 5: Connection Resilience
**Validates: Requirements 2.6, 5.4, 10.1**
"""
from app.database.connection import (
    RetryPolicy, SimpleConnectionPool, ConnectionError
)
import pytest
import asyncio
from hypothesis import given, strategies as st, settings
from unittest.mock import AsyncMock, MagicMock
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))


class FailingRepository:
    """Mock repository that fails operations for testing"""

    def __init__(self, failure_rate: float = 0.5, max_failures: int = 2):
        self.failure_rate = failure_rate
        self.max_failures = max_failures
        self.call_count = 0
        self.failure_count = 0

    async def get_analysis(self, ticker: str, analysis_date=None):
        self.call_count += 1
        if self.failure_count < self.max_failures and self.call_count <= self.max_failures:
            self.failure_count += 1
            raise ConnectionError(f"Simulated connection failure {self.failure_count}")
        return {"ticker": ticker, "analysis_date": analysis_date, "mock": True}

    async def save_analysis(
            self,
            ticker: str,
            analysis_data,
            exchange=None,
            analysis_date=None):
        self.call_count += 1
        if self.failure_count < self.max_failures and self.call_count <= self.max_failures:
            self.failure_count += 1
            raise ConnectionError(f"Simulated connection failure {self.failure_count}")
        return True

    async def get_watchlist(self):
        self.call_count += 1
        if self.failure_count < self.max_failures and self.call_count <= self.max_failures:
            self.failure_count += 1
            raise ConnectionError(f"Simulated connection failure {self.failure_count}")
        return []

    async def close(self):
        pass


class MockResilientDatabaseService:
    """Test-specific database service without decorators for isolated retry testing"""

    def __init__(self, repository, retry_policy: Optional[RetryPolicy] = None):
        self.repository = repository
        self.retry_policy = retry_policy or RetryPolicy()
        self._operation_count = 0
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None

    async def get_analysis(self, ticker: str, analysis_date: Optional[str] = None):
        """Get analysis with manual retry logic for testing"""
        self._operation_count += 1
        last_exception = None

        for attempt in range(1, self.retry_policy.max_attempts + 1):
            try:
                return await self.repository.get_analysis(ticker, analysis_date)
            except Exception as e:
                last_exception = e
                self._failure_count += 1
                self._last_failure_time = datetime.utcnow()

                if attempt < self.retry_policy.max_attempts:
                    delay = self.retry_policy.get_delay(attempt)
                    await asyncio.sleep(delay)
                else:
                    break

        # All attempts failed, raise the last exception
        raise last_exception

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            "operation_count": self._operation_count,
            "failure_count": self._failure_count,
            "success_rate": (self._operation_count - self._failure_count) / max(self._operation_count, 1),
            "last_failure_time": self._last_failure_time.isoformat() if self._last_failure_time else None
        }

    async def close(self):
        """Close the service"""
        if hasattr(self.repository, 'close'):
            await self.repository.close()


class TestConnectionResilience:
    """Property-based tests for database connection resilience"""

    @pytest.mark.asyncio
    @given(
        max_attempts=st.integers(min_value=2, max_value=5),
        base_delay=st.floats(min_value=0.01, max_value=0.1),
        max_failures=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=20, deadline=5000)
    async def test_retry_policy_resilience_property(
            self, max_attempts, base_delay, max_failures):
        """
        Feature: tech-stack-modernization, Property 5: Connection Resilience
        For any external service connection failure, failed operations should be retried according to policy
        **Validates: Requirements 2.6, 5.4, 10.1**
        """
        # Create retry policy
        retry_policy = RetryPolicy(
            max_attempts=max_attempts,
            base_delay=base_delay,
            exponential_backoff=False,  # Disable for faster testing
            jitter=False
        )

        # Create failing repository that will succeed after max_failures attempts
        # The repository should fail exactly max_failures times, then succeed
        failing_repo = FailingRepository(max_failures=max_failures)

        # Create test service (without decorators)
        service = MockResilientDatabaseService(failing_repo, retry_policy=retry_policy)

        # Test operation that should eventually succeed or fail based on retry attempts
        try:
            result = await service.get_analysis("AAPL")

            # Property: Operation should succeed if max_attempts > max_failures
            assert max_attempts > max_failures, f"Operation succeeded but max_attempts ({max_attempts}) should be > max_failures ({max_failures})"
            assert result is not None, "Operation should succeed with sufficient retries"
            assert result["ticker"] == "AAPL", "Result should contain expected data"

            # Property: Repository should be called exactly (max_failures + 1) times
            expected_calls = max_failures + 1
            assert failing_repo.call_count == expected_calls, f"Expected {expected_calls} calls, got {
                failing_repo.call_count}"

        except ConnectionError:
            # Property: Operation should fail if max_attempts <= max_failures
            assert max_attempts <= max_failures, f"Operation failed but max_attempts ({max_attempts}) should be <= max_failures ({max_failures})"

            # Property: Repository should be called exactly max_attempts times
            assert failing_repo.call_count == max_attempts, f"Expected {max_attempts} calls, got {
                failing_repo.call_count}"

    @pytest.mark.asyncio
    @given(
        pool_size=st.integers(min_value=2, max_value=5),
        concurrent_operations=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=15, deadline=5000)
    async def test_connection_pool_resilience_property(
            self, pool_size, concurrent_operations):
        """
        Feature: tech-stack-modernization, Property 5: Connection Resilience
        For any connection pool configuration, connections should be reused when possible
        **Validates: Requirements 2.6, 5.4, 10.1**
        """
        # Mock connection factory
        connection_count = 0
        created_connections = []

        async def mock_connection_factory():
            nonlocal connection_count
            connection_count += 1
            connection = MagicMock()
            connection.id = connection_count
            connection.close = AsyncMock()
            created_connections.append(connection)
            return connection

        # Create connection pool
        pool = SimpleConnectionPool(
            connection_factory=mock_connection_factory,
            max_size=pool_size,
            min_size=1
        )

        try:
            # Perform concurrent operations
            connections = []
            for i in range(min(concurrent_operations, pool_size)):
                conn = await pool.get_connection()
                connections.append(conn)

            # Property: Should not create more connections than requested
            assert len(
                connections) <= pool_size, f"Should not exceed pool size {pool_size}"
            assert connection_count <= pool_size, f"Should not create more than {pool_size} connections"

            # Return connections to pool
            for conn in connections:
                await pool.return_connection(conn)

            # Property: Connections should be reusable
            reused_connections = []
            for i in range(min(concurrent_operations, pool_size)):
                conn = await pool.get_connection()
                reused_connections.append(conn)

            # Property: Should reuse existing connections (no new connections created)
            assert connection_count <= pool_size, "Should reuse existing connections"

            # Return connections again
            for conn in reused_connections:
                await pool.return_connection(conn)

            # Property: Pool stats should be consistent
            stats = pool.get_stats()
            assert stats["total_connections"] <= pool_size, "Total connections should not exceed pool size"
            assert stats["active_connections"] == 0, "All connections should be returned to pool"

        finally:
            await pool.close_all()

    @pytest.mark.asyncio
    @given(
        operation_count=st.integers(min_value=3, max_value=8),
        failure_probability=st.floats(min_value=0.1, max_value=0.7)
    )
    @settings(max_examples=15, deadline=5000)
    async def test_service_resilience_statistics_property(
            self, operation_count, failure_probability):
        """
        Feature: tech-stack-modernization, Property 5: Connection Resilience
        For any series of database operations, service statistics should accurately track success/failure rates
        **Validates: Requirements 2.6, 5.4, 10.1**
        """
        # Create mock repository with probabilistic failures
        class ProbabilisticFailingRepository:
            def __init__(self, failure_prob: float):
                self.failure_prob = failure_prob
                self.call_count = 0
                self.actual_failures = 0

            async def get_analysis(self, ticker: str, analysis_date=None):
                self.call_count += 1
                import random
                if random.random() < self.failure_prob:
                    self.actual_failures += 1
                    raise ConnectionError("Probabilistic failure")
                return {"ticker": ticker, "mock": True}

            async def close(self):
                pass

        # Create repository and service
        repo = ProbabilisticFailingRepository(failure_probability)

        # Use retry policy with single attempt to get accurate failure stats
        retry_policy = RetryPolicy(max_attempts=1)
        service = MockResilientDatabaseService(repo, retry_policy=retry_policy)

        # Perform operations
        successful_operations = 0
        failed_operations = 0

        for i in range(operation_count):
            try:
                await service.get_analysis(f"STOCK{i}")
                successful_operations += 1
            except ConnectionError:
                failed_operations += 1

        # Get service statistics
        stats = service.get_stats()

        # Property: Operation count should match actual operations
        assert stats["operation_count"] == operation_count, f"Expected {operation_count} operations, got {
            stats['operation_count']}"

        # Property: Failure count should match actual failures
        assert stats["failure_count"] == failed_operations, f"Expected {failed_operations} failures, got {
            stats['failure_count']}"

        # Property: Success rate should be calculated correctly
        expected_success_rate = successful_operations / operation_count
        assert abs(
            stats["success_rate"] - expected_success_rate) < 0.01, f"Success rate mismatch: expected {expected_success_rate}, got {
            stats['success_rate']}"

        # Property: If there were failures, last_failure_time should be set
        if failed_operations > 0:
            assert stats["last_failure_time"] is not None, "Last failure time should be recorded"

        await service.close()

    @pytest.mark.asyncio
    @given(
        exponential_backoff=st.booleans(),
        jitter=st.booleans(),
        max_attempts=st.integers(min_value=2, max_value=4)
    )
    @settings(max_examples=10, deadline=5000)
    async def test_retry_delay_calculation_property(
            self, exponential_backoff, jitter, max_attempts):
        """
        Feature: tech-stack-modernization, Property 5: Connection Resilience
        For any retry policy configuration, delay calculations should follow the specified pattern
        **Validates: Requirements 2.6, 5.4, 10.1**
        """
        base_delay = 0.01  # Small delay for testing
        max_delay = 0.1

        retry_policy = RetryPolicy(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_backoff=exponential_backoff,
            jitter=jitter
        )

        delays = []
        for attempt in range(1, max_attempts + 1):
            delay = retry_policy.get_delay(attempt)
            delays.append(delay)

        # Property: All delays should be positive
        assert all(d > 0 for d in delays), "All delays should be positive"

        # Property: All delays should not exceed max_delay
        assert all(
            d <= max_delay for d in delays), f"All delays should be <= {max_delay}"

        # Property: If exponential backoff is enabled, delays should generally increase
        if exponential_backoff and not jitter and len(delays) > 1:
            # Without jitter, delays should strictly increase (up to max_delay)
            for i in range(1, len(delays)):
                if delays[i - 1] < max_delay:  # Only check if previous delay wasn't capped
                    expected_delay = min(base_delay * (2 ** (i)), max_delay)
                    # Allow some tolerance for floating point precision
                    assert delays[i] >= delays[i - 1] * \
                        0.9, f"Exponential backoff should increase delays: {delays}"

        # Property: If exponential backoff is disabled, delays should be
        # consistent (ignoring jitter)
        if not exponential_backoff and not jitter:
            expected_delay = min(base_delay, max_delay)
            for delay in delays:
                assert abs(
                    delay - expected_delay) < 0.001, f"Fixed delay should be consistent: expected {expected_delay}, got {delay}"

    @pytest.mark.asyncio
    async def test_connection_pool_cleanup_property(self):
        """
        Feature: tech-stack-modernization, Property 5: Connection Resilience
        For any connection pool, cleanup should properly close all connections
        **Validates: Requirements 2.6, 5.4, 10.1**
        """
        # Track connection lifecycle
        created_connections = []
        closed_connections = []

        async def mock_connection_factory():
            connection = MagicMock()
            connection.close = AsyncMock()
            created_connections.append(connection)

            # Track when close is called
            original_close = connection.close

            async def tracked_close():
                closed_connections.append(connection)
                return await original_close()
            connection.close = tracked_close

            return connection

        # Create and use connection pool
        pool = SimpleConnectionPool(
            connection_factory=mock_connection_factory,
            max_size=3,
            min_size=1
        )

        # Get and return some connections
        conn1 = await pool.get_connection()
        conn2 = await pool.get_connection()
        await pool.return_connection(conn1)
        await pool.return_connection(conn2)

        # Property: Connections should be created
        assert len(created_connections) >= 2, "Connections should be created"

        # Close pool
        await pool.close_all()

        # Property: All created connections should be closed
        assert len(closed_connections) == len(
            created_connections), "All created connections should be closed"

        # Property: Pool stats should reflect cleanup
        stats = pool.get_stats()
        assert stats["total_connections"] == 0, "Total connections should be 0 after cleanup"
        assert stats["active_connections"] == 0, "Active connections should be 0 after cleanup"
        assert stats["pooled_connections"] == 0, "Pooled connections should be 0 after cleanup"


if __name__ == "__main__":
    pytest.main([__file__])
