"""
Database factory for environment-specific database implementations
"""
import os
from typing import Optional
from app.database.repository import DatabaseRepository, SQLiteRepository, DynamoDBRepository


class DatabaseFactory:
    """Factory for creating database repositories based on environment"""

    @staticmethod
    def create_repository(environment: Optional[str] = None) -> DatabaseRepository:
        """
        Create appropriate database repository based on environment

        Args:
            environment: Environment name (production, development, test)
                        If None, uses ENVIRONMENT env var or defaults to development

        Returns:
            DatabaseRepository instance (SQLite for dev/test, DynamoDB for production)
        """
        if environment is None:
            environment = os.getenv("ENVIRONMENT", "development").lower()
        else:
            environment = environment.lower()

        if environment == "production":
            # Production uses DynamoDB
            table_name = os.getenv("DYNAMODB_TABLE_NAME", "stock-analyses")
            region = os.getenv("DYNAMODB_REGION", "eu-west-1")
            return DynamoDBRepository(table_name=table_name, region=region)
        else:
            # Development and test use SQLite
            db_path = os.getenv("SQLITE_DB_PATH", "stock_analysis.db")
            return SQLiteRepository(db_path=db_path)

    @staticmethod
    def create_sqlite_repository(db_path: str = "stock_analysis.db") -> SQLiteRepository:
        """Create SQLite repository explicitly"""
        return SQLiteRepository(db_path=db_path)

    @staticmethod
    def create_dynamodb_repository(table_name: Optional[str] = None,
                                  region: Optional[str] = None) -> DynamoDBRepository:
        """Create DynamoDB repository explicitly"""
        return DynamoDBRepository(table_name=table_name, region=region)


# Convenience function for getting the default repository
def get_database_repository(environment: Optional[str] = None) -> DatabaseRepository:
    """Get the appropriate database repository for the current environment"""
    return DatabaseFactory.create_repository(environment)
