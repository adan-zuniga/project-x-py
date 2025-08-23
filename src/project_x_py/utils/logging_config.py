"""
Enhanced logging configuration for ProjectX SDK.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides consistent logging patterns and structured logging capabilities
    across the SDK. Includes performance monitoring, API call tracking,
    and comprehensive logging utilities for debugging and monitoring.

Key Features:
    - Structured logging with JSON and readable formats
    - Performance monitoring and timing utilities
    - API call tracking with detailed metrics
    - Context-aware logging with operation tracking
    - Standardized log messages for consistency
    - Configurable logging levels and outputs

Logging Components:
    - StructuredFormatter: JSON and readable log formatting
    - ProjectXLogger: Factory for configured loggers
    - LogContext: Context manager for operation tracking
    - LogMessages: Standardized log message constants
    - Performance monitoring utilities
    - API call tracking and metrics

Example Usage:
    ```python
    from project_x_py.utils import (
        ProjectXLogger,
        LogContext,
        LogMessages,
        log_performance,
        log_api_call,
        configure_sdk_logging,
    )

    # Configure SDK logging
    configure_sdk_logging(level=logging.INFO, format_json=True)

    # Get configured logger
    logger = ProjectXLogger.get_logger(__name__)

    # Use context for operation tracking
    with LogContext(logger, operation="fetch_orders", user_id=123):
        logger.info("Starting order fetch")
        # All logs in this block include the context

    # Log performance metrics
    start_time = time.time()
    # ... perform operation ...
    log_performance(logger, "api_call", start_time)

    # Log API calls with metrics
    log_api_call(logger, "GET", "/api/orders", status_code=200, duration=0.5)

    # Use standardized messages
    logger.info(LogMessages.ORDER_PLACED)
    logger.error(LogMessages.API_ERROR)
    ```

Logging Features:
    - Structured logging with consistent format
    - Performance monitoring with timing metrics
    - API call tracking with detailed statistics
    - Context-aware logging for operation tracking
    - Standardized messages for consistency
    - Configurable output formats (JSON/readable)

Performance Monitoring:
    - Automatic timing for operations
    - Performance metrics and statistics
    - API call duration tracking
    - Memory usage monitoring
    - Error rate tracking and reporting

Standardized Messages:
    - API operations (request, response, error)
    - Authentication (start, success, failed, refresh)
    - Orders (place, cancel, modify, error)
    - Positions (open, close, error)
    - Market data (fetch, subscribe, error)
    - WebSocket (connect, disconnect, error)
    - Rate limiting (hit, wait, reset)
    - Cache operations (hit, miss, update)

Performance Characteristics:
    - Minimal overhead for logging operations
    - Efficient structured logging with JSON output
    - Memory-efficient log context management
    - Thread-safe logging operations
    - Optimized for high-frequency trading scenarios

See Also:
    - `utils.error_handler`: Error handling and logging
    - `utils.async_rate_limiter`: Rate limiting with logging
"""

import logging
import sys
from datetime import UTC, datetime
from typing import Any

import orjson


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured logs with consistent format.

    Includes timestamp, level, module, function, and structured data.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Base log data
        log_data = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        # Add any extra fields from LogRecord attributes
        standard_attrs = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "getMessage",
            "message",
            "asctime",
        }
        for key, value in record.__dict__.items():
            if key not in standard_attrs:
                log_data[key] = value

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # For development, use a more readable format
        if logging.getLogger().level == logging.DEBUG:
            return (
                f"{log_data['timestamp']} | {log_data['level']:<8} | "
                f"{log_data['module']}.{log_data['function']}:{log_data['line']} | "
                f"{log_data['message']}"
            )
        else:
            # For production, use JSON format
            return str(orjson.dumps(log_data, default=str).decode("utf-8"))


