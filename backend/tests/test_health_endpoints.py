"""
Unit tests for health check and metrics endpoints
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import json

from app.core.app import create_app


class TestHealthEndpoints:
    """Test health check and metrics endpoints functionality"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        app = create_app()
        return TestClient(app)
    
    def test_root_endpoint_returns_api_info(self, client):
        """
        Test that root endpoint returns expected API information
        Requirements: 1.6
        """
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "message" in data
        assert "version" in data
        assert "build_timestamp" in data
        assert "status" in data
        
        # Verify values
        assert data["message"] == "Stock Analysis API"
        assert data["version"] == "2.0.0"
        assert data["status"] == "healthy"
        
        # Verify build timestamp format (yymmdd-hh:mm)
        build_timestamp = data["build_timestamp"]
        assert len(build_timestamp) == 11  # yymmdd-hh:mm format
        assert build_timestamp[6] == "-"
        assert build_timestamp[9] == ":"
    
    def test_health_check_endpoint_returns_healthy_status(self, client):
        """
        Test that health check endpoint returns healthy status with proper format
        Requirements: 1.6
        """
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "build_timestamp" in data
        
        # Verify values
        assert data["status"] == "healthy"
        assert data["version"] == "2.0.0"
        
        # Verify timestamp is ISO format with Z suffix
        timestamp = data["timestamp"]
        assert timestamp.endswith("Z")
        
        # Should be parseable as ISO datetime
        parsed_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert isinstance(parsed_time, datetime)
    
    def test_metrics_endpoint_returns_basic_metrics(self, client):
        """
        Test that metrics endpoint returns basic metrics structure
        Requirements: 1.6
        """
        response = client.get("/metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields (basic implementation)
        assert "status" in data
        assert "uptime" in data
        assert "requests_total" in data
        assert "errors_total" in data
        
        # Verify status is healthy
        assert data["status"] == "healthy"
        
        # Note: In basic implementation, these are "unknown"
        # In production, these would be actual metrics
        assert data["uptime"] == "unknown"
        assert data["requests_total"] == "unknown"
        assert data["errors_total"] == "unknown"
    
    def test_health_endpoints_have_correlation_id_headers(self, client):
        """
        Test that health endpoints include correlation ID headers
        Requirements: 1.6
        """
        # Test root endpoint
        response = client.get("/")
        assert "x-correlation-id" in response.headers
        
        # Test health endpoint
        response = client.get("/health")
        assert "x-correlation-id" in response.headers
        
        # Test metrics endpoint
        response = client.get("/metrics")
        assert "x-correlation-id" in response.headers
    
    def test_health_endpoints_with_custom_correlation_id(self, client):
        """
        Test that health endpoints preserve custom correlation ID
        Requirements: 1.6
        """
        custom_correlation_id = "test-correlation-123"
        headers = {"x-correlation-id": custom_correlation_id}
        
        # Test root endpoint
        response = client.get("/", headers=headers)
        assert response.headers["x-correlation-id"] == custom_correlation_id
        
        # Test health endpoint
        response = client.get("/health", headers=headers)
        assert response.headers["x-correlation-id"] == custom_correlation_id
        
        # Test metrics endpoint
        response = client.get("/metrics", headers=headers)
        assert response.headers["x-correlation-id"] == custom_correlation_id
    
    def test_health_endpoints_have_security_headers(self, client):
        """
        Test that health endpoints include security headers
        Requirements: 1.6
        """
        response = client.get("/health")
        
        # Verify security headers are present
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    
    def test_health_endpoints_content_type(self, client):
        """
        Test that health endpoints return proper content type
        Requirements: 1.6
        """
        response = client.get("/health")
        
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")
    
    def test_health_endpoints_response_time(self, client):
        """
        Test that health endpoints respond quickly (basic performance test)
        Requirements: 1.6
        """
        import time
        
        start_time = time.time()
        response = client.get("/health")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Health check should be very fast (under 1 second)
        assert response_time < 1.0
        assert response.status_code == 200
    
    def test_health_check_json_structure_validity(self, client):
        """
        Test that health check returns valid JSON structure
        Requirements: 1.6
        """
        response = client.get("/health")
        
        # Should be valid JSON
        data = response.json()
        
        # Should be serializable back to JSON
        json_str = json.dumps(data)
        reparsed = json.loads(json_str)
        
        assert reparsed == data
    
    def test_multiple_health_check_requests_consistency(self, client):
        """
        Test that multiple health check requests return consistent structure
        Requirements: 1.6
        """
        responses = []
        
        # Make multiple requests
        for _ in range(5):
            response = client.get("/health")
            responses.append(response)
        
        # All should be successful
        for response in responses:
            assert response.status_code == 200
        
        # All should have the same structure
        first_data = responses[0].json()
        required_keys = set(first_data.keys())
        
        for response in responses[1:]:
            data = response.json()
            assert set(data.keys()) == required_keys
            assert data["status"] == "healthy"
            assert data["version"] == "2.0.0"
    
    def test_health_endpoints_handle_options_request(self, client):
        """
        Test that health endpoints handle OPTIONS requests (CORS preflight)
        Requirements: 1.6
        """
        # OPTIONS request should be handled by CORS middleware
        response = client.options("/health")
        
        # Should not return 405 Method Not Allowed
        # Exact status depends on CORS configuration
        assert response.status_code != 405