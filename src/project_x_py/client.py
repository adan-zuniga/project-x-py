"""
Async ProjectX Python SDK - Core Async Client Module

This module contains the async version of the ProjectX client class for the ProjectX Python SDK.
It provides a comprehensive asynchronous interface for interacting with the ProjectX Trading Platform
Gateway API, enabling developers to build high-performance trading applications.

The async client handles authentication, account management, market data retrieval, and basic
trading operations using async/await patterns for improved performance and concurrency.

Key Features:
- Async multi-account authentication and management
- Concurrent API operations with httpx
- Async historical market data retrieval with caching
- Non-blocking position tracking and trade history
- Async error handling and connection management
- HTTP/2 support for improved performance

For advanced trading operations, use the specialized managers:
- OrderManager: Complete order lifecycle management
- PositionManager: Portfolio analytics and risk management
- ProjectXRealtimeDataManager: Real-time multi-timeframe OHLCV data
- OrderBook: Level 2 market depth and microstructure analysis
"""

import asyncio
import datetime
import gc
import json
import logging
import os
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any

import httpx
import polars as pl
import pytz

from .config import ConfigManager
from .exceptions import (
    ProjectXAuthenticationError,
    ProjectXConnectionError,
    ProjectXDataError,
    ProjectXError,
    ProjectXInstrumentError,
    ProjectXRateLimitError,
    ProjectXServerError,
)
from .models import (
    Account,
    Instrument,
    Position,
    ProjectXConfig,
    Trade,
)


class RateLimiter:
    """Simple async rate limiter using sliding window."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait if necessary to stay within rate limits."""
        async with self._lock:
            now = time.time()
            # Remove old requests outside the window
            self.requests = [t for t in self.requests if t > now - self.window_seconds]

            if len(self.requests) >= self.max_requests:
                # Calculate wait time
                oldest_request = self.requests[0]
                wait_time = (oldest_request + self.window_seconds) - now
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    # Clean up again after waiting
                    now = time.time()
                    self.requests = [
                        t for t in self.requests if t > now - self.window_seconds
                    ]

            # Record this request
            self.requests.append(now)


