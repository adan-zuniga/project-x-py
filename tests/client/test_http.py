"""Tests for the HTTP client functionality of ProjectX client."""

from unittest.mock import patch

import httpx
import pytest

from project_x_py import ProjectX
from project_x_py.exceptions import (
    ProjectXAuthenticationError,
    ProjectXConnectionError,
    ProjectXDataError,
    ProjectXError,
    ProjectXRateLimitError,
    ProjectXServerError,
)


class TestHttpClient:
    """Tests for HTTP client functionality."""

    @pytest.mark.asyncio
    async def test_client_creation(self, mock_httpx_client):
        """Test HTTP client creation."""
        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            async with ProjectX("testuser", "test-api-key") as client:
                assert client._client is not None
                assert client._client == mock_httpx_client

    @pytest.mark.asyncio
    async def test_successful_request(self, initialized_client, mock_response):
        """Test successful API request."""
        client = initialized_client
        expected_data = {"success": True, "data": "test_value"}
        client._client.request.return_value = mock_response(json_data=expected_data)

        result = await client._make_request("GET", "/test/endpoint")

        assert result == expected_data
        client._client.request.assert_called_once()
        call_args = client._client.request.call_args[1]
        assert call_args["method"] == "GET"
        assert call_args["url"] == f"{client.base_url}/test/endpoint"

    @pytest.mark.asyncio
    async def test_auth_error_handling(self, initialized_client, mock_response):
        """Test authentication error handling."""
        client = initialized_client
        error_response = mock_response(
            status_code=401,
            json_data={"success": False, "message": "Authentication failed"},
        )
        client._client.request.return_value = error_response

        with pytest.raises(ProjectXAuthenticationError):
            await client._make_request("GET", "/test/endpoint")

    @pytest.mark.asyncio
    async def test_not_found_error_handling(self, initialized_client, mock_response):
        """Test not found error handling."""
        client = initialized_client
        error_response = mock_response(
            status_code=404,
            json_data={"success": False, "message": "Resource not found"},
        )
        client._client.request.return_value = error_response

        with pytest.raises(ProjectXDataError):
            await client._make_request("GET", "/test/endpoint")

    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self, initialized_client, mock_response):
        """Test rate limit error handling."""
        client = initialized_client
        error_response = mock_response(
            status_code=429,
            json_data={"success": False, "message": "Too many requests"},
        )
        error_response.headers.__getitem__ = (
            lambda _, key: "60" if key == "Retry-After" else None
        )

        # Set retry_attempts to 0 to avoid actual retries
        client.config.retry_attempts = 0
        client._client.request.return_value = error_response

        with pytest.raises(ProjectXRateLimitError) as exc_info:
            await client._make_request("GET", "/test/endpoint")

        assert "Rate limit" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_server_error_handling(self, initialized_client, mock_response):
        """Test server error handling."""
        client = initialized_client
        error_response = mock_response(
            status_code=500,
            json_data={"success": False, "message": "Internal server error"},
        )
        client._client.request.return_value = error_response

        with pytest.raises(ProjectXServerError):
            await client._make_request("GET", "/test/endpoint")

    @pytest.mark.asyncio
    async def test_client_error_handling(self, initialized_client, mock_response):
        """Test client error handling."""
        client = initialized_client
        error_response = mock_response(
            status_code=400, json_data={"success": False, "message": "Bad request"}
        )
        client._client.request.return_value = error_response

        with pytest.raises(ProjectXError):
            await client._make_request("GET", "/test/endpoint")

    @pytest.mark.asyncio
    async def test_retry_logic(self, initialized_client, mock_response):
        """Test retry logic for transient errors."""
        client = initialized_client

        # Mock a server error (retry-able) followed by a success response
        error_response = mock_response(status_code=503, json_data={"success": False})
        success_response = mock_response(
            json_data={"success": True, "data": "test_value"}
        )

        client._client.request.side_effect = [error_response, success_response]

        # Reduce max retries for testing
        client.config.retry_attempts = 3

        result = await client._make_request("GET", "/test/endpoint")

        assert result == {"success": True, "data": "test_value"}
        assert client._client.request.call_count == 2  # Initial request + 1 retry

    @pytest.mark.asyncio
    async def test_max_retry_exceeded(self, initialized_client, mock_response):
        """Test max retry exceeded raises error."""
        client = initialized_client

        # Mock server errors that exceed max retries
        error_response = mock_response(status_code=503, json_data={"success": False})

        # Side effect with multiple error responses
        client._client.request.side_effect = [error_response] * 4

        # Reduce max retries for testing
        client.config.retry_attempts = 3

        with pytest.raises(ProjectXServerError):
            await client._make_request("GET", "/test/endpoint")

        assert client._client.request.call_count == 4  # Initial + 3 retries

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, initialized_client):
        """Test connection error handling."""
        client = initialized_client

        # Set retry_attempts to 0 to avoid retries
        client.config.retry_attempts = 0

        # Mock a connection error
        client._client.request.side_effect = httpx.ConnectError("Failed to connect")

        with pytest.raises(ProjectXConnectionError) as exc_info:
            await client._make_request("GET", "/test/endpoint")

        assert "Failed to connect" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, initialized_client):
        """Test timeout error handling."""
        client = initialized_client

        # Set retry_attempts to 0 to avoid retries
        client.config.retry_attempts = 0

        # Mock a timeout error
        client._client.request.side_effect = httpx.TimeoutException("Request timed out")

        with pytest.raises(ProjectXConnectionError) as exc_info:
            await client._make_request("GET", "/test/endpoint")

        assert "timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_request_with_params(self, initialized_client, mock_response):
        """Test request with query parameters."""
        client = initialized_client

        client._client.request.return_value = mock_response(json_data={"success": True})
        test_params = {"param1": "value1", "param2": 123}

        await client._make_request("GET", "/test/endpoint", params=test_params)

        call_args = client._client.request.call_args[1]
        assert call_args["params"] == test_params

    @pytest.mark.asyncio
    async def test_request_with_data(self, initialized_client, mock_response):
        """Test request with JSON data."""
        client = initialized_client

        client._client.request.return_value = mock_response(json_data={"success": True})
        test_data = {"field1": "value1", "field2": 123}

        await client._make_request("POST", "/test/endpoint", data=test_data)

        call_args = client._client.request.call_args[1]
        assert call_args["json"] == test_data

    @pytest.mark.asyncio
    async def test_health_status(self, initialized_client, mock_response):
        """Test health status endpoint."""
        client = initialized_client

        api_response = mock_response(
            json_data={"status": "healthy", "version": "1.0.0"}
        )
        client._client.request.return_value = api_response

        health = await client.get_health_status()

        # Verify the structure matches the expected format
        assert "api_status" in health
        assert "api_version" in health
        assert "client_stats" in health

        # Verify key values
        assert health["api_status"] == "healthy"
        assert health["api_version"] == "1.0.0"
        assert isinstance(health["client_stats"], dict)

        # Verify client stats fields
        assert "api_calls" in health["client_stats"]
        assert "cache_hits" in health["client_stats"]
        assert "cache_hit_rate" in health["client_stats"]

        # Verify the API endpoint was called correctly
        client._client.request.assert_called_once()
        call_args = client._client.request.call_args[1]
        assert call_args["method"] == "GET"
        assert call_args["url"].endswith("/health")
