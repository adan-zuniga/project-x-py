"""
Standardized error messages for ProjectX SDK.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides consistent error messages and error formatting utilities to ensure
    uniform error reporting across the SDK. Includes standardized error codes,
    message templates, and error context creation for comprehensive error handling.

Key Features:
    - Standardized error messages for common scenarios
    - Error code categorization for different error types
    - Error message formatting with dynamic values
    - Error context creation with metadata
    - Exception enhancement with additional context
    - Comprehensive error categorization system

Error Categories:
    - Authentication: Login, token, and permission errors
    - Connection: Network, timeout, and SSL errors
    - API: Endpoint, method, and server errors
    - Data: Validation, parsing, and format errors
    - Trading: Order, position, and instrument errors
    - WebSocket: Connection, subscription, and message errors
    - Configuration: Missing, invalid, and parse errors

Example Usage:
    ```python
    from project_x_py.utils import (
        ErrorMessages,
        ErrorCode,
        format_error_message,
        create_error_context,
        enhance_exception,
    )

    # Use standardized error messages
    error_msg = format_error_message(
        ErrorMessages.API_RESOURCE_NOT_FOUND, resource="order/123"
    )
    # Returns: "Resource not found: order/123"

    # Create error context
    context = create_error_context("place_order", order_id="123", side="buy")

    # Enhance exceptions with context
    try:
        # Some operation
        pass
    except Exception as e:
        enhanced_error = enhance_exception(e, "place_order", order_id="123")
        raise enhanced_error

    # Get error code for categorization
    error_code = get_error_code(exception)
    if error_code == ErrorCode.API_RATE_LIMIT:
        # Handle rate limit error
        pass
    ```

Error Message Features:
    - Template-based messages with dynamic values
    - Comprehensive error categorization
    - Standardized error codes for programmatic handling
    - Rich error context with metadata
    - Exception enhancement with additional information
    - Consistent error reporting across all modules

Error Code Categories:
    - 1xxx: Authentication errors (AUTH_REQUIRED, AUTH_INVALID, etc.)
    - 2xxx: Connection errors (CONN_FAILED, CONN_TIMEOUT, etc.)
    - 3xxx: API errors (API_NOT_FOUND, API_RATE_LIMIT, etc.)
    - 4xxx: Data errors (DATA_VALIDATION, DATA_PARSING, etc.)
    - 5xxx: Trading errors (ORDER_INVALID, POSITION_NOT_FOUND, etc.)
    - 6xxx: WebSocket errors (WS_CONNECTION, WS_AUTH, etc.)
    - 9xxx: Internal errors (INTERNAL_ERROR, NOT_IMPLEMENTED, etc.)

Performance Characteristics:
    - Efficient error message formatting
    - Minimal memory overhead for error context
    - Fast error code categorization
    - Thread-safe error handling operations
    - Optimized for high-frequency error scenarios

See Also:
    - `utils.error_handler`: Error handling decorators and utilities
    - `utils.logging_config`: Logging for error reporting
"""

from datetime import UTC
from typing import Any


