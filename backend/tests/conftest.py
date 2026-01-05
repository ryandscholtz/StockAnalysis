"""
Pytest configuration and fixtures for the test suite
"""
import pytest
import tempfile
import os
import sys
from unittest.mock import Mock

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def temp_database():
    """Create a temporary database for testing"""
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    
    yield temp_db.name
    
    # Cleanup
    if os.path.exists(temp_db.name):
        os.unlink(temp_db.name)

@pytest.fixture
def mock_yahoo_client():
    """Create a mock Yahoo Finance client"""
    mock_client = Mock()
    
    # Mock successful quote response
    mock_client.get_quote.return_value = {
        'price': 150.25,
        'company_name': 'Test Company',
        'market_cap': 1000000000,
        'currency': 'USD',
        'symbol': 'TEST',
        'success': True,
        'api_attempts': []
    }
    
    # Mock search response
    mock_client.search_tickers.return_value = [
        {
            'ticker': 'TEST',
            'companyName': 'Test Company',
            'exchange': 'NASDAQ'
        }
    ]
    
    return mock_client

@pytest.fixture
def sample_watchlist_data():
    """Sample watchlist data for testing"""
    return [
        {
            'ticker': 'AAPL',
            'company_name': 'Apple Inc.',
            'exchange': 'NASDAQ',
            'added_at': '2024-01-01T00:00:00',
            'updated_at': '2024-01-01T00:00:00',
            'notes': None
        },
        {
            'ticker': 'GOOGL',
            'company_name': 'Alphabet Inc.',
            'exchange': 'NASDAQ',
            'added_at': '2024-01-01T00:00:00',
            'updated_at': '2024-01-01T00:00:00',
            'notes': 'Tech giant'
        }
    ]

@pytest.fixture
def sample_analysis_data():
    """Sample analysis data for testing"""
    return {
        'ticker': 'AAPL',
        'companyName': 'Apple Inc.',
        'currentPrice': 150.25,
        'fairValue': 160.00,
        'marginOfSafety': 6.1,
        'recommendation': 'Buy',
        'financialHealth': {
            'score': 85,
            'details': 'Strong financial position'
        },
        'businessQuality': {
            'score': 90,
            'details': 'Excellent business model'
        }
    }

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment before each test"""
    # Set test environment variables
    os.environ['TESTING'] = 'true'
    os.environ['LOG_LEVEL'] = 'ERROR'  # Reduce log noise during tests
    
    yield
    
    # Cleanup
    if 'TESTING' in os.environ:
        del os.environ['TESTING']
    if 'LOG_LEVEL' in os.environ:
        del os.environ['LOG_LEVEL']

@pytest.fixture
def mock_cache_manager():
    """Create a mock cache manager"""
    mock_cache = Mock()
    
    # Mock cache operations
    mock_cache.get.return_value = None  # Cache miss by default
    mock_cache.set.return_value = True
    mock_cache.delete.return_value = True
    mock_cache.clear.return_value = None
    mock_cache.get_stats.return_value = {
        'total_entries': 0,
        'active_entries': 0,
        'current_size_mb': 0.0,
        'max_size_mb': 100.0,
        'utilization_percent': 0.0
    }
    
    return mock_cache

@pytest.fixture
def mock_task_manager():
    """Create a mock background task manager"""
    mock_manager = Mock()
    
    # Mock task operations
    mock_manager.create_task.return_value = "test_task_id_123"
    mock_manager.get_task_status.return_value = {
        'id': 'test_task_id_123',
        'task_type': 'test_task',
        'status': 'completed',
        'progress': 100.0,
        'result': {'test': 'result'},
        'error': None
    }
    mock_manager.cancel_task.return_value = True
    
    return mock_manager

# Pytest configuration
def pytest_configure(config):
    """Configure pytest"""
    # Add custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "api: marks tests that require external API calls"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    # Skip slow tests by default unless explicitly requested
    if config.getoption("-m") is None:
        skip_slow = pytest.mark.skip(reason="use -m slow to run slow tests")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)