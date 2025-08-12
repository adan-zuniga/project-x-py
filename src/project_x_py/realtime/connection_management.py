"""
Connection management functionality for real-time client.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides connection management functionality for the ProjectX real-time client,
    including SignalR hub setup, connection establishment, reconnection handling,
    and JWT token refresh capabilities.

Key Features:
    - Dual-hub SignalR connection setup and management
    - Automatic reconnection with exponential backoff
    - JWT token authentication and refresh handling
    - Connection health monitoring and error handling
    - Thread-safe operations with proper lock management
    - Comprehensive connection statistics and health tracking

Connection Management Capabilities:
    - SignalR hub setup with ProjectX Gateway configuration
    - Connection establishment and health monitoring
    - Automatic reconnection with configurable intervals
    - JWT token refresh and reconnection handling
    - Connection event handling and error processing
    - Statistics tracking and health reporting

Example Usage:
    The functionality of this mixin is consumed through a `ProjectXRealtimeClient` instance.
    For most use cases, this is handled automatically by the `TradingSuite`.

    ```python
    # The following demonstrates the low-level connection lifecycle managed by this mixin.
    # Note: In a typical application, you would use TradingSuite, which handles this.
    from project_x_py import create_realtime_client

    # 1. Initialization (handled by factory or TradingSuite)
    # realtime_client = await create_realtime_client(jwt, account_id)

    # 2. Connection (handled by TradingSuite.create() or client.connect())
    # if await realtime_client.connect():
    #     print("Successfully connected to both User and Market hubs.")

    #     # 3. Health Monitoring
    #     if realtime_client.is_connected():
    #         stats = realtime_client.get_stats()
    #         print(f"Events received so far: {stats['events_received']}")

    #     # 4. Token Refresh (if managing tokens manually)
    #     # new_token = await get_new_token()
    #     # await realtime_client.update_jwt_token(new_token)

    #     # 5. Disconnection (handled by TradingSuite context manager or client.disconnect())
    #     await realtime_client.disconnect()
    ```

See Also:
    - `realtime.core.ProjectXRealtimeClient`
    - `realtime.event_handling.EventHandlingMixin`
    - `realtime.subscriptions.SubscriptionsMixin`
"""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any

from project_x_py.utils import (
    LogContext,
    LogMessages,
    ProjectXLogger,
    handle_errors,
)

try:
    from signalrcore.hub_connection_builder import HubConnectionBuilder
except ImportError:
    HubConnectionBuilder = None

if TYPE_CHECKING:
    from project_x_py.types import ProjectXRealtimeClientProtocol

logger = ProjectXLogger.get_logger(__name__)


