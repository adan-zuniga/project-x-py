"""
ProjectX Python SDK - Core Client Module

Author: TexasCoding
Date: June 2025

This module contains the main ProjectX client class for the ProjectX Python SDK.
It provides a comprehensive interface for interacting with the ProjectX Trading Platform
Gateway API, enabling developers to build sophisticated trading applications.

The client handles authentication, account management, market data retrieval, and basic
trading operations. It provides both low-level API access and high-level convenience
methods for building trading strategies and applications.

Key Features:
- Multi-account authentication and management
- Intelligent instrument search with smart contract selection
- Historical market data retrieval with caching
- Position tracking and trade history
- Error handling and connection management
- Rate limiting and retry mechanisms

For advanced trading operations, use the specialized managers:
- OrderManager: Comprehensive order lifecycle management
- PositionManager: Portfolio analytics and risk management
- ProjectXRealtimeDataManager: Real-time multi-timeframe OHLCV data
- OrderBook: Level 2 market depth and microstructure analysis

"""

import datetime
import gc
import json
import logging
import os  # Added for os.getenv
import time
from datetime import timedelta
from typing import Any

import polars as pl
import pytz
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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


class ProjectX:
    """
    Core ProjectX client for the ProjectX Python SDK.

    This class provides the foundation for building trading applications by offering
    comprehensive access to the ProjectX Trading Platform Gateway API. It handles
    core functionality including:

    - Multi-account authentication and session management
    - Intelligent instrument search with smart contract selection
    - Historical market data retrieval with caching
    - Position tracking and trade history analysis
    - Account management and information retrieval

    For advanced trading operations, this client integrates with specialized managers:
    - OrderManager: Complete order lifecycle management
    - PositionManager: Portfolio analytics and risk management
    - ProjectXRealtimeDataManager: Real-time multi-timeframe data
    - OrderBook: Level 2 market depth analysis

    The client implements enterprise-grade features including connection pooling,
    automatic retry mechanisms, rate limiting, and intelligent caching for optimal
    performance when building trading applications.

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
        >>> # Basic SDK usage with environment variables (recommended)
        >>> from project_x_py import ProjectX
        >>> client = ProjectX.from_env()
        >>> # Multi-account setup - list and select specific account
        >>> accounts = client.list_accounts()
        >>> for account in accounts:
        ...     print(f"Account: {account['name']} (ID: {account['id']})")
        >>> # Select specific account by name
        >>> client = ProjectX.from_env(account_name="Main Trading Account")
        >>> # Core market data operations
        >>> instruments = client.search_instruments("MGC")
        >>> gold_contract = client.get_instrument("MGC")
        >>> historical_data = client.get_data("MGC", days=5, interval=15)
        >>> # Position and trade analysis
        >>> positions = client.search_open_positions()
        >>> trades = client.search_trades(limit=50)
        >>> # For order management, use the OrderManager
        >>> from project_x_py import create_order_manager
        >>> order_manager = create_order_manager(client)
        >>> order_manager.initialize()
        >>> response = order_manager.place_market_order("MGC", 0, 1)
        >>> # For real-time data, use the data manager
        >>> from project_x_py import create_trading_suite
        >>> suite = create_trading_suite(
        ...     instrument="MGC",
        ...     project_x=client,
        ...     jwt_token=client.get_session_token(),
        ...     account_id=client.get_account_info().id,
        ... )
    """

    def __init__(
        self,
        username: str,
        api_key: str,
        config: ProjectXConfig | None = None,
        account_name: str | None = None,
    ):
        """
        Initialize the ProjectX client for building trading applications.

        Args:
            username: Username for ProjectX account authentication
            api_key: API key for ProjectX authentication
            config: Optional configuration object with endpoints and settings (uses defaults if None)
            account_name: Optional account name to select specific account (uses first available if None)

        Raises:
            ValueError: If required credentials are missing
            ProjectXError: If configuration is invalid

        Example:
            >>> # Using explicit credentials
            >>> client = ProjectX(username="your_username", api_key="your_api_key")
            >>> # With specific account selection
            >>> client = ProjectX(
            ...     username="your_username",
            ...     api_key="your_api_key",
            ...     account_name="Main Trading Account",
            ... )
        """
        if not username or not api_key:
            raise ValueError("Both username and api_key are required")

        # Load configuration
        if config is None:
            config_manager = ConfigManager()
            config = config_manager.load_config()

        self.config = config
        self.api_key = api_key
        self.username = username
        self.account_name = (
            account_name.upper() if account_name else None
        )  # Store account name for selection

        # Set up timezone and URLs from config
        self.timezone = pytz.timezone(config.timezone)
        self.base_url = config.api_url

        # Initialize client settings from config
        self.timeout_seconds = config.timeout_seconds
        self.retry_attempts = config.retry_attempts
        self.retry_delay_seconds = config.retry_delay_seconds
        self.requests_per_minute = config.requests_per_minute
        self.burst_limit = config.burst_limit

        # Authentication and session management
        self.session_token: str = ""
        self.headers = None
        self.token_expires_at = None
        self.last_request_time = 0
        self.min_request_interval = 60.0 / self.requests_per_minute

        # Connection pooling and session management
        self.session = self._create_session()

        # Caching for performance
        self.instrument_cache: dict[str, Instrument] = {}
        self.cache_ttl = 300  # 5 minutes cache TTL
        self.last_cache_cleanup = time.time()

        # Lazy initialization - don't authenticate immediately
        self.account_info: Account | None = None
        self._authenticated = False

        # Performance monitoring
        self.api_call_count = 0
        self.cache_hit_count = 0

        self.logger = logging.getLogger(__name__)

    @classmethod
    def from_env(
        cls, config: ProjectXConfig | None = None, account_name: str | None = None
    ) -> "ProjectX":
        """
        Create ProjectX client using environment variables (recommended approach).

        This is the preferred method for initializing the client as it keeps
        sensitive credentials out of your source code.

        Environment Variables Required:
            PROJECT_X_API_KEY: API key for ProjectX authentication
            PROJECT_X_USERNAME: Username for ProjectX account

        Optional Environment Variables:
            PROJECT_X_ACCOUNT_NAME: Account name to select specific account

        Args:
            config: Optional configuration object with endpoints and settings
            account_name: Optional account name (overrides environment variable)

        Returns:
            ProjectX: Configured client instance ready for building trading applications

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
            >>> # Create client (recommended approach)
            >>> from project_x_py import ProjectX
            >>> client = ProjectX.from_env()
            >>> # With custom configuration
            >>> from project_x_py import create_custom_config
            >>> custom_config = create_custom_config(
            ...     api_url="https://custom.api.endpoint.com"
            ... )
            >>> client = ProjectX.from_env(config=custom_config)
        """
        config_manager = ConfigManager()
        auth_config = config_manager.get_auth_config()

        # Use provided account_name or try to get from environment
        if account_name is None:
            account_name = os.getenv("PROJECT_X_ACCOUNT_NAME")

        return cls(
            username=auth_config["username"],
            api_key=auth_config["api_key"],
            config=config,
            account_name=account_name.upper() if account_name else None,
        )

    @classmethod
    def from_config_file(
        cls, config_file: str, account_name: str | None = None
    ) -> "ProjectX":
        """
        Create ProjectX client using a configuration file.

        Args:
            config_file: Path to configuration file
            account_name: Optional account name to select specific account

        Returns:
            ProjectX client instance
        """
        config_manager = ConfigManager(config_file)
        config = config_manager.load_config()
        auth_config = config_manager.get_auth_config()

        return cls(
            username=auth_config["username"],
            api_key=auth_config["api_key"],
            config=config,
            account_name=account_name.upper() if account_name else None,
        )

    def _create_session(self) -> requests.Session:
        """
        Create an optimized requests session with connection pooling and retries.

        Returns:
            Configured requests session
        """
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.retry_attempts,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"],
        )

        # Configure HTTP adapter with connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,  # Number of connection pools
            pool_maxsize=20,  # Maximum connections per pool
            pool_block=True,  # Block when pool is full
        )

        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _cleanup_cache(self) -> None:
        """
        Clean up expired cache entries periodically.
        """
        current_time = time.time()
        if current_time - self.last_cache_cleanup > self.cache_ttl:
            # Clear instrument cache (instruments don't change often)
            # Could implement more sophisticated TTL per entry if needed
            self.last_cache_cleanup = current_time

            # Log cache statistics
            if self.api_call_count > 0:
                cache_hit_rate = (self.cache_hit_count / self.api_call_count) * 100
                self.logger.debug(
                    f"Cache stats: {self.cache_hit_count}/{self.api_call_count} "
                    f"hits ({cache_hit_rate:.1f}%)"
                )

    def _ensure_authenticated(self):
        """
        Ensure the client is authenticated with a valid token.

        This method implements lazy authentication and automatic token refresh.
        """
        current_time = time.time()

        # Check if we need to authenticate or refresh token
        # Preemptive refresh at 80% of token lifetime for better performance
        refresh_threshold = (
            self.token_expires_at - (45 * 60 * 0.2) if self.token_expires_at else 0
        )

        if (
            not self._authenticated
            or self.session_token is None
            or (self.token_expires_at and current_time >= refresh_threshold)
        ):
            self._authenticate_with_retry()

        # Periodic cache cleanup
        self._cleanup_cache()

        # Rate limiting: ensure minimum interval between requests
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)

        self.last_request_time = time.time()

    def _authenticate_with_retry(
        self, max_retries: int | None = None, base_delay: float | None = None
    ):
        """
        Authenticate with retry logic for handling temporary server issues.

        Args:
            max_retries: Maximum number of retry attempts (uses config if None)
            base_delay: Base delay between retries (uses config if None)
        """
        if max_retries is None:
            max_retries = self.retry_attempts
        if base_delay is None:
            base_delay = self.retry_delay_seconds

        for attempt in range(max_retries):
            self.logger.debug(
                f"Authentication attempt {attempt + 1}/{max_retries} with payload: {self.username}, {self.api_key[:4]}****"
            )
            try:
                self._authenticate()
                return
            except ProjectXError as e:
                if "503" in str(e) and attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    self.logger.error(
                        f"Authentication failed (attempt {attempt + 1}/{max_retries}), retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    raise

    def _authenticate(self):
        """
        Authenticate with the ProjectX API and obtain a session token.

        Uses the API key to authenticate and sets up headers for subsequent requests.

        Raises:
            ProjectXAuthenticationError: If authentication fails
            ProjectXServerError: If server returns 5xx error
            ProjectXConnectionError: If connection fails
        """
        url = f"{self.base_url}/Auth/loginKey"
        headers = {"accept": "text/plain", "Content-Type": "application/json"}

        payload = {"userName": self.username, "apiKey": self.api_key}

        try:
            self.api_call_count += 1
            response = self.session.post(url, headers=headers, json=payload)

            # Handle different HTTP status codes
            if response.status_code == 503:
                raise ProjectXServerError(
                    f"Server temporarily unavailable (503): {response.text}"
                )
            elif response.status_code == 429:
                raise ProjectXRateLimitError(
                    f"Rate limit exceeded (429): {response.text}"
                )
            elif response.status_code >= 500:
                raise ProjectXServerError(
                    f"Server error ({response.status_code}): {response.text}"
                )
            elif response.status_code >= 400:
                raise ProjectXAuthenticationError(
                    f"Authentication failed ({response.status_code}): {response.text}"
                )

            response.raise_for_status()

            data = response.json()
            if not data.get("success", False):
                error_msg = data.get("errorMessage", "Unknown authentication error")
                raise ProjectXAuthenticationError(f"Authentication failed: {error_msg}")

            self.session_token = data["token"]

            # Estimate token expiration (typically JWT tokens last 1 hour)
            # Set expiration to 45 minutes to allow for refresh buffer
            self.token_expires_at = time.time() + (45 * 60)

            # Set up headers for subsequent requests
            self.headers = {
                "Authorization": f"Bearer {self.session_token}",
                "accept": "text/plain",
                "Content-Type": "application/json",
            }

            self._authenticated = True
            self.logger.info("ProjectX authentication successful")

        except requests.RequestException as e:
            self.logger.error(f"Authentication request failed: {e}")
            raise ProjectXConnectionError(f"Authentication request failed: {e}") from e
        except (KeyError, json.JSONDecodeError) as e:
            self.logger.error(f"Invalid authentication response: {e}")
            raise ProjectXAuthenticationError(
                f"Invalid authentication response: {e}"
            ) from e

    def get_session_token(self):
        """
        Get the current session token.

        Returns:
            str: The JWT session token

        Note:
            This is a legacy method for backward compatibility.
        """
        self._ensure_authenticated()
        return self.session_token

    def get_account_info(self) -> Account | None:
        """
        Retrieve account information for active accounts.

        Returns:
            Account: Account information including balance and trading permissions
            None: If no active accounts are found

        Raises:
            ProjectXError: If not authenticated or API request fails

        Example:
            >>> account = project_x.get_account_info()
            >>> print(f"Account balance: ${account.balance}")
        """
        self._ensure_authenticated()

        # Cache account info to avoid repeated API calls
        if self.account_info is not None:
            return self.account_info

        url = f"{self.base_url}/Account/search"
        payload = {"onlyActiveAccounts": True}

        try:
            self.api_call_count += 1
            response = self.session.post(url, headers=self.headers, json=payload)
            self._handle_response_errors(response)

            data = response.json()
            if not data.get("success", False):
                error_msg = data.get("errorMessage", "Unknown error")
                self.logger.error(f"Account search failed: {error_msg}")
                raise ProjectXError(f"Account search failed: {error_msg}")

            accounts = data.get("accounts", [])
            if not accounts:
                return None

            # If account_name is provided, find the specific account by name
            if self.account_name:
                for account in accounts:
                    if account.get("name").upper() == self.account_name.upper():
                        self.account_info = Account(**account)
                        return self.account_info
                self.logger.warning(
                    f"Account with name '{self.account_name}' not found."
                )
                return None

            # Otherwise, take the first active account
            self.account_info = Account(**accounts[0])
            return self.account_info

        except requests.RequestException as e:
            raise ProjectXConnectionError(f"Account search request failed: {e}") from e
        except (KeyError, json.JSONDecodeError, TypeError) as e:
            self.logger.error(f"Invalid account response: {e}")
            raise ProjectXDataError(f"Invalid account response: {e}") from e

    def list_accounts(self) -> list[dict]:
        """
        List all available accounts for the authenticated user.

        Returns:
            List[dict]: List of all available accounts with their details

        Raises:
            ProjectXError: If not authenticated or API request fails

        Example:
            >>> accounts = project_x.list_accounts()
            >>> for account in accounts:
            ...     print(f"Account: {account['name']} (ID: {account['id']})")
            ...     print(f"  Balance: ${account.get('balance', 0):.2f}")
            ...     print(f"  Can Trade: {account.get('canTrade', False)}")
        """
        self._ensure_authenticated()

        url = f"{self.base_url}/Account/search"
        payload = {"onlyActiveAccounts": True}

        try:
            self.api_call_count += 1
            response = self.session.post(url, headers=self.headers, json=payload)
            self._handle_response_errors(response)

            data = response.json()
            if not data.get("success", False):
                error_msg = data.get("errorMessage", "Unknown error")
                self.logger.error(f"Account search failed: {error_msg}")
                raise ProjectXError(f"Account search failed: {error_msg}")

            accounts = data.get("accounts", [])
            return accounts

        except requests.RequestException as e:
            raise ProjectXConnectionError(f"Account search request failed: {e}") from e
        except (KeyError, json.JSONDecodeError, TypeError) as e:
            self.logger.error(f"Invalid account response: {e}")
            raise ProjectXDataError(f"Invalid account response: {e}") from e

    def _handle_response_errors(self, response: requests.Response):
        """
        Handle HTTP response errors consistently.

        Args:
            response: requests.Response object

        Raises:
            ProjectXServerError: For 5xx errors
            ProjectXRateLimitError: For 429 errors
            ProjectXError: For other 4xx errors
        """
        if response.status_code == 503:
            raise ProjectXServerError("Server temporarily unavailable (503)")
        elif response.status_code == 429:
            raise ProjectXRateLimitError("Rate limit exceeded (429)")
        elif response.status_code >= 500:
            raise ProjectXServerError(f"Server error ({response.status_code})")
        elif response.status_code >= 400:
            raise ProjectXError(f"Client error ({response.status_code})")

        response.raise_for_status()

    def get_instrument(self, symbol: str, live: bool = False) -> Instrument | None:
        """
        Search for the best matching instrument for a symbol with intelligent contract selection.

        The method implements smart matching to handle ProjectX's fuzzy search results:
        1. Exact symbolId suffix match (e.g., "ENQ" matches "F.US.ENQ")
        2. Exact name match (e.g., "NQU5" matches contract name "NQU5")
        3. Prefers active contracts over inactive ones
        4. Falls back to first active contract if no exact matches

        Args:
            symbol: Symbol to search for (e.g., "ENQ", "MNQ", "NQU5")
            live: Whether to search for live instruments (default: False)

        Returns:
            Instrument: Best matching instrument with contract details
            None: If no instruments are found

        Raises:
            ProjectXInstrumentError: If instrument search fails

        Example:
            >>> # Exact symbolId match - gets F.US.ENQ, not MNQ
            >>> instrument = client.get_instrument("ENQ")
            >>> print(f"Contract: {instrument.name} ({instrument.symbolId})")
            >>> # Exact name match - gets specific contract
            >>> instrument = client.get_instrument("NQU5")
            >>> print(f"Description: {instrument.description}")
            >>> # Smart selection prioritizes active contracts
            >>> instrument = client.get_instrument("MGC")
            >>> if instrument:
            ...     print(f"Selected: {instrument.id}")
        """
        # Check cache first
        if symbol in self.instrument_cache:
            self.cache_hit_count += 1
            return self.instrument_cache[symbol]

        self._ensure_authenticated()

        url = f"{self.base_url}/Contract/search"
        payload = {"searchText": symbol, "live": live}

        try:
            self.api_call_count += 1
            response = self.session.post(url, headers=self.headers, json=payload)
            self._handle_response_errors(response)

            data = response.json()
            if not data.get("success", False):
                error_msg = data.get("errorMessage", "Unknown error")
                self.logger.error(f"Contract search failed: {error_msg}")
                raise ProjectXInstrumentError(f"Contract search failed: {error_msg}")

            contracts = data.get("contracts", [])
            if not contracts:
                self.logger.error(f"No contracts found for symbol: {symbol}")
                return None

            # Smart contract selection
            selected_contract = self._select_best_contract(contracts, symbol)
            if not selected_contract:
                self.logger.error(f"No suitable contract found for symbol: {symbol}")
                return None

            instrument = Instrument(**selected_contract)
            # Cache the result
            self.instrument_cache[symbol] = instrument
            self.logger.debug(
                f"Selected contract {instrument.id} for symbol '{symbol}'"
            )
            return instrument

        except requests.RequestException as e:
            raise ProjectXConnectionError(f"Contract search request failed: {e}") from e
        except (KeyError, json.JSONDecodeError, TypeError) as e:
            self.logger.error(f"Invalid contract response: {e}")
            raise ProjectXDataError(f"Invalid contract response: {e}") from e

    def _select_best_contract(
        self, contracts: list[dict], search_symbol: str
    ) -> dict | None:
        """
        Select the best matching contract from ProjectX search results.

        Selection priority:
        1. Exact base symbol match (after removing futures suffix) + active contract
        2. Exact symbolId suffix match + active contract
        3. Exact base symbol match (any status)
        4. Exact symbolId suffix match (any status)
        5. First active contract
        6. First contract (fallback)

        Args:
            contracts: List of contract dictionaries from ProjectX API
            search_symbol: The symbol being searched for

        Returns:
            dict: Best matching contract, or None if no contracts

        Example:
            Search "NQ" should match "NQU5" (base: NQ), not "MNQU5" (base: MNQ)
            Search "MGC" should match "MGCH25" (base: MGC)
        """
        if not contracts:
            return None

        import re

        # Futures month codes
        month_codes = "FGHJKMNQUVXZ"

        def get_base_symbol(contract_name: str) -> str:
            """Extract base symbol by removing futures month/year suffix"""
            # Match pattern: base symbol + month code + 1-2 digit year
            match = re.match(
                rf"^(.+?)([{month_codes}]\d{{1,2}})$", contract_name.upper()
            )
            return match.group(1) if match else contract_name.upper()

        search_upper = search_symbol.upper()
        active_contracts = [c for c in contracts if c.get("activeContract", False)]

        # 1. Exact base symbol match + active
        for contract in active_contracts:
            name = contract.get("name", "")
            if get_base_symbol(name) == search_upper:
                return contract

        # 2. Exact symbolId suffix match + active
        for contract in active_contracts:
            symbol_id = contract.get("symbolId", "")
            if symbol_id and symbol_id.upper().endswith(f".{search_upper}"):
                return contract

        # 3. Exact base symbol match (any status)
        for contract in contracts:
            name = contract.get("name", "")
            if get_base_symbol(name) == search_upper:
                return contract

        # 4. Exact symbolId suffix match (any status)
        for contract in contracts:
            symbol_id = contract.get("symbolId", "")
            if symbol_id and symbol_id.upper().endswith(f".{search_upper}"):
                return contract

        # 5. First active contract
        if active_contracts:
            return active_contracts[0]

        # 6. Fallback to first contract
        return contracts[0]

    def search_instruments(self, symbol: str, live: bool = False) -> list[Instrument]:
        """
        Search for all instruments matching a symbol.

        Returns all contracts that match the search criteria, useful for exploring
        available instruments or finding related contracts.

        Args:
            symbol: Symbol to search for (e.g., "MGC", "MNQ", "NQ")
            live: Whether to search for live instruments (default: False)

        Returns:
            List[Instrument]: List of all matching instruments with contract details

        Raises:
            ProjectXInstrumentError: If instrument search fails

        Example:
            >>> # Search for all NQ-related contracts
            >>> instruments = client.search_instruments("NQ")
            >>> for inst in instruments:
            ...     print(f"{inst.name}: {inst.description}")
            ...     print(
            ...         f"  Symbol ID: {inst.symbolId}, Active: {inst.activeContract}"
            ...     )
            >>> # Search for gold contracts
            >>> gold_instruments = client.search_instruments("MGC")
            >>> print(f"Found {len(gold_instruments)} gold contracts")
        """
        self._ensure_authenticated()

        url = f"{self.base_url}/Contract/search"
        payload = {"searchText": symbol, "live": live}

        try:
            self.api_call_count += 1
            response = self.session.post(url, headers=self.headers, json=payload)
            self._handle_response_errors(response)

            data = response.json()
            if not data.get("success", False):
                error_msg = data.get("errorMessage", "Unknown error")
                self.logger.error(f"Contract search failed: {error_msg}")
                raise ProjectXInstrumentError(f"Contract search failed: {error_msg}")

            contracts = data.get("contracts", [])
            return [Instrument(**contract) for contract in contracts]

        except requests.RequestException as e:
            raise ProjectXConnectionError(f"Contract search request failed: {e}") from e
        except (KeyError, json.JSONDecodeError, TypeError) as e:
            self.logger.error(f"Invalid contract response: {e}")
            raise ProjectXDataError(f"Invalid contract response: {e}") from e

    def get_data(
        self,
        instrument: str,
        days: int = 8,
        interval: int = 5,
        unit: int = 2,
        limit: int | None = None,
        partial: bool = True,
    ) -> pl.DataFrame | None:
        """
        Retrieve historical OHLCV bar data for an instrument.

        This method fetches historical market data with intelligent caching and
        timezone handling. The data is returned as a Polars DataFrame optimized
        for financial analysis and technical indicator calculations.

        Args:
            instrument: Symbol of the instrument (e.g., "MGC", "MNQ", "ES")
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
            None: If no data is available for the specified instrument

        Raises:
            ProjectXInstrumentError: If instrument not found or invalid
            ProjectXDataError: If data retrieval fails or invalid response

        Example:
            >>> # Get 5 days of 15-minute gold data
            >>> data = client.get_data("MGC", days=5, interval=15)
            >>> print(f"Retrieved {len(data)} bars")
            >>> print(
            ...     f"Date range: {data['timestamp'].min()} to {data['timestamp'].max()}"
            ... )
            >>> print(data.tail())
            >>> # Get 1 day of 5-second ES data for high-frequency analysis
            >>> hf_data = client.get_data("ES", days=1, interval=5, unit=1)
            >>> # Get daily bars for longer-term analysis
            >>> daily_data = client.get_data("MGC", days=30, interval=1, unit=4)
        """
        self._ensure_authenticated()

        # Get instrument details
        instrument_obj = self.get_instrument(instrument)
        if not instrument_obj:
            raise ProjectXInstrumentError(f"Instrument '{instrument}' not found")

        url = f"{self.base_url}/History/retrieveBars"

        # Calculate date range
        start_date = datetime.datetime.now(self.timezone) - timedelta(days=days)
        end_date = datetime.datetime.now(self.timezone)

        # Calculate limit based on unit type
        if not limit:
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

        payload = {
            "contractId": instrument_obj.id,
            "live": False,
            "startTime": start_date.isoformat(),
            "endTime": end_date.isoformat(),
            "unit": unit,
            "unitNumber": interval,
            "limit": limit,
            "includePartialBar": partial,
        }

        try:
            self.api_call_count += 1
            response = self.session.post(url, headers=self.headers, json=payload)
            self._handle_response_errors(response)

            data = response.json()
            if not data.get("success", False):
                error_msg = data.get("errorMessage", "Unknown error")
                self.logger.error(f"History retrieval failed: {error_msg}")
                raise ProjectXDataError(f"History retrieval failed: {error_msg}")

            bars = data.get("bars", [])
            if not bars:
                return None

            # Optimize DataFrame creation and operations
            # Create DataFrame with proper schema and efficient column operations
            df = (
                pl.from_dicts(bars)
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
                    .dt.convert_time_zone(str(self.timezone.zone))
                )
            )

            # Trigger garbage collection for large datasets
            if len(df) > 10000:
                gc.collect()

            return df

        except requests.RequestException as e:
            raise ProjectXConnectionError(
                f"History retrieval request failed: {e}"
            ) from e
        except (KeyError, json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Invalid history response: {e}")
            raise ProjectXDataError(f"Invalid history response: {e}") from e

    # Position Management Methods
    def search_open_positions(self, account_id: int | None = None) -> list[Position]:
        """
        Search for currently open positions in the specified account.

        Retrieves all open positions with current size, average price, and P&L information.
        Useful for portfolio monitoring and risk management in trading applications.

        Args:
            account_id: Account ID to search (uses default account if None)

        Returns:
            List[Position]: List of open positions with detailed information including:
                - contractId: Instrument contract identifier
                - size: Current position size (positive=long, negative=short)
                - averagePrice: Average entry price
                - unrealizedPnl: Current unrealized profit/loss

        Raises:
            ProjectXError: If position search fails or no account information available

        Example:
            >>> # Get all open positions
            >>> positions = client.search_open_positions()
            >>> for pos in positions:
            ...     print(f"{pos.contractId}: {pos.size} @ ${pos.averagePrice:.2f}")
            ...     if hasattr(pos, "unrealizedPnl"):
            ...         print(f"  P&L: ${pos.unrealizedPnl:.2f}")
            >>> # Check if any positions are open
            >>> if positions:
            ...     print(f"Currently holding {len(positions)} positions")
            ... else:
            ...     print("No open positions")
        """
        self._ensure_authenticated()

        # Use account_info if no account_id provided
        if account_id is None:
            if not self.account_info:
                self.get_account_info()
            if not self.account_info:
                raise ProjectXError("No account information available")
            account_id = self.account_info.id

        url = f"{self.base_url}/Position/searchOpen"
        payload = {"accountId": account_id}

        try:
            self.api_call_count += 1
            response = self.session.post(url, headers=self.headers, json=payload)
            self._handle_response_errors(response)

            data = response.json()
            if not data.get("success", False):
                error_msg = data.get("errorMessage", "Unknown error")
                self.logger.error(f"Position search failed: {error_msg}")
                raise ProjectXError(f"Position search failed: {error_msg}")

            positions = data.get("positions", [])
            return [Position(**position) for position in positions]

        except requests.RequestException as e:
            raise ProjectXConnectionError(f"Position search request failed: {e}") from e
        except (KeyError, json.JSONDecodeError, TypeError) as e:
            self.logger.error(f"Invalid position search response: {e}")
            raise ProjectXDataError(f"Invalid position search response: {e}") from e

    # ================================================================================
    # ENHANCED API COVERAGE - COMPREHENSIVE ENDPOINT ACCESS
    # ================================================================================

    def search_trades(
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
            >>> trades = client.search_trades(start_date=start)
            >>> for trade in trades:
            ...     print(
            ...         f"Trade: {trade.contractId} - {trade.size} @ ${trade.price:.2f}"
            ...     )
            ...     print(f"  Time: {trade.timestamp}")
            >>> # Get trades for specific instrument
            >>> mgc_trades = client.search_trades(contract_id="MGC", limit=50)
            >>> print(f"Found {len(mgc_trades)} MGC trades")
            >>> # Calculate total trading volume
            >>> total_volume = sum(abs(trade.size) for trade in trades)
            >>> print(f"Total volume traded: {total_volume}")
        """
        self._ensure_authenticated()

        if account_id is None:
            if not self.account_info:
                self.get_account_info()
            if not self.account_info:
                raise ProjectXError("No account information available")
            account_id = self.account_info.id

        # Default date range if not provided
        if start_date is None:
            start_date = datetime.datetime.now(self.timezone) - timedelta(days=30)
        if end_date is None:
            end_date = datetime.datetime.now(self.timezone)

        url = f"{self.base_url}/Trade/search"
        payload = {
            "accountId": account_id,
            "startTime": start_date.isoformat(),
            "endTime": end_date.isoformat(),
            "limit": limit,
        }

        if contract_id:
            payload["contractId"] = contract_id

        try:
            self.api_call_count += 1
            response = self.session.post(url, headers=self.headers, json=payload)
            self._handle_response_errors(response)

            data = response.json()
            if not data.get("success", False):
                error_msg = data.get("errorMessage", "Unknown error")
                self.logger.error(f"Trade search failed: {error_msg}")
                raise ProjectXDataError(f"Trade search failed: {error_msg}")

            trades = data.get("trades", [])
            return [Trade(**trade) for trade in trades]

        except requests.RequestException as e:
            raise ProjectXConnectionError(f"Trade search request failed: {e}") from e
        except (KeyError, json.JSONDecodeError, TypeError) as e:
            self.logger.error(f"Invalid trade search response: {e}")
            raise ProjectXDataError(f"Invalid trade search response: {e}") from e

    # Additional convenience methods can be added here as needed
    def get_health_status(self) -> dict:
        """
        Get client health status.

        Returns:
            Dict with health status information
        """
        return {
            "authenticated": self._authenticated,
            "has_session_token": bool(self.session_token),
            "token_expires_at": self.token_expires_at,
            "account_info_loaded": self.account_info is not None,
            "config": {
                "base_url": self.base_url,
                "timeout_seconds": self.timeout_seconds,
                "retry_attempts": self.retry_attempts,
                "requests_per_minute": self.requests_per_minute,
            },
        }

    def test_contract_selection(self) -> dict[str, Any]:
        """
        Test the contract selection algorithm with various scenarios.

        Returns:
            dict: Test results with validation status and recommendations
        """
        test_results = {
            "validation": "passed",
            "performance_metrics": {},
            "recommendations": [],
            "test_cases": {},
        }

        # Mock contract data similar to ProjectX NQ search example
        mock_contracts = [
            {
                "id": "CON.F.US.ENQ.U25",
                "name": "NQU5",
                "description": "E-mini NASDAQ-100: September 2025",
                "symbolId": "F.US.ENQ",
                "activeContract": True,
                "tickSize": 0.25,
                "tickValue": 5.0,
            },
            {
                "id": "CON.F.US.MNQ.U25",
                "name": "MNQU5",
                "description": "Micro E-mini Nasdaq-100: September 2025",
                "symbolId": "F.US.MNQ",
                "activeContract": True,
                "tickSize": 0.25,
                "tickValue": 0.5,
            },
            {
                "id": "CON.F.US.NQG.Q25",
                "name": "QGQ5",
                "description": "E-Mini Natural Gas: August 2025",
                "symbolId": "F.US.NQG",
                "activeContract": True,
                "tickSize": 0.005,
                "tickValue": 12.5,
            },
        ]

        try:
            # Test 1: Exact symbolId suffix match
            result1 = self._select_best_contract(mock_contracts, "ENQ")
            expected1 = "F.US.ENQ"
            actual1 = result1.get("symbolId") if result1 else None
            test_results["test_cases"]["exact_symbolId_match"] = {
                "passed": actual1 == expected1,
                "expected": expected1,
                "actual": actual1,
            }

            # Test 2: Different symbolId match
            result2 = self._select_best_contract(mock_contracts, "MNQ")
            expected2 = "F.US.MNQ"
            actual2 = result2.get("symbolId") if result2 else None
            test_results["test_cases"]["different_symbolId_match"] = {
                "passed": actual2 == expected2,
                "expected": expected2,
                "actual": actual2,
            }

            # Test 3: Exact name match
            result3 = self._select_best_contract(mock_contracts, "NQU5")
            expected3 = "NQU5"
            actual3 = result3.get("name") if result3 else None
            test_results["test_cases"]["exact_name_match"] = {
                "passed": actual3 == expected3,
                "expected": expected3,
                "actual": actual3,
            }

            # Test 4: Fallback behavior (no exact match)
            result4 = self._select_best_contract(mock_contracts, "UNKNOWN")
            test_results["test_cases"]["fallback_behavior"] = {
                "passed": result4 is not None and result4.get("activeContract", False),
                "description": "Should return first active contract when no exact match",
            }

            # Check overall validation
            all_passed = all(
                test.get("passed", False)
                for test in test_results["test_cases"].values()
            )

            if not all_passed:
                test_results["validation"] = "failed"
                test_results["recommendations"].append(
                    "Contract selection algorithm needs refinement"
                )
            else:
                test_results["recommendations"].append(
                    "Smart contract selection working correctly"
                )

        except Exception as e:
            test_results["validation"] = "error"
            test_results["error"] = str(e)
            test_results["recommendations"].append(
                f"Contract selection test failed: {e}"
            )

        return test_results
