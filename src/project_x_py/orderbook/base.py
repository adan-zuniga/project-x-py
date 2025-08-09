"""
Base async orderbook functionality for ProjectX.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Defines the core data structures and foundational async methods for the ProjectX
    orderbook system. Implements thread-safe storage, trade history, best price/spread
    tracking, and callback/event infrastructure for all higher-level analytics.

Key Features:
    - Thread-safe Polars DataFrame bid/ask storage
    - Recent trade history, spread, and tick size tracking
    - Price level refreshment for iceberg/cluster analysis
    - Async callback/event registration for orderbook events
    - Configurable memory management and cleanup
    - Real-time data validation and error handling
    - Comprehensive orderbook snapshot generation
    - Trade flow classification and statistics

Core Data Structures:
    - orderbook_bids/asks: Polars DataFrames for price level storage
    - recent_trades: Trade execution history with classification
    - price_level_history: Historical price level updates for analysis
    - best_bid/ask_history: Top-of-book price tracking
    - spread_history: Bid-ask spread monitoring
    - trade_flow_stats: Aggressive/passive trade classification

Example Usage:
    ```python
    # V3: Using OrderBookBase with EventBus
    from project_x_py.events import EventBus, EventType

    event_bus = EventBus()
    base = OrderBookBase("MNQ", event_bus)  # V3: EventBus required


    # V3: Register event handlers via EventBus
    @event_bus.on(EventType.TRADE_TICK)
    async def on_trade(data):
        print(
            f"Trade: {data['size']} @ {data['price']} ({data['side']})"
        )  # V3: actual field names


    @event_bus.on(EventType.MARKET_DEPTH_UPDATE)
    async def on_depth(data):
        print(f"Depth update: {len(data['bids'])} bids, {len(data['asks'])} asks")


    # Get orderbook snapshot
    snapshot = await base.get_orderbook_snapshot(levels=5)
    print(f"Best bid: {snapshot['best_bid']}, Best ask: {snapshot['best_ask']}")
    print(f"Spread: {snapshot['spread']}, Imbalance: {snapshot['imbalance']:.2%}")
    ```

See Also:
    - `orderbook.analytics.MarketAnalytics`
    - `orderbook.detection.OrderDetection`
    - `orderbook.memory.MemoryManager`
"""

import asyncio
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import polars as pl
import pytz

if TYPE_CHECKING:
    from project_x_py.client import ProjectXBase

from project_x_py.exceptions import ProjectXError
from project_x_py.orderbook.memory import MemoryManager
from project_x_py.types import (
    DEFAULT_TIMEZONE,
    CallbackType,
    DomType,
    MemoryConfig,
)
from project_x_py.types.config_types import OrderbookConfig
from project_x_py.types.market_data import (
    OrderbookSnapshot,
    PriceLevelDict,
)
from project_x_py.utils import (
    LogMessages,
    ProjectXLogger,
    handle_errors,
)

logger = ProjectXLogger.get_logger(__name__)


