"""
Tests for TaskManagerMixin functionality.

Author: @TexasCoding
Date: 2025-08-17
"""

import asyncio
from unittest.mock import Mock

import pytest

from project_x_py.utils.task_management import TaskManagerMixin


class TaskManagerImplementation(TaskManagerMixin):
    """Test implementation of TaskManagerMixin."""

    def __init__(self):
        super().__init__()
        self._init_task_manager()  # Initialize the task manager
        self.logger = Mock()
        self.test_value = 0

    async def long_running_task(self, duration: float = 0.1):
        """Simulate a long-running task."""
        await asyncio.sleep(duration)
        self.test_value += 1
        return self.test_value

    async def failing_task(self):
        """Task that raises an exception."""
        await asyncio.sleep(0.01)
        raise ValueError("Test error")


class TestTaskManagerMixin:
    """Test suite for TaskManagerMixin."""

    @pytest.mark.asyncio
    async def test_create_task_basic(self):
        """Test basic task creation."""
        manager = TaskManagerImplementation()

        # Create a task
        task = manager._create_task(manager.long_running_task(0.01), name="test_task")

        assert task in manager._managed_tasks
        assert task not in manager._persistent_tasks
        assert task.get_name() == "test_task"

        # Wait for task to complete
        result = await task
        assert result == 1
        assert manager.test_value == 1

    @pytest.mark.asyncio
    async def test_create_persistent_task(self):
        """Test creating persistent tasks."""
        manager = TaskManagerImplementation()

        # Create persistent task
        task = manager._create_task(
            manager.long_running_task(0.01), name="persistent_task", persistent=True
        )

        assert task in manager._managed_tasks
        assert task in manager._persistent_tasks

        await task

    @pytest.mark.asyncio
    async def test_cleanup_all_tasks(self):
        """Test cleaning up all tasks."""
        manager = TaskManagerImplementation()

        # Create multiple tasks
        tasks = [
            manager._create_task(manager.long_running_task(0.1), name=f"task_{i}")
            for i in range(5)
        ]

        # Tasks should be tracked
        for task in tasks:
            assert task in manager._managed_tasks

        # Cleanup all tasks
        await manager._cleanup_tasks()

        # All tasks should be cancelled
        for task in tasks:
            assert task.cancelled() or task.done()

    @pytest.mark.asyncio
    async def test_cleanup_persistent_tasks(self):
        """Test cleaning up persistent tasks."""
        manager = TaskManagerImplementation()

        # Create mixed tasks
        regular_task = manager._create_task(
            manager.long_running_task(0.1), name="regular"
        )
        persistent_task = manager._create_task(
            manager.long_running_task(0.1), name="persistent", persistent=True
        )

        # Check that persistent task is tracked separately
        assert persistent_task in manager._persistent_tasks
        assert regular_task not in manager._persistent_tasks

        # Cleanup all tasks
        await manager._cleanup_tasks()

        # All tasks should be cancelled
        assert regular_task.cancelled() or regular_task.done()
        assert persistent_task.cancelled() or persistent_task.done()

    @pytest.mark.asyncio
    async def test_task_error_handling(self):
        """Test that task errors are handled properly."""
        manager = TaskManagerImplementation()

        # Create a failing task
        task = manager._create_task(manager.failing_task(), name="error_task")

        # Task should complete with exception
        with pytest.raises(ValueError, match="Test error"):
            await task

        # Task should be tracked as done
        assert task.done()
        assert not task.cancelled()

    @pytest.mark.asyncio
    async def test_cleanup_completed_tasks(self):
        """Test that completed tasks are cleaned up from WeakSet."""
        manager = TaskManagerImplementation()

        # Create and complete tasks
        tasks = []
        for i in range(5):
            task = manager._create_task(
                manager.long_running_task(0.001), name=f"quick_task_{i}"
            )
            tasks.append(task)

        # Wait for completion
        await asyncio.gather(*tasks)

        # Force garbage collection
        import gc

        gc.collect()

        # Completed tasks may be removed from WeakSet
        # Task tracking should still work
        new_task = manager._create_task(
            manager.long_running_task(0.01), name="new_task"
        )
        assert new_task in manager._managed_tasks
        await new_task

    @pytest.mark.asyncio
    async def test_concurrent_task_creation(self):
        """Test creating tasks concurrently."""
        manager = TaskManagerImplementation()

        async def create_task_async(index: int):
            """Create a task asynchronously."""
            return manager._create_task(
                manager.long_running_task(0.01), name=f"concurrent_{index}"
            )

        # Create multiple tasks concurrently
        tasks = await asyncio.gather(*[create_task_async(i) for i in range(10)])

        # All tasks should be tracked
        for task in tasks:
            assert task in manager._managed_tasks

        # Wait for all to complete
        results = await asyncio.gather(*tasks)
        assert len(results) == 10

    @pytest.mark.asyncio
    async def test_task_done_callback(self):
        """Test that task done callback is registered."""
        manager = TaskManagerImplementation()

        # Create a task
        task = manager._create_task(
            manager.long_running_task(0.01), name="callback_task"
        )

        # Verify callback is added
        assert len(task._callbacks) > 0

        # Complete the task
        await task

        # Task should handle completion
        assert task.done()

    @pytest.mark.asyncio
    async def test_cleanup_idempotency(self):
        """Test that cleanup methods are idempotent."""
        manager = TaskManagerImplementation()

        # Create some tasks
        task1 = manager._create_task(manager.long_running_task(0.01), name="task1")
        task2 = manager._create_task(
            manager.long_running_task(0.01), name="task2", persistent=True
        )

        # Multiple cleanups should not raise errors
        await manager._cleanup_tasks()
        await manager._cleanup_tasks()  # Second call should be safe

        assert task1.cancelled() or task1.done()
        assert task2.cancelled() or task2.done()

    @pytest.mark.asyncio
    async def test_task_errors_collection(self):
        """Test that task errors are collected."""
        manager = TaskManagerImplementation()

        # Create failing tasks
        tasks = []
        for i in range(3):
            task = manager._create_task(manager.failing_task(), name=f"failing_{i}")
            tasks.append(task)

        # Gather with return_exceptions to not raise
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should be exceptions
        assert all(isinstance(r, Exception) for r in results)

        # Errors should be collected in task_errors
        assert len(manager._task_errors) >= 3

    @pytest.mark.asyncio
    async def test_mixed_task_completion(self):
        """Test mix of successful and failing tasks."""
        manager = TaskManagerImplementation()

        # Create mixed tasks
        success_task = manager._create_task(
            manager.long_running_task(0.01), name="success"
        )
        fail_task = manager._create_task(manager.failing_task(), name="fail")

        # Gather with exceptions
        results = await asyncio.gather(success_task, fail_task, return_exceptions=True)

        # Check results
        assert isinstance(results[0], int)  # Success returns int
        assert isinstance(results[1], ValueError)  # Failure returns exception
