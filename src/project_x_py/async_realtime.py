"""
Async ProjectX Realtime Client for ProjectX Gateway API

This module provides an async Python client for the ProjectX real-time API, which provides
access to the ProjectX trading platform real-time events via SignalR WebSocket connections.

Key Features:
- Full async/await support for all operations
- Asyncio-based connection management
- Non-blocking event processing
- Async callbacks for all events
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import TYPE_CHECKING, Any

try:
    from signalrcore.hub_connection_builder import HubConnectionBuilder
except ImportError:
    HubConnectionBuilder = None

from .utils import RateLimiter

if TYPE_CHECKING:
    from .models import ProjectXConfig


class AsyncProjectXRealtimeClient:
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

    Architecture:
        - Pure event forwarding (no business logic)
        - No data caching (handled by managers)
        - No payload parsing (managers handle ProjectX formats)
        - Minimal stateful operations

    Real-time Hubs (per ProjectX Gateway docs):
        - User Hub: Account, position, and order updates
        - Market Hub: Quote, trade, and market depth data

    Example:
        >>> # Create async client with ProjectX Gateway URLs
        >>> client = AsyncProjectXRealtimeClient(jwt_token, account_id)
        >>> # Register async managers for event handling
        >>> await client.add_callback("position_update", position_manager.handle_update)
        >>> await client.add_callback("order_update", order_manager.handle_update)
        >>> await client.add_callback("quote_update", data_manager.handle_quote)
        >>>
        >>> # Connect and subscribe
        >>> if await client.connect():
        ...     await client.subscribe_user_updates()
        ...     await client.subscribe_market_data(["CON.F.US.MGC.M25"])

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

        Args:
            jwt_token: JWT authentication token
            account_id: ProjectX account ID
            user_hub_url: Optional user hub URL (overrides config)
            market_hub_url: Optional market hub URL (overrides config)
            config: Optional ProjectXConfig with default URLs

        Note:
            If no URLs are provided, defaults to ProjectX Gateway demo endpoints.
            For TopStepX, pass TopStepX URLs or use ProjectXConfig with TopStepX URLs.
        """
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

        # Build complete URLs with authentication
        self.user_hub_url = f"{final_user_url}?access_token={jwt_token}"
        self.market_hub_url = f"{final_market_url}?access_token={jwt_token}"

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
        self.user_connection = None
        self.market_connection = None

        # Connection state tracking
        self.user_connected = False
        self.market_connected = False
        self.setup_complete = False

        # Event callbacks (pure forwarding, no caching)
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

        self.rate_limiter = RateLimiter(requests_per_minute=60)

        # Async locks for thread-safe operations
        self._callback_lock = asyncio.Lock()
        self._connection_lock = asyncio.Lock()

        # Store the event loop for cross-thread task scheduling
        self._loop = None

    async def setup_connections(self):
        """Set up SignalR hub connections with ProjectX Gateway configuration."""
        try:
            if HubConnectionBuilder is None:
                raise ImportError("signalrcore is required for real-time functionality")

            async with self._connection_lock:
                # Build user hub connection
                self.user_connection = (
                    HubConnectionBuilder()
                    .with_url(self.user_hub_url)
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

                # Build market hub connection
                self.market_connection = (
                    HubConnectionBuilder()
                    .with_url(self.market_hub_url)
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

    async def connect(self) -> bool:
        """Connect to ProjectX Gateway SignalR hubs asynchronously."""
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

    async def _start_connection_async(self, connection, name: str):
        """Start a SignalR connection asynchronously."""
        # SignalR connections are synchronous, so we run them in executor
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, connection.start)
        self.logger.info(f"✅ {name.capitalize()} hub connection started")

    async def disconnect(self):
        """Disconnect from ProjectX Gateway hubs."""
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

    async def subscribe_user_updates(self) -> bool:
        """
        Subscribe to all user-specific real-time updates.

        Subscribes to:
        - Account updates (balance, buying power, etc.)
        - Position updates (new, changed, closed positions)
        - Order updates (new, filled, cancelled orders)
        - Trade executions (fills)

        Returns:
            bool: True if subscription successful
        """
        if not self.user_connected:
            self.logger.error("❌ User hub not connected")
            return False

        try:
            self.logger.info(f"📡 Subscribing to user updates for {self.account_id}")
            if self.user_connection is None:
                self.logger.error("❌ User connection not available")
                return False
            # ProjectX Gateway expects Subscribe method with account ID
            loop = asyncio.get_event_loop()

            # Subscribe to account updates
            await loop.run_in_executor(
                None,
                self.user_connection.send,
                "SubscribeAccounts",
                [],  # Empty list for accounts subscription
            )

            # Subscribe to order updates
            await loop.run_in_executor(
                None,
                self.user_connection.send,
                "SubscribeOrders",
                [int(self.account_id)],  # List with int account ID
            )

            # Subscribe to position updates
            await loop.run_in_executor(
                None,
                self.user_connection.send,
                "SubscribePositions",
                [int(self.account_id)],  # List with int account ID
            )

            # Subscribe to trade updates
            await loop.run_in_executor(
                None,
                self.user_connection.send,
                "SubscribeTrades",
                [int(self.account_id)],  # List with int account ID
            )

            self.logger.info("✅ Subscribed to user updates")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to subscribe to user updates: {e}")
            return False

    async def subscribe_market_data(self, contract_ids: list[str]) -> bool:
        """
        Subscribe to market data for specific contracts.

        Args:
            contract_ids: List of ProjectX contract IDs (e.g., ["CON.F.US.MGC.M25"])

        Returns:
            bool: True if subscription successful
        """
        if not self.market_connected:
            self.logger.error("❌ Market hub not connected")
            return False

        try:
            self.logger.info(
                f"📊 Subscribing to market data for {len(contract_ids)} contracts"
            )

            # Store for reconnection (avoid duplicates)
            for contract_id in contract_ids:
                if contract_id not in self._subscribed_contracts:
                    self._subscribed_contracts.append(contract_id)

            # Subscribe using ProjectX Gateway methods (same as sync client)
            loop = asyncio.get_event_loop()
            for contract_id in contract_ids:
                # Subscribe to quotes
                if self.market_connection is None:
                    self.logger.error("❌ Market connection not available")
                    return False
                await loop.run_in_executor(
                    None,
                    self.market_connection.send,
                    "SubscribeContractQuotes",
                    [contract_id],
                )
                # Subscribe to trades
                await loop.run_in_executor(
                    None,
                    self.market_connection.send,
                    "SubscribeContractTrades",
                    [contract_id],
                )
                # Subscribe to market depth
                await loop.run_in_executor(
                    None,
                    self.market_connection.send,
                    "SubscribeContractMarketDepth",
                    [contract_id],
                )

            self.logger.info(f"✅ Subscribed to {len(contract_ids)} contracts")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to subscribe to market data: {e}")
            return False

    async def unsubscribe_user_updates(self) -> bool:
        """
        Unsubscribe from all user-specific real-time updates.
        """
        if not self.user_connected:
            self.logger.error("❌ User hub not connected")
            return False

        if self.user_connection is None:
            self.logger.error("❌ User connection not available")
            return False

        try:
            loop = asyncio.get_event_loop()

            # Unsubscribe from account updates
            await loop.run_in_executor(
                None,
                self.user_connection.send,
                "UnsubscribeAccounts",
                self.account_id,
            )

            # Unsubscribe from order updates

            await loop.run_in_executor(
                None,
                self.user_connection.send,
                "UnsubscribeOrders",
                [self.account_id],
            )

            # Unsubscribe from position updates

            await loop.run_in_executor(
                None,
                self.user_connection.send,
                "UnsubscribePositions",
                self.account_id,
            )

            # Unsubscribe from trade updates

            await loop.run_in_executor(
                None,
                self.user_connection.send,
                "UnsubscribeTrades",
                self.account_id,
            )

            self.logger.info("✅ Unsubscribed from user updates")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to unsubscribe from user updates: {e}")
            return False

    async def unsubscribe_market_data(self, contract_ids: list[str]) -> bool:
        """
        Unsubscribe from market data for specific contracts.

        Args:
            contract_ids: List of ProjectX contract IDs to unsubscribe

        Returns:
            bool: True if unsubscription successful
        """
        if not self.market_connected:
            self.logger.error("❌ Market hub not connected")
            return False

        try:
            self.logger.info(f"🛑 Unsubscribing from {len(contract_ids)} contracts")

            # Remove from stored contracts
            for contract_id in contract_ids:
                if contract_id in self._subscribed_contracts:
                    self._subscribed_contracts.remove(contract_id)

            # ProjectX Gateway expects Unsubscribe method
            loop = asyncio.get_event_loop()
            if self.market_connection is None:
                self.logger.error("❌ Market connection not available")
                return False

            # Unsubscribe from quotes
            await loop.run_in_executor(
                None,
                self.market_connection.send,
                "UnsubscribeContractQuotes",
                [contract_ids],
            )

            # Unsubscribe from trades
            await loop.run_in_executor(
                None,
                self.market_connection.send,
                "UnsubscribeContractTrades",
                [contract_ids],
            )

            # Unsubscribe from market depth
            await loop.run_in_executor(
                None,
                self.market_connection.send,
                "UnsubscribeContractMarketDepth",
                [contract_ids],
            )

            self.logger.info(f"✅ Unsubscribed from {len(contract_ids)} contracts")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to unsubscribe from market data: {e}")
            return False

    async def add_callback(
        self,
        event_type: str,
        callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None] | None],
    ):
        """
        Register an async callback for specific event types.

        Event types:
        - User events: account_update, position_update, order_update, trade_execution
        - Market events: quote_update, market_trade, market_depth

        Args:
            event_type: Type of event to subscribe to
            callback: Async function to call when event occurs
        """
        async with self._callback_lock:
            self.callbacks[event_type].append(callback)
            self.logger.debug(f"Registered callback for {event_type}")

    async def remove_callback(
        self,
        event_type: str,
        callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None] | None],
    ):
        """Remove a registered callback."""
        async with self._callback_lock:
            if event_type in self.callbacks and callback in self.callbacks[event_type]:
                self.callbacks[event_type].remove(callback)
                self.logger.debug(f"Removed callback for {event_type}")

    async def _trigger_callbacks(self, event_type: str, data: dict[str, Any]):
        """Trigger all callbacks for a specific event type asynchronously."""
        callbacks = self.callbacks.get(event_type, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    # Handle sync callbacks
                    callback(data)
            except Exception as e:
                self.logger.error(f"Error in {event_type} callback: {e}")

    # Connection event handlers
    def _on_user_hub_open(self):
        """Handle user hub connection open."""
        self.user_connected = True
        self.logger.info("✅ User hub connected")

    def _on_user_hub_close(self):
        """Handle user hub connection close."""
        self.user_connected = False
        self.logger.warning("❌ User hub disconnected")

    def _on_market_hub_open(self):
        """Handle market hub connection open."""
        self.market_connected = True
        self.logger.info("✅ Market hub connected")

    def _on_market_hub_close(self):
        """Handle market hub connection close."""
        self.market_connected = False
        self.logger.warning("❌ Market hub disconnected")

    def _on_connection_error(self, hub: str, error):
        """Handle connection errors."""
        self.logger.error(f"❌ {hub.capitalize()} hub error: {error}")
        self.stats["connection_errors"] += 1

    # Event forwarding methods (cross-thread safe)
    def _forward_account_update(self, *args):
        """Forward account update to registered callbacks."""
        self._schedule_async_task("account_update", args)

    def _forward_position_update(self, *args):
        """Forward position update to registered callbacks."""
        self._schedule_async_task("position_update", args)

    def _forward_order_update(self, *args):
        """Forward order update to registered callbacks."""
        self._schedule_async_task("order_update", args)

    def _forward_trade_execution(self, *args):
        """Forward trade execution to registered callbacks."""
        self._schedule_async_task("trade_execution", args)

    def _forward_quote_update(self, *args):
        """Forward quote update to registered callbacks."""
        self._schedule_async_task("quote_update", args)

    def _forward_market_trade(self, *args):
        """Forward market trade to registered callbacks."""
        self._schedule_async_task("market_trade", args)

    def _forward_market_depth(self, *args):
        """Forward market depth to registered callbacks."""
        self._schedule_async_task("market_depth", args)

    def _schedule_async_task(self, event_type: str, data):
        """Schedule async task in the main event loop from any thread."""
        if self._loop and not self._loop.is_closed():
            try:
                asyncio.run_coroutine_threadsafe(
                    self._forward_event_async(event_type, data), self._loop
                )
            except Exception as e:
                # Fallback for logging - avoid recursion
                print(f"Error scheduling async task: {e}")
        else:
            # Fallback - try to create task in current loop context
            try:
                task = asyncio.create_task(self._forward_event_async(event_type, data))
                # Fire and forget - we don't need to await the task
                task.add_done_callback(lambda t: None)
            except RuntimeError:
                # No event loop available, log and continue
                print(f"No event loop available for {event_type} event")

    async def _forward_event_async(self, event_type: str, args):
        """Forward event to registered callbacks asynchronously."""
        self.stats["events_received"] += 1
        self.stats["last_event_time"] = datetime.now()

        # Log event (debug level)
        self.logger.debug(
            f"📨 Received {event_type} event: {len(args) if hasattr(args, '__len__') else 'N/A'} items"
        )

        # Parse args and create structured data like sync version
        try:
            if event_type in ["quote_update", "market_trade", "market_depth"]:
                # Market events - parse SignalR format like sync version
                if len(args) == 1:
                    # Single argument - the data payload
                    raw_data = args[0]
                    if isinstance(raw_data, list) and len(raw_data) >= 2:
                        # SignalR format: [contract_id, actual_data_dict]
                        contract_id = raw_data[0]
                        data = raw_data[1]
                    elif isinstance(raw_data, dict):
                        contract_id = raw_data.get(
                            "symbol" if event_type == "quote_update" else "symbolId",
                            "unknown",
                        )
                        data = raw_data
                    else:
                        contract_id = "unknown"
                        data = raw_data
                elif len(args) == 2:
                    # Two arguments - contract_id and data
                    contract_id, data = args
                else:
                    self.logger.warning(
                        f"Unexpected {event_type} args: {len(args)} - {args}"
                    )
                    return

                # Create structured callback data like sync version
                callback_data = {"contract_id": contract_id, "data": data}

            else:
                # User events - single data payload like sync version
                callback_data = args[0] if args else {}

            # Trigger callbacks with structured data
            await self._trigger_callbacks(event_type, callback_data)

        except Exception as e:
            self.logger.error(f"Error processing {event_type} event: {e}")
            self.logger.debug(f"Args received: {args}")

    def is_connected(self) -> bool:
        """Check if both hubs are connected."""
        return self.user_connected and self.market_connected

    def get_stats(self) -> dict[str, Any]:
        """Get connection statistics."""
        return {
            **self.stats,
            "user_connected": self.user_connected,
            "market_connected": self.market_connected,
            "subscribed_contracts": len(self._subscribed_contracts),
        }

    async def update_jwt_token(self, new_jwt_token: str):
        """
        Update JWT token and reconnect with new credentials.

        Args:
            new_jwt_token: New JWT authentication token
        """
        self.logger.info("🔑 Updating JWT token and reconnecting...")

        # Disconnect existing connections
        await self.disconnect()

        # Update token
        self.jwt_token = new_jwt_token

        # Update URLs with new token
        self.user_hub_url = f"{self.base_user_url}?access_token={new_jwt_token}"
        self.market_hub_url = f"{self.base_market_url}?access_token={new_jwt_token}"

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

    async def cleanup(self):
        """Clean up resources when shutting down."""
        await self.disconnect()
        async with self._callback_lock:
            self.callbacks.clear()
        self.logger.info("✅ AsyncProjectXRealtimeClient cleanup completed")
