"""
Comprehensive async tests converted from synchronous test files.

Tests both sync and async components to ensure compatibility.
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from project_x_py import (
    AsyncProjectX,
    ProjectX,
    ProjectXAuthenticationError,
    ProjectXConfig,
)


class TestAsyncProjectXClient:
    """Test suite for the async ProjectX client."""

    @pytest.mark.asyncio
    async def test_async_init_with_credentials(self):
        """Test async client initialization with explicit credentials."""
        client = AsyncProjectX(username="test_user", api_key="test_key")

        assert client.username == "test_user"
        assert client.api_key == "test_key"
        assert client.account_name is None
        assert client.session_token == ""

    @pytest.mark.asyncio
    async def test_async_init_with_config(self):
        """Test async client initialization with custom configuration."""
        config = ProjectXConfig(timeout_seconds=60, retry_attempts=5)

        client = AsyncProjectX(username="test_user", api_key="test_key", config=config)

        assert client.config.timeout_seconds == 60
        assert client.config.retry_attempts == 5

    @pytest.mark.asyncio
    async def test_async_init_missing_credentials(self):
        """Test async client initialization with missing credentials."""
        # AsyncProjectX doesn't validate credentials at init time
        client1 = AsyncProjectX(username="", api_key="test_key")
        client2 = AsyncProjectX(username="test_user", api_key="")

        # Validation happens during authentication
        assert client1.username == ""
        assert client2.api_key == ""

    @pytest.mark.asyncio
    async def test_async_authenticate_success(self):
        """Test successful async authentication."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock successful authentication response
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": True,
                "token": "test_jwt_token",
            }
            mock_response.raise_for_status.return_value = None
            mock_client.post.return_value = mock_response

            async with AsyncProjectX(
                username="test_user", api_key="test_key"
            ) as client:
                await client.authenticate()

                assert client.session_token == "test_jwt_token"

                # Verify the request was made correctly
                mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_authenticate_failure(self):
        """Test async authentication failure."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock failed authentication response
            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {
                "success": False,
                "errorMessage": "Invalid credentials",
            }
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "401 Unauthorized", request=Mock(), response=mock_response
            )
            mock_client.post.return_value = mock_response

            async with AsyncProjectX(
                username="test_user", api_key="test_key"
            ) as client:
                with pytest.raises(ProjectXAuthenticationError):
                    await client.authenticate()

    @pytest.mark.asyncio
    async def test_async_concurrent_operations(self):
        """Test concurrent async operations."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock authentication
            auth_response = AsyncMock()
            auth_response.status_code = 200
            auth_response.json.return_value = {"success": True, "token": "test_token"}
            auth_response.raise_for_status.return_value = None

            # Mock account info
            account_response = AsyncMock()
            account_response.status_code = 200
            account_response.json.return_value = {
                "simAccounts": [
                    {
                        "id": "12345",
                        "name": "Test Account",
                        "balance": 50000.0,
                        "canTrade": True,
                        "simulated": True,
                    }
                ],
                "liveAccounts": [],
            }
            account_response.raise_for_status.return_value = None

            # Mock API responses
            mock_responses = {
                "positions": {"success": True, "positions": []},
                "orders": {"success": True, "orders": []},
                "instruments": {"success": True, "instruments": []},
            }

            async def mock_response_func(url, **kwargs):
                response = AsyncMock()
                response.status_code = 200
                response.raise_for_status.return_value = None

                if "/auth/login" in url:
                    response.json.return_value = {
                        "success": True,
                        "token": "test_token",
                    }
                elif "/account" in url or "account" in url.lower():
                    response.json.return_value = account_response.json.return_value
                elif "positions" in url:
                    response.json.return_value = mock_responses["positions"]
                elif "orders" in url:
                    response.json.return_value = mock_responses["orders"]
                elif "instruments" in url:
                    response.json.return_value = mock_responses["instruments"]
                else:
                    response.json.return_value = {"success": True}

                return response

            mock_client.post = mock_response_func
            mock_client.get = mock_response_func

            async with AsyncProjectX(
                username="test_user", api_key="test_key"
            ) as client:
                await client.authenticate()

                # Test concurrent operations
                results = await asyncio.gather(
                    client.search_open_positions(),
                    client.search_open_orders(),
                    client.search_instruments("TEST"),
                )

                assert len(results) == 3
                assert all(result is not None for result in results)

    @pytest.mark.asyncio
    async def test_async_context_manager_cleanup(self):
        """Test that async context manager properly cleans up resources."""
        cleanup_called = False

        class MockAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                nonlocal cleanup_called
                cleanup_called = True

            async def post(self, *args, **kwargs):
                response = AsyncMock()
                response.status_code = 200
                response.json.return_value = {"success": True}
                response.raise_for_status.return_value = None
                return response

        with patch("httpx.AsyncClient", MockAsyncClient):
            async with AsyncProjectX(
                username="test_user", api_key="test_key"
            ) as client:
                pass

        assert cleanup_called

    @pytest.mark.asyncio
    async def test_async_error_handling_in_concurrent_operations(self):
        """Test error handling in concurrent async operations."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock authentication
            auth_response = AsyncMock()
            auth_response.status_code = 200
            auth_response.json.return_value = {"success": True, "token": "test_token"}
            mock_client.post.return_value = auth_response

            # Mock mixed successful and failing operations
            async def mock_get(url, **kwargs):
                if "positions" in url:
                    response = AsyncMock()
                    response.status_code = 200
                    response.json.return_value = {"success": True, "positions": []}
                    return response
                elif "orders" in url:
                    raise httpx.ConnectError("Network error")
                elif "instruments" in url:
                    response = AsyncMock()
                    response.status_code = 200
                    response.json.return_value = {"success": True, "instruments": []}
                    return response

            mock_client.get = mock_get

            async with AsyncProjectX(
                username="test_user", api_key="test_key"
            ) as client:
                await client.authenticate()

                # Use gather with return_exceptions=True
                results = await asyncio.gather(
                    client.search_open_positions(),
                    client.search_open_orders(),
                    client.search_instruments("TEST"),
                    return_exceptions=True,
                )

                # Verify we got mixed results
                assert len(results) == 3
                assert not isinstance(results[0], Exception)  # Success
                assert isinstance(results[1], Exception)  # Error
                assert not isinstance(results[2], Exception)  # Success


class TestAsyncProjectXConfig:
    """Test suite for ProjectX configuration (sync tests work for both)."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ProjectXConfig()

        assert config.api_url == "https://api.topstepx.com/api"
        assert config.timezone == "America/Chicago"
        assert config.timeout_seconds == 30
        assert config.retry_attempts == 3

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ProjectXConfig(
            timeout_seconds=60, retry_attempts=5, requests_per_minute=30
        )

        assert config.timeout_seconds == 60
        assert config.retry_attempts == 5
        assert config.requests_per_minute == 30


