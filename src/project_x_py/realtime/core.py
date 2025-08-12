"""
Async ProjectX Realtime Client for ProjectX Gateway API

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides an async Python client for the ProjectX real-time API, which provides
    access to the ProjectX trading platform real-time events via SignalR WebSocket
    connections. Implements dual-hub architecture for user and market data streams.

Key Features:
    - Full async/await support for all operations
    - Asyncio-based connection management
    - Non-blocking event processing
    - Async callbacks for all events
    - Dual-hub SignalR connections (User + Market)
    - Automatic reconnection with exponential backoff
    - JWT token authentication and refresh handling
    - Thread-safe event processing and callback execution
    - Connection health monitoring and statistics

Architecture:
    - Pure event forwarding (no business logic)
    - No data caching (handled by managers)
    - No payload parsing (managers handle ProjectX formats)
    - Minimal stateful operations
    - Mixin-based design for modular functionality

Real-time Hubs:
    - User Hub: Account, position, and order updates
    - Market Hub: Quote, trade, and market depth data

Note:
    This class forms the low-level foundation for real-time data. For most applications,
    the `TradingSuite` is the recommended entry point as it abstracts away the direct
    management of this client, its connections, and its events.

Example Usage:
    The example below shows how to use the client directly. In a real application,
    the `position_manager`, `order_manager`, and `data_manager` would be instances
    of the SDK's manager classes.

    ```python
    # V3: Create async client with ProjectX Gateway URLs
    import asyncio
    from project_x_py import create_realtime_client


    async def main():
        # V3: Use factory function for proper initialization
        client = await create_realtime_client(jwt_token, account_id)

        # V3: Register async managers for event handling
        # await client.add_callback("position_update", position_manager.handle_update)
        # await client.add_callback("order_update", order_manager.handle_update)
        # await client.add_callback("quote_update", data_manager.handle_quote)

        # V3: Connect and check both hub connections
        if await client.connect():
            print(f"User Hub: {client.user_connected}")
            print(f"Market Hub: {client.market_connected}")

            # V3: Subscribe to user and market data
            await client.subscribe_user_updates()
            await client.subscribe_market_data(["MGC", "MNQ"])

            # V3: Process events
            await asyncio.sleep(60)

            # V3: Clean disconnect
            await client.disconnect()


    # asyncio.run(main())
    ```

Event Types (per ProjectX Gateway docs):
    User Hub: GatewayUserAccount, GatewayUserPosition, GatewayUserOrder, GatewayUserTrade
    Market Hub: GatewayQuote, GatewayDepth, GatewayTrade

Integration:
    - AsyncPositionManager handles position events and caching
    - AsyncOrderManager handles order events and tracking
    - AsyncRealtimeDataManager handles market data and caching
    - This client only handles connections and event forwarding
"""

import asyncio
import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from project_x_py.realtime.connection_management import ConnectionManagementMixin
from project_x_py.realtime.event_handling import EventHandlingMixin
from project_x_py.realtime.subscriptions import SubscriptionsMixin

if TYPE_CHECKING:
    from project_x_py.models import ProjectXConfig


