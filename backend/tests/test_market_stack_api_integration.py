"""
Unit tests for Market Stack API integration
Tests that Market Stack API is configured as primary backup data source
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.backup_clients import MarketStackClient, BackupDataFetcher
from app.data.data_fetcher import DataFetcher


class TestMarketStackClient:
    """Test cases for MarketStackClient"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.client = MarketStackClient()
    
    def test_client_initialization_with_api_key(self):
        """Test client initialization with API key"""
        with patch.dict(os.environ, {'MARKETSTACK_API_KEY': 'test_key'}):
            client = MarketStackClient()
            assert client.api_key == 'test_key'
            assert client.base_url == "http://api.marketstack.com/v1"
    
    def test_client_initialization_without_api_key(self):
        """Test client initialization without API key"""
        with patch.dict(os.environ, {}, clear=True):
            client = MarketStackClient()
            assert client.api_key is None
    
    @patch('requests.get')
    def test_make_request_success(self, mock_get):
        """Test successful API request"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{'last': 150.25, 'volume': 1000000, 'date': '2024-01-01T10:00:00'}]
        }
        mock_get.return_value = mock_response
        
        client = MarketStackClient(api_key='test_key')
        result = client._make_request('intraday/latest', {'symbols': 'AAPL'})
        
        assert result is not None
        assert 'data' in result
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_make_request_rate_limit(self, mock_get):
        """Test API request with rate limit response"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response
        
        client = MarketStackClient(api_key='test_key')
        result = client._make_request('intraday/latest', {'symbols': 'AAPL'})
        
        assert result is None
    
    @patch('requests.get')
    def test_make_request_without_api_key(self, mock_get):
        """Test API request without API key"""
        client = MarketStackClient(api_key=None)
        result = client._make_request('intraday/latest', {'symbols': 'AAPL'})
        
        assert result is None
        mock_get.assert_not_called()
    
    @patch('requests.get')
    def test_get_intraday_success(self, mock_get):
        """Test successful intraday data retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{'last': 150.25, 'volume': 1000000, 'date': '2024-01-01T10:00:00'}]
        }
        mock_get.return_value = mock_response
        
        client = MarketStackClient(api_key='test_key')
        result = client.get_intraday('AAPL')
        
        assert result is not None
        assert result['price'] == 150.25
        assert result['volume'] == 1000000
        assert result['timestamp'] == '2024-01-01T10:00:00'
    
    @patch('requests.get')
    def test_get_intraday_no_data(self, mock_get):
        """Test intraday data retrieval with no data"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': []}
        mock_get.return_value = mock_response
        
        client = MarketStackClient(api_key='test_key')
        result = client.get_intraday('INVALID')
        
        assert result is None