class ConnectionManagementMixin:
    """Mixin for connection management functionality."""

    def __init__(self) -> None:
        """Initialize connection management attributes."""
        super().__init__()
        self._loop: asyncio.AbstractEventLoop | None = None

    @handle_errors("setup connections")
    async def setup_connections(self: "ProjectXRealtimeClientProtocol") -> None:
        """
        Set up SignalR hub connections with ProjectX Gateway configuration.

        Initializes both user and market hub connections with proper event handlers,
        automatic reconnection, and ProjectX-specific event mappings. Must be called
        before connect() or is called automatically on first connect().

        Hub Configuration:
            - User Hub: Account, position, order, and trade events
            - Market Hub: Quote, trade, and market depth events
            - Both hubs: Automatic reconnection with exponential backoff
            - Keep-alive: 10 second interval
            - Reconnect intervals: [1, 3, 5, 5, 5, 5] seconds

        Event Mappings:
            User Hub Events:
                - GatewayUserAccount -> account_update
                - GatewayUserPosition -> position_update
                - GatewayUserOrder -> order_update
                - GatewayUserTrade -> trade_execution

            Market Hub Events:
                - GatewayQuote -> quote_update
                - GatewayTrade -> market_trade
                - GatewayDepth -> market_depth

        Raises:
            ImportError: If signalrcore package is not installed
            Exception: If connection setup fails

        Note:
            This method is idempotent - safe to call multiple times.
            Sets self.setup_complete = True when successful.
        """
        with LogContext(
            logger,
            operation="setup_connections",
            user_hub=self.user_hub_url,
            market_hub=self.market_hub_url,
        ):
            logger.debug(LogMessages.WS_CONNECT, extra={"phase": "setup"})

            if HubConnectionBuilder is None:
                raise ImportError("signalrcore is required for real-time functionality")

            async with self._connection_lock:
                # Build user hub connection with JWT as query parameter
                # SignalR WebSocket connections often need auth tokens in URL, not headers
                user_url_with_token = (
                    f"{self.user_hub_url}?access_token={self.jwt_token}"
                )
                self.user_connection = (
                    HubConnectionBuilder()
                    .with_url(user_url_with_token)
                    .configure_logging(
                        logger.level,
                        socket_trace=False,
                        handler=None,
                    )
                    .with_automatic_reconnect(
                        {
                            "type": "interval",
                            "keep_alive_interval": 10,
                            "intervals": [1, 3, 5, 5, 5, 5],
                        }
                    )
                    .build()
                )

                # Build market hub connection with JWT as query parameter
                market_url_with_token = (
                    f"{self.market_hub_url}?access_token={self.jwt_token}"
                )
                self.market_connection = (
                    HubConnectionBuilder()
                    .with_url(market_url_with_token)
                    .configure_logging(
                        logger.level,
                        socket_trace=False,
                        handler=None,  # Use None to avoid duplicate logging
                    )
                    .with_automatic_reconnect(
                        {
                            "type": "interval",
                            "keep_alive_interval": 10,
                            "intervals": [1, 3, 5, 5, 5, 5],
                        }
                    )
                    .build()
                )

                # Set up connection event handlers
                assert self.user_connection is not None
                assert self.market_connection is not None

                self.user_connection.on_open(lambda: self._on_user_hub_open())
                self.user_connection.on_close(lambda: self._on_user_hub_close())
                self.user_connection.on_error(
                    lambda data: self._on_connection_error("user", data)
                )

                self.market_connection.on_open(lambda: self._on_market_hub_open())
                self.market_connection.on_close(lambda: self._on_market_hub_close())
                self.market_connection.on_error(
                    lambda data: self._on_connection_error("market", data)
                )

                # Set up ProjectX Gateway event handlers (per official documentation)
                # User Hub Events
                self.user_connection.on(
                    "GatewayUserAccount", self._forward_account_update
                )
                self.user_connection.on(
                    "GatewayUserPosition", self._forward_position_update
                )
                self.user_connection.on("GatewayUserOrder", self._forward_order_update)
                self.user_connection.on(
                    "GatewayUserTrade", self._forward_trade_execution
                )

                # Market Hub Events
                self.market_connection.on("GatewayQuote", self._forward_quote_update)
                self.market_connection.on("GatewayTrade", self._forward_market_trade)
                self.market_connection.on("GatewayDepth", self._forward_market_depth)

                logger.debug(
                    LogMessages.WS_CONNECTED, extra={"phase": "setup_complete"}
                )
                self.setup_complete = True

    @handle_errors("connect", reraise=False, default_return=False)
    async def connect(self: "ProjectXRealtimeClientProtocol") -> bool:
        """
        Connect to ProjectX Gateway SignalR hubs asynchronously.

        Establishes connections to both user and market hubs, enabling real-time
        event streaming. Connections are made concurrently for efficiency.

        Returns:
            bool: True if both hubs connected successfully, False otherwise

        Connection Process:
            1. Sets up connections if not already done
            2. Stores event loop for cross-thread operations
            3. Starts user hub connection
            4. Starts market hub connection
            5. Waits for connection establishment
            6. Updates connection statistics

        Example:
            >>> client = ProjectXRealtimeClient(jwt_token, account_id)
            >>> if await client.connect():
            ...     print("Connected to ProjectX Gateway")
            ...     # Subscribe to updates
            ...     await client.subscribe_user_updates()
            ...     await client.subscribe_market_data(["MGC", "NQ"])
            ... else:
            ...     print("Connection failed")

        Side Effects:
            - Sets self.user_connected and self.market_connected flags
            - Updates connection statistics
            - Stores event loop reference

        Note:
            - Both hubs must connect for success
            - SignalR connections run in thread executor for async compatibility
            - Automatic reconnection is configured but initial connect may fail
        """
        with LogContext(
            logger,
            operation="connect",
            account_id=self.account_id,
        ):
            if not self.setup_complete:
                await self.setup_connections()

            # Store the event loop for cross-thread task scheduling
            self._loop = asyncio.get_event_loop()

            logger.debug(LogMessages.WS_CONNECT)

            async with self._connection_lock:
                # Start both connections
                if self.user_connection:
                    await self._start_connection_async(self.user_connection, "user")
                else:
                    logger.error(
                        LogMessages.WS_ERROR,
                        extra={"error": "User connection not available"},
                    )
                    return False

                if self.market_connection:
                    await self._start_connection_async(self.market_connection, "market")
                else:
                    logger.error(
                        LogMessages.WS_ERROR,
                        extra={"error": "Market connection not available"},
                    )
                    return False

                # Wait for connections to establish and stabilize
                await asyncio.sleep(2.0)  # Increased wait time for connection stability

                if self.user_connected and self.market_connected:
                    self.stats["connected_time"] = datetime.now()
                    logger.debug(LogMessages.WS_CONNECTED)
                    return True
                else:
                    logger.error(
                        LogMessages.WS_ERROR,
                        extra={"error": "Failed to establish all connections"},
                    )
                    return False

    @handle_errors("start connection")
    async def _start_connection_async(
        self: "ProjectXRealtimeClientProtocol", connection: Any, name: str
    ) -> None:
        """
        Start a SignalR connection asynchronously.

        Wraps the synchronous SignalR start() method to work with asyncio by
        running it in a thread executor.

        Args:
            connection: SignalR HubConnection instance to start
            name (str): Hub name for logging ("user" or "market")

        Note:
            This is an internal method that bridges sync SignalR with async code.
        """
        # SignalR connections are synchronous, so we run them in executor
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, connection.start)
        logger.debug(LogMessages.WS_CONNECTED, extra={"hub": name})

    @handle_errors("disconnect")
    async def disconnect(self: "ProjectXRealtimeClientProtocol") -> None:
        """
        Disconnect from ProjectX Gateway hubs.

        Gracefully closes both user and market hub connections. Safe to call
        even if not connected. Clears connection flags but preserves callbacks
        and subscriptions for potential reconnection.

        Example:
            >>> # Graceful shutdown
            >>> await client.disconnect()
            >>> print("Disconnected from ProjectX Gateway")
            >>>
            >>> # Can reconnect later
            >>> if await client.connect():
            ...     # Previous subscriptions must be re-established
            ...     await client.subscribe_user_updates()

        Side Effects:
            - Sets self.user_connected = False
            - Sets self.market_connected = False
            - Stops SignalR connections

        Note:
            Does not clear callbacks or subscription lists, allowing for
            reconnection with the same configuration.
        """
        with LogContext(
            logger,
            operation="disconnect",
            account_id=self.account_id,
        ):
            logger.debug(LogMessages.WS_DISCONNECT)

            async with self._connection_lock:
                if self.user_connection:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self.user_connection.stop)
                    self.user_connected = False

                if self.market_connection:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self.market_connection.stop)
                    self.market_connected = False

                logger.debug(LogMessages.WS_DISCONNECTED)

    # Connection event handlers
    def _on_user_hub_open(self: "ProjectXRealtimeClientProtocol") -> None:
        """
        Handle user hub connection open.

        Called by SignalR when user hub connection is established.
        Sets connection flag and logs success.

        Side Effects:
            - Sets self.user_connected = True
            - Logs connection success
        """
        self.user_connected = True
        self.logger.info("✅ User hub connected")

    def _on_user_hub_close(self: "ProjectXRealtimeClientProtocol") -> None:
        """
        Handle user hub connection close.

        Called by SignalR when user hub connection is lost.
        Clears connection flag and logs warning.

        Side Effects:
            - Sets self.user_connected = False
            - Logs disconnection warning

        Note:
            Automatic reconnection will attempt based on configuration.
        """
        self.user_connected = False
        self.logger.warning("❌ User hub disconnected")

    def _on_market_hub_open(self: "ProjectXRealtimeClientProtocol") -> None:
        """
        Handle market hub connection open.

        Called by SignalR when market hub connection is established.
        Sets connection flag and logs success.

        Side Effects:
            - Sets self.market_connected = True
            - Logs connection success
        """
        self.market_connected = True
        self.logger.info("✅ Market hub connected")

    def _on_market_hub_close(self: "ProjectXRealtimeClientProtocol") -> None:
        """
        Handle market hub connection close.

        Called by SignalR when market hub connection is lost.
        Clears connection flag and logs warning.

        Side Effects:
            - Sets self.market_connected = False
            - Logs disconnection warning

        Note:
            Automatic reconnection will attempt based on configuration.
        """
        self.market_connected = False
        self.logger.warning("❌ Market hub disconnected")

    def _on_connection_error(
        self: "ProjectXRealtimeClientProtocol", hub: str, error: Any
    ) -> None:
        """
        Handle connection errors.

        Processes errors from SignalR connections. Filters out normal completion
        messages that SignalR sends as part of its protocol.

        Args:
            hub (str): Hub name ("user" or "market")
            error: Error object or message from SignalR

        Side Effects:
            - Increments connection error counter for real errors
            - Logs errors (excludes CompletionMessage)

        Note:
            SignalR CompletionMessage is not an error - it's a normal protocol message.
        """
        # Check if this is a SignalR CompletionMessage (not an error)
        error_type = type(error).__name__
        if "CompletionMessage" in error_type:
            # This is a normal SignalR protocol message, not an error
            logger.debug(f"SignalR completion message from {hub} hub: {error}")
            return

        # Log actual errors
        logger.error(LogMessages.WS_ERROR, extra={"hub": hub, "error": str(error)})
        self.stats["connection_errors"] += 1

    @handle_errors("update JWT token", reraise=False, default_return=False)
    async def update_jwt_token(
        self: "ProjectXRealtimeClientProtocol", new_jwt_token: str
    ) -> bool:
        """
        Update JWT token and reconnect with new credentials.

        Handles JWT token refresh for expired or updated tokens. Disconnects current
        connections, updates URLs with new token, and re-establishes all subscriptions.

        Args:
            new_jwt_token (str): New JWT authentication token from AsyncProjectX

        Returns:
            bool: True if reconnection successful with new token

        Process:
            1. Disconnect existing connections
            2. Update token and connection URLs
            3. Reset connection state
            4. Reconnect to both hubs
            5. Re-subscribe to user updates
            6. Re-subscribe to previous market data

        Example:
            >>> # Token refresh on expiry
            >>> async def refresh_connection():
            ...     # Get new token
            ...     await project_x.authenticate()
            ...     new_token = project_x.session_token
            ...     # Update real-time client
            ...     if await realtime_client.update_jwt_token(new_token):
            ...         print("Reconnected with new token")
            ...     else:
            ...         print("Reconnection failed")
            >>> # Scheduled token refresh
            >>> async def token_refresh_loop():
            ...     while True:
            ...         await asyncio.sleep(3600)  # Every hour
            ...         await refresh_connection()

        Side Effects:
            - Disconnects and reconnects both hubs
            - Re-subscribes to all previous subscriptions
            - Updates internal token and URLs

        Note:
            - Callbacks are preserved during reconnection
            - Market data subscriptions are restored automatically
            - Brief data gap during reconnection process
        """
        with LogContext(
            logger,
            operation="update_jwt_token",
            account_id=self.account_id,
        ):
            logger.debug(LogMessages.AUTH_REFRESH)

            # Disconnect existing connections
            await self.disconnect()

            # Update JWT token for header authentication
            self.jwt_token = new_jwt_token

            # Reset setup flag to force new connection setup
            self.setup_complete = False

            # Reconnect
            if await self.connect():
                # Re-subscribe to user updates
                await self.subscribe_user_updates()

                # Re-subscribe to market data
                if self._subscribed_contracts:
                    await self.subscribe_market_data(self._subscribed_contracts)

                logger.debug(LogMessages.WS_RECONNECT)
                return True
            else:
                logger.error(
                    LogMessages.WS_ERROR,
                    extra={"error": "Failed to reconnect with new JWT token"},
                )
                return False

    def is_connected(self: "ProjectXRealtimeClientProtocol") -> bool:
        """
        Check if both hubs are connected.

        Returns:
            bool: True only if both user and market hubs are connected

        Example:
            >>> if client.is_connected():
            ...     print("Fully connected")
            ... elif client.user_connected:
            ...     print("Only user hub connected")
            ... elif client.market_connected:
            ...     print("Only market hub connected")
            ... else:
            ...     print("Not connected")

        Note:
            Both hubs must be connected for full functionality.
            Check individual flags for partial connection status.
        """
        return self.user_connected and self.market_connected

    def get_stats(self: "ProjectXRealtimeClientProtocol") -> dict[str, Any]:
        """
        Get connection statistics.

        Provides comprehensive statistics about connection health, event flow,
        and subscription status.

        Returns:
            dict[str, Any]: Statistics dictionary containing:
                - events_received (int): Total events processed
                - connection_errors (int): Total connection errors
                - last_event_time (datetime): Most recent event timestamp
                - connected_time (datetime): When connection established
                - user_connected (bool): User hub connection status
                - market_connected (bool): Market hub connection status
                - subscribed_contracts (int): Number of market subscriptions

        Example:
            >>> stats = client.get_stats()
            >>> print(f"Events received: {stats['events_received']}")
            >>> print(f"Uptime: {datetime.now() - stats['connected_time']}")
            >>> if stats["connection_errors"] > 10:
            ...     print("Warning: High error count")
            >>> # Monitor event flow
            >>> last_event = stats["last_event_time"]
            >>> if last_event and (datetime.now() - last_event).seconds > 60:
            ...     print("Warning: No events for 60 seconds")

        Use Cases:
            - Connection health monitoring
            - Debugging event flow issues
            - Uptime tracking
            - Error rate monitoring
        """
        return {
            **self.stats,
            "user_connected": self.user_connected,
            "market_connected": self.market_connected,
            "subscribed_contracts": len(self._subscribed_contracts),
        }
