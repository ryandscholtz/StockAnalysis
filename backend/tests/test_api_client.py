"""
Unit tests for API client functionality
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.api_client import YahooFinanceClient

class TestYahooFinanceClient:
    """Test cases for YahooFinanceClient"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.client = YahooFinanceClient()
    
    def test_client_initialization(self):
        """Test client initialization"""
        assert self.client.session is None
        assert isinstance(self.client, YahooFinanceClient)
    
    @patch('yfinance.Ticker')
    def test_get_ticker_success(self, mock_ticker_class):
        """Test successful ticker creation"""
        mock_ticker = Mock()
        mock_ticker.fast_info = Mock()
        mock_ticker_class.return_value = mock_ticker
        
        result = self.client.get_ticker("AAPL")
        
        assert result == mock_ticker
        mock_ticker_class.assert_called_once_with("AAPL")
    
    @patch('yfinance.Ticker')
    def test_get_ticker_with_exception(self, mock_ticker_class):
        """Test ticker creation with exception"""
        mock_ticker_class.side_effect = Exception("Network error")
        
        result = self.client.get_ticker("INVALID")
        
        assert result is None
    
    def test_get_current_price_with_mock_ticker(self):
        """Test get_current_price with mocked ticker"""
        # Create mock ticker with history data
        mock_ticker = Mock()
        
        # Mock successful history call with proper pandas-like behavior
        mock_close_series = Mock()
        mock_close_series.iloc = Mock()
        mock_close_series.iloc.__getitem__ = Mock(return_value=150.25)
        
        mock_history = Mock()
        mock_history.empty = False
        mock_history.__getitem__ = Mock(return_value=mock_close_series)
        
        mock_ticker.history.return_value = mock_history
        
        result = self.client.get_current_price(mock_ticker)
        
        # Should get price from history
        assert result == 150.25
    
    def test_get_current_price_empty_history(self):
        """Test get_current_price with empty history"""
        mock_ticker = Mock()
        
        # Mock empty history
        mock_history = Mock()
        mock_history.empty = True
        mock_ticker.history.return_value = mock_history
        
        # Mock fast_info failure
        mock_ticker.fast_info = None
        
        # Mock info failure
        mock_ticker.info = {}
        
        result = self.client.get_current_price(mock_ticker)
        
        assert result is None
    
    @patch('app.data.api_client.YahooFinanceClient._try_yahoo_finance')
    @patch('app.data.api_client.YahooFinanceClient._build_successful_response')
    def test_get_quote_success(self, mock_build_response, mock_try_yahoo):
        """Test successful quote retrieval"""
        # Setup mock for Yahoo Finance attempt
        mock_try_yahoo.return_value = [{
            'api': 'Yahoo Finance',
            'method': 'yf.Ticker() creation',
            'status': 'success',
            'price': 150.25,
            'details': 'Successfully retrieved price'
        }]
        
        # Setup mock for successful response building
        expected_response = {
            'success': True,
            'price': 150.25,
            'company_name': 'Apple Inc.',
            'symbol': 'AAPL',
            'api_attempts': mock_try_yahoo.return_value
        }
        mock_build_response.return_value = expected_response
        
        result = self.client.get_quote("AAPL")
        
        assert result is not None
        assert result['success'] is True
        assert result['price'] == 150.25
        assert result['company_name'] == 'Apple Inc.'
        assert result['symbol'] == 'AAPL'
        assert 'api_attempts' in result
    
    @patch('app.data.api_client.YahooFinanceClient._try_yahoo_finance')
    @patch('app.data.api_client.YahooFinanceClient._build_failure_response')
    def test_get_quote_ticker_creation_failure(self, mock_build_failure, mock_try_yahoo):
        """Test quote retrieval when ticker creation fails"""
        # Yahoo Finance fails
        mock_try_yahoo.return_value = [{
            'api': 'Yahoo Finance',
            'method': 'yf.Ticker() creation',
            'status': 'failed',
            'error': 'Could not create ticker object',
            'details': 'yf.Ticker(INVALID) returned None - symbol may not exist or be invalid'
        }]
        
        # Mock failure response
        expected_response = {
            'success': False,
            'error': 'All APIs failed to retrieve quote',
            'symbol': 'INVALID',
            'api_attempts': mock_try_yahoo.return_value
        }
        mock_build_failure.return_value = expected_response
        
        result = self.client.get_quote("INVALID")
        
        assert result is not None
        assert 'error' in result
        assert result['symbol'] == "INVALID"
        assert 'api_attempts' in result
    
    @patch('app.data.api_client.YahooFinanceClient._try_yahoo_finance')
    @patch('app.data.api_client.YahooFinanceClient._try_backup_apis')
    @patch('app.data.api_client.YahooFinanceClient._build_successful_response')
    def test_get_quote_with_backup_apis(self, mock_build_response, mock_backup, mock_yahoo):
        """Test quote retrieval falling back to backup APIs"""
        # Yahoo Finance fails
        mock_yahoo.return_value = [
            {
                'api': 'Yahoo Finance',
                'method': 'ticker.history',
                'status': 'failed',
                'error': 'Rate limited'
            }
        ]
        
        # Backup API succeeds
        mock_backup.return_value = [
            {
                'api': 'Alpha Vantage',
                'method': 'get_quote',
                'status': 'success',
                'price': 145.50,
                'company_name': 'Apple Inc.'
            }
        ]
        
        # Mock successful response
        expected_response = {
            'success': True,
            'price': 145.50,
            'company_name': 'Apple Inc.',
            'symbol': 'AAPL',
            'api_attempts': mock_yahoo.return_value + mock_backup.return_value
        }
        mock_build_response.return_value = expected_response
        
        result = self.client.get_quote("AAPL")
        
        assert result is not None
        assert result['success'] is True
        assert result['price'] == 145.50
    
    @patch('requests.get')
    def test_search_tickers_empty_query(self, mock_get):
        """Test ticker search with empty results"""
        # Mock empty response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'quotes': []}
        mock_get.return_value = mock_response
        
        result = self.client.search_tickers("NONEXISTENTCOMPANY12345")
        
        # Should return a list (even if empty)
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_search_tickers_valid_format(self):
        """Test that search_tickers returns properly formatted results"""
        # Mock the requests.get call
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'quotes': [
                    {
                        'symbol': 'AAPL',
                        'longname': 'Apple Inc.',
                        'exchange': 'NASDAQ',
                        'quoteType': 'EQUITY'
                    }
                ]
            }
            mock_get.return_value = mock_response
            
            result = self.client.search_tickers("AAPL")
            
            assert isinstance(result, list)
            if len(result) > 0:
                item = result[0]
                assert 'ticker' in item
                assert 'companyName' in item
                assert 'exchange' in item