@pytest.fixture
async def mock_async_client():
    """Fixture providing a mocked AsyncProjectX client."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Mock successful authentication
        auth_response = AsyncMock()
        auth_response.status_code = 200
        auth_response.json.return_value = {"success": True, "token": "test_token"}
        auth_response.raise_for_status.return_value = None

        # Mock account info
        account_response = AsyncMock()
        account_response.status_code = 200
        account_response.json.return_value = {
            "simAccounts": [
                {
                    "id": "12345",
                    "name": "Test Account",
                    "balance": 50000.0,
                    "canTrade": True,
                    "simulated": True,
                }
            ],
            "liveAccounts": [],
        }

        mock_client.post.return_value = auth_response
        mock_client.get.return_value = account_response

        client = AsyncProjectX(username="test_user", api_key="test_key")
        # Simulate authentication
        client.session_token = "test_token"
        client.account_info = Mock(id="12345", name="Test Account")
        yield client


class TestAsyncProjectXIntegration:
    """Integration tests that require async authentication."""

    @pytest.mark.asyncio
    async def test_authenticated_async_client_operations(self, mock_async_client):
        """Test operations with an authenticated async client."""
        assert mock_async_client.session_token == "test_token"
        assert mock_async_client.account_info is not None
        assert mock_async_client.account_info.name == "Test Account"

    @pytest.mark.asyncio
    async def test_async_rate_limiting(self):
        """Test async rate limiting functionality."""
        from project_x_py.utils import AsyncRateLimiter

        rate_limiter = AsyncRateLimiter(requests_per_minute=120)  # 2 per second

        request_count = 0

        async def make_request():
            nonlocal request_count
            async with rate_limiter:
                request_count += 1
                await asyncio.sleep(0.01)  # Simulate work

        # Try to make 5 requests concurrently
        start_time = asyncio.get_event_loop().time()
        await asyncio.gather(*[make_request() for _ in range(5)])
        end_time = asyncio.get_event_loop().time()

        # Should take at least 2 seconds due to rate limiting
        assert end_time - start_time >= 2.0
        assert request_count == 5


class TestSyncAsyncCompatibility:
    """Test compatibility between sync and async components."""

    def test_config_compatibility(self):
        """Test that config works with both sync and async clients."""
        config = ProjectXConfig(timeout_seconds=45)

        # Test with sync client
        sync_client = ProjectX(username="test", api_key="test", config=config)
        assert sync_client.config.timeout_seconds == 45

        # Test with async client
        async_client = AsyncProjectX(username="test", api_key="test", config=config)
        assert async_client.config.timeout_seconds == 45

    @pytest.mark.asyncio
    async def test_model_compatibility(self):
        """Test that models work with both client types."""
        from project_x_py.models import Account

        # Test model creation
        account_data = {
            "id": "12345",
            "name": "Test Account",
            "balance": 50000.0,
            "canTrade": True,
            "simulated": True,
        }

        account = Account(**account_data)
        assert account.id == "12345"
        assert account.name == "Test Account"
        assert account.balance == 50000.0

    @pytest.mark.asyncio
    async def test_exception_compatibility(self):
        """Test that exceptions work with both client types."""
        # Test that the same exceptions can be used
        with pytest.raises(ProjectXAuthenticationError):
            raise ProjectXAuthenticationError("Test error")

        # Test async context
        async def async_error():
            raise ProjectXAuthenticationError("Async test error")

        with pytest.raises(ProjectXAuthenticationError):
            await async_error()
