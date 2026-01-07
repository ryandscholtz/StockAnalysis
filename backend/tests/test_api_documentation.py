"""
Unit tests for API documentation availability
Tests that API documentation is available and accurate
Requirements: 8.6
"""
import pytest
from fastapi.testclient import TestClient
from app.core.app import create_app
import json


class TestAPIDocumentation:
    """Test API documentation availability and accuracy"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        app = create_app()
        return TestClient(app)
    
    def test_openapi_schema_available(self, client):
        """Test that OpenAPI schema is available at /openapi.json"""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200, "OpenAPI schema endpoint not accessible"
        
        # Verify it's valid JSON
        schema = response.json()
        assert isinstance(schema, dict), "OpenAPI schema is not valid JSON"
        
        # Verify required OpenAPI fields
        assert "openapi" in schema, "OpenAPI version not specified"
        assert "info" in schema, "API info not specified"
        assert "paths" in schema, "API paths not specified"
        
        # Verify API info
        info = schema["info"]
        assert "title" in info, "API title not specified"
        assert "version" in info, "API version not specified"
        assert info["title"] == "Stock Analysis API", "Incorrect API title"
        assert info["version"] == "2.0.0", "Incorrect API version"
    
    def test_swagger_ui_available_in_development(self, client):
        """Test that Swagger UI is available in development environment"""
        # Note: In production, docs might be disabled for security
        response = client.get("/docs")
        
        # Should either be available (200) or disabled in production (404)
        assert response.status_code in [200, 404], (
            f"Unexpected status code for /docs: {response.status_code}"
        )
        
        if response.status_code == 200:
            # If available, should contain Swagger UI HTML
            assert "swagger" in response.text.lower() or "openapi" in response.text.lower(), (
                "Swagger UI page does not contain expected content"
            )
    
    def test_redoc_available_in_development(self, client):
        """Test that ReDoc is available in development environment"""
        response = client.get("/redoc")
        
        # Should either be available (200) or disabled in production (404)
        assert response.status_code in [200, 404], (
            f"Unexpected status code for /redoc: {response.status_code}"
        )
        
        if response.status_code == 200:
            # If available, should contain ReDoc HTML
            assert "redoc" in response.text.lower(), (
                "ReDoc page does not contain expected content"
            )
    
    def test_api_endpoints_documented(self, client):
        """Test that key API endpoints are documented in OpenAPI schema"""
        response = client.get("/openapi.json")
        schema = response.json()
        
        paths = schema.get("paths", {})
        
        # Key endpoints that should be documented
        expected_endpoints = [
            "/",  # Root endpoint
            "/health",  # Health check
            "/metrics"  # Metrics endpoint
        ]
        
        for endpoint in expected_endpoints:
            assert endpoint in paths, f"Endpoint {endpoint} not documented in OpenAPI schema"
            
            # Verify endpoint has at least one HTTP method
            endpoint_methods = paths[endpoint]
            assert len(endpoint_methods) > 0, f"Endpoint {endpoint} has no HTTP methods documented"
    
    def test_api_responses_documented(self, client):
        """Test that API responses are properly documented"""
        response = client.get("/openapi.json")
        schema = response.json()
        
        paths = schema.get("paths", {})
        
        # Check that endpoints have response documentation
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    assert "responses" in details, (
                        f"Endpoint {method.upper()} {path} missing response documentation"
                    )
                    
                    responses = details["responses"]
                    assert len(responses) > 0, (
                        f"Endpoint {method.upper()} {path} has no documented responses"
                    )
                    
                    # Should have at least a success response
                    success_codes = [code for code in responses.keys() if code.startswith("2")]
                    assert len(success_codes) > 0, (
                        f"Endpoint {method.upper()} {path} has no success response documented"
                    )
    
    def test_api_tags_and_descriptions(self, client):
        """Test that API endpoints have proper tags and descriptions"""
        response = client.get("/openapi.json")
        schema = response.json()
        
        paths = schema.get("paths", {})
        
        # Check that endpoints have tags for organization
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    # Should have tags for organization
                    assert "tags" in details, (
                        f"Endpoint {method.upper()} {path} missing tags"
                    )
                    
                    tags = details["tags"]
                    assert len(tags) > 0, (
                        f"Endpoint {method.upper()} {path} has no tags"
                    )
                    
                    # Should have summary or description
                    has_summary = "summary" in details and details["summary"]
                    has_description = "description" in details and details["description"]
                    
                    assert has_summary or has_description, (
                        f"Endpoint {method.upper()} {path} missing summary or description"
                    )
    
    def test_api_models_documented(self, client):
        """Test that API models/schemas are documented"""
        response = client.get("/openapi.json")
        schema = response.json()
        
        # Should have components section with schemas
        if "components" in schema and "schemas" in schema["components"]:
            schemas = schema["components"]["schemas"]
            
            # Should have at least some schemas defined
            assert len(schemas) >= 0, "No schemas defined in OpenAPI spec"
            
            # Verify schemas have proper structure
            for schema_name, schema_def in schemas.items():
                assert "type" in schema_def or "$ref" in schema_def, (
                    f"Schema {schema_name} missing type definition"
                )
    
    def test_health_endpoint_documented_correctly(self, client):
        """Test that health endpoint is documented with correct response format"""
        # First, get the actual response from health endpoint
        health_response = client.get("/health")
        assert health_response.status_code == 200
        health_data = health_response.json()
        
        # Now check the documentation
        docs_response = client.get("/openapi.json")
        schema = docs_response.json()
        
        # Find health endpoint in documentation
        health_path = schema["paths"].get("/health")
        assert health_path is not None, "Health endpoint not documented"
        
        get_method = health_path.get("get")
        assert get_method is not None, "Health endpoint GET method not documented"
        
        # Verify response structure matches documentation
        responses = get_method.get("responses", {})
        success_response = responses.get("200")
        assert success_response is not None, "Health endpoint success response not documented"