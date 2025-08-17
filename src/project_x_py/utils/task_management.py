"""
Async task management utilities for ProjectX SDK.

Provides mixins and utilities for proper async task lifecycle management,
preventing memory leaks and ensuring clean shutdown.

Author: SDK v3.1.14
Date: 2025-01-17
"""

import asyncio
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any
from weakref import WeakSet

if TYPE_CHECKING:
    from asyncio import Task

logger = logging.getLogger(__name__)


class TaskManagerMixin:
    """
    Mixin for proper async task management.

    Provides task tracking, cleanup, and cancellation capabilities to prevent
    memory leaks from untracked asyncio tasks. Any class using asyncio.create_task
    should inherit from this mixin.

    Example:
        ```python
        class MyManager(TaskManagerMixin):
            def __init__(self):
                super().__init__()
                self._init_task_manager()

            async def start_background_work(self):
                task = self._create_task(self._background_worker())
                # Task is automatically tracked

            async def cleanup(self):
                await self._cleanup_tasks()
        ```
    """

    def _init_task_manager(self) -> None:
        """Initialize task management attributes."""
        self._managed_tasks: WeakSet[Task[Any]] = WeakSet()
        self._persistent_tasks: set[Task[Any]] = set()  # Tasks that should not be GC'd
        self._task_errors: list[BaseException] = []
        self._cleanup_in_progress = False

    def _create_task(
        self, coro: Any, name: str | None = None, persistent: bool = False
    ) -> "Task[Any]":
        """
        Create and track an async task.

        Args:
            coro: Coroutine to run
            name: Optional task name for debugging
            persistent: If True, task won't be garbage collected until cleanup

        Returns:
            Created task
        """
        task = asyncio.create_task(coro)

        if name:
            task.set_name(name)

        # Track the task
        self._managed_tasks.add(task)
        if persistent:
            self._persistent_tasks.add(task)

        # Add error handler
        task.add_done_callback(self._task_done_callback)

        logger.debug(f"Created task: {name or task.get_name()}")
        return task

    def _task_done_callback(self, task: "Task[Any]") -> None:
        """
        Callback when a tracked task completes.

        Args:
            task: Completed task
        """
        # Remove from persistent set if present
        self._persistent_tasks.discard(task)

        # Check for exceptions
        try:
            if not task.cancelled():
                exception = task.exception()
                if exception:
                    self._task_errors.append(exception)
                    logger.error(
                        f"Task {task.get_name()} failed with exception: {exception}"
                    )
        except asyncio.CancelledError:
            pass  # Task was cancelled, which is fine
        except Exception as e:
            logger.error(f"Error checking task result: {e}")

    async def _cleanup_tasks(self, timeout: float = 5.0) -> None:
        """
        Cancel and cleanup all tracked tasks.

        Args:
            timeout: Maximum time to wait for tasks to cancel
        """
        if self._cleanup_in_progress:
            return

        self._cleanup_in_progress = True

        try:
            # Get all tasks (WeakSet may have removed some)
            all_tasks = list(self._managed_tasks) + list(self._persistent_tasks)
            pending_tasks = [t for t in all_tasks if not t.done()]

            if not pending_tasks:
                return

            logger.info(f"Cancelling {len(pending_tasks)} pending tasks")

            # Cancel all pending tasks
            for task in pending_tasks:
                task.cancel()

            # Wait for cancellation with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*pending_tasks, return_exceptions=True),
                    timeout=timeout,
                )
            except TimeoutError:
                logger.warning(
                    f"{len([t for t in pending_tasks if not t.done()])} tasks "
                    f"did not complete within {timeout}s timeout"
                )

            # Clear task sets
            self._persistent_tasks.clear()

        finally:
            self._cleanup_in_progress = False

    def get_task_stats(self) -> dict[str, Any]:
        """
        Get statistics about managed tasks.

        Returns:
            Dictionary with task statistics
        """
        all_tasks = list(self._managed_tasks) + list(self._persistent_tasks)
        return {
            "total_tasks": len(all_tasks),
            "pending_tasks": len([t for t in all_tasks if not t.done()]),
            "completed_tasks": len(
                [t for t in all_tasks if t.done() and not t.cancelled()]
            ),
            "cancelled_tasks": len([t for t in all_tasks if t.cancelled()]),
            "failed_tasks": len(self._task_errors),
            "persistent_tasks": len(self._persistent_tasks),
        }


class AsyncContextManager(TaskManagerMixin):
    """
    Base class for async context managers with proper task cleanup.

    Ensures all async tasks are properly cancelled when exiting the context.

    Example:
        ```python
        class MyAsyncManager(AsyncContextManager):
            async def __aenter__(self):
                await super().__aenter__()
                # Start background tasks
                self._create_task(self._monitor())
                return self

            async def _monitor(self):
                while True:
                    # Do monitoring
                    await asyncio.sleep(1)
        ```
    """

    def __init__(self) -> None:
        """Initialize the async context manager."""
        super().__init__()
        self._init_task_manager()

    async def __aenter__(self) -> "AsyncContextManager":
        """Enter the async context."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Exit the async context and cleanup tasks.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        await self._cleanup_tasks()


def create_fire_and_forget_task(
    coro: Any,
    name: str | None = None,
    error_handler: Callable[[BaseException], None] | None = None,
) -> "Task[Any]":
    """
    Create a fire-and-forget task with optional error handling.

    Use this for tasks that should run independently without tracking.

    Args:
        coro: Coroutine to run
        name: Optional task name for debugging
        error_handler: Optional callable to handle exceptions

    Returns:
        Created task

    Example:
        ```python
        def handle_error(e: Exception):
            logger.error(f"Background task failed: {e}")


        create_fire_and_forget_task(
            process_data(), name="data_processor", error_handler=handle_error
        )
        ```
    """
    task = asyncio.create_task(coro)

    if name:
        task.set_name(name)

    def done_callback(t: "Task[Any]") -> None:
        try:
            if not t.cancelled():
                exception = t.exception()
                if exception and error_handler:
                    error_handler(exception)
                elif exception:
                    logger.error(
                        f"Fire-and-forget task {t.get_name()} failed: {exception}"
                    )
        except Exception as e:
            logger.error(f"Error in fire-and-forget callback: {e}")

    task.add_done_callback(done_callback)
    return task
