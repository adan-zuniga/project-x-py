"""Tests for error messages and error utilities."""

import pytest

from project_x_py.exceptions import (
    ProjectXAuthenticationError,
    ProjectXConnectionError,
    ProjectXDataError,
    ProjectXError,
    ProjectXRateLimitError,
)
from project_x_py.utils.error_messages import (
    ErrorCode,
    ErrorMessages,
    create_error_context,
    enhance_exception,
    format_error_message,
    get_error_code,
)


class TestErrorMessages:
    """Test error message constants and formatting."""

    def test_error_message_constants(self):
        """Test that error message constants are defined."""
        assert (
            ErrorMessages.AUTH_MISSING_CREDENTIALS
            == "Missing authentication credentials"
        )
        assert ErrorMessages.CONN_TIMEOUT == "Connection timed out"
        assert ErrorMessages.ORDER_NOT_FOUND == "Order not found: {order_id}"
        assert (
            ErrorMessages.API_RATE_LIMITED
            == "Rate limit exceeded, retry after {retry_after}s"
        )

    def test_format_error_message_success(self):
        """Test successful error message formatting."""
        msg = format_error_message(
            ErrorMessages.API_RESOURCE_NOT_FOUND, resource="order/12345"
        )
        assert msg == "Resource not found: order/12345"

        msg = format_error_message(ErrorMessages.ORDER_INVALID_SIZE, size=-5)
        assert msg == "Invalid order size: -5"

    def test_format_error_message_missing_placeholder(self):
        """Test formatting with missing placeholder."""
        msg = format_error_message(
            ErrorMessages.API_RATE_LIMITED
            # Missing retry_after parameter
        )
        assert "missing value for: 'retry_after'" in msg

    def test_format_error_message_extra_params(self):
        """Test formatting with extra parameters (should be ignored)."""
        msg = format_error_message(ErrorMessages.CONN_TIMEOUT, extra_param="ignored")
        assert msg == "Connection timed out"


class TestErrorContext:
    """Test error context creation."""

    def test_create_error_context_basic(self):
        """Test basic error context creation."""
        context = create_error_context("test_operation")

        assert context["operation"] == "test_operation"
        assert "timestamp" in context
        assert "timestamp_unix" in context
        assert context["timestamp"].endswith("Z")

    def test_create_error_context_with_details(self):
        """Test error context with additional details."""
        context = create_error_context(
            "place_order",
            instrument="ES",
            size=10,
            side="BUY",
            order_id=None,  # Should be filtered out
        )

        assert context["operation"] == "place_order"
        assert context["instrument"] == "ES"
        assert context["size"] == 10
        assert context["side"] == "BUY"
        assert "order_id" not in context  # None values filtered

    def test_create_error_context_timestamps(self):
        """Test timestamp fields are properly formatted."""
        import time

        before = time.time()
        context = create_error_context("test")
        after = time.time()

        # Unix timestamp should be in range
        assert before <= context["timestamp_unix"] <= after

        # ISO timestamp should parse correctly
        from datetime import datetime

        dt = datetime.fromisoformat(context["timestamp"].replace("Z", "+00:00"))
        assert dt.timestamp() == pytest.approx(context["timestamp_unix"], rel=0.01)


class TestEnhanceException:
    """Test exception enhancement."""

    def test_enhance_standard_exception(self):
        """Test enhancing a standard exception."""
        original = ValueError("Invalid value")
        enhanced = enhance_exception(
            original, "process_data", input_type="string", value="abc123"
        )

        assert isinstance(enhanced, ProjectXError)
        assert "process_data failed" in str(enhanced)
        assert "Invalid value" in str(enhanced)
        assert enhanced.response_data["operation"] == "process_data"
        assert enhanced.response_data["input_type"] == "string"

    def test_enhance_projectx_exception(self):
        """Test enhancing an existing ProjectX exception."""
        original = ProjectXDataError("Bad data", error_code=4001)
        original.response_data = {"existing": "data"}

        enhanced = enhance_exception(original, "validate_order", order_type="LIMIT")

        # Should be the same instance
        assert enhanced is original
        # Should preserve existing data
        assert enhanced.response_data["existing"] == "data"
        # Should add new context
        assert enhanced.response_data["operation"] == "validate_order"
        assert enhanced.response_data["order_type"] == "LIMIT"

    def test_enhance_exception_no_response_data(self):
        """Test enhancing ProjectX exception without response_data."""
        original = ProjectXError("Test error")
        enhanced = enhance_exception(original, "test_op", key="value")

        assert enhanced is original
        assert enhanced.response_data is not None
        assert enhanced.response_data["key"] == "value"


class TestErrorCode:
    """Test error code constants and utilities."""

    def test_error_code_constants(self):
        """Test error code constant values."""
        # Auth codes (1xxx)
        assert ErrorCode.AUTH_REQUIRED == 1001
        assert ErrorCode.AUTH_EXPIRED == 1003

        # Connection codes (2xxx)
        assert ErrorCode.CONN_FAILED == 2001
        assert ErrorCode.CONN_TIMEOUT == 2002

        # API codes (3xxx)
        assert ErrorCode.API_NOT_FOUND == 3404
        assert ErrorCode.API_BAD_REQUEST == 3400
        assert ErrorCode.API_RATE_LIMIT == 3429

        # Trading codes (5xxx)
        assert ErrorCode.ORDER_INVALID == 5001
        assert ErrorCode.POSITION_NOT_FOUND == 5102

    def test_get_error_code_for_exceptions(self):
        """Test getting error codes for different exception types."""
        # Authentication error
        exc = ProjectXAuthenticationError("Auth failed")
        assert get_error_code(exc) == ErrorCode.AUTH_INVALID

        # Rate limit error
        exc = ProjectXRateLimitError("Too many requests")
        assert get_error_code(exc) == ErrorCode.API_RATE_LIMIT

        # Connection error
        exc = ProjectXConnectionError("Network error")
        assert get_error_code(exc) == ErrorCode.CONN_FAILED

        # Data error
        exc = ProjectXDataError("Invalid data")
        assert get_error_code(exc) == ErrorCode.DATA_INVALID

    def test_get_error_code_with_existing_code(self):
        """Test getting error code when exception already has one."""
        exc = ProjectXError("Test error", error_code=9999)
        assert get_error_code(exc) == 9999

    def test_get_error_code_for_standard_exception(self):
        """Test getting error code for non-ProjectX exception."""
        exc = ValueError("Not a ProjectX error")
        assert get_error_code(exc) is None

    def test_get_error_code_generic_projectx_error(self):
        """Test getting error code for generic ProjectX error."""
        exc = ProjectXError("Generic error")
        assert get_error_code(exc) == ErrorCode.INTERNAL_ERROR
