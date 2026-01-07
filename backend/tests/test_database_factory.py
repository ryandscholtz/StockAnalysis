"""
Unit tests for database factory environment selection
Tests Requirements 2.1 and 2.2: Production uses DynamoDB, development uses SQLite
"""
from app.database.repository import SQLiteRepository, DynamoDBRepository
from app.database.factory import DatabaseFactory, get_database_repository
import pytest
import os
import tempfile
from unittest.mock import patch
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))


class TestDatabaseFactory:
    """Test database factory environment selection"""

    def test_production_environment_uses_dynamodb(self):
        """Test that production environment uses DynamoDB"""
        # Test explicit production environment
        repo = DatabaseFactory.create_repository("production")
        assert isinstance(repo, DynamoDBRepository)

        # Test case insensitive
        repo = DatabaseFactory.create_repository("PRODUCTION")
        assert isinstance(repo, DynamoDBRepository)

    def test_development_environment_uses_sqlite(self):
        """Test that development environment uses SQLite"""
        # Test explicit development environment
        repo = DatabaseFactory.create_repository("development")
        assert isinstance(repo, SQLiteRepository)

        # Test case insensitive
        repo = DatabaseFactory.create_repository("DEVELOPMENT")
        assert isinstance(repo, SQLiteRepository)

    def test_test_environment_uses_sqlite(self):
        """Test that test environment uses SQLite"""
        repo = DatabaseFactory.create_repository("test")
        assert isinstance(repo, SQLiteRepository)

        repo = DatabaseFactory.create_repository("TEST")
        assert isinstance(repo, SQLiteRepository)

    def test_unknown_environment_defaults_to_sqlite(self):
        """Test that unknown environments default to SQLite (development)"""
        repo = DatabaseFactory.create_repository("unknown")
        assert isinstance(repo, SQLiteRepository)

        repo = DatabaseFactory.create_repository("staging")
        assert isinstance(repo, SQLiteRepository)

    @patch.dict(os.environ, {"ENVIRONMENT": "production"})
    def test_environment_from_env_var_production(self):
        """Test reading environment from ENVIRONMENT env var - production"""
        repo = DatabaseFactory.create_repository()
        assert isinstance(repo, DynamoDBRepository)

    @patch.dict(os.environ, {"ENVIRONMENT": "development"})
    def test_environment_from_env_var_development(self):
        """Test reading environment from ENVIRONMENT env var - development"""
        repo = DatabaseFactory.create_repository()
        assert isinstance(repo, SQLiteRepository)

    @patch.dict(os.environ, {}, clear=True)
    def test_no_environment_defaults_to_development(self):
        """Test that missing ENVIRONMENT env var defaults to development (SQLite)"""
        repo = DatabaseFactory.create_repository()
        assert isinstance(repo, SQLiteRepository)

    @patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "DYNAMODB_TABLE_NAME": "test-table",
        "DYNAMODB_REGION": "us-west-2"
    })
    def test_production_uses_environment_config(self):
        """Test that production DynamoDB uses environment configuration"""
        with patch('app.database.dynamodb_service.DynamoDBService') as mock_service:
            repo = DatabaseFactory.create_repository()
            assert isinstance(repo, DynamoDBRepository)
            # Verify DynamoDBService was called with correct parameters
            mock_service.assert_called_once_with(
                table_name="test-table", region="us-west-2")

    @patch.dict(os.environ, {
        "ENVIRONMENT": "development",
        "SQLITE_DB_PATH": "test_custom.db"
    })
    def test_development_uses_environment_config(self):
        """Test that development SQLite uses environment configuration"""
        with patch('app.database.db_service.DatabaseService') as mock_service:
            repo = DatabaseFactory.create_repository()
            assert isinstance(repo, SQLiteRepository)
            # Verify DatabaseService was called with correct path
            mock_service.assert_called_once_with(db_path="test_custom.db")

    def test_explicit_sqlite_creation(self):
        """Test explicit SQLite repository creation"""
        # Use a temporary file for testing
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            repo = DatabaseFactory.create_sqlite_repository(tmp_path)
            assert isinstance(repo, SQLiteRepository)
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        # Test default path
        repo = DatabaseFactory.create_sqlite_repository()
        assert isinstance(repo, SQLiteRepository)

    def test_explicit_dynamodb_creation(self):
        """Test explicit DynamoDB repository creation"""
        repo = DatabaseFactory.create_dynamodb_repository()
        assert isinstance(repo, DynamoDBRepository)

        repo = DatabaseFactory.create_dynamodb_repository("custom-table", "us-east-1")
        assert isinstance(repo, DynamoDBRepository)

    def test_get_database_repository_convenience_function(self):
        """Test convenience function works correctly"""
        # Test with explicit environment
        repo = get_database_repository("production")
        assert isinstance(repo, DynamoDBRepository)

        repo = get_database_repository("development")
        assert isinstance(repo, SQLiteRepository)

        # Test with no environment (should use env var or default)
        repo = get_database_repository()
        assert isinstance(repo, (SQLiteRepository, DynamoDBRepository))


class TestDatabaseFactoryIntegration:
    """Integration tests for database factory"""

    def test_sqlite_repository_basic_functionality(self):
        """Test that created SQLite repository has basic functionality"""
        # Use a temporary file for testing
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            repo = DatabaseFactory.create_sqlite_repository(tmp_path)

            # Test that it has the required methods
            assert hasattr(repo, 'has_analysis_today')
            assert hasattr(repo, 'get_analysis')
            assert hasattr(repo, 'save_analysis')
            assert hasattr(repo, 'get_watchlist')
            assert hasattr(repo, 'close')

            # Test that methods are callable
            assert callable(repo.has_analysis_today)
            assert callable(repo.get_analysis)
            assert callable(repo.save_analysis)
            assert callable(repo.get_watchlist)
            assert callable(repo.close)
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_dynamodb_repository_basic_functionality(self):
        """Test that created DynamoDB repository has basic functionality"""
        # Mock the DynamoDB service to avoid AWS calls
        with patch('app.database.dynamodb_service.DynamoDBService'):
            repo = DatabaseFactory.create_dynamodb_repository()

            # Test that it has the required methods
            assert hasattr(repo, 'has_analysis_today')
            assert hasattr(repo, 'get_analysis')
            assert hasattr(repo, 'save_analysis')
            assert hasattr(repo, 'get_watchlist')
            assert hasattr(repo, 'close')

            # Test that methods are callable
            assert callable(repo.has_analysis_today)
            assert callable(repo.get_analysis)
            assert callable(repo.save_analysis)
            assert callable(repo.get_watchlist)
            assert callable(repo.close)


if __name__ == "__main__":
    pytest.main([__file__])