class ProjectXRealtimeClient(
    ConnectionManagementMixin,
    EventHandlingMixin,
    SubscriptionsMixin,
):
    """
    Async real-time client for ProjectX Gateway API WebSocket connections.

    This class provides an async interface for ProjectX SignalR connections and
    forwards all events to registered managers. It does NOT cache data or perform
    business logic - that's handled by the specialized managers.

    Features:
        - Async SignalR WebSocket connections to ProjectX Gateway hubs
        - Event forwarding to registered async managers
        - Automatic reconnection with exponential backoff
        - JWT token refresh and reconnection
        - Connection health monitoring
        - Async event callbacks
        - Thread-safe event processing and callback execution
        - Comprehensive connection statistics and health tracking

    Architecture:
        - Pure event forwarding (no business logic)
        - No data caching (handled by managers)
        - No payload parsing (managers handle ProjectX formats)
        - Minimal stateful operations
        - Mixin-based design for modular functionality

    Real-time Hubs (per ProjectX Gateway docs):
        - User Hub: Account, position, and order updates
        - Market Hub: Quote, trade, and market depth data

    Connection Management:
        - Dual-hub SignalR connections with automatic reconnection
        - JWT token authentication via Authorization headers
        - Connection health monitoring and error handling
        - Thread-safe operations with proper lock management

    Event Processing:
        - Cross-thread event scheduling for asyncio compatibility
        - Support for both async and sync callbacks
        - Error isolation to prevent callback failures
        - Event statistics and flow monitoring

    Example:
        >>> # V3: Create async client with factory function
        >>> client = await create_realtime_client(jwt_token, account_id)
        >>> # V3: Register async callbacks for event handling
        >>> async def handle_position(data):
        ...     print(f"Position: {data.get('contractId')} - {data.get('netPos')}")
        >>> async def handle_order(data):
        ...     print(f"Order {data.get('id')}: {data.get('status')}")
        >>> async def handle_quote(data):
        ...     print(f"Quote: {data.get('bid')} x {data.get('ask')}")
        >>> await client.add_callback("position_update", handle_position)
        >>> await client.add_callback("order_update", handle_order)
        >>> await client.add_callback("quote_update", handle_quote)
        >>>
        >>> # V3: Connect and subscribe with error handling
        >>> if await client.connect():
        ...     await client.subscribe_user_updates()
        ...     await client.subscribe_market_data(["MGC", "MNQ"])
        ... else:
        ...     print("Connection failed")

    Event Types (per ProjectX Gateway docs):
        User Hub: GatewayUserAccount, GatewayUserPosition, GatewayUserOrder, GatewayUserTrade
        Market Hub: GatewayQuote, GatewayDepth, GatewayTrade

    Integration:
        - AsyncPositionManager handles position events and caching
        - AsyncOrderManager handles order events and tracking
        - AsyncRealtimeDataManager handles market data and caching
        - This client only handles connections and event forwarding
    """

    def __init__(
        self,
        jwt_token: str,
        account_id: str,
        user_hub_url: str | None = None,
        market_hub_url: str | None = None,
        config: "ProjectXConfig | None" = None,
    ):
        """
        Initialize async ProjectX real-time client with configurable SignalR connections.

        Creates a dual-hub SignalR client for real-time ProjectX Gateway communication.
        Handles both user-specific events (positions, orders) and market data (quotes, trades).

        Args:
            jwt_token (str): JWT authentication token from AsyncProjectX.authenticate().
                Must be valid and not expired for successful connection.
            account_id (str): ProjectX account ID for user-specific subscriptions.
                Used to filter position, order, and trade events.
            user_hub_url (str, optional): Override URL for user hub endpoint.
                If provided, takes precedence over config URL.
                Defaults to None (uses config or default).
            market_hub_url (str, optional): Override URL for market hub endpoint.
                If provided, takes precedence over config URL.
                Defaults to None (uses config or default).
            config (ProjectXConfig, optional): Configuration object with hub URLs.
                Provides default URLs if direct URLs not specified.
                Defaults to None (uses TopStepX defaults).

        URL Priority:
            1. Direct parameters (user_hub_url, market_hub_url)
            2. Config URLs (config.user_hub_url, config.market_hub_url)
            3. Default TopStepX endpoints

        Example:
            >>> # V3: Using factory function (recommended)
            >>> client = await create_realtime_client(
            ...     jwt_token=client.get_session_token(),
            ...     account_id=str(client.get_account_info().id),
            ... )
            >>> # V3: Using direct instantiation with default endpoints
            >>> client = ProjectXRealtimeClient(jwt_token=jwt_token, account_id="12345")
            >>>
            >>> # V3: Using custom config for different environments
            >>> from project_x_py.models import ProjectXConfig
            >>> config = ProjectXConfig(
            ...     user_hub_url="https://gateway.topstepx.com/hubs/user",
            ...     market_hub_url="https://gateway.topstepx.com/hubs/market",
            ... )
            >>> client = ProjectXRealtimeClient(
            ...     jwt_token=jwt_token, account_id="12345", config=config
            ... )
            >>>
            >>> # V3: Override specific URL for testing
            >>> client = ProjectXRealtimeClient(
            ...     jwt_token=jwt_token,
            ...     account_id="12345",
            ...     market_hub_url="https://test.topstepx.com/hubs/market",
            ... )

        Note:
            - JWT token is passed securely via Authorization header
            - Both hubs must connect successfully for full functionality
            - SignalR connections are established lazily on connect()
        """
        # Initialize parent mixins
        super().__init__()

        self.jwt_token = jwt_token
        self.account_id = account_id

        # Determine URLs with priority: params > config > defaults
        if config:
            default_user_url = config.user_hub_url
            default_market_url = config.market_hub_url
        else:
            # Default to TopStepX endpoints
            default_user_url = "https://rtc.topstepx.com/hubs/user"
            default_market_url = "https://rtc.topstepx.com/hubs/market"

        final_user_url = user_hub_url or default_user_url
        final_market_url = market_hub_url or default_market_url

        # Store URLs without tokens (tokens will be passed in headers)
        self.user_hub_url = final_user_url
        self.market_hub_url = final_market_url

        # Set up base URLs for token refresh
        if config:
            # Use config URLs if provided
            self.base_user_url = config.user_hub_url
            self.base_market_url = config.market_hub_url
        elif user_hub_url and market_hub_url:
            # Use provided URLs
            self.base_user_url = user_hub_url
            self.base_market_url = market_hub_url
        else:
            # Default to TopStepX endpoints
            self.base_user_url = "https://rtc.topstepx.com/hubs/user"
            self.base_market_url = "https://rtc.topstepx.com/hubs/market"

        # SignalR connection objects
        self.user_connection: Any | None = None
        self.market_connection: Any | None = None

        # Connection state tracking
        self.user_connected = False
        self.market_connected = False
        self.setup_complete = False

        # Event callbacks (pure forwarding, no caching) - already initialized in mixin
        if not hasattr(self, "callbacks"):
            self.callbacks: defaultdict[str, list[Any]] = defaultdict(list)

        # Basic statistics (no business logic)
        self.stats = {
            "events_received": 0,
            "connection_errors": 0,
            "last_event_time": None,
            "connected_time": None,
        }

        # Track subscribed contracts for reconnection
        self._subscribed_contracts: list[str] = []

        # Logger
        self.logger = logging.getLogger(__name__)

        self.logger.info("AsyncProjectX real-time client initialized")
        self.logger.info(f"User Hub: {final_user_url}")
        self.logger.info(f"Market Hub: {final_market_url}")

        # Async locks for thread-safe operations - check if not already initialized
        if not hasattr(self, "_callback_lock"):
            self._callback_lock = asyncio.Lock()
        if not hasattr(self, "_connection_lock"):
            self._connection_lock = asyncio.Lock()