class ProjectX:
    """
    Async core ProjectX client for the ProjectX Python SDK.

    This class provides the async foundation for building trading applications by offering
    comprehensive asynchronous access to the ProjectX Trading Platform Gateway API. It handles
    core functionality including:

    - Async multi-account authentication and session management
    - Concurrent instrument search with smart contract selection
    - Async historical market data retrieval with caching
    - Non-blocking position tracking and trade history analysis
    - Async account management and information retrieval

    For advanced trading operations, this client integrates with specialized managers:
    - OrderManager: Complete order lifecycle management
    - PositionManager: Portfolio analytics and risk management
    - ProjectXRealtimeDataManager: Real-time multi-timeframe data
    - OrderBook: Level 2 market depth analysis

    The client implements enterprise-grade features including HTTP/2 connection pooling,
    automatic retry mechanisms, rate limiting, and intelligent caching for optimal
    performance when building high-frequency trading applications.

    Attributes:
        config (ProjectXConfig): Configuration settings for API endpoints and behavior
        api_key (str): API key for authentication
        username (str): Username for authentication
        account_name (str | None): Optional account name for multi-account selection
        base_url (str): Base URL for the API endpoints
        session_token (str): JWT token for authenticated requests
        headers (dict): HTTP headers for API requests
        account_info (Account): Selected account information

    Example:
        >>> # Basic async SDK usage with environment variables (recommended)
        >>> import asyncio
        >>> from project_x_py import ProjectX
        >>>
        >>> async def main():
        >>>     async with ProjectX.from_env() as client:
        >>>         await client.authenticate()
        >>>         positions = await client.get_positions()
        >>>         print(f"Found {len(positions)} positions")
        >>>
        >>> asyncio.run(main())
    """

    def __init__(
        self,
        username: str,
        api_key: str,
        config: ProjectXConfig | None = None,
        account_name: str | None = None,
    ):
        """
        Initialize async ProjectX client for building trading applications.

        Args:
            username: ProjectX username for authentication
            api_key: API key for ProjectX authentication
            config: Optional configuration object with endpoints and settings
            account_name: Optional account name to select specific account
        """
        self.username = username
        self.api_key = api_key
        self.account_name = account_name

        # Use provided config or create default
        self.config = config or ProjectXConfig()
        self.base_url = self.config.api_url

        # Session management
        self.session_token = ""
        self.token_expiry: datetime.datetime | None = None
        self.headers: dict[str, str] = {"Content-Type": "application/json"}

        # HTTP client - will be initialized in __aenter__
        self._client: httpx.AsyncClient | None = None

        # Cache for instrument data (symbol -> instrument)
        self._instrument_cache: dict[str, Instrument] = {}
        self._instrument_cache_time: dict[str, float] = {}

        # Cache for market data
        self._market_data_cache: dict[str, pl.DataFrame] = {}
        self._market_data_cache_time: dict[str, float] = {}

        # Cache cleanup tracking
        self.cache_ttl = 300  # 5 minutes default
        self.last_cache_cleanup = time.time()

        # Lazy initialization - don't authenticate immediately
        self.account_info: Account | None = None
        self._authenticated = False

        # Performance monitoring
        self.api_call_count = 0
        self.cache_hit_count = 0

        # Rate limiting - 100 requests per minute by default
        self.rate_limiter = RateLimiter(max_requests=100, window_seconds=60)

        self.logger = logging.getLogger(__name__)

    async def __aenter__(self) -> "ProjectX":
        """Async context manager entry."""
        self._client = await self._create_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @classmethod
    @asynccontextmanager
    async def from_env(
        cls, config: ProjectXConfig | None = None, account_name: str | None = None
    ) -> AsyncGenerator["ProjectX", None]:
        """
        Create async ProjectX client using environment variables (recommended approach).

        This is the preferred method for initializing the async client as it keeps
        sensitive credentials out of your source code.

        Environment Variables Required:
            PROJECT_X_API_KEY: API key for ProjectX authentication
            PROJECT_X_USERNAME: Username for ProjectX account

        Optional Environment Variables:
            PROJECT_X_ACCOUNT_NAME: Account name to select specific account

        Args:
            config: Optional configuration object with endpoints and settings
            account_name: Optional account name (overrides environment variable)

        Yields:
            ProjectX: Configured async client instance ready for building trading applications

        Raises:
            ValueError: If required environment variables are not set

        Example:
            >>> # Set environment variables first
            >>> import os
            >>> os.environ["PROJECT_X_API_KEY"] = "your_api_key_here"
            >>> os.environ["PROJECT_X_USERNAME"] = "your_username_here"
            >>> os.environ["PROJECT_X_ACCOUNT_NAME"] = (
            ...     "Main Trading Account"  # Optional
            ... )
            >>>
            >>> # Create async client (recommended approach)
            >>> import asyncio
            >>> from project_x_py import ProjectX
            >>>
            >>> async def main():
            >>>     async with ProjectX.from_env() as client:
            >>>         await client.authenticate()
            >>> # Use the client...
            >>>
            >>> asyncio.run(main())
        """
        config_manager = ConfigManager()
        auth_config = config_manager.get_auth_config()

        # Use provided account_name or try to get from environment
        if account_name is None:
            account_name = os.getenv("PROJECT_X_ACCOUNT_NAME")

        client = cls(
            username=auth_config["username"],
            api_key=auth_config["api_key"],
            config=config,
            account_name=account_name.upper() if account_name else None,
        )

        async with client:
            yield client

    @classmethod
    @asynccontextmanager
    async def from_config_file(
        cls, config_file: str, account_name: str | None = None
    ) -> AsyncGenerator["ProjectX", None]:
        """Create async ProjectX client using a configuration file.

        Alternative initialization method that loads configuration and credentials
        from a JSON file instead of environment variables. Useful for managing
        multiple configurations or environments.

        Args:
            config_file (str): Path to JSON configuration file containing:
                - username: ProjectX account username
                - api_key: API authentication key
                - api_url: API endpoint URL (optional)
                - websocket_url: WebSocket URL (optional)
                - timezone: Preferred timezone (optional)
            account_name (str | None): Optional account name to select when
                multiple accounts are available. Overrides any account name
                specified in the config file.

        Yields:
            ProjectX: Configured client instance ready for trading operations

        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If config file is invalid JSON
            ValueError: If required fields are missing from config
            ProjectXAuthenticationError: If authentication fails

        Example:
            >>> # Create config file
            >>> config = {
            ...     "username": "your_username",
            ...     "api_key": "your_api_key",
            ...     "api_url": "https://api.topstepx.com/api",
            ...     "timezone": "US/Central",
            ... }
            >>>
            >>> # Use client with config file
            >>> async with ProjectX.from_config_file("config.json") as client:
            ...     await client.authenticate()
            ...     # Client is ready for trading

        Note:
            - Config file should not be committed to version control
            - Consider using environment variables for production
            - File permissions should restrict access to the config file
        """
        config_manager = ConfigManager(config_file)
        config = config_manager.load_config()
        auth_config = config_manager.get_auth_config()

        client = cls(
            username=auth_config["username"],
            api_key=auth_config["api_key"],
            config=config,
            account_name=account_name.upper() if account_name else None,
        )

        async with client:
            yield client

    async def _create_client(self) -> httpx.AsyncClient:
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

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = await self._create_client()
        return self._client

    async def _make_request(
        self,
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
                        method, endpoint, data, params, headers, retry_count + 1
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
                        method, endpoint, data, params, headers, retry_count + 1
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
                        method, endpoint, data, params, headers, retry_count + 1
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

    async def _refresh_authentication(self) -> None:
        """Refresh authentication if token is expired or about to expire."""
        if self._should_refresh_token():
            await self.authenticate()

    def _should_refresh_token(self) -> bool:
        """Check if token should be refreshed."""
        if not self.token_expiry:
            return True

        # Refresh if token expires in less than 5 minutes
        buffer_time = timedelta(minutes=5)
        return datetime.datetime.now(pytz.UTC) >= (self.token_expiry - buffer_time)

    async def authenticate(self) -> None:
        """
        Authenticate with ProjectX API and select account.

        This method handles the complete authentication flow:
        1. Authenticates with username and API key
        2. Retrieves available accounts
        3. Selects the specified account or first available

        The authentication token is automatically refreshed when needed
        during API calls.

        Raises:
            ProjectXAuthenticationError: If authentication fails
            ValueError: If specified account is not found

        Example:
            >>> async with AsyncProjectX.from_env() as client:
            >>>     await client.authenticate()
            >>>     print(f"Authenticated as {client.account_info.username}")
            >>>     print(f"Using account: {client.account_info.name}")
        """
        # Authenticate and get token
        auth_data = {
            "userName": self.username,
            "apiKey": self.api_key,
        }

        response = await self._make_request("POST", "/Auth/loginKey", data=auth_data)

        if not response:
            raise ProjectXAuthenticationError("Authentication failed")

        self.session_token = response["token"]
        self.headers["Authorization"] = f"Bearer {self.session_token}"

        # Parse token to get expiry
        try:
            import base64

            token_parts = self.session_token.split(".")
            if len(token_parts) >= 2:
                # Add padding if necessary
                payload = token_parts[1]
                payload += "=" * (4 - len(payload) % 4)
                decoded = base64.urlsafe_b64decode(payload)
                token_data = json.loads(decoded)
                self.token_expiry = datetime.datetime.fromtimestamp(
                    token_data["exp"], tz=pytz.UTC
                )
        except Exception as e:
            self.logger.warning(f"Could not parse token expiry: {e}")
            # Set a default expiry of 1 hour
            self.token_expiry = datetime.datetime.now(pytz.UTC) + timedelta(hours=1)

        # Get accounts using the same endpoint as sync client
        payload = {"onlyActiveAccounts": True}
        accounts_response = await self._make_request(
            "POST", "/Account/search", data=payload
        )
        if not accounts_response or not accounts_response.get("success", False):
            raise ProjectXAuthenticationError("Account search failed")

        accounts_data = accounts_response.get("accounts", [])
        accounts = [Account(**acc) for acc in accounts_data]

        if not accounts:
            raise ProjectXAuthenticationError("No accounts found for user")

        # Select account
        if self.account_name:
            # Find specific account
            selected_account = None
            for account in accounts:
                if account.name.upper() == self.account_name.upper():
                    selected_account = account
                    break

            if not selected_account:
                available = ", ".join(acc.name for acc in accounts)
                raise ValueError(
                    f"Account '{self.account_name}' not found. "
                    f"Available accounts: {available}"
                )
        else:
            # Use first account
            selected_account = accounts[0]

        self.account_info = selected_account
        self._authenticated = True
        self.logger.info(
            f"Authenticated successfully. Using account: {selected_account.name}"
        )

    async def _ensure_authenticated(self) -> None:
        """Ensure client is authenticated before making API calls."""
        if not self._authenticated or self._should_refresh_token():
            await self.authenticate()

    # Additional async methods would follow the same pattern...
    # For brevity, I'll add a few key methods to demonstrate the pattern

    async def get_positions(self) -> list[Position]:
        """
        Get all open positions for the authenticated account.

        Returns:
            List of Position objects representing current holdings

        Example:
            >>> positions = await client.get_positions()
            >>> for pos in positions:
            >>>     print(f"{pos.symbol}: {pos.quantity} @ {pos.price}")
        """
        await self._ensure_authenticated()

        if not self.account_info:
            raise ProjectXError("No account selected")

        response = await self._make_request(
            "GET", f"/accounts/{self.account_info.id}/positions"
        )

        if not response or not isinstance(response, list):
            return []

        return [Position(**pos) for pos in response]

    async def get_instrument(self, symbol: str, live: bool = False) -> Instrument:
        """
        Get detailed instrument information with caching.

        Args:
            symbol: Trading symbol (e.g., 'NQ', 'ES', 'MGC')
            live: If True, only return live/active contracts (default: False)

        Returns:
            Instrument object with complete contract details

        Example:
            >>> instrument = await client.get_instrument("NQ")
            >>> print(f"Trading {instrument.symbol} - {instrument.name}")
            >>> print(f"Tick size: {instrument.tick_size}")
        """
        await self._ensure_authenticated()

        # Check cache first
        cache_key = symbol.upper()
        if cache_key in self._instrument_cache:
            cache_age = time.time() - self._instrument_cache_time.get(cache_key, 0)
            if cache_age < self.cache_ttl:
                self.cache_hit_count += 1
                return self._instrument_cache[cache_key]

        # Search for instrument
        payload = {"searchText": symbol, "live": live}
        response = await self._make_request("POST", "/Contract/search", data=payload)

        if not response or not response.get("success", False):
            raise ProjectXInstrumentError(f"No instruments found for symbol: {symbol}")

        contracts_data = response.get("contracts", [])
        if not contracts_data:
            raise ProjectXInstrumentError(f"No instruments found for symbol: {symbol}")

        # Select best match
        best_match = self._select_best_contract(contracts_data, symbol)
        instrument = Instrument(**best_match)

        # Cache the result
        self._instrument_cache[cache_key] = instrument
        self._instrument_cache_time[cache_key] = time.time()

        # Periodic cache cleanup
        if time.time() - self.last_cache_cleanup > 3600:  # Every hour
            await self._cleanup_cache()

        return instrument

    async def _cleanup_cache(self) -> None:
        """Clean up expired cache entries."""
        current_time = time.time()

        # Clean instrument cache
        expired_instruments = [
            symbol
            for symbol, cache_time in self._instrument_cache_time.items()
            if current_time - cache_time > self.cache_ttl
        ]
        for symbol in expired_instruments:
            del self._instrument_cache[symbol]
            del self._instrument_cache_time[symbol]

        # Clean market data cache
        expired_data = [
            key
            for key, cache_time in self._market_data_cache_time.items()
            if current_time - cache_time > self.cache_ttl
        ]
        for key in expired_data:
            del self._market_data_cache[key]
            del self._market_data_cache_time[key]

        self.last_cache_cleanup = current_time

        # Force garbage collection if caches were large
        if len(expired_instruments) > 10 or len(expired_data) > 10:
            gc.collect()

    def _select_best_contract(
        self, instruments: list[dict[str, Any]], search_symbol: str
    ) -> dict[str, Any]:
        """
        Select the best matching contract from search results.

        This method implements smart contract selection logic for futures:
        - Exact matches are preferred
        - For futures, selects the front month contract
        - For micro contracts, ensures correct symbol (e.g., MNQ for micro Nasdaq)

        Args:
            instruments: List of instrument dictionaries from search
            search_symbol: Original search symbol

        Returns:
            Best matching instrument dictionary
        """
        if not instruments:
            raise ProjectXInstrumentError(f"No instruments found for: {search_symbol}")

        search_upper = search_symbol.upper()

        # First try exact match
        for inst in instruments:
            if inst.get("symbol", "").upper() == search_upper:
                return inst

        # For futures, try to find the front month
        # Extract base symbol and find all contracts
        import re

        futures_pattern = re.compile(r"^(.+?)([FGHJKMNQUVXZ]\d{1,2})$")
        base_symbols: dict[str, list[dict[str, Any]]] = {}

        for inst in instruments:
            symbol = inst.get("symbol", "").upper()
            match = futures_pattern.match(symbol)
            if match:
                base = match.group(1)
                if base not in base_symbols:
                    base_symbols[base] = []
                base_symbols[base].append(inst)

        # Find contracts matching our search
        matching_base = None
        for base in base_symbols:
            if base == search_upper or search_upper.startswith(base):
                matching_base = base
                break

        if matching_base and base_symbols[matching_base]:
            # Sort by symbol to get front month (alphabetical = chronological for futures)
            sorted_contracts = sorted(
                base_symbols[matching_base], key=lambda x: x.get("symbol", "")
            )
            return sorted_contracts[0]

        # Default to first result
        return instruments[0]

    async def get_health_status(self) -> dict[str, Any]:
        """
        Get health status of the client including performance metrics.

        Returns:
            Dictionary with health and performance information
        """
        await self._ensure_authenticated()

        return {
            "authenticated": self._authenticated,
            "account": self.account_info.name if self.account_info else None,
            "api_calls": self.api_call_count,
            "cache_hits": self.cache_hit_count,
            "cache_hit_rate": (
                self.cache_hit_count / self.api_call_count
                if self.api_call_count > 0
                else 0
            ),
            "instrument_cache_size": len(self._instrument_cache),
            "market_data_cache_size": len(self._market_data_cache),
            "token_expires_in": (
                (self.token_expiry - datetime.datetime.now(pytz.UTC)).total_seconds()
                if self.token_expiry
                else 0
            ),
        }

    async def list_accounts(self) -> list[Account]:
        """
        List all available accounts for the authenticated user.

        Returns:
            List of Account objects

        Raises:
            ProjectXAuthenticationError: If not authenticated

        Example:
            >>> accounts = await client.list_accounts()
            >>> for account in accounts:
            >>>     print(f"{account.name}: ${account.balance:,.2f}")
        """
        await self._ensure_authenticated()

        payload = {"onlyActiveAccounts": True}
        response = await self._make_request("POST", "/Account/search", data=payload)

        if not response or not response.get("success", False):
            return []

        accounts_data = response.get("accounts", [])
        return [Account(**acc) for acc in accounts_data]

    async def search_instruments(
        self, query: str, live: bool = False
    ) -> list[Instrument]:
        """
        Search for instruments by symbol or name.

        Args:
            query: Search query (symbol or partial name)
            live: If True, search only live/active instruments

        Returns:
            List of Instrument objects matching the query

        Example:
            >>> instruments = await client.search_instruments("gold")
            >>> for inst in instruments:
            >>>     print(f"{inst.name}: {inst.description}")
        """
        await self._ensure_authenticated()

        payload = {"searchText": query, "live": live}
        response = await self._make_request("POST", "/Contract/search", data=payload)

        if not response or not response.get("success", False):
            return []

        contracts_data = response.get("contracts", [])
        return [Instrument(**contract) for contract in contracts_data]

    async def get_bars(
        self,
        symbol: str,
        days: int = 8,
        interval: int = 5,
        unit: int = 2,
        limit: int | None = None,
        partial: bool = True,
    ) -> pl.DataFrame:
        """
        Retrieve historical OHLCV bar data for an instrument.

        This method fetches historical market data with intelligent caching and
        timezone handling. The data is returned as a Polars DataFrame optimized
        for financial analysis and technical indicator calculations.

        Args:
            symbol: Symbol of the instrument (e.g., "MGC", "MNQ", "ES")
            days: Number of days of historical data (default: 8)
            interval: Interval between bars in the specified unit (default: 5)
            unit: Time unit for the interval (default: 2 for minutes)
                  1=Second, 2=Minute, 3=Hour, 4=Day, 5=Week, 6=Month
            limit: Maximum number of bars to retrieve (auto-calculated if None)
            partial: Include incomplete/partial bars (default: True)

        Returns:
            pl.DataFrame: DataFrame with OHLCV data and timezone-aware timestamps
                Columns: timestamp, open, high, low, close, volume
                Timezone: Converted to your configured timezone (default: US/Central)

        Raises:
            ProjectXInstrumentError: If instrument not found or invalid
            ProjectXDataError: If data retrieval fails or invalid response

        Example:
            >>> # Get 5 days of 15-minute gold data
            >>> data = await client.get_bars("MGC", days=5, interval=15)
            >>> print(f"Retrieved {len(data)} bars")
            >>> print(
            ...     f"Date range: {data['timestamp'].min()} to {data['timestamp'].max()}"
            ... )
        """
        await self._ensure_authenticated()

        # Check market data cache
        cache_key = f"{symbol}_{days}_{interval}_{unit}_{partial}"
        current_time = time.time()

        if cache_key in self._market_data_cache:
            cache_age = current_time - self._market_data_cache_time.get(cache_key, 0)
            # Market data cache for 5 minutes
            if cache_age < 300:
                self.cache_hit_count += 1
                return self._market_data_cache[cache_key]

        # Lookup instrument
        instrument = await self.get_instrument(symbol)

        # Calculate date range (same as sync version)
        from datetime import timedelta

        start_date = datetime.datetime.now(pytz.UTC) - timedelta(days=days)
        end_date = datetime.datetime.now(pytz.UTC)

        # Calculate limit based on unit type (same as sync version)
        if limit is None:
            if unit == 1:  # Seconds
                total_seconds = int((end_date - start_date).total_seconds())
                limit = int(total_seconds / interval)
            elif unit == 2:  # Minutes
                total_minutes = int((end_date - start_date).total_seconds() / 60)
                limit = int(total_minutes / interval)
            elif unit == 3:  # Hours
                total_hours = int((end_date - start_date).total_seconds() / 3600)
                limit = int(total_hours / interval)
            else:  # Days or other units
                total_minutes = int((end_date - start_date).total_seconds() / 60)
                limit = int(total_minutes / interval)

        # Prepare payload (same as sync version)
        payload = {
            "contractId": instrument.id,
            "live": False,
            "startTime": start_date.isoformat(),
            "endTime": end_date.isoformat(),
            "unit": unit,
            "unitNumber": interval,
            "limit": limit,
            "includePartialBar": partial,
        }

        # Fetch data using correct endpoint (same as sync version)
        response = await self._make_request(
            "POST", "/History/retrieveBars", data=payload
        )

        if not response:
            return pl.DataFrame()

        # Handle the response format (same as sync version)
        if not response.get("success", False):
            error_msg = response.get("errorMessage", "Unknown error")
            self.logger.error(f"History retrieval failed: {error_msg}")
            return pl.DataFrame()

        bars_data = response.get("bars", [])
        if not bars_data:
            return pl.DataFrame()

        # Convert to DataFrame and process like sync version
        data = (
            pl.DataFrame(bars_data)
            .sort("t")
            .rename(
                {
                    "t": "timestamp",
                    "o": "open",
                    "h": "high",
                    "l": "low",
                    "c": "close",
                    "v": "volume",
                }
            )
            .with_columns(
                # Optimized datetime conversion with cached timezone
                pl.col("timestamp")
                .str.to_datetime()
                .dt.replace_time_zone("UTC")
                .dt.convert_time_zone(self.config.timezone)
            )
        )

        if data.is_empty():
            return data

        # Sort by timestamp
        data = data.sort("timestamp")

        # Cache the result
        self._market_data_cache[cache_key] = data
        self._market_data_cache_time[cache_key] = current_time

        # Cleanup cache periodically
        if current_time - self.last_cache_cleanup > 3600:
            await self._cleanup_cache()

        return data

    async def search_open_positions(
        self, account_id: int | None = None
    ) -> list[Position]:
        """
        Search for open positions across accounts.

        Args:
            account_id: Optional account ID to filter positions

        Returns:
            List of Position objects

        Example:
            >>> positions = await client.search_open_positions()
            >>> total_pnl = sum(pos.unrealized_pnl for pos in positions)
            >>> print(f"Total P&L: ${total_pnl:,.2f}")
        """
        await self._ensure_authenticated()

        # Use the account_id from the authenticated account if not provided
        if account_id is None and self.account_info:
            account_id = self.account_info.id

        if account_id is None:
            raise ProjectXError("No account ID available for position search")

        payload = {"accountId": account_id}
        response = await self._make_request(
            "POST", "/Position/searchOpen", data=payload
        )

        if not response or not response.get("success", False):
            return []

        positions_data = response.get("positions", [])
        return [Position(**pos) for pos in positions_data]

    async def search_trades(
        self,
        start_date: datetime.datetime | None = None,
        end_date: datetime.datetime | None = None,
        contract_id: str | None = None,
        account_id: int | None = None,
        limit: int = 100,
    ) -> list[Trade]:
        """
        Search trade execution history for analysis and reporting.

        Retrieves executed trades within the specified date range, useful for
        performance analysis, tax reporting, and strategy evaluation.

        Args:
            start_date: Start date for trade search (default: 30 days ago)
            end_date: End date for trade search (default: now)
            contract_id: Optional contract ID filter for specific instrument
            account_id: Account ID to search (uses default account if None)
            limit: Maximum number of trades to return (default: 100)

        Returns:
            List[Trade]: List of executed trades with detailed information including:
                - contractId: Instrument that was traded
                - size: Trade size (positive=buy, negative=sell)
                - price: Execution price
                - timestamp: Execution time
                - commission: Trading fees

        Raises:
            ProjectXError: If trade search fails or no account information available

        Example:
            >>> from datetime import datetime, timedelta
            >>> # Get last 7 days of trades
            >>> start = datetime.now() - timedelta(days=7)
            >>> trades = await client.search_trades(start_date=start)
            >>> for trade in trades:
            >>>     print(
            >>>         f"Trade: {trade.contractId} - {trade.size} @ ${trade.price:.2f}"
            >>>     )
        """
        await self._ensure_authenticated()

        if account_id is None:
            if not self.account_info:
                raise ProjectXError("No account information available")
            account_id = self.account_info.id

        # Default date range
        if end_date is None:
            end_date = datetime.datetime.now(pytz.UTC)
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        # Prepare parameters
        params = {
            "accountId": account_id,
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "limit": limit,
        }

        if contract_id:
            params["contractId"] = contract_id

        response = await self._make_request("GET", "/trades/search", params=params)

        if not response or not isinstance(response, list):
            return []

        return [Trade(**trade) for trade in response]