class OrderBookBase:
    """
    Base class for async orderbook with core functionality.

    This class implements the fundamental orderbook infrastructure including data
    structures for storing bid/ask levels, trade history, and related market data.
    It provides thread-safe operations through asyncio locks and establishes the
    foundation for the component-based architecture of the complete orderbook.

    Key responsibilities:
    1. Maintain bid and ask price level data in Polars DataFrames
    2. Track and store recent trades with side classification
    3. Calculate and monitor best bid/ask prices and spreads
    4. Provide thread-safe data access through locks
    5. Implement the callback registration system
    6. Support price level history tracking for advanced analytics
    7. Manage trade flow statistics and classification
    8. Handle real-time data validation and error recovery

    This base class is designed to be extended by the full OrderBook implementation,
    which adds specialized components for analytics, detection algorithms, and real-time
    data handling.

    Thread safety:
        All public methods acquire the appropriate locks before accessing shared data
        structures, making them safe to call from multiple asyncio tasks concurrently.

    Data Structures:
        - orderbook_bids/asks: Polars DataFrames storing price levels with volumes
        - recent_trades: Trade execution history with side classification
        - price_level_history: Historical updates for iceberg/cluster analysis
        - best_bid/ask_history: Top-of-book price tracking over time
        - spread_history: Bid-ask spread monitoring and statistics
        - trade_flow_stats: Aggressive/passive trade classification metrics

    Performance Characteristics:
        - Memory-efficient Polars DataFrame operations
        - Thread-safe concurrent access patterns
        - Real-time data processing capabilities
        - Automatic memory management integration
    """

    def __init__(
        self,
        instrument: str,
        event_bus: Any,
        project_x: "ProjectXBase | None" = None,
        timezone_str: str = DEFAULT_TIMEZONE,
        config: OrderbookConfig | None = None,
    ):
        """
        Initialize the async orderbook base.

        Args:
            instrument: Trading instrument symbol
            project_x: Optional ProjectX client for tick size lookup
            timezone_str: Timezone for timestamps (default: America/Chicago)
            config: Optional configuration for orderbook behavior
        """
        self.instrument = instrument
        self.project_x = project_x
        self.event_bus = event_bus  # Store the event bus for emitting events
        self.timezone = pytz.timezone(timezone_str)
        self.logger = ProjectXLogger.get_logger(__name__)

        # Store configuration with defaults
        self.config = config or {}
        self._apply_config_defaults()

        # Cache instrument tick size during initialization
        self._tick_size: Decimal | None = None

        # Async locks for thread-safe operations
        self.orderbook_lock = asyncio.Lock()
        self._callback_lock = asyncio.Lock()

        # Memory configuration (now uses config settings)
        self.memory_config = MemoryConfig(
            max_trades=self.max_trade_history,
            max_depth_entries=self.max_depth_levels,
        )
        self.memory_manager = MemoryManager(self, self.memory_config)

        # Level 2 orderbook storage with Polars DataFrames
        self.orderbook_bids = pl.DataFrame(
            {
                "price": [],
                "volume": [],
                "timestamp": [],
            },
            schema={
                "price": pl.Float64,
                "volume": pl.Int64,
                "timestamp": pl.Datetime(time_zone=timezone_str),
            },
        )

        self.orderbook_asks = pl.DataFrame(
            {
                "price": [],
                "volume": [],
                "timestamp": [],
            },
            schema={
                "price": pl.Float64,
                "volume": pl.Int64,
                "timestamp": pl.Datetime(time_zone=timezone_str),
            },
        )

        # Trade flow storage (Type 5 - actual executions)
        self.recent_trades = pl.DataFrame(
            {
                "price": [],
                "volume": [],
                "timestamp": [],
                "side": [],  # "buy" or "sell" inferred from price movement
                "spread_at_trade": [],
                "mid_price_at_trade": [],
                "best_bid_at_trade": [],
                "best_ask_at_trade": [],
                "order_type": [],
            },
            schema={
                "price": pl.Float64,
                "volume": pl.Int64,
                "timestamp": pl.Datetime(time_zone=timezone_str),
                "side": pl.Utf8,
                "spread_at_trade": pl.Float64,
                "mid_price_at_trade": pl.Float64,
                "best_bid_at_trade": pl.Float64,
                "best_ask_at_trade": pl.Float64,
                "order_type": pl.Utf8,
            },
        )

        # Orderbook metadata
        self.last_orderbook_update: datetime | None = None
        self.last_level2_data: dict[str, Any] | None = None
        self.level2_update_count = 0

        # Order type statistics
        self.order_type_stats: dict[str, int] = defaultdict(int)

        # Callbacks for orderbook events
        # EventBus is now used for all event handling

        # Price level refresh history for advanced analytics
        self.price_level_history: dict[tuple[float, str], list[dict[str, Any]]] = (
            defaultdict(list)
        )

        # Best bid/ask tracking
        self.best_bid_history: list[dict[str, Any]] = []
        self.best_ask_history: list[dict[str, Any]] = []
        self.spread_history: list[dict[str, Any]] = []

        # Support/resistance level tracking
        self.support_levels: list[dict[str, Any]] = []
        self.resistance_levels: list[dict[str, Any]] = []

        # Cumulative delta tracking
        self.cumulative_delta = 0
        # Use deque for automatic size management of delta history
        from collections import deque

        self.delta_history: deque[dict[str, Any]] = deque(maxlen=1000)

        # VWAP tracking
        self.vwap_numerator = 0.0
        self.vwap_denominator = 0
        self.session_start_time = datetime.now(self.timezone).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Market microstructure analytics
        self.trade_flow_stats: dict[str, int] = defaultdict(int)

    def _apply_config_defaults(self) -> None:
        """Apply default values for configuration options."""
        # Orderbook settings
        self.max_depth_levels = self.config.get("max_depth_levels", 100)
        self.max_trade_history = self.config.get("max_trade_history", 1000)
        self.enable_market_by_order = self.config.get("enable_market_by_order", False)
        self.enable_analytics = self.config.get("enable_analytics", True)
        self.enable_pattern_detection = self.config.get(
            "enable_pattern_detection", True
        )
        self.snapshot_interval_seconds = self.config.get("snapshot_interval_seconds", 1)
        self.memory_limit_mb = self.config.get("memory_limit_mb", 256)
        self.compression_level = self.config.get("compression_level", 1)
        self.enable_delta_updates = self.config.get("enable_delta_updates", True)
        self.price_precision = self.config.get("price_precision", 4)

    def _map_trade_type(self, type_code: int) -> str:
        """Map ProjectX DomType codes to human-readable trade types."""
        try:
            return DomType(type_code).name
        except ValueError:
            return f"Unknown_{type_code}"

    @handle_errors("get tick size", reraise=False, default_return=Decimal("0.01"))
    async def get_tick_size(self) -> Decimal:
        """Get the tick size for the instrument."""
        if self._tick_size is None and self.project_x:
            contract_details = await self.project_x.get_instrument(self.instrument)
            if contract_details and hasattr(contract_details, "tickSize"):
                self._tick_size = Decimal(str(contract_details.tickSize))
            else:
                self._tick_size = Decimal("0.01")  # Default fallback
        return self._tick_size or Decimal("0.01")

    def _get_best_bid_ask_unlocked(self) -> dict[str, Any]:
        """
        Internal method to get best bid/ask without acquiring lock.
        Must be called with orderbook_lock already held.
        """
        try:
            best_bid = None
            best_ask = None

            # Get best bid (highest price) - optimized with chaining
            if self.orderbook_bids.height > 0:
                bid_with_volume = (
                    self.orderbook_bids.filter(pl.col("volume") > 0)
                    .sort("price", descending=True)
                    .head(1)
                )
                if bid_with_volume.height > 0:
                    best_bid = float(bid_with_volume["price"][0])

            # Get best ask (lowest price) - optimized with chaining
            if self.orderbook_asks.height > 0:
                ask_with_volume = (
                    self.orderbook_asks.filter(pl.col("volume") > 0)
                    .sort("price", descending=False)
                    .head(1)
                )
                if ask_with_volume.height > 0:
                    best_ask = float(ask_with_volume["price"][0])

            # Calculate spread
            spread = None
            if best_bid is not None and best_ask is not None:
                spread = best_ask - best_bid

            # Update history
            current_time = datetime.now(self.timezone)
            if best_bid is not None:
                self.best_bid_history.append(
                    {
                        "price": best_bid,
                        "timestamp": current_time,
                    }
                )

            if best_ask is not None:
                self.best_ask_history.append(
                    {
                        "price": best_ask,
                        "timestamp": current_time,
                    }
                )

            if spread is not None:
                self.spread_history.append(
                    {
                        "spread": spread,
                        "timestamp": current_time,
                    }
                )

            return {
                "bid": best_bid,
                "ask": best_ask,
                "spread": spread,
                "timestamp": current_time,
            }

        except Exception as e:
            self.logger.error(
                LogMessages.DATA_ERROR,
                extra={"operation": "get_best_bid_ask", "error": str(e)},
            )
            return {"bid": None, "ask": None, "spread": None, "timestamp": None}

    @handle_errors(
        "get best bid/ask",
        reraise=False,
        default_return={"bid": None, "ask": None, "spread": None, "timestamp": None},
    )
    async def get_best_bid_ask(self) -> dict[str, Any]:
        """
        Get current best bid and ask prices with spread calculation.

        This method provides the current top-of-book information, including the best
        (highest) bid price, best (lowest) ask price, the calculated spread between
        them, and the timestamp of the calculation. It also updates internal history
        tracking for bid, ask, and spread values.

        The method is thread-safe and acquires the orderbook lock before accessing
        the underlying data structures.

        Returns:
            Dict containing:
                bid: The highest bid price (float or None if no bids)
                ask: The lowest ask price (float or None if no asks)
                spread: The difference between ask and bid (float or None if either missing)
                timestamp: The time of calculation (datetime)

        Example:
            >>> # V3: Get best bid/ask with spread
            >>> prices = await orderbook.get_best_bid_ask()
            >>> if prices["bid"] is not None and prices["ask"] is not None:
            ...     print(
            ...         f"Bid: {prices['bid']:.2f}, Ask: {prices['ask']:.2f}, "
            ...         f"Spread: {prices['spread']:.2f} ticks"
            ...     )
            ...     # V3: Calculate mid price
            ...     mid = (prices["bid"] + prices["ask"]) / 2
            ...     print(f"Mid price: {mid:.2f}")
            ... else:
            ...     print("Incomplete market data")
        """
        async with self.orderbook_lock:
            return self._get_best_bid_ask_unlocked()

    @handle_errors("get bid-ask spread", reraise=False, default_return=None)
    async def get_bid_ask_spread(self) -> float | None:
        """Get the current bid-ask spread."""
        best_prices = await self.get_best_bid_ask()
        return best_prices.get("spread")

    def _get_orderbook_bids_unlocked(self, levels: int = 10) -> pl.DataFrame:
        """Internal method to get orderbook bids without acquiring lock."""
        try:
            if self.orderbook_bids.height == 0:
                return pl.DataFrame(
                    {"price": [], "volume": [], "timestamp": []},
                    schema={
                        "price": pl.Float64,
                        "volume": pl.Int64,
                        "timestamp": pl.Datetime(time_zone=self.timezone.zone),
                    },
                )

            # Get top N bid levels by price - optimized chaining
            return (
                self.orderbook_bids.lazy()  # Use lazy evaluation for better performance
                .filter(pl.col("volume") > 0)
                .sort("price", descending=True)
                .head(levels)
                .collect()
            )
        except Exception as e:
            self.logger.error(
                LogMessages.DATA_ERROR,
                extra={"operation": "get_orderbook_bids", "error": str(e)},
            )
            return pl.DataFrame()

    @handle_errors("get orderbook bids", reraise=False, default_return=pl.DataFrame())
    async def get_orderbook_bids(self, levels: int = 10) -> pl.DataFrame:
        """Get orderbook bids up to specified levels."""
        async with self.orderbook_lock:
            return self._get_orderbook_bids_unlocked(levels)

    def _get_orderbook_asks_unlocked(self, levels: int = 10) -> pl.DataFrame:
        """Internal method to get orderbook asks without acquiring lock."""
        try:
            if self.orderbook_asks.height == 0:
                return pl.DataFrame(
                    {"price": [], "volume": [], "timestamp": []},
                    schema={
                        "price": pl.Float64,
                        "volume": pl.Int64,
                        "timestamp": pl.Datetime(time_zone=self.timezone.zone),
                    },
                )

            # Get top N ask levels by price - optimized chaining
            return (
                self.orderbook_asks.lazy()  # Use lazy evaluation for better performance
                .filter(pl.col("volume") > 0)
                .sort("price", descending=False)
                .head(levels)
                .collect()
            )
        except Exception as e:
            self.logger.error(
                LogMessages.DATA_ERROR,
                extra={"operation": "get_orderbook_asks", "error": str(e)},
            )
            return pl.DataFrame()

    @handle_errors("get orderbook asks", reraise=False, default_return=pl.DataFrame())
    async def get_orderbook_asks(self, levels: int = 10) -> pl.DataFrame:
        """Get orderbook asks up to specified levels."""
        async with self.orderbook_lock:
            return self._get_orderbook_asks_unlocked(levels)

    @handle_errors("get orderbook snapshot")
    async def get_orderbook_snapshot(self, levels: int = 10) -> OrderbookSnapshot:
        """
        Get a complete snapshot of the current orderbook state.

        This method provides a comprehensive snapshot of the current orderbook state,
        including top-of-book information, bid/ask levels, volume totals, and imbalance
        calculations. It's designed to give a complete picture of the market at a single
        point in time for analysis or display purposes.

        The snapshot includes:
        - Best bid and ask prices with spread
        - Mid-price calculation
        - Specified number of bid and ask levels with prices and volumes
        - Total volume on bid and ask sides
        - Order count on each side
        - Bid/ask imbalance ratio
        - Last update timestamp and update count

        The method is thread-safe and acquires the orderbook lock during execution.

        Args:
            levels: Number of price levels to include on each side (default: 10)

        Returns:
            Dict containing the complete orderbook snapshot with all the fields
            specified above. See OrderbookSnapshot type for details.

        Raises:
            ProjectXError: If an error occurs during snapshot generation

        Example:
            >>> # V3: Get full orderbook with 5 levels on each side
            >>> snapshot = await orderbook.get_orderbook_snapshot(levels=5)
            >>>
            >>> # V3: Print top of book with imbalance
            >>> print(
            ...     f"Best Bid: {snapshot['best_bid']:.2f} ({snapshot['total_bid_volume']} contracts)"
            ... )
            >>> print(
            ...     f"Best Ask: {snapshot['best_ask']:.2f} ({snapshot['total_ask_volume']} contracts)"
            ... )
            >>> print(
            ...     f"Spread: {snapshot['spread']:.2f}, Mid: {snapshot['mid_price']:.2f}"
            ... )
            >>> print(
            ...     f"Imbalance: {snapshot['imbalance']:.2%} ({'Bid Heavy' if snapshot['imbalance'] > 0 else 'Ask Heavy'})"
            ... )
            >>>
            >>> # V3: Display depth with cumulative volume
            >>> cumulative_bid = 0
            >>> print("\nBids:")
            >>> for bid in snapshot["bids"]:
            ...     cumulative_bid += bid["volume"]
            ...     print(
            ...         f"  {bid['price']:.2f}: {bid['volume']:5d} (cum: {cumulative_bid:6d})"
            ...     )
            >>>
            >>> cumulative_ask = 0
            >>> print("\nAsks:")
            >>> for ask in snapshot["asks"]:
            ...     cumulative_ask += ask["volume"]
            ...     print(
            ...         f"  {ask['price']:.2f}: {ask['volume']:5d} (cum: {cumulative_ask:6d})"
            ...     )
        """
        async with self.orderbook_lock:
            try:
                # Get best prices - use unlocked version since we already hold the lock
                best_prices = self._get_best_bid_ask_unlocked()

                # Get bid and ask levels - use unlocked versions
                bids = self._get_orderbook_bids_unlocked(levels)
                asks = self._get_orderbook_asks_unlocked(levels)

                # Convert to lists of PriceLevelDict
                bid_levels: list[PriceLevelDict] = (
                    [
                        {
                            "price": float(row["price"]),
                            "volume": int(row["volume"]),
                            "timestamp": row["timestamp"],
                        }
                        for row in bids.to_dicts()
                    ]
                    if not bids.is_empty()
                    else []
                )

                ask_levels: list[PriceLevelDict] = (
                    [
                        {
                            "price": float(row["price"]),
                            "volume": int(row["volume"]),
                            "timestamp": row["timestamp"],
                        }
                        for row in asks.to_dicts()
                    ]
                    if not asks.is_empty()
                    else []
                )

                # Calculate totals
                total_bid_volume = bids["volume"].sum() if not bids.is_empty() else 0
                total_ask_volume = asks["volume"].sum() if not asks.is_empty() else 0

                # Calculate imbalance
                imbalance = None
                if total_bid_volume > 0 or total_ask_volume > 0:
                    imbalance = (total_bid_volume - total_ask_volume) / (
                        total_bid_volume + total_ask_volume
                    )

                return {
                    "instrument": self.instrument,
                    "timestamp": datetime.now(self.timezone),
                    "best_bid": best_prices["bid"],
                    "best_ask": best_prices["ask"],
                    "spread": best_prices["spread"],
                    "mid_price": (
                        (best_prices["bid"] + best_prices["ask"]) / 2
                        if best_prices["bid"] and best_prices["ask"]
                        else None
                    ),
                    "bids": bid_levels,
                    "asks": ask_levels,
                    "total_bid_volume": int(total_bid_volume),
                    "total_ask_volume": int(total_ask_volume),
                    "bid_count": len(bid_levels),
                    "ask_count": len(ask_levels),
                    "imbalance": imbalance,
                }

            except Exception as e:
                self.logger.error(
                    LogMessages.DATA_ERROR,
                    extra={"operation": "get_orderbook_snapshot", "error": str(e)},
                )
                raise ProjectXError(f"Failed to get orderbook snapshot: {e}") from e

    @handle_errors("get recent trades", reraise=False, default_return=[])
    async def get_recent_trades(self, count: int = 100) -> list[dict[str, Any]]:
        """Get recent trades from the orderbook."""
        async with self.orderbook_lock:
            try:
                if self.recent_trades.height == 0:
                    return []

                # Get most recent trades
                recent = self.recent_trades.tail(count)
                return recent.to_dicts()

            except Exception as e:
                self.logger.error(
                    LogMessages.DATA_ERROR,
                    extra={"operation": "get_recent_trades", "error": str(e)},
                )
                return []

    @handle_errors("get order type statistics", reraise=False, default_return={})
    async def get_order_type_statistics(self) -> dict[str, int]:
        """Get statistics about different order types processed."""
        async with self.orderbook_lock:
            return self.order_type_stats.copy()

    @handle_errors("add callback", reraise=False)
    async def add_callback(self, event_type: str, callback: CallbackType) -> None:
        """
        Register a callback for orderbook events.

        This method allows client code to register callbacks that will be triggered when
        specific orderbook events occur. Callbacks can be either synchronous functions or
        asynchronous coroutines. When an event occurs, all registered callbacks for that
        event type will be executed with the event data.

        Supported event types:
        - "depth_update": Triggered when a price level is updated
        - "trade": Triggered when a new trade is processed
        - "best_bid_change": Triggered when the best bid price changes
        - "best_ask_change": Triggered when the best ask price changes
        - "spread_change": Triggered when the bid-ask spread changes
        - "reset": Triggered when the orderbook is reset

        Args:
            event_type: The type of event to listen for (from the list above)
            callback: A callable function or coroutine that will receive the event data.
                The callback should accept a single parameter: a dictionary containing
                the event data specific to that event type.

        Example:
            >>> # V3: DEPRECATED - Use EventBus instead
            >>> # Old callback style (deprecated):
            >>> # await orderbook.add_callback("trade", on_trade)
            >>> # V3: Modern EventBus approach
            >>> from project_x_py.events import EventBus, EventType
            >>> event_bus = EventBus()
            >>> @event_bus.on(EventType.TRADE_TICK)
            >>> async def on_trade(data):
            ...     print(
            ...         f"Trade: {data['size']} @ {data['price']} ({data['side']})"
            ...     )  # V3: actual field names
            >>> @event_bus.on(EventType.MARKET_DEPTH_UPDATE)
            >>> async def on_depth_change(data):
            ...     print(
            ...         f"New best bid: {data['bids'][0]['price'] if data['bids'] else 'None'}"
            ...     )
            >>> # V3: Events automatically flow through EventBus
        """
        async with self._callback_lock:
            logger.warning(
                "add_callback is deprecated. Use TradingSuite.on() with EventType enum instead."
            )
            logger.debug(
                LogMessages.CALLBACK_REGISTERED,
                extra={"event_type": event_type, "component": "orderbook"},
            )

    @handle_errors("remove callback", reraise=False)
    async def remove_callback(self, event_type: str, callback: CallbackType) -> None:
        """Remove a registered callback."""
        async with self._callback_lock:
            logger.warning(
                "remove_callback is deprecated. Use TradingSuite.off() with EventType enum instead."
            )
            logger.debug(
                LogMessages.CALLBACK_REMOVED,
                extra={"event_type": event_type, "component": "orderbook"},
            )

    async def _trigger_callbacks(self, event_type: str, data: dict[str, Any]) -> None:
        """
        Trigger all callbacks for a specific event type.

        This method executes all registered callbacks for a given event type,
        handling both synchronous and asynchronous callback functions. It
        ensures that callback failures don't prevent other callbacks from
        executing or affect the orderbook's operation.

        Args:
            event_type: The type of event that occurred (e.g., "trade", "depth_update")
            data: Event data to pass to the callbacks

        Note:
            Callback errors are logged but do not raise exceptions to prevent
            disrupting the orderbook's operation.
        """
        # Emit event through EventBus
        from project_x_py.event_bus import EventType

        # Map orderbook event types to EventType enum
        event_mapping = {
            "orderbook_update": EventType.ORDERBOOK_UPDATE,
            "market_depth": EventType.MARKET_DEPTH_UPDATE,
            "depth_update": EventType.MARKET_DEPTH_UPDATE,
            "quote_update": EventType.QUOTE_UPDATE,
            "trade": EventType.TRADE_TICK,
        }

        if event_type in event_mapping:
            await self.event_bus.emit(
                event_mapping[event_type], data, source="OrderBook"
            )

        # Legacy callbacks have been removed - use EventBus

    @handle_errors("cleanup", reraise=False)
    async def cleanup(self) -> None:
        """Clean up resources."""
        await self.memory_manager.stop()
        # EventBus handles all event cleanup
        logger.info(
            LogMessages.CLEANUP_COMPLETE,
            extra={"component": "OrderBook"},
        )