class TestAPIClientErrorHandling:
    """Test error handling in API client"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.client = YahooFinanceClient()
    
    def test_get_current_price_with_tracking_structure(self):
        """Test that _get_current_price_with_tracking returns proper structure"""
        mock_ticker = Mock()
        
        # Mock all methods to fail
        mock_ticker.history.side_effect = Exception("API Error")
        mock_ticker.fast_info = None
        mock_ticker.info = {}
        
        result = self.client._get_current_price_with_tracking(mock_ticker, "TEST")
        
        # Should return list of attempts
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Each attempt should have required fields
        for attempt in result:
            assert 'api' in attempt
            assert 'method' in attempt
            assert 'status' in attempt
            assert 'details' in attempt
    
    def test_build_failure_response(self):
        """Test failure response building"""
        mock_attempts = [
            {
                'api': 'Yahoo Finance',
                'method': 'test_method',
                'status': 'failed',
                'error': 'Test error'
            }
        ]
        
        result = self.client._build_failure_response("TEST", mock_attempts)
        
        assert 'error' in result
        assert 'error_detail' in result
        assert 'symbol' in result
        assert 'api_attempts' in result
        assert result['symbol'] == "TEST"
    
    def test_build_successful_response(self):
        """Test successful response building"""
        mock_attempts = [
            {
                'api': 'Yahoo Finance',
                'method': 'test_method',
                'status': 'success'
            }
        ]
        
        result = self.client._build_successful_response("TEST", 150.25, mock_attempts)
        
        assert result['price'] == 150.25
        assert result['symbol'] == "TEST"
        assert result['success'] is True
        assert 'api_attempts' in result
        assert 'error_detail' in result

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])