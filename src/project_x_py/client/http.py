"""HTTP client and request handling for ProjectX client."""

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import httpx

from project_x_py.exceptions import (
    ProjectXAuthenticationError,
    ProjectXConnectionError,
    ProjectXDataError,
    ProjectXError,
    ProjectXRateLimitError,
    ProjectXServerError,
)

if TYPE_CHECKING:
    from project_x_py.client.protocols import ProjectXClientProtocol

logger = logging.getLogger(__name__)


class HttpMixin:
    """Mixin class providing HTTP client functionality."""

    def __init__(self) -> None:
        """Initialize HTTP client attributes."""
        super().__init__()
        self._client: httpx.AsyncClient | None = None
        self.api_call_count = 0

    async def _create_client(self: "ProjectXClientProtocol") -> httpx.AsyncClient:
        """
        Create an optimized httpx async client with connection pooling and retries.

        This method configures the HTTP client with:
        - HTTP/2 support for improved performance
        - Connection pooling to reduce overhead
        - Automatic retries on transient failures
        - Custom timeout settings
        - Proper SSL verification

        Returns:
            httpx.AsyncClient: Configured async HTTP client
        """
        # Configure timeout
        timeout = httpx.Timeout(
            connect=10.0,
            read=self.config.timeout_seconds,
            write=self.config.timeout_seconds,
            pool=self.config.timeout_seconds,
        )

        # Configure limits for connection pooling
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30.0,
        )

        # Create async client with HTTP/2 support
        client = httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            http2=True,
            verify=True,
            follow_redirects=True,
            headers={
                "User-Agent": "ProjectX-Python-SDK/2.0.0",
                "Accept": "application/json",
            },
        )

        return client

    async def _ensure_client(self: "ProjectXClientProtocol") -> httpx.AsyncClient:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = await self._create_client()
        return self._client

    async def _make_request(
        self: "ProjectXClientProtocol",
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        retry_count: int = 0,
    ) -> Any:
        """
        Make an async HTTP request with error handling and retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            data: Optional request body data
            params: Optional query parameters
            headers: Optional additional headers
            retry_count: Current retry attempt count

        Returns:
            Response data (can be dict, list, or other JSON-serializable type)

        Raises:
            ProjectXError: Various specific exceptions based on error type
        """
        client = await self._ensure_client()

        url = f"{self.base_url}{endpoint}"
        request_headers = {**self.headers, **(headers or {})}

        # Add authorization if we have a token
        if self.session_token and endpoint != "/Auth/loginKey":
            request_headers["Authorization"] = f"Bearer {self.session_token}"

        # Apply rate limiting
        await self.rate_limiter.acquire()

        self.api_call_count += 1

        try:
            response = await client.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=request_headers,
            )

            # Handle rate limiting
            if response.status_code == 429:
                if retry_count < self.config.retry_attempts:
                    retry_after = int(response.headers.get("Retry-After", "5"))
                    self.logger.warning(
                        f"Rate limited, retrying after {retry_after} seconds"
                    )
                    await asyncio.sleep(retry_after)
                    return await self._make_request(
                        method=method,
                        endpoint=endpoint,
                        data=data,
                        params=params,
                        headers=headers,
                        retry_count=retry_count + 1,
                    )
                raise ProjectXRateLimitError("Rate limit exceeded after retries")

            # Handle successful responses
            if response.status_code in (200, 201, 204):
                if response.status_code == 204:
                    return {}
                return response.json()

            # Handle authentication errors
            if response.status_code == 401:
                if endpoint != "/Auth/loginKey" and retry_count == 0:
                    # Try to refresh authentication
                    await self._refresh_authentication()
                    return await self._make_request(
                        method=method,
                        endpoint=endpoint,
                        data=data,
                        params=params,
                        headers=headers,
                        retry_count=retry_count + 1,
                    )
                raise ProjectXAuthenticationError("Authentication failed")

            # Handle client errors
            if 400 <= response.status_code < 500:
                error_msg = f"Client error: {response.status_code}"
                try:
                    error_data = response.json()
                    if "message" in error_data:
                        error_msg = error_data["message"]
                    elif "error" in error_data:
                        error_msg = error_data["error"]
                except Exception:
                    error_msg = response.text

                if response.status_code == 404:
                    raise ProjectXDataError(f"Resource not found: {error_msg}")
                else:
                    raise ProjectXError(error_msg)

            # Handle server errors with retry
            if 500 <= response.status_code < 600:
                if retry_count < self.config.retry_attempts:
                    wait_time = 2**retry_count  # Exponential backoff
                    self.logger.warning(
                        f"Server error {response.status_code}, retrying in {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
                    return await self._make_request(
                        method=method,
                        endpoint=endpoint,
                        data=data,
                        params=params,
                        headers=headers,
                        retry_count=retry_count + 1,
                    )
                raise ProjectXServerError(
                    f"Server error: {response.status_code} - {response.text}"
                )

        except httpx.ConnectError as e:
            if retry_count < self.config.retry_attempts:
                wait_time = 2**retry_count
                self.logger.warning(f"Connection error, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
                return await self._make_request(
                    method, endpoint, data, params, headers, retry_count + 1
                )
            raise ProjectXConnectionError(f"Failed to connect to API: {e}") from e
        except httpx.TimeoutException as e:
            if retry_count < self.config.retry_attempts:
                wait_time = 2**retry_count
                self.logger.warning(f"Request timeout, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
                return await self._make_request(
                    method, endpoint, data, params, headers, retry_count + 1
                )
            raise ProjectXConnectionError(f"Request timeout: {e}") from e
        except Exception as e:
            if not isinstance(e, ProjectXError):
                raise ProjectXError(f"Unexpected error: {e}") from e
            raise

    async def get_health_status(self: "ProjectXClientProtocol") -> dict[str, Any]:
        """
        Get API health status and client statistics.

        Returns:
            Dict containing:
                - api_status: Current API status
                - api_version: API version information
                - client_stats: Client-side statistics including cache performance

        Example:
            >>> status = await client.get_health_status()
            >>> print(f"API Status: {status['api_status']}")
            >>> print(f"Cache hit rate: {status['client_stats']['cache_hit_rate']:.1%}")
        """
        # Get API health
        try:
            response = await self._make_request("GET", "/health")
            api_status = response.get("status", "unknown")
            api_version = response.get("version", "unknown")
        except Exception:
            api_status = "error"
            api_version = "unknown"

        # Calculate client statistics
        total_cache_requests = self.cache_hit_count + self.api_call_count
        cache_hit_rate = (
            self.cache_hit_count / total_cache_requests
            if total_cache_requests > 0
            else 0
        )

        return {
            "api_status": api_status,
            "api_version": api_version,
            "client_stats": {
                "api_calls": self.api_call_count,
                "cache_hits": self.cache_hit_count,
                "cache_hit_rate": cache_hit_rate,
                "authenticated": self._authenticated,
                "account": self.account_info.name if self.account_info else None,
            },
        }
