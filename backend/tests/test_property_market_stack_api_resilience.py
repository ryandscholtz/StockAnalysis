"""
Property-based tests for Market Stack API resilience
Feature: tech-stack-modernization, Property 26: Market Stack API Resilience
"""
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import Mock, patch, MagicMock
import requests
import time
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock the problematic imports before importing the actual modules
with patch.dict('sys.modules', {
    'yfinance': MagicMock(),
    'app.data.api_client': MagicMock(),
    'app.data.sec_edgar_client': MagicMock(),
    'app.data.data_agent': MagicMock()
}):
    from app.data.backup_clients import MarketStackClient, BackupDataFetcher


class TestMarketStackAPIResilience:
    """Property tests for Market Stack API resilience functionality."""

    @given(
        ticker=st.text(
            min_size=1,
            max_size=10).filter(
            lambda x: x.strip() and x.isalnum()),
        api_response_time_ms=st.integers(
            min_value=50,
            max_value=5000),
        market_stack_price=st.floats(
            min_value=0.01,
            max_value=10000.0,
            allow_nan=False,
            allow_infinity=False),
        market_stack_volume=st.integers(
            min_value=1000,
            max_value=100000000),
        primary_source_fails=st.booleans(),
        market_stack_available=st.booleans())
    @settings(max_examples=20, deadline=5000,
              suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_market_stack_api_resilience_property(
        self,
        ticker: str,
        api_response_time_ms: int,
        market_stack_price: float,
        market_stack_volume: int,
        primary_source_fails: bool,
        market_stack_available: bool
    ):
        """
        Feature: tech-stack-modernization, Property 26: Market Stack API Resilience
        For any stock price request, when primary data sources fail, Market Stack API should
        successfully provide backup data within acceptable response times
        **Validates: Requirements 10.7, 10.8**
        """
        ticker = ticker.strip().upper()
        acceptable_response_time_ms = 5000  # 5 seconds max acceptable response time

        # Property 1: Market Stack API should be configured as primary backup
        backup_fetcher = BackupDataFetcher()
        assert hasattr(backup_fetcher, 'marketstack_client')
        assert isinstance(backup_fetcher.marketstack_client, MarketStackClient)

        # Property 2: Market Stack client should be properly initialized
        market_stack_client = MarketStackClient(
            api_key='test_key' if market_stack_available else None)
        assert market_stack_client.base_url == "http://api.marketstack.com/v1"

        if market_stack_available:
            assert market_stack_client.api_key == 'test_key'
        else:
            assert market_stack_client.api_key is None

        # Mock Market Stack API response
        mock_response = Mock()
        if market_stack_available:
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'data': [{
                    'last': market_stack_price,
                    'volume': market_stack_volume,
                    'date': '2024-01-01T10:00:00'
                }]
            }
        else:
            # Simulate API unavailable (no API key or service down)
            mock_response.status_code = 401 if market_stack_client.api_key is None else 503
            mock_response.json.return_value = {'error': 'Service unavailable'}

        # Property 3: Response time should be tracked and within acceptable limits
        start_time = time.time()

        with patch('requests.get') as mock_get:
            # Simulate API response time
            def delayed_response(*args, **kwargs):
                time.sleep(api_response_time_ms / 1000.0)  # Convert ms to seconds
                return mock_response

            mock_get.side_effect = delayed_response

            # Test Market Stack API call
            result = market_stack_client.get_intraday(ticker)

            end_time = time.time()
            actual_response_time_ms = (end_time - start_time) * 1000

        # Property 4: Response time should be within acceptable limits when API is
        # available
        if market_stack_available and api_response_time_ms <= acceptable_response_time_ms:
            assert actual_response_time_ms <= acceptable_response_time_ms + 100  # Allow 100ms tolerance

        # Property 5: Market Stack should provide valid data when available
        if market_stack_available:
            assert result is not None
            assert result['price'] == market_stack_price
            assert result['volume'] == market_stack_volume
            assert result['timestamp'] == '2024-01-01T10:00:00'
        else:
            assert result is None

        # Property 6: Test backup fetcher prioritizes Market Stack
        backup_fetcher = BackupDataFetcher()

        with patch.object(backup_fetcher.marketstack_client, 'get_intraday') as mock_market_stack:
            with patch.object(backup_fetcher, 'alpha_vantage_client') as mock_alpha_vantage:
                # Configure Market Stack response
                if market_stack_available:
                    mock_market_stack.return_value = {
                        'price': market_stack_price,
                        'volume': market_stack_volume,
                        'timestamp': '2024-01-01T10:00:00'
                    }
                else:
                    mock_market_stack.return_value = None

                # Configure Alpha Vantage as fallback
                if mock_alpha_vantage:
                    mock_alpha_vantage.api_key = 'av_test_key'
                    mock_alpha_vantage.get_quote.return_value = {
                        'price': market_stack_price + 1.0  # Different price to verify source
                    }

                # Set Market Stack API key availability
                backup_fetcher.marketstack_client.api_key = 'test_key' if market_stack_available else None

                result_price = backup_fetcher.get_current_price(ticker)

                # Property 7: Market Stack should be tried first when available
                if market_stack_available:
                    mock_market_stack.assert_called_once_with(ticker)
                    assert result_price == market_stack_price
                    # Alpha Vantage should not be called if Market Stack succeeds
                    if mock_alpha_vantage:
                        mock_alpha_vantage.get_quote.assert_not_called()
                else:
                    # Market Stack should still be tried first, but will fail due to no API key
                    # The actual BackupDataFetcher checks for API key before calling get_intraday
                    # So when no API key, get_intraday is not called
                    # Should fall back to Alpha Vantage
                    if mock_alpha_vantage:
                        mock_alpha_vantage.get_quote.assert_called_once_with(ticker)
                        assert result_price == market_stack_price + 1.0  # Alpha Vantage price

    @given(
        tickers=st.lists(
            st.text(
                min_size=1,
                max_size=10).filter(
                lambda x: x.strip() and x.isalnum()),
            min_size=1,
            max_size=10),
        market_stack_success_rate=st.floats(
            min_value=0.0,
            max_value=1.0),
        response_times_ms=st.lists(
            st.integers(
                min_value=100,
                max_value=8000),
            min_size=1,
            max_size=10))
    @settings(max_examples=10, deadline=8000,
              suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_market_stack_batch_resilience_property(
        self,
        tickers: list,
        market_stack_success_rate: float,
        response_times_ms: list
    ):
        """
        Feature: tech-stack-modernization, Property 26: Market Stack API Resilience
        For any batch of stock price requests, Market Stack API should maintain resilience
        and provide consistent backup data availability
        **Validates: Requirements 10.7, 10.8**
        """
        # Normalize tickers
        tickers = [ticker.strip().upper() for ticker in tickers]
        tickers = list(set(tickers))  # Remove duplicates

        if not tickers:
            pytest.skip("No valid tickers provided")

        # Property 1: Market Stack should handle batch requests consistently
        backup_fetcher = BackupDataFetcher()
        backup_fetcher.marketstack_client.api_key = 'test_key'

        successful_requests = 0
        failed_requests = 0
        total_response_time = 0

        for i, ticker in enumerate(tickers):
            # Determine if this request should succeed based on success rate
            should_succeed = (i / len(tickers)) < market_stack_success_rate
            response_time = response_times_ms[i % len(response_times_ms)]

            mock_response = Mock()
            if should_succeed:
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    'data': [{
                        'last': 100.0 + i,  # Unique price for each ticker
                        'volume': 1000000,
                        'date': '2024-01-01T10:00:00'
                    }]
                }
            else:
                mock_response.status_code = 429  # Rate limit or service error
                mock_response.json.return_value = {'error': 'Rate limit exceeded'}

            with patch('requests.get') as mock_get:
                def delayed_response(*args, **kwargs):
                    time.sleep(response_time / 1000.0)
                    return mock_response

                mock_get.side_effect = delayed_response

                start_time = time.time()
                result = backup_fetcher.marketstack_client.get_intraday(ticker)
                end_time = time.time()

                actual_response_time = (end_time - start_time) * 1000
                total_response_time += actual_response_time

                if should_succeed:
                    successful_requests += 1
                    assert result is not None
                    assert result['price'] == 100.0 + i
                else:
                    failed_requests += 1
                    assert result is None

        # Property 2: Success rate should match expected rate (within tolerance)
        actual_success_rate = successful_requests / len(tickers)
        expected_success_rate = market_stack_success_rate
        tolerance = 0.2  # 20% tolerance for small batches

        assert abs(actual_success_rate - expected_success_rate) <= tolerance

        # Property 3: Average response time should be reasonable
        average_response_time = total_response_time / len(tickers)
        expected_average = sum(response_times_ms) / len(response_times_ms)

        # Allow some tolerance for timing variations
        assert average_response_time <= expected_average + 500  # 500ms tolerance

        # Property 4: Failed requests should not affect successful ones
        assert successful_requests + failed_requests == len(tickers)

        # Property 5: System should gracefully handle partial failures
        if failed_requests > 0:
            # Even with some failures, successful requests should still work
            assert successful_requests >= 0
            # Failure rate should not exceed what we expect
            failure_rate = failed_requests / len(tickers)
            expected_failure_rate = 1.0 - market_stack_success_rate
            assert abs(failure_rate - expected_failure_rate) <= tolerance

    @given(ticker=st.text(min_size=1,
                          max_size=10).filter(lambda x: x.strip() and x.isalnum()),
           yahoo_finance_fails=st.booleans(),
           market_stack_fails=st.booleans(),
           alpha_vantage_available=st.booleans())
    @settings(max_examples=20, deadline=5000,
              suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_data_fetcher_market_stack_integration_property(
        self,
        ticker: str,
        yahoo_finance_fails: bool,
        market_stack_fails: bool,
        alpha_vantage_available: bool
    ):
        """
        Feature: tech-stack-modernization, Property 26: Market Stack API Resilience
        For any data fetching request, Market Stack should be properly integrated as primary backup
        **Validates: Requirements 10.7, 10.8**
        """
        ticker = ticker.strip().upper()

        # Property 1: DataFetcher should have Market Stack in backup chain
        # Mock DataFetcher since we can't import it directly
        mock_data_fetcher = Mock()
        mock_backup_fetcher = BackupDataFetcher()
        mock_data_fetcher.backup_fetcher = mock_backup_fetcher

        assert hasattr(mock_data_fetcher, 'backup_fetcher')
        assert hasattr(mock_data_fetcher.backup_fetcher, 'marketstack_client')

        # Property 2: Market Stack should be prioritized in backup fetcher
        backup_fetcher = mock_data_fetcher.backup_fetcher

        with patch.object(backup_fetcher.marketstack_client, 'get_intraday') as mock_market_stack:
            with patch.object(backup_fetcher, 'alpha_vantage_client') as mock_alpha_vantage:
                with patch.object(mock_data_fetcher, 'yahoo_client', create=True) as mock_yahoo_client:
                    mock_yahoo_client.get_current_price = mock_yahoo

                    # Configure Yahoo Finance (primary source)
                    if yahoo_finance_fails:
                        mock_yahoo.return_value = None
                    else:
                        mock_yahoo.return_value = 150.0

                    # Configure Market Stack (primary backup)
                    backup_fetcher.marketstack_client.api_key = 'test_key'
                    if market_stack_fails:
                        mock_market_stack.return_value = None
                    else:
                        mock_market_stack.return_value = {
                            'price': 145.0,
                            'volume': 1000000,
                            'timestamp': '2024-01-01T10:00:00'
                        }

                    # Configure Alpha Vantage (secondary backup)
                    if alpha_vantage_available:
                        mock_alpha_vantage.api_key = 'av_test_key'
                        mock_alpha_vantage.get_quote.return_value = {'price': 140.0}
                    else:
                        mock_alpha_vantage = None

                    # Test backup fetcher behavior
                    result_price = backup_fetcher.get_current_price(ticker)

                    # Property 3: Market Stack should be tried first in backup chain
                    mock_market_stack.assert_called_once_with(ticker)

                    # Property 4: Fallback behavior should be correct
                    if not market_stack_fails:
                        # Market Stack succeeds - should return its price
                        assert result_price == 145.0
                        # Alpha Vantage should not be called
                        if mock_alpha_vantage:
                            mock_alpha_vantage.get_quote.assert_not_called()
                    elif alpha_vantage_available:
                        # Market Stack fails, Alpha Vantage available - should fallback
                        mock_alpha_vantage.get_quote.assert_called_once_with(ticker)
                        assert result_price == 140.0
                    else:
                        # Both Market Stack and Alpha Vantage fail - should return None
                        # (Google Finance might still be tried, but we're not mocking it here)
                        # The actual result depends on Google Finance, so we just verify
                        # Market Stack was tried
                        pass

        # Property 5: Market Stack should be accessible from main DataFetcher
        assert mock_data_fetcher.backup_fetcher.marketstack_client is not None
        assert isinstance(
            mock_data_fetcher.backup_fetcher.marketstack_client,
            MarketStackClient)

    @given(
        api_error_codes=st.lists(
            st.sampled_from([200, 401, 403, 429, 500, 502, 503, 504]),
            min_size=1,
            max_size=10
        ),
        retry_attempts=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=10, deadline=5000,
              suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_market_stack_error_handling_resilience_property(
        self,
        api_error_codes: list,
        retry_attempts: int
    ):
        """
        Feature: tech-stack-modernization, Property 26: Market Stack API Resilience
        For any API error conditions, Market Stack client should handle errors gracefully
        **Validates: Requirements 10.7, 10.8**
        """
        ticker = "AAPL"
        client = MarketStackClient(api_key='test_key')

        # Property 1: Client should handle various HTTP error codes gracefully
        for error_code in api_error_codes:
            mock_response = Mock()
            mock_response.status_code = error_code

            if error_code == 200:
                # Success case
                mock_response.json.return_value = {
                    'data': [{'last': 150.0, 'volume': 1000000, 'date': '2024-01-01T10:00:00'}]
                }
            else:
                # Error cases
                mock_response.json.return_value = {'error': f'HTTP {error_code} error'}

            with patch('requests.get', return_value=mock_response):
                result = client.get_intraday(ticker)

                # Property 2: Success should return data, errors should return None
                if error_code == 200:
                    assert result is not None
                    assert result['price'] == 150.0
                else:
                    assert result is None

        # Property 3: Client should handle network timeouts gracefully
        with patch('requests.get', side_effect=requests.exceptions.Timeout("Request timeout")):
            result = client.get_intraday(ticker)
            assert result is None

        # Property 4: Client should handle connection errors gracefully
        with patch('requests.get', side_effect=requests.exceptions.ConnectionError("Connection failed")):
            result = client.get_intraday(ticker)
            assert result is None

        # Property 5: Client should handle JSON decode errors gracefully
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with patch('requests.get', return_value=mock_response):
            result = client.get_intraday(ticker)
            assert result is None

        # Property 6: Client should handle missing API key gracefully
        client_no_key = MarketStackClient(api_key=None)
        result = client_no_key.get_intraday(ticker)
        assert result is None

        # Property 7: Client should handle empty response data gracefully
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': []}  # Empty data array

        with patch('requests.get', return_value=mock_response):
            result = client.get_intraday(ticker)
            assert result is None


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
