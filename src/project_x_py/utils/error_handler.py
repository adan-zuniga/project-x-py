"""
Centralized error handling utilities for ProjectX SDK.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides consistent error handling patterns, logging, and retry logic
    across the entire SDK. Implements decorators, context managers, and
    utilities for robust error handling in async and sync operations.

Key Features:
    - Decorator-based error handling for functions and methods
    - Automatic retry logic with exponential backoff
    - Rate limit handling with automatic delay
    - Response validation and error context
    - Comprehensive logging and error reporting
    - Support for both async and sync operations

Error Handling Patterns:
    - @handle_errors: General error handling with logging
    - @retry_on_network_error: Automatic retry for network issues
    - @handle_rate_limit: Rate limit handling with automatic delay
    - @validate_response: Response structure validation
    - ErrorContext: Context manager for batch operations

Example Usage:
    ```python
    from project_x_py.utils import (
        handle_errors,
        retry_on_network_error,
        handle_rate_limit,
        validate_response,
        ErrorContext,
    )


    # General error handling
    @handle_errors("fetch market data", reraise=False)
    async def get_market_data():
        # Implementation
        pass


    # Network retry with exponential backoff
    @retry_on_network_error(max_attempts=3, initial_delay=1.0)
    async def api_call():
        # Implementation
        pass


    # Rate limit handling
    @handle_rate_limit(fallback_delay=60.0)
    async def make_api_call():
        # Implementation
        pass


    # Response validation
    @validate_response(required_fields=["id", "status"])
    async def get_order(order_id: str):
        # Implementation
        pass


    # Batch operation error handling
    async with ErrorContext("process orders") as ctx:
        for order in orders:
            try:
                await process_order(order)
            except Exception as e:
                ctx.add_error(order.id, e)
    ```

Error Handling Benefits:
    - Consistent error handling across all SDK operations
    - Automatic retry logic for transient failures
    - Rate limit compliance with automatic delays
    - Comprehensive logging for debugging
    - Graceful degradation with fallback options
    - Type-safe error handling with proper exceptions

Performance Characteristics:
    - Minimal overhead for error handling
    - Efficient retry logic with exponential backoff
    - Memory-efficient error context management
    - Thread-safe operations for concurrent access
    - Optimized for high-frequency trading scenarios

See Also:
    - `utils.error_messages`: Standardized error messages
    - `utils.logging_config`: Logging for error reporting
    - `utils.async_rate_limiter`: Rate limiting utilities
"""

import asyncio
import functools
import logging
from collections.abc import Callable
from typing import Any, Literal, TypeVar, cast

import httpx

from project_x_py.exceptions import (
    ProjectXConnectionError,
    ProjectXDataError,
    ProjectXError,
    ProjectXRateLimitError,
    ProjectXServerError,
)

T = TypeVar("T")


