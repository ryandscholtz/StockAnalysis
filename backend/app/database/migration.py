"""
Database migration utilities for schema updates and data migrations
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class Migration(ABC):
    """Abstract base class for database migrations"""
    
    def __init__(self, version: str, description: str):
        self.version = version
        self.description = description
        self.applied_at: Optional[datetime] = None
    
    @abstractmethod
    async def up(self, repository) -> bool:
        """Apply the migration"""
        pass
    
    @abstractmethod
    async def down(self, repository) -> bool:
        """Rollback the migration"""
        pass
    
    def __str__(self):
        return f"Migration {self.version}: {self.description}"


class MigrationRunner:
    """Handles running database migrations"""
    
    def __init__(self, repository):
        self.repository = repository
        self.migrations: List[Migration] = []
        self._applied_migrations: Dict[str, datetime] = {}
    
    def add_migration(self, migration: Migration):
        """Add a migration to the runner"""
        self.migrations.append(migration)
        # Sort by version to ensure proper order
        self.migrations.sort(key=lambda m: m.version)
    
    async def get_applied_migrations(self) -> Dict[str, datetime]:
        """Get list of applied migrations from database"""
        # For now, use in-memory tracking
        # In a real implementation, this would query a migrations table
        return self._applied_migrations.copy()
    
    async def mark_migration_applied(self, version: str, applied_at: datetime):
        """Mark a migration as applied"""
        self._applied_migrations[version] = applied_at
    
    async def mark_migration_unapplied(self, version: str):
        """Mark a migration as unapplied"""
        if version in self._applied_migrations:
            del self._applied_migrations[version]
    
    async def run_migrations(self) -> bool:
        """
        Run all pending migrations
        
        Returns:
            True if all migrations applied successfully
        """
        applied_migrations = await self.get_applied_migrations()
        
        success = True
        for migration in self.migrations:
            if migration.version not in applied_migrations:
                logger.info(f"Applying migration: {migration}")
                try:
                    if await migration.up(self.repository):
                        await self.mark_migration_applied(migration.version, datetime.utcnow())
                        migration.applied_at = datetime.utcnow()
                        logger.info(f"Successfully applied migration {migration.version}")
                    else:
                        logger.error(f"Failed to apply migration {migration.version}")
                        success = False
                        break
                except Exception as e:
                    logger.error(f"Error applying migration {migration.version}: {e}")
                    success = False
                    break
            else:
                logger.debug(f"Migration {migration.version} already applied, skipping")
        
        return success
    
    async def rollback_migration(self, version: str) -> bool:
        """
        Rollback a specific migration
        
        Args:
            version: Version of migration to rollback
        
        Returns:
            True if rollback successful
        """
        applied_migrations = await self.get_applied_migrations()
        
        if version not in applied_migrations:
            logger.warning(f"Migration {version} is not applied, cannot rollback")
            return False
        
        # Find the migration
        migration = None
        for m in self.migrations:
            if m.version == version:
                migration = m
                break
        
        if not migration:
            logger.error(f"Migration {version} not found")
            return False
        
        try:
            logger.info(f"Rolling back migration: {migration}")
            if await migration.down(self.repository):
                await self.mark_migration_unapplied(version)
                migration.applied_at = None
                logger.info(f"Successfully rolled back migration {version}")
                return True
            else:
                logger.error(f"Failed to rollback migration {version}")
                return False
        except Exception as e:
            logger.error(f"Error rolling back migration {version}: {e}")
            return False


# Example migrations for testing
class AddAnalysisWeightsColumnMigration(Migration):
    """Example migration: Add analysis_weights column to stock_analyses table"""
    
    def __init__(self):
        super().__init__("001", "Add analysis_weights column to stock_analyses table")
    
    async def up(self, repository) -> bool:
        """Add the analysis_weights column"""
        try:
            # For SQLite, we would add the column
            # For DynamoDB, this is a no-op since it's schemaless
            logger.info("Adding analysis_weights column (simulated)")
            return True
        except Exception as e:
            logger.error(f"Failed to add analysis_weights column: {e}")
            return False
    
    async def down(self, repository) -> bool:
        """Remove the analysis_weights column"""
        try:
            # For SQLite, we would drop the column (complex in SQLite)
            # For DynamoDB, this is a no-op
            logger.info("Removing analysis_weights column (simulated)")
            return True
        except Exception as e:
            logger.error(f"Failed to remove analysis_weights column: {e}")
            return False


class AddBusinessTypeIndexMigration(Migration):
    """Example migration: Add index on business_type column"""
    
    def __init__(self):
        super().__init__("002", "Add index on business_type column")
    
    async def up(self, repository) -> bool:
        """Add the business_type index"""
        try:
            logger.info("Adding business_type index (simulated)")
            return True
        except Exception as e:
            logger.error(f"Failed to add business_type index: {e}")
            return False
    
    async def down(self, repository) -> bool:
        """Remove the business_type index"""
        try:
            logger.info("Removing business_type index (simulated)")
            return True
        except Exception as e:
            logger.error(f"Failed to remove business_type index: {e}")
            return False


def create_migration_runner(repository) -> MigrationRunner:
    """Create a migration runner with standard migrations"""
    runner = MigrationRunner(repository)
    
    # Add standard migrations
    runner.add_migration(AddAnalysisWeightsColumnMigration())
    runner.add_migration(AddBusinessTypeIndexMigration())
    
    return runner