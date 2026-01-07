"""
Minimal integration test to verify setup
"""
import pytest
from fastapi.testclient import TestClient
from app.core.app import app


def test_health_endpoint():
    """Test health endpoint works"""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_root_endpoint():
    """Test root endpoint works"""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["status"] == "healthy"


@pytest.mark.integration
def test_api_search_endpoint():
    """Test API search endpoint"""
    client = TestClient(app)
    response = client.get("/api/search?q=AAPL")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data


@pytest.mark.integration
def test_api_presets_endpoint():
    """Test API presets endpoint"""
    client = TestClient(app)
    response = client.get("/api/analysis-presets")
    assert response.status_code == 200
    data = response.json()
    assert "presets" in data
    assert "business_types" in data
