"""
ProjectX Realtime Client for ProjectX Gateway API

This module provides a Python client for the ProjectX real-time API, which provides
access to the ProjectX trading platform real-time events via SignalR WebSocket connections.

Author: TexasCoding
Date: June 2025
"""

import logging
import time
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING

from signalrcore.hub_connection_builder import HubConnectionBuilder

from .utils import RateLimiter

if TYPE_CHECKING:
    from .models import ProjectXConfig


class ProjectXRealtimeClient:
    """
    Simplified real-time client for ProjectX Gateway API WebSocket connections.

    This class provides a clean interface for ProjectX SignalR connections and
    forwards all events to registered managers. It does NOT cache data or perform
    business logic - that's handled by the specialized managers.

    Features:
        - Clean SignalR WebSocket connections to ProjectX Gateway hubs
        - Event forwarding to registered managers (no duplicate processing)
        - Automatic reconnection with exponential backoff
        - JWT token refresh and reconnection
        - Connection health monitoring
        - Simplified event callbacks (no caching/parsing)

    Architecture:
        - Pure event forwarding (no business logic)
        - No data caching (handled by managers)
        - No payload parsing (managers handle ProjectX formats)
        - Minimal stateful operations

    Real-time Hubs (per ProjectX Gateway docs):
        - User Hub: Account, position, and order updates
        - Market Hub: Quote, trade, and market depth data

    Example:
        >>> # Create client with ProjectX Gateway URLs
        >>> client = ProjectXRealtimeClient(jwt_token, account_id)
        >>> # Register managers for event handling
        >>> client.add_callback("position_update", position_manager.handle_update)
        >>> client.add_callback("order_update", order_manager.handle_update)
        >>> client.add_callback("quote_update", data_manager.handle_quote)
        >>>
        >>> # Connect and subscribe
        >>> if client.connect():
        ...     client.subscribe_user_updates()
        ...     client.subscribe_market_data(["CON.F.US.MGC.M25"])

    Event Types (per ProjectX Gateway docs):
        User Hub: GatewayUserAccount, GatewayUserPosition, GatewayUserOrder, GatewayUserTrade
        Market Hub: GatewayQuote, GatewayDepth, GatewayTrade

    Integration:
        - PositionManager handles position events and caching
        - OrderManager handles order events and tracking
        - RealtimeDataManager handles market data and caching
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
        Initialize ProjectX real-time client with configurable SignalR connections.

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
        self.callbacks: defaultdict[str, list] = defaultdict(list)

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

        self.logger.info("ProjectX real-time client initialized")
        self.logger.info(f"User Hub: {final_user_url}")
        self.logger.info(f"Market Hub: {final_market_url}")

        self.rate_limiter = RateLimiter(requests_per_minute=60)

    def setup_connections(self):
        """Set up SignalR hub connections with ProjectX Gateway configuration."""
        try:
            if HubConnectionBuilder is None:
                raise ImportError("signalrcore is required for real-time functionality")

            # Build user hub connection
            self.user_connection = (
                HubConnectionBuilder()
                .with_url(self.user_hub_url)
                .configure_logging(
                    logging.INFO, socket_trace=False, handler=logging.StreamHandler()
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
                    logging.INFO, socket_trace=False, handler=logging.StreamHandler()
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
            self.user_connection.on("GatewayUserAccount", self._forward_account_update)
            self.user_connection.on(
                "GatewayUserPosition", self._forward_position_update
            )
            self.user_connection.on("GatewayUserOrder", self._forward_order_update)
            self.user_connection.on("GatewayUserTrade", self._forward_trade_execution)

            # Market Hub Events
            self.market_connection.on("GatewayQuote", self._forward_quote_update)
            self.market_connection.on("GatewayTrade", self._forward_market_trade)
            self.market_connection.on("GatewayDepth", self._forward_market_depth)

            self.logger.info("✅ ProjectX Gateway connections configured")
            self.setup_complete = True

        except Exception as e:
            self.logger.error(f"❌ Failed to setup ProjectX connections: {e}")
            raise

    def connect(self) -> bool:
        """Connect to ProjectX Gateway SignalR hubs."""
        if not self.setup_complete:
            self.setup_connections()

        self.logger.info("🔌 Connecting to ProjectX Gateway...")

        try:
            # Start both connections
            if self.user_connection:
                self.user_connection.start()
            else:
                self.logger.error("❌ User connection not available")
                return False

            if self.market_connection:
                self.market_connection.start()
            else:
                self.logger.error("❌ Market connection not available")
                return False

            # Wait for connections with timeout
            max_wait = 20
            start_time = time.time()

            while (not self.user_connected or not self.market_connected) and (
                time.time() - start_time
            ) < max_wait:
                time.sleep(0.5)

            if self.user_connected and self.market_connected:
                self.stats["connected_time"] = datetime.now()
                self.logger.info("✅ Connected to ProjectX Gateway")
                return True
            else:
                self.logger.error("❌ Failed to connect within timeout")
                self.disconnect()
                return False

        except Exception as e:
            self.logger.error(f"❌ Connection failed: {e}")
            self.disconnect()
            return False

    def disconnect(self):
        """Disconnect from ProjectX Gateway hubs."""
        self.logger.info("🔌 Disconnecting from ProjectX Gateway...")

        try:
            if self.user_connection:
                self.user_connection.stop()
            if self.market_connection:
                self.market_connection.stop()

            self.user_connected = False
            self.market_connected = False
            self.logger.info("✅ Disconnected from ProjectX Gateway")

        except Exception as e:
            self.logger.error(f"❌ Disconnection error: {e}")

    # Connection event handlers
    def _on_user_hub_open(self):
        """Handle user hub connection opening."""
        self.user_connected = True
        self.logger.info("✅ User hub connected")
        self._trigger_callbacks(
            "connection_status", {"hub": "user", "status": "connected"}
        )

    def _on_user_hub_close(self):
        """Handle user hub connection closing."""
        self.user_connected = False
        self.logger.warning("❌ User hub disconnected")
        self._trigger_callbacks(
            "connection_status", {"hub": "user", "status": "disconnected"}
        )

    def _on_market_hub_open(self):
        """Handle market hub connection opening."""
        self.market_connected = True
        self.logger.info("✅ Market hub connected")
        self._trigger_callbacks(
            "connection_status", {"hub": "market", "status": "connected"}
        )

    def _on_market_hub_close(self):
        """Handle market hub connection closing."""
        self.market_connected = False
        self.logger.warning("❌ Market hub disconnected")
        self._trigger_callbacks(
            "connection_status", {"hub": "market", "status": "disconnected"}
        )

    def _on_connection_error(self, hub_type: str, data):
        """Handle connection errors."""
        self.stats["connection_errors"] += 1
        self.logger.error(f"🚨 {hub_type.title()} hub error: {data}")

        if "unauthorized" in str(data).lower() or "401" in str(data):
            self.logger.warning("⚠️ Authentication error - token may be expired")

        self._trigger_callbacks(
            "connection_status", {"hub": hub_type, "status": "error", "data": data}
        )

    # Pure event forwarding handlers (no caching or business logic)
    def _forward_account_update(self, *args):
        """Forward ProjectX GatewayUserAccount events to managers."""
        try:
            self._update_stats()
            # User events typically have single data payload
            data = args[0] if args else {}
            self.logger.debug("📨 Account update forwarded")
            self._trigger_callbacks("account_update", data)
        except Exception as e:
            self.logger.error(f"Error in _forward_account_update: {e}")
            self.logger.debug(f"Args received: {args}")

    def _forward_position_update(self, *args):
        """Forward ProjectX GatewayUserPosition events to managers."""
        try:
            self._update_stats()
            # User events typically have single data payload
            data = args[0] if args else {}
            self.logger.debug("📨 Position update forwarded")
            self._trigger_callbacks("position_update", data)
        except Exception as e:
            self.logger.error(f"Error in _forward_position_update: {e}")
            self.logger.debug(f"Args received: {args}")

    def _forward_order_update(self, *args):
        """Forward ProjectX GatewayUserOrder events to managers."""
        try:
            self._update_stats()
            # User events typically have single data payload
            data = args[0] if args else {}
            self.logger.debug("📨 Order update forwarded")
            self._trigger_callbacks("order_update", data)
        except Exception as e:
            self.logger.error(f"Error in _forward_order_update: {e}")
            self.logger.debug(f"Args received: {args}")

    def _forward_trade_execution(self, *args):
        """Forward ProjectX GatewayUserTrade events to managers."""
        try:
            self._update_stats()
            # User events typically have single data payload
            data = args[0] if args else {}
            self.logger.debug("📨 Trade execution forwarded")
            self._trigger_callbacks("trade_execution", data)
        except Exception as e:
            self.logger.error(f"Error in _forward_trade_execution: {e}")
            self.logger.debug(f"Args received: {args}")

    def _forward_quote_update(self, *args):
        """Forward ProjectX GatewayQuote events to managers."""
        try:
            self._update_stats()

            # Handle different SignalR callback signatures
            if len(args) == 1:
                # Single argument - the data payload
                raw_data = args[0]
                if isinstance(raw_data, list) and len(raw_data) >= 2:
                    # SignalR format: [contract_id, actual_data_dict]
                    contract_id = raw_data[0]
                    data = raw_data[1]
                elif isinstance(raw_data, dict):
                    contract_id = raw_data.get("symbol", "unknown")
                    data = raw_data
                else:
                    contract_id = "unknown"
                    data = raw_data
            elif len(args) == 2:
                # Two arguments - contract_id and data
                contract_id, data = args
            else:
                self.logger.warning(
                    f"Unexpected _forward_quote_update args: {len(args)} - {args}"
                )
                return

            self.logger.debug(f"📨 Quote update forwarded: {contract_id}")
            self._trigger_callbacks(
                "quote_update", {"contract_id": contract_id, "data": data}
            )
        except Exception as e:
            self.logger.error(f"Error in _forward_quote_update: {e}")
            self.logger.debug(f"Args received: {args}")

    def _forward_market_trade(self, *args):
        """Forward ProjectX GatewayTrade events to managers."""
        try:
            self._update_stats()

            # Handle different SignalR callback signatures
            if len(args) == 1:
                # Single argument - the data payload
                raw_data = args[0]
                if isinstance(raw_data, list) and len(raw_data) >= 2:
                    # SignalR format: [contract_id, actual_data_dict]
                    contract_id = raw_data[0]
                    data = raw_data[1]
                elif isinstance(raw_data, dict):
                    contract_id = raw_data.get("symbolId", "unknown")
                    data = raw_data
                else:
                    contract_id = "unknown"
                    data = raw_data
            elif len(args) == 2:
                # Two arguments - contract_id and data
                contract_id, data = args
            else:
                self.logger.warning(
                    f"Unexpected _forward_market_trade args: {len(args)} - {args}"
                )
                return

            self.logger.debug(f"📨 Market trade forwarded: {contract_id}")
            self._trigger_callbacks(
                "market_trade", {"contract_id": contract_id, "data": data}
            )
        except Exception as e:
            self.logger.error(f"Error in _forward_market_trade: {e}")
            self.logger.debug(f"Args received: {args}")

    def _forward_market_depth(self, *args):
        """Forward ProjectX GatewayDepth events to managers."""
        try:
            self._update_stats()

            # Handle different SignalR callback signatures
            if len(args) == 1:
                # Single argument - the data payload
                raw_data = args[0]
                if isinstance(raw_data, list) and len(raw_data) >= 2:
                    # SignalR format: [contract_id, actual_data_dict]
                    contract_id = raw_data[0]
                    data = raw_data[1]
                elif isinstance(raw_data, dict):
                    contract_id = raw_data.get("contractId", "unknown")
                    data = raw_data
                else:
                    contract_id = "unknown"
                    data = raw_data
            elif len(args) == 2:
                # Two arguments - contract_id and data
                contract_id, data = args
            else:
                self.logger.warning(
                    f"Unexpected _forward_market_depth args: {len(args)} - {args}"
                )
                return

            self.logger.debug(f"📨 Market depth forwarded: {contract_id}")
            self._trigger_callbacks(
                "market_depth", {"contract_id": contract_id, "data": data}
            )
        except Exception as e:
            self.logger.error(f"Error in _forward_market_depth: {e}")
            self.logger.debug(f"Args received: {args}")

    def _update_stats(self):
        """Update basic statistics."""
        self.stats["events_received"] += 1
        self.stats["last_event_time"] = datetime.now()

    # Subscription methods (per ProjectX Gateway documentation)
    def subscribe_user_updates(self) -> bool:
        """Subscribe to user-specific updates per ProjectX Gateway API."""
        if not self.user_connected or not self.user_connection:
            self.logger.error("❌ Cannot subscribe: User hub not connected")
            return False

        try:
            self.logger.info(
                f"📡 Subscribing to user updates for account {self.account_id}"
            )

            with self.rate_limiter:
                self.user_connection.send("SubscribeAccounts", [])
            with self.rate_limiter:
                self.user_connection.send("SubscribePositions", [int(self.account_id)])
            with self.rate_limiter:
                self.user_connection.send("SubscribeOrders", [int(self.account_id)])
            with self.rate_limiter:
                self.user_connection.send("SubscribeTrades", [int(self.account_id)])

            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to subscribe to user updates: {e}")
            return False

    def subscribe_market_data(self, contract_ids: list[str]) -> bool:
        """Subscribe to market data per ProjectX Gateway API."""
        if not self.market_connected or not self.market_connection:
            self.logger.error("❌ Cannot subscribe: Market hub not connected")
            return False

        try:
            self.logger.info(f"📡 Subscribing to market data: {contract_ids}")

            # Track for reconnection
            self._subscribed_contracts = contract_ids.copy()

            # Subscribe using ProjectX Gateway methods
            for contract_id in contract_ids:
                with self.rate_limiter:
                    self.market_connection.send(
                        "SubscribeContractQuotes", [contract_id]
                    )
                with self.rate_limiter:
                    self.market_connection.send(
                        "SubscribeContractTrades", [contract_id]
                    )
                with self.rate_limiter:
                    self.market_connection.send(
                        "SubscribeContractMarketDepth", [contract_id]
                    )

            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to subscribe to market data: {e}")
            return False

    # Callback management
    def add_callback(self, event_type: str, callback: Callable):
        """Add callback for specific event types."""
        self.callbacks[event_type].append(callback)
        self.logger.debug(f"Callback added for {event_type}")

    def remove_callback(self, event_type: str, callback: Callable):
        """Remove callback for specific event types."""
        if callback in self.callbacks[event_type]:
            self.callbacks[event_type].remove(callback)
            self.logger.debug(f"Callback removed for {event_type}")

    def _trigger_callbacks(self, event_type: str, data):
        """Trigger all callbacks for an event type."""
        for callback in self.callbacks[event_type]:
            try:
                callback(data)
            except Exception as e:
                self.logger.error(f"Error in {event_type} callback: {e}")

    # Utility methods
    def is_connected(self) -> bool:
        """Check if both hubs are connected."""
        return self.user_connected and self.market_connected

    def get_connection_status(self) -> dict:
        """Get connection status and statistics."""
        return {
            "user_connected": self.user_connected,
            "market_connected": self.market_connected,
            "setup_complete": self.setup_complete,
            "subscribed_contracts": self._subscribed_contracts.copy(),
            "statistics": self.stats.copy(),
            "callbacks_registered": {
                event: len(callbacks) for event, callbacks in self.callbacks.items()
            },
        }

    def refresh_token_and_reconnect(self, project_x_client) -> bool:
        """Refresh JWT token and reconnect using configured endpoints."""
        try:
            self.logger.info("🔄 Refreshing JWT token and reconnecting...")

            # Disconnect
            self.disconnect()

            # Get fresh token
            new_token = project_x_client.get_session_token()
            if not new_token:
                raise Exception("Failed to get fresh JWT token")

            # Update URLs with fresh token using stored base URLs
            self.jwt_token = new_token
            self.user_hub_url = f"{self.base_user_url}?access_token={new_token}"
            self.market_hub_url = f"{self.base_market_url}?access_token={new_token}"

            # Reset and reconnect
            self.setup_complete = False
            success = self.connect()

            if success:
                self.logger.info("✅ Token refreshed and reconnected")
                # Re-subscribe to market data
                if self._subscribed_contracts:
                    self.subscribe_market_data(self._subscribed_contracts)
                return True
            else:
                self.logger.error("❌ Failed to reconnect after token refresh")
                return False

        except Exception as e:
            self.logger.error(f"❌ Error refreshing token: {e}")
            return False

    def cleanup(self):
        """Clean up resources and connections."""
        self.disconnect()
        self.callbacks.clear()
        self._subscribed_contracts.clear()
        self.logger.info("✅ ProjectX real-time client cleanup completed")
