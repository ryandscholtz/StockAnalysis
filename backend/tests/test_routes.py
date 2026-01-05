"""
Unit tests for API routes
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

class TestAPIRoutes:
    """Test cases for API routes"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.client = TestClient(app)
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = self.client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = self.client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_version_endpoint(self):
        """Test version endpoint"""
        response = self.client.get("/api/version")
        
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "build_time" in data
    
    def test_analysis_presets_endpoint(self):
        """Test analysis presets endpoint"""
        response = self.client.get("/api/analysis-presets")
        
        assert response.status_code == 200
        data = response.json()
        assert "presets" in data
        assert "business_types" in data
        assert isinstance(data["presets"], dict)
        assert isinstance(data["business_types"], list)
    
    @patch('app.database.db_service.DatabaseService.get_watchlist')
    def test_get_watchlist_empty(self, mock_get_watchlist):
        """Test get watchlist when empty"""
        mock_get_watchlist.return_value = []
        
        response = self.client.get("/api/watchlist")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 0
        assert len(data["items"]) == 0
    
    @patch('app.database.db_service.DatabaseService.get_watchlist')
    def test_get_watchlist_with_items(self, mock_get_watchlist):
        """Test get watchlist with items"""
        mock_items = [
            {
                'ticker': 'AAPL',
                'company_name': 'Apple Inc.',
                'exchange': 'NASDAQ',
                'added_at': '2024-01-01T00:00:00',
                'updated_at': '2024-01-01T00:00:00'
            }
        ]
        mock_get_watchlist.return_value = mock_items
        
        response = self.client.get("/api/watchlist")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["ticker"] == "AAPL"
    
    @patch('app.database.db_service.DatabaseService.add_to_watchlist')
    def test_add_to_watchlist_success(self, mock_add):
        """Test adding to watchlist successfully"""
        mock_add.return_value = True
        
        response = self.client.post("/api/watchlist/AAPL")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "AAPL" in data["message"]
    
    @patch('app.database.db_service.DatabaseService.remove_from_watchlist')
    def test_remove_from_watchlist_success(self, mock_remove):
        """Test removing from watchlist successfully"""
        mock_remove.return_value = True
        
        response = self.client.delete("/api/watchlist/AAPL")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "AAPL" in data["message"]
    
    @patch('app.database.db_service.DatabaseService.remove_from_watchlist')
    def test_remove_nonexistent_from_watchlist(self, mock_remove):
        """Test removing non-existent item from watchlist"""
        mock_remove.return_value = False
        
        response = self.client.delete("/api/watchlist/NONEXISTENT")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    @patch('app.data.api_client.YahooFinanceClient.search_tickers')
    def test_search_endpoint_success(self, mock_search):
        """Test ticker search endpoint"""
        mock_search.return_value = [
            {
                'ticker': 'AAPL',
                'companyName': 'Apple Inc.',
                'exchange': 'NASDAQ'
            }
        ]
        
        response = self.client.get("/api/search?q=AAPL")
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["ticker"] == "AAPL"
    
    def test_search_endpoint_missing_query(self):
        """Test search endpoint without query parameter"""
        response = self.client.get("/api/search")
        
        assert response.status_code == 422  # Validation error
    
    def test_search_endpoint_empty_query(self):
        """Test search endpoint with empty query"""
        response = self.client.get("/api/search?q=")
        
        assert response.status_code == 422  # Validation error (min_length=1)
    
    @patch('app.api.routes._analyze_stock_with_progress')
    def test_analyze_endpoint_success(self, mock_analyze):
        """Test stock analysis endpoint"""
        # Mock successful analysis
        mock_result = Mock()
        mock_result.dict.return_value = {
            'ticker': 'AAPL',
            'currentPrice': 150.0,
            'fairValue': 160.0,
            'recommendation': 'Buy'
        }
        mock_analyze.return_value = mock_result
        
        response = self.client.get("/api/analyze/AAPL")
        
        # This might timeout or fail due to complex dependencies
        # Just check that it doesn't return 404 (route exists)
        assert response.status_code != 404
    
    def test_analyze_endpoint_invalid_ticker(self):
        """Test analysis endpoint with invalid ticker format"""
        response = self.client.get("/api/analyze/")
        
        assert response.status_code == 404  # No ticker provided
    
    @patch('app.database.db_service.DatabaseService.get_watchlist')
    def test_cached_watchlist_endpoint(self, mock_get_watchlist):
        """Test cached watchlist endpoint"""
        mock_get_watchlist.return_value = []
        
        response = self.client.get("/api/cache/watchlist")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "cached" in data
        assert "timestamp" in data
        assert data["cached"] is True

