"""Tests for error handling decorators and utilities."""

import logging
from datetime import UTC
from unittest.mock import Mock, patch

import httpx
import pytest

from project_x_py.exceptions import (
    ProjectXConnectionError,
    ProjectXDataError,
    ProjectXError,
    ProjectXRateLimitError,
    ProjectXServerError,
)
from project_x_py.utils.error_handler import (
    ErrorContext,
    handle_errors,
    handle_rate_limit,
    retry_on_network_error,
    validate_response,
)


class TestHandleErrors:
    """Test the handle_errors decorator."""

    def test_handle_errors_sync_success(self):
        """Test sync function succeeds without errors."""

        @handle_errors("test operation", reraise=True)
        def test_func(x: int) -> int:
            return x * 2

        result = test_func(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_handle_errors_async_success(self):
        """Test async function succeeds without errors."""

        @handle_errors("test operation", reraise=True)
        async def test_func(x: int) -> int:
            return x * 2

        result = await test_func(5)
        assert result == 10

    def test_handle_errors_sync_with_projectx_error(self, caplog):
        """Test sync function with ProjectX error."""

        @handle_errors("test operation", reraise=True)
        def test_func():
            raise ProjectXError("Test error", error_code=123)

        with pytest.raises(ProjectXError) as exc_info:
            test_func()

        assert str(exc_info.value) == "Test error"
        assert "ProjectX error during test operation" in caplog.text

    @pytest.mark.asyncio
    async def test_handle_errors_async_with_http_error(self, caplog):
        """Test async function with HTTP error."""

        @handle_errors("test operation", reraise=True)
        async def test_func():
            raise httpx.ConnectError("Connection failed")

        with pytest.raises(ProjectXConnectionError) as exc_info:
            await test_func()

        assert "HTTP error during test operation" in str(exc_info.value)
        assert "HTTP error during test operation" in caplog.text

    def test_handle_errors_no_reraise(self):
        """Test error handling without re-raising."""

        @handle_errors("test operation", reraise=False, default_return=42)
        def test_func():
            raise ValueError("Test error")

        result = test_func()
        assert result == 42

    @pytest.mark.asyncio
    async def test_handle_errors_with_custom_logger(self):
        """Test with custom logger."""
        mock_logger = Mock(spec=logging.Logger)

        @handle_errors("test operation", logger=mock_logger, reraise=False)
        async def test_func():
            raise ProjectXError("Test error")

        await test_func()
        mock_logger.error.assert_called_once()


class TestRetryOnNetworkError:
    """Test the retry_on_network_error decorator."""

    @pytest.mark.asyncio
    async def test_retry_async_success_first_try(self):
        """Test async function succeeds on first try."""
        call_count = 0

        @retry_on_network_error(max_attempts=3, initial_delay=0.1)
        async def test_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await test_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_async_success_after_retries(self):
        """Test async function succeeds after retries."""
        call_count = 0

        @retry_on_network_error(max_attempts=3, initial_delay=0.01)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("Connection failed")
            return "success"

        result = await test_func()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_async_max_attempts_exceeded(self):
        """Test async function fails after max attempts."""
        call_count = 0

        @retry_on_network_error(max_attempts=3, initial_delay=0.01)
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise httpx.TimeoutException("Timeout")

        with pytest.raises(httpx.TimeoutException):
            await test_func()

        assert call_count == 3

    def test_retry_sync_success_after_retries(self):
        """Test sync function succeeds after retries."""
        call_count = 0

        @retry_on_network_error(max_attempts=3, initial_delay=0.01)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ProjectXServerError("Server error")
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_with_custom_exceptions(self):
        """Test retry with custom exception types."""
        call_count = 0

        @retry_on_network_error(
            max_attempts=2, initial_delay=0.01, retry_on=(ValueError,)
        )
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Custom error")
            return "success"

        result = await test_func()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_exponential_backoff(self):
        """Test exponential backoff timing."""
        delays = []

        async def mock_sleep(delay):
            delays.append(delay)

        @retry_on_network_error(
            max_attempts=4, initial_delay=0.1, backoff_factor=2.0, max_delay=1.0
        )
        async def test_func():
            raise httpx.ConnectError("Connection failed")

        with patch("asyncio.sleep", mock_sleep):
            with pytest.raises(httpx.ConnectError):
                await test_func()

        # Check delays: 0.1, 0.2, 0.4 (capped at max_delay)
        assert len(delays) == 3
        assert delays[0] == 0.1
        assert delays[1] == 0.2
        assert delays[2] == 0.4


class TestHandleRateLimit:
    """Test the handle_rate_limit decorator."""

    @pytest.mark.asyncio
    async def test_handle_rate_limit_no_error(self):
        """Test function without rate limit error."""

        @handle_rate_limit(fallback_delay=1.0)
        async def test_func():
            return "success"

        result = await test_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_handle_rate_limit_with_retry(self):
        """Test rate limit handling with retry."""
        call_count = 0

        async def mock_sleep(delay):
            pass

        @handle_rate_limit(fallback_delay=0.1)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ProjectXRateLimitError("Rate limited")
            return "success"

        with patch("asyncio.sleep", mock_sleep):
            result = await test_func()

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_handle_rate_limit_with_reset_time(self):
        """Test rate limit handling with reset time in response."""
        from datetime import datetime, timedelta

        # Future reset time
        reset_time = datetime.now(UTC) + timedelta(seconds=5)

        call_count = 0
        actual_delay = None

        async def mock_sleep(delay):
            nonlocal actual_delay
            actual_delay = delay

        @handle_rate_limit()
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                error = ProjectXRateLimitError("Rate limited")
                error.response_data = {"reset_at": reset_time.isoformat()}
                raise error
            return "success"

        with patch("asyncio.sleep", mock_sleep):
            result = await test_func()

        assert result == "success"
        assert call_count == 2
        assert actual_delay is not None
        assert 4 <= actual_delay <= 6  # Should be close to 5 seconds


class TestValidateResponse:
    """Test the validate_response decorator."""

    @pytest.mark.asyncio
    async def test_validate_response_async_success(self):
        """Test async response validation success."""

        @validate_response(required_fields=["id", "status"], response_type=dict)
        async def test_func():
            return {"id": 123, "status": "active", "extra": "data"}

        result = await test_func()
        assert result["id"] == 123
        assert result["status"] == "active"

    def test_validate_response_sync_success(self):
        """Test sync response validation success."""

        @validate_response(required_fields=["name"], response_type=dict)
        def test_func():
            return {"name": "test", "value": 42}

        result = test_func()
        assert result["name"] == "test"

    @pytest.mark.asyncio
    async def test_validate_response_wrong_type(self):
        """Test validation fails with wrong type."""

        @validate_response(response_type=dict)
        async def test_func():
            return ["not", "a", "dict"]

        with pytest.raises(ProjectXDataError) as exc_info:
            await test_func()

        assert "expected dict, got list" in str(exc_info.value)

    def test_validate_response_missing_fields(self):
        """Test validation fails with missing fields."""

        @validate_response(required_fields=["id", "name", "status"])
        def test_func():
            return {"id": 123, "status": "active"}

        with pytest.raises(ProjectXDataError) as exc_info:
            test_func()

        assert "Missing required fields" in str(exc_info.value)
        assert "name" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_response_no_validation(self):
        """Test decorator with no validation criteria."""

        @validate_response()
        async def test_func():
            return "any value"

        result = await test_func()
        assert result == "any value"


class TestErrorContext:
    """Test the ErrorContext context manager."""

    def test_error_context_no_errors(self):
        """Test context with no errors."""
        with ErrorContext("test operation") as ctx:
            # Do some work without errors
            pass

        assert not ctx.has_errors
        assert ctx.error_count == 0
        assert ctx.get_summary() == "No errors"

    def test_error_context_with_errors(self, caplog):
        """Test context with collected errors."""
        with ErrorContext("test operation") as ctx:
            ctx.add_error("item1", ValueError("Bad value"))
            ctx.add_error("item2", KeyError("Missing key"))
            ctx.add_error("item3", ValueError("Another bad value"))

        assert ctx.has_errors
        assert ctx.error_count == 3
        summary = ctx.get_summary()
        assert "2 ValueError" in summary
        assert "1 KeyError" in summary
        assert "Errors during test operation" in caplog.text

    @pytest.mark.asyncio
    async def test_error_context_async(self):
        """Test async context manager."""
        errors_found = []

        async with ErrorContext("async operation") as ctx:
            for i in range(5):
                try:
                    if i % 2 == 0:
                        raise ValueError(f"Error {i}")
                except Exception as e:
                    ctx.add_error(f"item{i}", e)
                    errors_found.append(i)

        assert ctx.error_count == 3
        assert errors_found == [0, 2, 4]

    def test_error_context_with_exception(self):
        """Test context doesn't suppress exceptions."""
        with pytest.raises(RuntimeError):
            with ErrorContext("failing operation") as ctx:
                ctx.add_error("pre-error", ValueError("Before main error"))
                raise RuntimeError("Main error")

        # Context should still have the pre-error
        assert ctx.error_count == 1