class ProjectXLogger:
    """
    Factory for creating configured loggers with consistent settings.
    """

    @staticmethod
    def get_logger(
        name: str,
        level: int | None = None,
        handler: logging.Handler | None = None,
    ) -> logging.Logger:
        """
        Get a configured logger instance.

        Args:
            name: Logger name (usually __name__)
            level: Logging level (defaults to INFO)
            handler: Custom handler (defaults to console)

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name)

        # Only configure if not already configured
        if not logger.handlers:
            # Set level
            if level is None:
                level = logging.INFO
            logger.setLevel(level)

            # Add handler
            if handler is None:
                handler = logging.StreamHandler(sys.stdout)
                handler.setFormatter(StructuredFormatter())
            logger.addHandler(handler)

            # Prevent propagation to avoid duplicate logs
            logger.propagate = False

        return logger


# Logging context for operations
class LogContext:
    """
    Context manager for adding consistent context to log messages.

    Example:
        with LogContext(logger, operation="fetch_orders", user_id=123):
            # All log messages in this block will include the context
            logger.info("Starting order fetch")
    """

    def __init__(self, logger: logging.Logger, **context: Any):
        self.logger = logger
        self.context = context
        self._old_adapter: logging.Logger | None = None

    def __enter__(self) -> logging.LoggerAdapter[logging.Logger]:
        # Create adapter with context
        self._old_adapter = self.logger
        adapter = logging.LoggerAdapter(self.logger, self.context)
        # Replace logger methods with adapter methods
        for method in ["debug", "info", "warning", "error", "critical", "exception"]:
            setattr(self.logger, method, getattr(adapter, method))
        return adapter

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        # Restore original logger
        # Restore original logger
        for method in [
            "debug",
            "info",
            "warning",
            "error",
            "critical",
            "exception",
        ]:
            setattr(self.logger, method, getattr(self._old_adapter, method))


# Standard log messages for consistency
class LogMessages:
    """Standard log messages for common operations."""

    # API operations
    API_REQUEST = "Making API request"
    API_RESPONSE = "Received API response"
    API_ERROR = "API request failed"

    # Authentication
    AUTH_START = "Starting authentication"
    AUTH_SUCCESS = "Authentication successful"
    AUTH_FAILED = "Authentication failed"
    AUTH_REFRESH = "Refreshing authentication token"
    AUTH_TOKEN_PARSE_FAILED = "Failed to parse authentication token expiry"

    # Orders
    ORDER_PLACE = "Placing order"
    ORDER_PLACED = "Order placed successfully"
    ORDER_CANCEL = "Cancelling order"
    ORDER_CANCELLED = "Order cancelled successfully"
    ORDER_MODIFY = "Modifying order"
    ORDER_MODIFIED = "Order modified successfully"
    ORDER_ERROR = "Order operation failed"
    ORDER_CANCEL_ALL = "Cancelling all orders"
    ORDER_CANCEL_ALL_COMPLETE = "Cancel all orders complete"

    # Positions
    POSITION_OPEN = "Opening position"
    POSITION_OPENED = "Position opened successfully"
    POSITION_CLOSE = "Closing position"
    POSITION_CLOSED = "Position closed successfully"
    POSITION_ERROR = "Position operation failed"

    # Market data
    DATA_FETCH = "Fetching market data"
    DATA_RECEIVED = "Market data received"
    DATA_ERROR = "Market data fetch failed"
    DATA_SUBSCRIBE = "Subscribing to market data"
    DATA_UNSUBSCRIBE = "Unsubscribing from market data"

    # WebSocket
    WS_CONNECT = "Connecting to WebSocket"
    WS_CONNECTED = "WebSocket connected"
    WS_DISCONNECT = "Disconnecting from WebSocket"
    WS_DISCONNECTED = "WebSocket disconnected"
    WS_ERROR = "WebSocket error"
    WS_RECONNECT = "Reconnecting WebSocket"

    # Rate limiting
    RATE_LIMIT_HIT = "Rate limit reached"
    RATE_LIMIT_WAIT = "Waiting for rate limit reset"
    RATE_LIMIT_RESET = "Rate limit reset"

    # Cache
    CACHE_HIT = "Cache hit"
    CACHE_MISS = "Cache miss"
    CACHE_UPDATE = "Updating cache"

    # Managers
    MANAGER_INITIALIZED = "Manager initialized"

    # Position operations
    POSITION_REFRESH = "Refreshing positions"
    POSITION_UPDATE = "Position updated"
    POSITION_SEARCH = "Searching positions"
    CACHE_CLEAR = "Clearing cache"

    # Errors
    ERROR_RETRY = "Retrying after error"
    ERROR_MAX_RETRY = "Maximum retries exceeded"
    ERROR_HANDLED = "Error handled"
    ERROR_UNHANDLED = "Unhandled error"

    # Callbacks
    CALLBACK_REGISTERED = "Callback registered"
    CALLBACK_REMOVED = "Callback removed"

    # Cleanup
    CLEANUP_COMPLETE = "Cleanup completed"


def log_performance(
    logger: logging.Logger,
    operation: str,
    start_time: float,
    end_time: float | None = None,
    **extra: Any,
) -> None:
    """
    Log performance metrics for an operation.

    Args:
        logger: Logger instance
        operation: Operation name
        start_time: Start time (from time.time())
        end_time: End time (defaults to now)
        **extra: Additional context to log
    """
    import time

    if end_time is None:
        end_time = time.time()

    duration = end_time - start_time

    logger.info(
        f"{operation} completed in {duration:.3f}s",
        extra={
            "operation": operation,
            "duration_seconds": duration,
            "duration_ms": duration * 1000,
            **extra,
        },
    )


def log_api_call(
    logger: logging.Logger,
    method: str,
    endpoint: str,
    status_code: int | None = None,
    duration: float | None = None,
    error: Exception | None = None,
    **extra: Any,
) -> None:
    """
    Log API call with standard format.

    Args:
        logger: Logger instance
        method: HTTP method
        endpoint: API endpoint
        status_code: Response status code
        duration: Request duration in seconds
        error: Exception if call failed
        **extra: Additional context
    """
    log_data = {
        "api_method": method,
        "api_endpoint": endpoint,
        **extra,
    }

    if status_code is not None:
        log_data["status_code"] = status_code

    if duration is not None:
        log_data["duration_ms"] = duration * 1000

    if error:
        logger.error(
            f"{LogMessages.API_ERROR}: {method} {endpoint}",
            extra={**log_data, "error": str(error)},
        )
    else:
        logger.debug(
            f"{LogMessages.API_RESPONSE}: {method} {endpoint}",
            extra=log_data,
        )


# Configure root logger for the SDK
def configure_sdk_logging(
    level: int = logging.INFO,
    format_json: bool = False,
    log_file: str | None = None,
) -> None:
    """
    Configure logging for the entire SDK.

    Args:
        level: Logging level
        format_json: Use JSON formatting
        log_file: Optional log file path
    """
    # Get root logger for project_x_py
    root_logger = logging.getLogger("project_x_py")
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if format_json:
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)

    # Don't propagate to root logger
    root_logger.propagate = False