class ErrorMessages:
    """Standardized error messages for common scenarios."""

    # Authentication errors
    AUTH_MISSING_CREDENTIALS = "Missing authentication credentials"
    AUTH_INVALID_CREDENTIALS = "Invalid authentication credentials"
    AUTH_TOKEN_EXPIRED = "Authentication token has expired"
    AUTH_TOKEN_INVALID = "Invalid authentication token"
    AUTH_SESSION_EXPIRED = "Session has expired, please re-authenticate"
    AUTH_PERMISSION_DENIED = "Permission denied for this operation"
    AUTH_FAILED = "Authentication failed"
    AUTH_NO_ACCOUNTS = "No accounts found for user"

    # Connection errors
    CONN_FAILED = "Failed to connect to ProjectX API"
    CONN_TIMEOUT = "Connection timed out"
    CONN_LOST = "Lost connection to server"
    CONN_REFUSED = "Connection refused by server"
    CONN_SSL_ERROR = "SSL/TLS connection error"

    # API errors
    API_INVALID_ENDPOINT = "Invalid API endpoint: {endpoint}"
    API_METHOD_NOT_ALLOWED = "HTTP method {method} not allowed for {endpoint}"
    API_RESOURCE_NOT_FOUND = "Resource not found: {resource}"
    API_INVALID_REQUEST = "Invalid request: {reason}"
    API_SERVER_ERROR = "Server error: {status_code} - {message}"
    API_RATE_LIMITED = "Rate limit exceeded, retry after {retry_after}s"
    API_REQUEST_FAILED = "API request failed"

    # Data validation errors
    DATA_MISSING_FIELD = "Missing required field: {field}"
    DATA_INVALID_TYPE = "Invalid type for {field}: expected {expected}, got {actual}"
    DATA_INVALID_VALUE = "Invalid value for {field}: {value}"
    DATA_PARSE_ERROR = "Failed to parse {data_type}: {reason}"
    DATA_VALIDATION_FAILED = "Data validation failed: {errors}"

    # Order errors
    ORDER_INVALID_SIDE = "Invalid order side: {side}"
    ORDER_INVALID_TYPE = "Invalid order type: {order_type}"
    ORDER_NO_ACCOUNT = "No account information available"
    ORDER_FAILED = "Order placement failed"
    ORDER_SEARCH_FAILED = "Order search failed"
    ORDER_INVALID_SIZE = "Invalid order size: {size}"
    ORDER_INVALID_PRICE = "Invalid order price: {price}"
    ORDER_NOT_FOUND = "Order not found: {order_id}"
    ORDER_ALREADY_FILLED = "Order already filled: {order_id}"
    ORDER_ALREADY_CANCELLED = "Order already cancelled: {order_id}"
    ORDER_CANCEL_FAILED = "Failed to cancel order {order_id}: {reason}"
    ORDER_MODIFY_FAILED = "Failed to modify order {order_id}: {reason}"
    ORDER_INSUFFICIENT_MARGIN = "Insufficient margin for order"
    ORDER_MARKET_CLOSED = "Market is closed for {instrument}"
    ORDER_RISK_EXCEEDED = "Order exceeds risk limits"

    # Position errors
    POSITION_NOT_FOUND = "Position not found: {position_id}"
    POSITION_ALREADY_CLOSED = "Position already closed: {position_id}"
    POSITION_INSUFFICIENT_SIZE = "Insufficient position size for operation"
    POSITION_WRONG_SIDE = "Operation not allowed for {side} position"

    # Instrument errors
    INSTRUMENT_NOT_FOUND = "Instrument not found: {symbol}"
    INSTRUMENT_NOT_TRADEABLE = "Instrument not tradeable: {symbol}"
    INSTRUMENT_MARKET_CLOSED = "Market closed for {symbol}"
    INSTRUMENT_INVALID_SYMBOL = "Invalid symbol format: {symbol}"

    # WebSocket errors
    WS_CONNECTION_FAILED = "WebSocket connection failed: {reason}"
    WS_AUTHENTICATION_FAILED = "WebSocket authentication failed"
    WS_SUBSCRIPTION_FAILED = "Failed to subscribe to {channel}: {reason}"
    WS_MESSAGE_PARSE_ERROR = "Failed to parse WebSocket message"
    WS_UNEXPECTED_CLOSE = "WebSocket closed unexpectedly: {code} - {reason}"

    # Configuration errors
    CONFIG_MISSING = "Missing configuration: {key}"
    CONFIG_INVALID = "Invalid configuration value for {key}: {value}"
    CONFIG_FILE_NOT_FOUND = "Configuration file not found: {path}"
    CONFIG_PARSE_ERROR = "Failed to parse configuration: {reason}"

    # Account errors
    ACCOUNT_NOT_FOUND = (
        "Account '{account_name}' not found. Available accounts: {available_accounts}"
    )

    # General errors
    INTERNAL_ERROR = "Internal error: {reason}"
    NOT_IMPLEMENTED = "Feature not implemented: {feature}"
    OPERATION_FAILED = "Operation failed: {operation}"
    INVALID_STATE = "Invalid state for operation: {state}"
    TIMEOUT = "Operation timed out after {timeout}s"