def handle_errors(
    operation: str,
    logger: logging.Logger | None = None,
    reraise: bool = True,
    default_return: Any = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for consistent error handling across the SDK.

    This decorator catches exceptions, logs them consistently, and optionally
    re-raises them with additional context.

    Args:
        operation: Description of the operation being performed
        logger: Logger instance to use (defaults to module logger)
        reraise: Whether to re-raise exceptions after logging
        default_return: Default value to return if exception occurs and reraise=False

    Example:
        @handle_errors("fetch market data")
        async def get_bars(self, symbol: str):
            # Implementation
            pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(func.__module__)

            try:
                return await func(*args, **kwargs)  # type: ignore[misc]
            except ProjectXError as e:
                # Already a ProjectX error, just add context
                logger.error(
                    f"ProjectX error during {operation}: {e}",
                    extra={
                        "error_type": type(e).__name__,
                        "error_code": getattr(e, "error_code", None),
                        "operation": operation,
                        "function": func.__name__,
                    },
                )
                if reraise:
                    raise
                return cast(T, default_return)
            except httpx.HTTPError as e:
                # Convert HTTP errors to ProjectX errors
                logger.error(
                    f"HTTP error during {operation}: {e}",
                    extra={
                        "error_type": type(e).__name__,
                        "operation": operation,
                        "function": func.__name__,
                    },
                )
                if reraise:
                    raise ProjectXConnectionError(
                        f"HTTP error during {operation}: {e}"
                    ) from e
                return cast(T, default_return)
            except Exception as e:
                # Unexpected errors
                logger.exception(
                    f"Unexpected error during {operation}",
                    extra={
                        "error_type": type(e).__name__,
                        "operation": operation,
                        "function": func.__name__,
                    },
                )
                if reraise:
                    raise ProjectXError(
                        f"Unexpected error during {operation}: {e}"
                    ) from e
                return cast(T, default_return)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(func.__module__)

            try:
                return func(*args, **kwargs)
            except ProjectXError as e:
                logger.error(
                    f"ProjectX error during {operation}: {e}",
                    extra={
                        "error_type": type(e).__name__,
                        "error_code": getattr(e, "error_code", None),
                        "operation": operation,
                        "function": func.__name__,
                    },
                )
                if reraise:
                    raise
                return cast(T, default_return)
            except Exception as e:
                logger.exception(
                    f"Unexpected error during {operation}",
                    extra={
                        "error_type": type(e).__name__,
                        "operation": operation,
                        "function": func.__name__,
                    },
                )
                if reraise:
                    raise ProjectXError(
                        f"Unexpected error during {operation}: {e}"
                    ) from e
                return cast(T, default_return)

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return cast(Callable[..., T], async_wrapper)
        else:
            return cast(Callable[..., T], sync_wrapper)

    return decorator


def retry_on_network_error(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    retry_on: tuple[type[Exception], ...] = (
        httpx.ConnectError,
        httpx.TimeoutException,
        ProjectXConnectionError,
        ProjectXServerError,
    ),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to retry operations on network errors with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        retry_on: Tuple of exception types to retry on

    Example:
        @retry_on_network_error(max_attempts=5, initial_delay=0.5)
        async def api_call(self):
            # Implementation
            pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            logger = logging.getLogger(func.__module__)
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)  # type: ignore[misc]
                except retry_on as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        delay = min(
                            initial_delay * (backoff_factor**attempt), max_delay
                        )
                        logger.warning(
                            f"Retry {attempt + 1}/{max_attempts} for {func.__name__} "
                            f"after {type(e).__name__}, waiting {delay:.1f}s",
                            extra={
                                "attempt": attempt + 1,
                                "max_attempts": max_attempts,
                                "delay": delay,
                                "error_type": type(e).__name__,
                                "function": func.__name__,
                            },
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"Max retries ({max_attempts}) exceeded for {func.__name__}",
                            extra={
                                "max_attempts": max_attempts,
                                "error_type": type(e).__name__,
                                "function": func.__name__,
                            },
                        )

            # Re-raise the last exception
            if last_exception:
                raise last_exception
            else:
                # Should never reach here, but just in case
                raise RuntimeError(
                    f"Unexpected state in retry logic for {func.__name__}"
                )

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            logger = logging.getLogger(func.__module__)
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        delay = min(
                            initial_delay * (backoff_factor**attempt), max_delay
                        )
                        logger.warning(
                            f"Retry {attempt + 1}/{max_attempts} for {func.__name__} "
                            f"after {type(e).__name__}, waiting {delay:.1f}s"
                        )
                        # For sync functions, we can't use asyncio.sleep
                        import time

                        time.sleep(delay)
                    else:
                        logger.error(
                            f"Max retries ({max_attempts}) exceeded for {func.__name__}"
                        )

            if last_exception:
                raise last_exception
            else:
                raise RuntimeError(
                    f"Unexpected state in retry logic for {func.__name__}"
                )

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return cast(Callable[..., T], async_wrapper)
        else:
            return cast(Callable[..., T], sync_wrapper)

    return decorator


def handle_rate_limit(
    logger: logging.Logger | None = None,
    fallback_delay: float = 60.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to handle rate limit errors with automatic retry.

    Args:
        logger: Logger instance to use
        fallback_delay: Default delay if rate limit reset time is not available

    Example:
        @handle_rate_limit(fallback_delay=30.0)
        async def make_api_call(self):
            # Implementation
            pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(func.__module__)

            try:
                return await func(*args, **kwargs)  # type: ignore[misc]
            except ProjectXRateLimitError as e:
                # Check if we have a reset time in the response
                reset_time = None
                if hasattr(e, "response_data") and e.response_data:
                    reset_time = e.response_data.get("reset_at")

                if reset_time:
                    # Calculate delay until reset
                    from datetime import datetime

                    try:
                        reset_dt = datetime.fromisoformat(
                            reset_time.replace("Z", "+00:00")
                        )
                        now = datetime.now(reset_dt.tzinfo)
                        delay = max((reset_dt - now).total_seconds(), 1.0)
                    except Exception:
                        delay = fallback_delay
                else:
                    delay = fallback_delay

                logger.warning(
                    f"Rate limit hit in {func.__name__}, waiting {delay:.1f}s",
                    extra={
                        "delay": delay,
                        "function": func.__name__,
                        "reset_time": reset_time,
                    },
                )

                await asyncio.sleep(delay)

                # Retry once after waiting
                return await func(*args, **kwargs)  # type: ignore[misc]

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            # Sync version is simpler - just re-raise
            # (rate limiting is primarily an async concern)
            return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return cast(Callable[..., T], async_wrapper)
        else:
            return cast(Callable[..., T], sync_wrapper)

    return decorator


def validate_response(
    required_fields: list[str] | None = None,
    response_type: type | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to validate API response structure.

    Args:
        required_fields: List of required fields in the response
        response_type: Expected type of the response

    Example:
        @validate_response(required_fields=["id", "status"], response_type=dict)
        async def get_order(self, order_id: str):
            # Implementation
            pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            result = await func(*args, **kwargs)  # type: ignore[misc]

            # Validate type
            if response_type is not None and not isinstance(result, response_type):
                raise ProjectXDataError(
                    f"Invalid response type from {func.__name__}: "
                    f"expected {response_type.__name__}, got {type(result).__name__}"
                )

            # Validate required fields
            if required_fields and isinstance(result, dict):
                missing_fields = [f for f in required_fields if f not in result]
                if missing_fields:
                    raise ProjectXDataError(
                        f"Missing required fields in response from {func.__name__}: "
                        f"{', '.join(missing_fields)}"
                    )

            return cast(T, result)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            result = func(*args, **kwargs)

            # Validate type
            if response_type is not None and not isinstance(result, response_type):
                raise ProjectXDataError(
                    f"Invalid response type from {func.__name__}: "
                    f"expected {response_type.__name__}, got {type(result).__name__}"
                )

            # Validate required fields
            if required_fields and isinstance(result, dict):
                missing_fields = [f for f in required_fields if f not in result]
                if missing_fields:
                    raise ProjectXDataError(
                        f"Missing required fields in response from {func.__name__}: "
                        f"{', '.join(missing_fields)}"
                    )

            return cast(T, result)  # type: ignore[redundant-cast]

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return cast(Callable[..., T], async_wrapper)
        else:
            return cast(Callable[..., T], sync_wrapper)

    return decorator


# Error context manager for batch operations
class ErrorContext:
    """
    Context manager for handling errors in batch operations.

    Collects errors during batch processing and provides summary.

    Example:
        async with ErrorContext("process orders") as ctx:
            for order in orders:
                try:
                    await process_order(order)
                except Exception as e:
                    ctx.add_error(order.id, e)

        if ctx.has_errors:
            logger.error(f"Failed to process {ctx.error_count} orders")
    """

    def __init__(self, operation: str, logger: logging.Logger | None = None):
        self.operation = operation
        self.logger = logger or logging.getLogger(__name__)
        self.errors: list[tuple[str, Exception]] = []

    def add_error(self, context: str, error: Exception) -> None:
        """Add an error to the context."""
        self.errors.append((context, error))

    @property
    def has_errors(self) -> bool:
        """Check if any errors were collected."""
        return len(self.errors) > 0

    @property
    def error_count(self) -> int:
        """Get the number of errors collected."""
        return len(self.errors)

    def get_summary(self) -> str:
        """Get a summary of all errors."""
        if not self.errors:
            return "No errors"

        error_types: dict[str, int] = {}
        for _, error in self.errors:
            error_type = type(error).__name__
            error_types[error_type] = error_types.get(error_type, 0) + 1

        summary_parts = [f"{count} {etype}" for etype, count in error_types.items()]
        return f"{self.error_count} errors: {', '.join(summary_parts)}"

    def __enter__(self) -> "ErrorContext":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Literal[False]:
        if self.has_errors:
            self.logger.error(
                f"Errors during {self.operation}: {self.get_summary()}",
                extra={
                    "operation": self.operation,
                    "error_count": self.error_count,
                    "errors": [
                        (ctx, str(e)) for ctx, e in self.errors[:10]
                    ],  # First 10
                },
            )
        return False  # Don't suppress exceptions

    async def __aenter__(self) -> "ErrorContext":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        return self.__exit__(exc_type, exc_val, exc_tb)
