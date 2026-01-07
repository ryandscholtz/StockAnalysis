"""
Property-based tests for database migration idempotency
Tests Property 4: Database Migration Idempotency
**Validates: Requirements 2.5**
"""
import pytest
import asyncio
import tempfile
import os
from hypothesis import given, strategies as st, settings
from unittest.mock import AsyncMock, MagicMock
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database.migration import Migration, MigrationRunner, create_migration_runner
from app.database.factory import DatabaseFactory
from app.database.repository import SQLiteRepository


class TestMigration(Migration):
    """Test migration for property testing"""
    
    def __init__(self, version: str, should_succeed: bool = True):
        super().__init__(version, f"Test migration {version}")
        self.should_succeed = should_succeed
        self.up_call_count = 0
        self.down_call_count = 0
    
    async def up(self, repository) -> bool:
        """Apply the migration"""
        self.up_call_count += 1
        return self.should_succeed
    
    async def down(self, repository) -> bool:
        """Rollback the migration"""
        self.down_call_count += 1
        return self.should_succeed


class TestDatabaseMigrationIdempotency:
    """Property-based tests for database migration idempotency"""
    
    @pytest.mark.asyncio
    @given(
        migration_versions=st.lists(
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Nd', 'Lu', 'Ll'))),
            min_size=1,
            max_size=5,
            unique=True
        ),
        run_count=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=50, deadline=5000)
    async def test_migration_idempotency_property(self, migration_versions, run_count):
        """
        Feature: tech-stack-modernization, Property 4: Database Migration Idempotency
        For any database migration operation, running the migration multiple times should produce the same final state without errors
        **Validates: Requirements 2.5**
        """
        # Create a unique temporary database for testing to avoid file conflicts
        import uuid
        tmp_dir = tempfile.gettempdir()
        tmp_path = os.path.join(tmp_dir, f"test_migration_{uuid.uuid4().hex}.db")
        
        repository = None
        try:
            # Create repository and migration runner
            repository = DatabaseFactory.create_sqlite_repository(tmp_path)
            runner = MigrationRunner(repository)
            
            # Add test migrations
            migrations = []
            for version in sorted(migration_versions):
                migration = TestMigration(version, should_succeed=True)
                migrations.append(migration)
                runner.add_migration(migration)
            
            # Run migrations multiple times
            results = []
            for i in range(run_count):
                result = await runner.run_migrations()
                results.append(result)
            
            # Property: All runs should succeed
            assert all(results), f"Not all migration runs succeeded: {results}"
            
            # Property: Each migration's up() method should only be called once
            # (subsequent runs should skip already applied migrations)
            for migration in migrations:
                assert migration.up_call_count == 1, f"Migration {migration.version} up() called {migration.up_call_count} times, expected 1"
            
            # Property: Applied migrations should be consistent across runs
            applied_migrations = await runner.get_applied_migrations()
            expected_versions = set(migration_versions)
            actual_versions = set(applied_migrations.keys())
            assert actual_versions == expected_versions, f"Applied migrations {actual_versions} don't match expected {expected_versions}"
            
        finally:
            # Ensure repository connection is closed before file cleanup
            if repository:
                await repository.close()
            
            # Clean up temporary file with retry for Windows file locking
            import time
            for attempt in range(3):
                try:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                    break
                except PermissionError:
                    if attempt < 2:  # Retry up to 3 times
                        time.sleep(0.1)  # Brief delay for file handle cleanup
                        continue
                    else:
                        # Log warning but don't fail test - temp files will be cleaned up eventually
                        import warnings
                        warnings.warn(f"Could not delete temporary file {tmp_path} - will be cleaned up by OS")
    
    @pytest.mark.asyncio
    @given(
        migration_versions=st.lists(
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Nd', 'Lu', 'Ll'))),
            min_size=1,
            max_size=3,
            unique=True
        )
    )
    @settings(max_examples=30, deadline=5000)
    async def test_partial_migration_idempotency_property(self, migration_versions):
        """
        Feature: tech-stack-modernization, Property 4: Database Migration Idempotency
        For any partial migration state, re-running migrations should complete remaining migrations without re-applying completed ones
        **Validates: Requirements 2.5**
        """
        # Create a unique temporary database for testing to avoid file conflicts
        import uuid
        tmp_dir = tempfile.gettempdir()
        tmp_path = os.path.join(tmp_dir, f"test_partial_migration_{uuid.uuid4().hex}.db")
        
        repository = None
        try:
            # Create repository and migration runner
            repository = DatabaseFactory.create_sqlite_repository(tmp_path)
            runner = MigrationRunner(repository)
            
            # Add test migrations
            migrations = []
            sorted_versions = sorted(migration_versions)
            for version in sorted_versions:
                migration = TestMigration(version, should_succeed=True)
                migrations.append(migration)
                runner.add_migration(migration)
            
            # Apply migrations partially (simulate some already applied)
            if len(migrations) > 1:
                # Mark first migration as already applied
                first_migration = migrations[0]
                await runner.mark_migration_applied(first_migration.version, asyncio.get_event_loop().time())
            
            # Run migrations
            result = await runner.run_migrations()
            assert result, "Migration run should succeed"
            
            # Property: Already applied migrations should not be re-applied
            if len(migrations) > 1:
                first_migration = migrations[0]
                assert first_migration.up_call_count == 0, f"Already applied migration {first_migration.version} should not be called again"
            
            # Property: Remaining migrations should be applied exactly once
            for migration in migrations[1:]:
                assert migration.up_call_count == 1, f"Migration {migration.version} should be called exactly once"
            
            # Property: All migrations should be marked as applied
            applied_migrations = await runner.get_applied_migrations()
            expected_versions = set(migration_versions)
            actual_versions = set(applied_migrations.keys())
            assert actual_versions == expected_versions, f"Applied migrations {actual_versions} don't match expected {expected_versions}"
            
        finally:
            # Ensure repository connection is closed before file cleanup
            if repository:
                await repository.close()
            
            # Clean up temporary file with retry for Windows file locking
            import time
            for attempt in range(3):
                try:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                    break
                except PermissionError:
                    if attempt < 2:  # Retry up to 3 times
                        time.sleep(0.1)  # Brief delay for file handle cleanup
                        continue
                    else:
                        # Log warning but don't fail test - temp files will be cleaned up eventually
                        import warnings
                        warnings.warn(f"Could not delete temporary file {tmp_path} - will be cleaned up by OS")
    
    @pytest.mark.asyncio
    @given(
        migration_version=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Nd', 'Lu', 'Ll'))),
        rollback_count=st.integers(min_value=2, max_value=4)
    )
    @settings(max_examples=30, deadline=5000)
    async def test_rollback_idempotency_property(self, migration_version, rollback_count):
        """
        Feature: tech-stack-modernization, Property 4: Database Migration Idempotency
        For any migration rollback operation, rolling back multiple times should be idempotent
        **Validates: Requirements 2.5**
        """
        # Create a unique temporary database for testing to avoid file conflicts
        import uuid
        tmp_dir = tempfile.gettempdir()
        tmp_path = os.path.join(tmp_dir, f"test_rollback_{uuid.uuid4().hex}.db")
        
        repository = None
        try:
            # Create repository and migration runner
            repository = DatabaseFactory.create_sqlite_repository(tmp_path)
            runner = MigrationRunner(repository)
            
            # Add and apply test migration
            migration = TestMigration(migration_version, should_succeed=True)
            runner.add_migration(migration)
            
            # Apply the migration first
            result = await runner.run_migrations()
            assert result, "Initial migration should succeed"
            assert migration.up_call_count == 1, "Migration should be applied once"
            
            # Rollback multiple times
            rollback_results = []
            for i in range(rollback_count):
                result = await runner.rollback_migration(migration_version)
                rollback_results.append(result)
            
            # Property: First rollback should succeed, subsequent ones should fail gracefully
            assert rollback_results[0] == True, "First rollback should succeed"
            for result in rollback_results[1:]:
                assert result == False, "Subsequent rollbacks should fail gracefully (migration not applied)"
            
            # Property: Migration down() method should only be called once
            assert migration.down_call_count == 1, f"Migration down() called {migration.down_call_count} times, expected 1"
            
            # Property: Migration should not be in applied list after rollback
            applied_migrations = await runner.get_applied_migrations()
            assert migration_version not in applied_migrations, "Rolled back migration should not be in applied list"
            
        finally:
            # Ensure repository connection is closed before file cleanup
            if repository:
                await repository.close()
            
            # Clean up temporary file with retry for Windows file locking
            import time
            for attempt in range(3):
                try:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                    break
                except PermissionError:
                    if attempt < 2:  # Retry up to 3 times
                        time.sleep(0.1)  # Brief delay for file handle cleanup
                        continue
                    else:
                        # Log warning but don't fail test - temp files will be cleaned up eventually
                        import warnings
                        warnings.warn(f"Could not delete temporary file {tmp_path} - will be cleaned up by OS")
    
    @pytest.mark.asyncio
    async def test_migration_failure_handling_property(self):
        """
        Feature: tech-stack-modernization, Property 4: Database Migration Idempotency
        For any failed migration, the system should remain in a consistent state and allow retry
        **Validates: Requirements 2.5**
        """
        # Create a unique temporary database for testing to avoid file conflicts
        import uuid
        tmp_dir = tempfile.gettempdir()
        tmp_path = os.path.join(tmp_dir, f"test_failure_{uuid.uuid4().hex}.db")
        
        repository = None
        try:
            # Create repository and migration runner
            repository = DatabaseFactory.create_sqlite_repository(tmp_path)
            runner = MigrationRunner(repository)
            
            # Add migrations: one that succeeds, one that fails, one that would succeed
            success_migration = TestMigration("001", should_succeed=True)
            failure_migration = TestMigration("002", should_succeed=False)
            pending_migration = TestMigration("003", should_succeed=True)
            
            runner.add_migration(success_migration)
            runner.add_migration(failure_migration)
            runner.add_migration(pending_migration)
            
            # Run migrations (should fail on second migration)
            result = await runner.run_migrations()
            assert result == False, "Migration run should fail due to failing migration"
            
            # Property: Successful migration should be applied
            assert success_migration.up_call_count == 1, "Successful migration should be applied"
            
            # Property: Failed migration should be attempted
            assert failure_migration.up_call_count == 1, "Failed migration should be attempted"
            
            # Property: Pending migration should not be attempted after failure
            assert pending_migration.up_call_count == 0, "Pending migration should not be attempted after failure"
            
            # Property: Only successful migration should be marked as applied
            applied_migrations = await runner.get_applied_migrations()
            assert "001" in applied_migrations, "Successful migration should be marked as applied"
            assert "002" not in applied_migrations, "Failed migration should not be marked as applied"
            assert "003" not in applied_migrations, "Pending migration should not be marked as applied"
            
            # Property: Fix the failing migration and retry should work
            failure_migration.should_succeed = True
            result = await runner.run_migrations()
            assert result == True, "Retry after fixing should succeed"
            
            # Property: All migrations should now be applied exactly once more
            assert success_migration.up_call_count == 1, "Already applied migration should not be re-run"
            assert failure_migration.up_call_count == 2, "Fixed migration should be attempted again"
            assert pending_migration.up_call_count == 1, "Pending migration should now be applied"
            
        finally:
            # Ensure repository connection is closed before file cleanup
            if repository:
                await repository.close()
            
            # Clean up temporary file with retry for Windows file locking
            import time
            for attempt in range(3):
                try:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                    break
                except PermissionError:
                    if attempt < 2:  # Retry up to 3 times
                        time.sleep(0.1)  # Brief delay for file handle cleanup
                        continue
                    else:
                        # Log warning but don't fail test - temp files will be cleaned up eventually
                        import warnings
                        warnings.warn(f"Could not delete temporary file {tmp_path} - will be cleaned up by OS")


if __name__ == "__main__":
    pytest.main([__file__])