def format_error_message(template: str, **kwargs: Any) -> str:
    """
    Format an error message template with provided values.

    Args:
        template: Error message template with {placeholders}
        **kwargs: Values to substitute in template

    Returns:
        Formatted error message

    Example:
        >>> format_error_message(
        ...     ErrorMessages.API_RESOURCE_NOT_FOUND, resource="order/123"
        ... )
        "Resource not found: order/123"
    """
    try:
        return template.format(**kwargs)
    except KeyError as e:
        # If a placeholder is missing, include it in the error
        return f"{template} (missing value for: {e})"


def create_error_context(
    operation: str,
    **details: Any,
) -> dict[str, Any]:
    """
    Create standardized error context dictionary.

    Args:
        operation: Operation that failed
        **details: Additional error details

    Returns:
        Error context dictionary
    """
    import time
    from datetime import datetime

    context = {
        "operation": operation,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "timestamp_unix": time.time(),
    }

    # Add details, filtering out None values
    for key, value in details.items():
        if value is not None:
            context[key] = value

    return context


def enhance_exception(
    exception: Exception,
    operation: str,
    **context: Any,
) -> Exception:
    """
    Enhance an exception with additional context.

    Args:
        exception: Original exception
        operation: Operation that failed
        **context: Additional context

    Returns:
        Enhanced exception with context
    """
    # Import here to avoid circular dependency
    from project_x_py.exceptions import ProjectXError

    # Create context dict
    error_context = create_error_context(operation, **context)

    # If it's already a ProjectX exception, enhance it
    if isinstance(exception, ProjectXError):
        # Update response data with context
        if exception.response_data is None:
            exception.response_data = {}  # type: ignore[unreachable]
        exception.response_data.update(error_context)
        return exception

    # Wrap in ProjectXError
    message = f"{operation} failed: {exception!s}"
    return ProjectXError(
        message=message,
        response_data=error_context,
    )


class ErrorCode:
    """Standard error codes for categorizing errors."""

    # Authentication (1xxx)
    AUTH_REQUIRED = 1001
    AUTH_INVALID = 1002
    AUTH_EXPIRED = 1003
    AUTH_PERMISSION = 1004

    # Connection (2xxx)
    CONN_FAILED = 2001
    CONN_TIMEOUT = 2002
    CONN_LOST = 2003
    CONN_SSL = 2004

    # API (3xxx)
    API_NOT_FOUND = 3404
    API_BAD_REQUEST = 3400
    API_FORBIDDEN = 3403
    API_RATE_LIMIT = 3429
    API_SERVER_ERROR = 3500

    # Data (4xxx)
    DATA_VALIDATION = 4001
    DATA_PARSING = 4002
    DATA_MISSING = 4003
    DATA_INVALID = 4004

    # Trading (5xxx)
    ORDER_INVALID = 5001
    ORDER_NOT_FOUND = 5002
    ORDER_REJECTED = 5003
    POSITION_INVALID = 5101
    POSITION_NOT_FOUND = 5102

    # WebSocket (6xxx)
    WS_CONNECTION = 6001
    WS_AUTH = 6002
    WS_SUBSCRIPTION = 6003
    WS_MESSAGE = 6004

    # Internal (9xxx)
    INTERNAL_ERROR = 9001
    NOT_IMPLEMENTED = 9002
    INVALID_STATE = 9003


def get_error_code(exception: Exception) -> int | None:
    """
    Get standardized error code for an exception.

    Args:
        exception: Exception to categorize

    Returns:
        Error code or None if not categorizable
    """
    from project_x_py.exceptions import (
        ProjectXAuthenticationError,
        ProjectXConnectionError,
        ProjectXDataError,
        ProjectXError,
        ProjectXRateLimitError,
        ProjectXServerError,
    )

    if isinstance(exception, ProjectXAuthenticationError):
        return ErrorCode.AUTH_INVALID
    elif isinstance(exception, ProjectXRateLimitError):
        return ErrorCode.API_RATE_LIMIT
    elif isinstance(exception, ProjectXServerError):
        return ErrorCode.API_SERVER_ERROR
    elif isinstance(exception, ProjectXConnectionError):
        return ErrorCode.CONN_FAILED
    elif isinstance(exception, ProjectXDataError):
        return ErrorCode.DATA_INVALID
    elif isinstance(exception, ProjectXError):
        # Check if it has an error code already
        if hasattr(exception, "error_code") and exception.error_code:
            return exception.error_code
        return ErrorCode.INTERNAL_ERROR
    else:
        return None
