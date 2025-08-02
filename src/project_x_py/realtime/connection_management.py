"""Connection management functionality for real-time client."""

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

try:
    from signalrcore.hub_connection_builder import HubConnectionBuilder
except ImportError:
    HubConnectionBuilder = None

if TYPE_CHECKING:
    from project_x_py.realtime.types import ProjectXRealtimeClientProtocol


class ConnectionManagementMixin:
    """Mixin for connection management functionality."""

    def __init__(self) -> None:
        """Initialize connection management attributes."""
        super().__init__()
        self._loop: asyncio.AbstractEventLoop | None = None

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
        try:
            if HubConnectionBuilder is None:
                raise ImportError("signalrcore is required for real-time functionality")

            async with self._connection_lock:
                # Build user hub connection with JWT in headers
                self.user_connection = (
                    HubConnectionBuilder()
                    .with_url(
                        self.user_hub_url,
                        options={
                            "headers": {"Authorization": f"Bearer {self.jwt_token}"}
                        },
                    )
                    .configure_logging(
                        logging.INFO,
                        socket_trace=False,
                        handler=logging.StreamHandler(),
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

                # Build market hub connection with JWT in headers
                self.market_connection = (
                    HubConnectionBuilder()
                    .with_url(
                        self.market_hub_url,
                        options={
                            "headers": {"Authorization": f"Bearer {self.jwt_token}"}
                        },
                    )
                    .configure_logging(
                        logging.INFO,
                        socket_trace=False,
                        handler=logging.StreamHandler(),
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

                self.logger.info("✅ ProjectX Gateway connections configured")
                self.setup_complete = True

        except Exception as e:
            self.logger.error(f"❌ Failed to setup ProjectX connections: {e}")
            raise

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
        if not self.setup_complete:
            await self.setup_connections()

        # Store the event loop for cross-thread task scheduling
        self._loop = asyncio.get_event_loop()

        self.logger.info("🔌 Connecting to ProjectX Gateway...")

        try:
            async with self._connection_lock:
                # Start both connections
                if self.user_connection:
                    await self._start_connection_async(self.user_connection, "user")
                else:
                    self.logger.error("❌ User connection not available")
                    return False

                if self.market_connection:
                    await self._start_connection_async(self.market_connection, "market")
                else:
                    self.logger.error("❌ Market connection not available")
                    return False

                # Wait for connections to establish
                await asyncio.sleep(0.5)

                if self.user_connected and self.market_connected:
                    self.stats["connected_time"] = datetime.now()
                    self.logger.info("✅ ProjectX Gateway connections established")
                    return True
                else:
                    self.logger.error("❌ Failed to establish all connections")
                    return False

        except Exception as e:
            self.logger.error(f"❌ Connection error: {e}")
            self.stats["connection_errors"] += 1
            return False

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
        self.logger.info(f"✅ {name.capitalize()} hub connection started")

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
        self.logger.info("📴 Disconnecting from ProjectX Gateway...")

        async with self._connection_lock:
            if self.user_connection:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.user_connection.stop)
                self.user_connected = False

            if self.market_connection:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.market_connection.stop)
                self.market_connected = False

            self.logger.info("✅ Disconnected from ProjectX Gateway")

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
            self.logger.debug(f"SignalR completion message from {hub} hub: {error}")
            return

        # Log actual errors
        self.logger.error(f"❌ {hub.capitalize()} hub error: {error}")
        self.stats["connection_errors"] += 1

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
        self.logger.info("🔑 Updating JWT token and reconnecting...")

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

            self.logger.info("✅ Reconnected with new JWT token")
            return True
        else:
            self.logger.error("❌ Failed to reconnect with new JWT token")
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