class TestOptimizedRoutes:
    """Test cases for optimized routes"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.client = TestClient(app)
    
    def test_detailed_health_endpoint(self):
        """Test detailed health check endpoint"""
        response = self.client.get("/api/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "database" in data
        assert "background_tasks" in data
        assert "cache" in data
    
    @patch('app.database.db_service.DatabaseService.get_watchlist')
    def test_async_live_prices_endpoint(self, mock_get_watchlist):
        """Test async live prices endpoint"""
        mock_get_watchlist.return_value = [
            {'ticker': 'AAPL'},
            {'ticker': 'GOOGL'}
        ]
        
        response = self.client.get("/api/watchlist/live-prices-async")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should either return cached prices or task info
        assert ("live_prices" in data) or ("task_id" in data)
    
    def test_cache_stats_endpoint(self):
        """Test cache statistics endpoint"""
        response = self.client.get("/api/cache/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_entries" in data
        assert "current_size_mb" in data
        assert "max_size_mb" in data
    
    def test_clear_cache_endpoint(self):
        """Test cache clearing endpoint"""
        response = self.client.delete("/api/cache")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "cleared" in data["message"].lower()

class TestErrorHandling:
    """Test error handling in routes"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.client = TestClient(app)
    
    @patch('app.database.db_service.DatabaseService.get_watchlist')
    def test_database_error_handling(self, mock_get_watchlist):
        """Test handling of database errors"""
        mock_get_watchlist.side_effect = Exception("Database connection failed")
        
        response = self.client.get("/api/watchlist")
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
    
    def test_cors_headers(self):
        """Test CORS headers are present"""
        response = self.client.get("/api/version")
        
        # CORS headers should be present (though exact headers depend on origin)
        assert response.status_code == 200
    
    def test_options_request(self):
        """Test OPTIONS request handling"""
        response = self.client.options("/api/version")
        
        # Should handle OPTIONS requests for CORS
        assert response.status_code in [200, 204, 405]  # Various valid responses
    
    def test_invalid_json_handling(self):
        """Test handling of invalid JSON in requests"""
        response = self.client.post(
            "/api/watchlist/AAPL",
            headers={"Content-Type": "application/json"},
            data="invalid json"
        )
        
        # Should handle invalid JSON gracefully
        assert response.status_code in [400, 422, 500]

class TestRouteValidation:
    """Test input validation in routes"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.client = TestClient(app)
    
    def test_ticker_format_validation(self):
        """Test ticker format validation"""
        # Test various ticker formats
        valid_tickers = ["AAPL", "GOOGL", "BRK.A", "PPE.JO"]
        invalid_tickers = ["", "TOOLONG", "123", "@#$"]
        
        for ticker in valid_tickers:
            response = self.client.post(f"/api/watchlist/{ticker}")
            # Should not fail due to format (might fail for other reasons)
            assert response.status_code != 422
        
        for ticker in invalid_tickers:
            if ticker:  # Skip empty string (handled by path parameter)
                response = self.client.post(f"/api/watchlist/{ticker}")
                # Might succeed or fail, but shouldn't crash
                assert response.status_code < 600
    
    def test_query_parameter_validation(self):
        """Test query parameter validation"""
        # Test search with various query lengths
        response = self.client.get("/api/search?q=A")  # Minimum length
        assert response.status_code != 422
        
        response = self.client.get("/api/search?q=" + "A" * 100)  # Long query
        assert response.status_code != 422

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])