"""Base client class with lifecycle methods for ProjectX."""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import httpx

from project_x_py.client.auth import AuthenticationMixin
from project_x_py.client.cache import CacheMixin
from project_x_py.client.http import HttpMixin
from project_x_py.client.market_data import MarketDataMixin
from project_x_py.client.rate_limiter import RateLimiter
from project_x_py.client.trading import TradingMixin
from project_x_py.config import ConfigManager
from project_x_py.exceptions import ProjectXAuthenticationError
from project_x_py.models import Account, ProjectXConfig


class ProjectXBase(
    AuthenticationMixin,
    HttpMixin,
    CacheMixin,
    MarketDataMixin,
    TradingMixin,
):
    """Base class combining all ProjectX client functionality."""

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
        # Initialize all mixins
        super().__init__()

        self.username = username
        self.api_key = api_key
        self.account_name = account_name

        # Ensure _client is properly typed
        self._client: httpx.AsyncClient | None = None

        # Use provided config or create default
        self.config = config or ProjectXConfig()
        self.base_url = self.config.api_url

        # Initialize headers
        self.headers: dict[str, str] = {"Content-Type": "application/json"}

        # Lazy initialization - don't authenticate immediately
        self.account_info: Account | None = None

        # Rate limiting - 100 requests per minute by default
        self.rate_limiter = RateLimiter(max_requests=100, window_seconds=60)

        self.logger = logging.getLogger(__name__)

    async def __aenter__(self) -> "ProjectXBase":
        """Async context manager entry."""
        self._client = await self._create_client()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def get_session_token(self) -> str:
        """
        Get the current session JWT token.

        Returns:
            str: JWT token for authentication

        Raises:
            ProjectXAuthenticationError: If not authenticated
        """
        if not self._authenticated or not self.session_token:
            raise ProjectXAuthenticationError(
                "Not authenticated. Call authenticate() first."
            )
        return self.session_token

    def get_account_info(self) -> Account:
        """
        Get the currently selected account information.

        Returns:
            Account: Current account details

        Raises:
            ProjectXAuthenticationError: If not authenticated
        """
        if not self.account_info:
            raise ProjectXAuthenticationError(
                "No account selected. Call authenticate() first."
            )
        return self.account_info

    @classmethod
    @asynccontextmanager
    async def from_env(
        cls, config: ProjectXConfig | None = None, account_name: str | None = None
    ) -> AsyncGenerator["ProjectXBase", None]:
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
    ) -> AsyncGenerator["ProjectXBase", None]:
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
