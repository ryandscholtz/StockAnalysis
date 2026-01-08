"""
Unit tests for background task manager functionality
"""
from app.background_tasks import BackgroundTaskManager, TaskStatus, BackgroundTask
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBackgroundTaskManager:
    """Test cases for BackgroundTaskManager"""

    def setup_method(self):
        """Setup for each test method"""
        self.task_manager = BackgroundTaskManager()
        # Clear any existing tasks
        self.task_manager.tasks.clear()
        self.task_manager.running_tasks.clear()

    def test_task_manager_initialization(self):
        """Test task manager initialization"""
        assert len(self.task_manager.tasks) == 0
        assert len(self.task_manager.running_tasks) == 0
        assert self.task_manager.max_concurrent_tasks == 10
        assert self.task_manager.task_timeout == 300

    @pytest.mark.asyncio
    async def test_create_simple_task(self):
        """Test creating a simple synchronous task"""
        def simple_task(x, y):
            return x + y

        task_id = self.task_manager.create_task("test_task", simple_task, 5, 3)

        # Task should be created
        assert task_id in self.task_manager.tasks
        assert task_id in self.task_manager.running_tasks

        # Wait for task completion
        await asyncio.sleep(0.1)

        # Check task status
        task_status = self.task_manager.get_task_status(task_id)
        assert task_status is not None
        assert task_status["status"] == "completed"
        assert task_status["result"] == 8

    @pytest.mark.asyncio
    async def test_create_async_task(self):
        """Test creating an async task"""
        async def async_task(message):
            await asyncio.sleep(0.05)
            return f"Processed: {message}"

        task_id = self.task_manager.create_task("async_test", async_task, "hello")

        # Task should be created and running
        assert task_id in self.task_manager.tasks

        # Wait for completion
        await asyncio.sleep(0.1)

        task_status = self.task_manager.get_task_status(task_id)
        assert task_status["status"] == "completed"
        assert task_status["result"] == "Processed: hello"

    @pytest.mark.asyncio
    async def test_task_with_exception(self):
        """Test task that raises an exception"""
        def failing_task():
            raise ValueError("Test error")

        task_id = self.task_manager.create_task("failing_task", failing_task)

        # Wait for task to fail
        await asyncio.sleep(0.1)

        task_status = self.task_manager.get_task_status(task_id)
        assert task_status["status"] == "failed"
        assert "Test error" in task_status["error"]

    @pytest.mark.asyncio
    async def test_task_cancellation(self):
        """Test task cancellation"""
        async def long_running_task():
            await asyncio.sleep(10)  # Long running task
            return "completed"

        task_id = self.task_manager.create_task("long_task", long_running_task)

        # Task should be running
        await asyncio.sleep(0.05)
        task_status = self.task_manager.get_task_status(task_id)
        assert task_status["status"] == "running"

        # Cancel the task
        result = self.task_manager.cancel_task(task_id)
        assert result is True

        # Wait for cancellation to take effect
        await asyncio.sleep(0.1)

        task_status = self.task_manager.get_task_status(task_id)
        assert task_status["status"] == "cancelled"

    def test_get_nonexistent_task_status(self):
        """Test getting status of non-existent task"""
        status = self.task_manager.get_task_status("nonexistent_id")
        assert status is None

    def test_cancel_nonexistent_task(self):
        """Test cancelling non-existent task"""
        result = self.task_manager.cancel_task("nonexistent_id")
        assert result is False

    @pytest.mark.asyncio
    async def test_task_with_metadata(self):
        """Test task creation with metadata"""
        def simple_task():
            return "done"

        metadata = {"user": "test_user", "priority": "high"}
        task_id = self.task_manager.create_task(
            "meta_task", simple_task, metadata=metadata)

        await asyncio.sleep(0.1)

        task_status = self.task_manager.get_task_status(task_id)
        assert task_status["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_task_progress_tracking(self):
        """Test task progress and timing tracking"""
        def quick_task():
            return "result"

        task_id = self.task_manager.create_task("progress_task", quick_task)

        # Check initial status
        initial_status = self.task_manager.get_task_status(task_id)
        assert initial_status["progress"] == 0.0
        assert initial_status["created_at"] is not None

        # Wait for completion
        await asyncio.sleep(0.1)

        final_status = self.task_manager.get_task_status(task_id)
        assert final_status["progress"] == 100.0
        assert final_status["started_at"] is not None
        assert final_status["completed_at"] is not None

    def test_cleanup_old_tasks(self):
        """Test cleanup of old completed tasks"""
        # Create a mock old task with completed_at in the past
        old_task = BackgroundTask(
            id="old_task",
            task_type="test",
            status=TaskStatus.COMPLETED,
            created_at=datetime.now() - timedelta(hours=2),
            completed_at=datetime.now() - timedelta(hours=2)  # 2 hours ago
        )

        # Manually add to tasks (simulating old task)
        self.task_manager.tasks["old_task"] = old_task

        # Run cleanup with 1 hour (should remove tasks older than 1 hour)
        self.task_manager.cleanup_old_tasks(max_age_hours=1)

        # Task should be removed
        assert "old_task" not in self.task_manager.tasks


class TestBackgroundTaskFunctions:
    """Test the specific background task functions"""

    @pytest.mark.asyncio
    async def test_fetch_live_prices_background_empty_list(self):
        """Test live prices background task with empty ticker list"""
        from app.background_tasks import fetch_live_prices_background

        result = await fetch_live_prices_background([])

        assert "live_prices" in result
        assert len(result["live_prices"]) == 0

    @pytest.mark.asyncio
    @patch('app.data.api_client.YahooFinanceClient.get_quote')
    async def test_fetch_live_prices_background_with_tickers(self, mock_get_quote):
        """Test live prices background task with mock tickers"""
        from app.background_tasks import fetch_live_prices_background

        # Mock the API response
        mock_get_quote.return_value = {
            'success': True,
            'price': 150.25,
            'company_name': 'Apple Inc.',
            'symbol': 'AAPL',
            'api_attempts': []
        }

        result = await fetch_live_prices_background(["AAPL"])

        assert "live_prices" in result
        assert "AAPL" in result["live_prices"]

        # Should have success info
        aapl_data = result["live_prices"]["AAPL"]
        assert aapl_data["success"] is True
        assert aapl_data["price"] == 150.25


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