class TestBackupDataFetcherMarketStackPriority:
    """Test that BackupDataFetcher prioritizes Market Stack API"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.fetcher = BackupDataFetcher()
    
    def test_market_stack_client_initialized(self):
        """Test that Market Stack client is initialized in BackupDataFetcher"""
        assert hasattr(self.fetcher, 'marketstack_client')
        assert isinstance(self.fetcher.marketstack_client, MarketStackClient)
    
    @patch.object(MarketStackClient, 'get_intraday')
    @patch.object(MarketStackClient, '__init__', return_value=None)
    def test_get_current_price_market_stack_first(self, mock_init, mock_get_intraday):
        """Test that get_current_price tries Market Stack first"""
        # Setup Market Stack client with API key
        fetcher = BackupDataFetcher()
        fetcher.marketstack_client.api_key = 'test_key'
        
        # Mock successful Market Stack response
        mock_get_intraday.return_value = {'price': 150.25}
        
        result = fetcher.get_current_price('AAPL')
        
        assert result == 150.25
        mock_get_intraday.assert_called_once_with('AAPL')
    
    @patch.object(MarketStackClient, 'get_intraday')
    def test_get_current_price_market_stack_priority_over_alpha_vantage(self, mock_get_intraday):
        """Test that Market Stack is prioritized over Alpha Vantage"""
        # Setup Market Stack client with API key
        self.fetcher.marketstack_client.api_key = 'test_key'
        
        # Mock successful Market Stack response
        mock_get_intraday.return_value = {'price': 150.25}
        
        # Mock Alpha Vantage client (should not be called)
        with patch.object(self.fetcher, 'alpha_vantage_client') as mock_av:
            mock_av.api_key = 'av_test_key'
            mock_av.get_quote.return_value = {'price': 145.00}  # Different price
            
            result = self.fetcher.get_current_price('AAPL')
            
            # Should get Market Stack price, not Alpha Vantage
            assert result == 150.25
            mock_get_intraday.assert_called_once_with('AAPL')
            # Alpha Vantage should not be called since Market Stack succeeded
            mock_av.get_quote.assert_not_called()
    
    @patch.object(MarketStackClient, 'get_intraday')
    def test_get_current_price_fallback_when_market_stack_fails(self, mock_get_intraday):
        """Test fallback to other sources when Market Stack fails"""
        # Setup Market Stack client with API key but failing response
        self.fetcher.marketstack_client.api_key = 'test_key'
        mock_get_intraday.return_value = None  # Market Stack fails
        
        # Mock Alpha Vantage client as fallback
        with patch.object(self.fetcher, 'alpha_vantage_client') as mock_av:
            mock_av.api_key = 'av_test_key'
            mock_av.get_quote.return_value = {'price': 145.00}
            
            result = self.fetcher.get_current_price('AAPL')
            
            # Should get Alpha Vantage price as fallback
            assert result == 145.00
            mock_get_intraday.assert_called_once_with('AAPL')
            mock_av.get_quote.assert_called_once_with('AAPL')
    
    @patch.object(MarketStackClient, 'get_intraday')
    def test_get_quote_with_metrics_market_stack_first(self, mock_get_intraday):
        """Test that get_quote_with_metrics tries Market Stack first"""
        # Setup Market Stack client with API key
        self.fetcher.marketstack_client.api_key = 'test_key'
        
        # Mock successful Market Stack response
        mock_get_intraday.return_value = {'price': 150.25, 'volume': 1000000}
        
        result = self.fetcher.get_quote_with_metrics('AAPL')
        
        assert result is not None
        assert result['price'] == 150.25
        mock_get_intraday.assert_called_once_with('AAPL')


class TestDataFetcherMarketStackIntegration:
    """Test Market Stack integration in main DataFetcher"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.data_fetcher = DataFetcher()
    
    def test_backup_fetcher_has_market_stack(self):
        """Test that DataFetcher's backup_fetcher includes Market Stack"""
        assert hasattr(self.data_fetcher, 'backup_fetcher')
        assert hasattr(self.data_fetcher.backup_fetcher, 'marketstack_client')
        assert isinstance(self.data_fetcher.backup_fetcher.marketstack_client, MarketStackClient)
    
    def test_data_fetcher_uses_market_stack_in_backup_sources(self):
        """Test that DataFetcher's backup sources include Market Stack as primary"""
        # Verify that the backup fetcher is configured with Market Stack
        assert hasattr(self.data_fetcher.backup_fetcher, 'marketstack_client')
        assert isinstance(self.data_fetcher.backup_fetcher.marketstack_client, MarketStackClient)
        
        # Test that Market Stack is called first in backup sources
        with patch.object(self.data_fetcher.backup_fetcher.marketstack_client, 'get_intraday') as mock_market_stack:
            mock_market_stack.return_value = {'price': 150.25}
            
            # Set API key to ensure Market Stack is tried
            self.data_fetcher.backup_fetcher.marketstack_client.api_key = 'test_key'
            
            result = self.data_fetcher.backup_fetcher.get_current_price('AAPL')
            
            # Should get Market Stack price
            assert result == 150.25
            mock_market_stack.assert_called_once_with('AAPL')


class TestMarketStackAPIConfiguration:
    """Test Market Stack API configuration and environment setup"""
    
    def test_market_stack_api_key_environment_variable(self):
        """Test that Market Stack client reads from MARKETSTACK_API_KEY environment variable"""
        test_key = 'test_marketstack_key_12345'
        
        with patch.dict(os.environ, {'MARKETSTACK_API_KEY': test_key}):
            client = MarketStackClient()
            assert client.api_key == test_key
    
    def test_market_stack_api_key_parameter_override(self):
        """Test that API key parameter overrides environment variable"""
        env_key = 'env_key'
        param_key = 'param_key'
        
        with patch.dict(os.environ, {'MARKETSTACK_API_KEY': env_key}):
            client = MarketStackClient(api_key=param_key)
            assert client.api_key == param_key
    
    def test_market_stack_base_url_configuration(self):
        """Test that Market Stack client uses correct base URL"""
        client = MarketStackClient()
        assert client.base_url == "http://api.marketstack.com/v1"
    
    @patch('app.data.backup_clients.logger')
    def test_market_stack_logging_on_success(self, mock_logger):
        """Test that successful Market Stack calls are logged"""
        fetcher = BackupDataFetcher()
        fetcher.marketstack_client.api_key = 'test_key'
        
        with patch.object(fetcher.marketstack_client, 'get_intraday') as mock_get_intraday:
            mock_get_intraday.return_value = {'price': 150.25}
            
            result = fetcher.get_current_price('AAPL')
            
            assert result == 150.25
            # Check that success is logged
            mock_logger.info.assert_called_with("Got price from MarketStack: 150.25")
    
    @patch('app.data.backup_clients.logger')
    def test_market_stack_logging_on_failure(self, mock_logger):
        """Test that failed Market Stack calls are logged"""
        fetcher = BackupDataFetcher()
        fetcher.marketstack_client.api_key = 'test_key'
        
        with patch.object(fetcher.marketstack_client, 'get_intraday') as mock_get_intraday:
            mock_get_intraday.return_value = None  # API failure
            
            # Mock other clients to also fail so we can see the Market Stack failure log
            with patch.object(fetcher, 'alpha_vantage_client', None):
                with patch.object(fetcher, 'fmp_client') as mock_fmp:
                    mock_fmp.api_key = None  # No API key
                    with patch.object(fetcher.google_finance_client, 'get_current_price') as mock_google:
                        mock_google.return_value = None  # Google Finance also fails
                        
                        result = fetcher.get_current_price('AAPL')
                        
                        assert result is None
                        # Check that failure is logged
                        mock_logger.debug.assert_any_call("MarketStack returned no price for AAPL")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])