"""
Real-time data handling for the async orderbook.

This module handles WebSocket callbacks, real-time data processing,
and orderbook updates from the ProjectX Gateway.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

import polars as pl

if TYPE_CHECKING:
    from project_x_py.realtime import ProjectXRealtimeClient

import logging

from project_x_py.orderbook.base import OrderBookBase
from project_x_py.orderbook.types import DomType


class RealtimeHandler:
    """Handles real-time data updates for the async orderbook."""

    def __init__(self, orderbook: OrderBookBase):
        self.orderbook = orderbook
        self.logger = logging.getLogger(__name__)
        self.realtime_client: ProjectXRealtimeClient | None = None

        # Track connection state
        self.is_connected = False
        self.subscribed_contracts: set[str] = set()

    async def initialize(
        self,
        realtime_client: "ProjectXRealtimeClient",
        subscribe_to_depth: bool = True,
        subscribe_to_quotes: bool = True,
    ) -> bool:
        """
        Initialize real-time data feed connection.

        Args:
            realtime_client: real-time client instance
            subscribe_to_depth: Subscribe to market depth updates
            subscribe_to_quotes: Subscribe to quote updates

        Returns:
            bool: True if initialization successful
        """
        try:
            self.realtime_client = realtime_client

            # Setup callbacks
            await self._setup_realtime_callbacks()

            # Note: Don't subscribe here - the example already subscribes with the proper contract ID
            # The example gets the contract ID and subscribes after initialization

            self.is_connected = True

            self.logger.info(
                f"OrderBook initialized successfully for {self.orderbook.instrument}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize OrderBook: {e}")
            return False

    async def _setup_realtime_callbacks(self) -> None:
        """Setup callbacks for real-time data processing."""
        if not self.realtime_client:
            return

        # Market depth callback for Level 2 data
        await self.realtime_client.add_callback(
            "market_depth", self._on_market_depth_update
        )

        # Quote callback for best bid/ask tracking
        await self.realtime_client.add_callback("quote_update", self._on_quote_update)

    async def _on_market_depth_update(self, data: dict[str, Any]) -> None:
        """Callback for market depth updates (Level 2 data)."""
        try:
            self.logger.debug(f"Market depth callback received: {list(data.keys())}")
            # The data comes structured as {"contract_id": ..., "data": ...}
            contract_id = data.get("contract_id", "")
            if isinstance(data.get("data"), list) and len(data.get("data", [])) > 0:
                self.logger.debug(f"First data entry: {data['data'][0]}")
            if not self._is_relevant_contract(contract_id):
                return

            # Process the market depth data
            await self._process_market_depth(data)

            # Trigger any registered callbacks
            await self.orderbook._trigger_callbacks(
                "market_depth_processed",
                {
                    "contract_id": contract_id,
                    "update_count": self.orderbook.level2_update_count,
                    "timestamp": datetime.now(self.orderbook.timezone),
                },
            )

        except Exception as e:
            self.logger.error(f"Error processing market depth update: {e}")

    async def _on_quote_update(self, data: dict[str, Any]) -> None:
        """Callback for quote updates."""
        try:
            # The data comes structured as {"contract_id": ..., "data": ...}
            contract_id = data.get("contract_id", "")
            if not self._is_relevant_contract(contract_id):
                return

            # Extract quote data
            quote_data = data.get("data", {})

            # Trigger quote update callbacks
            await self.orderbook._trigger_callbacks(
                "quote_update",
                {
                    "contract_id": contract_id,
                    "bid": quote_data.get("bid"),
                    "ask": quote_data.get("ask"),
                    "bid_size": quote_data.get("bidSize"),
                    "ask_size": quote_data.get("askSize"),
                    "timestamp": datetime.now(self.orderbook.timezone),
                },
            )

        except Exception as e:
            self.logger.error(f"Error processing quote update: {e}")

    def _is_relevant_contract(self, contract_id: str) -> bool:
        """Check if the contract ID is relevant to this orderbook."""
        if contract_id == self.orderbook.instrument:
            return True

        # Handle case where instrument might be a symbol and contract_id is full ID
        clean_contract = contract_id.replace("CON.F.US.", "").split(".")[0]
        clean_instrument = self.orderbook.instrument.replace("CON.F.US.", "").split(
            "."
        )[0]

        is_match = clean_contract.startswith(clean_instrument)
        if not is_match:
            self.logger.debug(
                f"Contract mismatch: received '{contract_id}' (clean: '{clean_contract}'), "
                f"expected '{self.orderbook.instrument}' (clean: '{clean_instrument}')"
            )
        return is_match

    async def _process_market_depth(self, data: dict[str, Any]) -> None:
        """Process market depth update from ProjectX Gateway."""
        market_data = data.get("data", [])
        if not market_data:
            return

        self.logger.debug(f"Processing market depth data: {len(market_data)} entries")
        if len(market_data) > 0:
            self.logger.debug(f"Sample entry: {market_data[0]}")

        # Update statistics
        self.orderbook.level2_update_count += 1

        # Process each market depth entry
        async with self.orderbook.orderbook_lock:
            current_time = datetime.now(self.orderbook.timezone)

            # Get best prices before processing updates - use unlocked version since we're already in the lock
            pre_update_best = self.orderbook._get_best_bid_ask_unlocked()
            pre_update_bid = pre_update_best.get("bid")
            pre_update_ask = pre_update_best.get("ask")

            for entry in market_data:
                await self._process_single_depth_entry(
                    entry, current_time, pre_update_bid, pre_update_ask
                )

            self.orderbook.last_orderbook_update = current_time
            self.orderbook.last_level2_data = data

            # Update memory stats
            self.orderbook.memory_manager.memory_stats["total_trades"] = (
                self.orderbook.recent_trades.height
            )

    async def _process_single_depth_entry(
        self,
        entry: dict[str, Any],
        current_time: datetime,
        pre_update_bid: float | None,
        pre_update_ask: float | None,
    ) -> None:
        """Process a single depth entry from market data."""
        try:
            trade_type = entry.get("type", 0)
            price = float(entry.get("price", 0))
            volume = int(entry.get("volume", 0))

            # Map type and update statistics
            type_name = self.orderbook._map_trade_type(trade_type)
            self.orderbook.order_type_stats[f"type_{trade_type}_count"] += 1

            # Handle different trade types
            if trade_type == DomType.TRADE:
                # Process actual trade execution
                await self._process_trade(
                    price,
                    volume,
                    current_time,
                    pre_update_bid,
                    pre_update_ask,
                    type_name,
                )
            elif trade_type == DomType.BID:
                # Update bid side
                await self._update_orderbook_level(
                    price, volume, current_time, is_bid=True
                )
            elif trade_type == DomType.ASK:
                # Update ask side
                await self._update_orderbook_level(
                    price, volume, current_time, is_bid=False
                )
            elif trade_type in (DomType.BEST_BID, DomType.NEW_BEST_BID):
                # New best bid
                await self._update_orderbook_level(
                    price, volume, current_time, is_bid=True
                )
            elif trade_type in (DomType.BEST_ASK, DomType.NEW_BEST_ASK):
                # New best ask
                await self._update_orderbook_level(
                    price, volume, current_time, is_bid=False
                )
            elif trade_type == DomType.RESET:
                # Reset orderbook
                await self._reset_orderbook()

        except Exception as e:
            self.logger.error(f"Error processing depth entry: {e}")

    async def _process_trade(
        self,
        price: float,
        volume: int,
        timestamp: datetime,
        pre_bid: float | None,
        pre_ask: float | None,
        order_type: str,
    ) -> None:
        """Process a trade execution."""
        # Determine trade side based on price relative to spread
        side = "unknown"
        if pre_bid is not None and pre_ask is not None:
            _mid_price = (pre_bid + pre_ask) / 2
            if price >= pre_ask:
                side = "buy"
                self.orderbook.trade_flow_stats["aggressive_buy_volume"] += volume
            elif price <= pre_bid:
                side = "sell"
                self.orderbook.trade_flow_stats["aggressive_sell_volume"] += volume
            else:
                # Trade inside spread - likely market maker
                side = "neutral"
                self.orderbook.trade_flow_stats["market_maker_trades"] += 1

        # Calculate spread at trade time
        spread_at_trade = None
        mid_price_at_trade = None
        if pre_bid is not None and pre_ask is not None:
            spread_at_trade = pre_ask - pre_bid
            mid_price_at_trade = (pre_bid + pre_ask) / 2

        # Update cumulative delta
        if side == "buy":
            self.orderbook.cumulative_delta += volume
        elif side == "sell":
            self.orderbook.cumulative_delta -= volume

        # Store delta history
        self.orderbook.delta_history.append(
            {
                "timestamp": timestamp,
                "delta": self.orderbook.cumulative_delta,
                "volume": volume,
                "side": side,
            }
        )

        # Update VWAP
        self.orderbook.vwap_numerator += price * volume
        self.orderbook.vwap_denominator += volume

        # Create trade record
        new_trade = pl.DataFrame(
            {
                "price": [price],
                "volume": [volume],
                "timestamp": [timestamp],
                "side": [side],
                "spread_at_trade": [spread_at_trade],
                "mid_price_at_trade": [mid_price_at_trade],
                "best_bid_at_trade": [pre_bid],
                "best_ask_at_trade": [pre_ask],
                "order_type": [order_type],
            }
        )

        # Append to recent trades
        self.orderbook.recent_trades = pl.concat(
            [self.orderbook.recent_trades, new_trade],
            how="vertical",
        )

        # Trigger trade callback
        await self.orderbook._trigger_callbacks(
            "trade_processed",
            {
                "trade_data": {
                    "price": price,
                    "volume": volume,
                    "timestamp": timestamp,
                    "side": side,
                    "order_type": order_type,
                },
                "cumulative_delta": self.orderbook.cumulative_delta,
            },
        )

    async def _update_orderbook_level(
        self, price: float, volume: int, timestamp: datetime, is_bid: bool
    ) -> None:
        """Update a single orderbook level."""
        # Select the appropriate DataFrame
        orderbook_df = (
            self.orderbook.orderbook_bids if is_bid else self.orderbook.orderbook_asks
        )
        side = "bid" if is_bid else "ask"

        # Update price level history for analytics
        history_key = (price, side)
        self.orderbook.price_level_history[history_key].append(
            {
                "volume": volume,
                "timestamp": timestamp,
                "change_type": "update",
            }
        )

        # Check if price level exists
        existing = orderbook_df.filter(pl.col("price") == price)

        if existing.height > 0:
            if volume == 0:
                # Remove the level
                orderbook_df = orderbook_df.filter(pl.col("price") != price)
            else:
                # Update the level
                orderbook_df = orderbook_df.with_columns(
                    pl.when(pl.col("price") == price)
                    .then(pl.lit(volume))
                    .otherwise(pl.col("volume"))
                    .alias("volume"),
                    pl.when(pl.col("price") == price)
                    .then(pl.lit(timestamp))
                    .otherwise(pl.col("timestamp"))
                    .alias("timestamp"),
                )
        else:
            if volume > 0:
                # Add new level
                new_level = pl.DataFrame(
                    {
                        "price": [price],
                        "volume": [volume],
                        "timestamp": [timestamp],
                    }
                )
                orderbook_df = pl.concat([orderbook_df, new_level], how="vertical")

        # Update the appropriate DataFrame
        if is_bid:
            self.orderbook.orderbook_bids = orderbook_df
        else:
            self.orderbook.orderbook_asks = orderbook_df

    async def _reset_orderbook(self) -> None:
        """Reset the orderbook state."""
        self.orderbook.orderbook_bids = pl.DataFrame(
            {"price": [], "volume": [], "timestamp": []},
            schema={
                "price": pl.Float64,
                "volume": pl.Int64,
                "timestamp": pl.Datetime(time_zone=self.orderbook.timezone.zone),
            },
        )
        self.orderbook.orderbook_asks = pl.DataFrame(
            {"price": [], "volume": [], "timestamp": []},
            schema={
                "price": pl.Float64,
                "volume": pl.Int64,
                "timestamp": pl.Datetime(time_zone=self.orderbook.timezone.zone),
            },
        )
        self.logger.info("Orderbook reset due to RESET event")

    async def disconnect(self) -> None:
        """Disconnect from real-time data feed."""
        if self.realtime_client and self.subscribed_contracts:
            try:
                # Unsubscribe from market data
                await self.realtime_client.unsubscribe_market_data(
                    list(self.subscribed_contracts)
                )

                # Remove callbacks
                await self.realtime_client.remove_callback(
                    "market_depth", self._on_market_depth_update
                )
                await self.realtime_client.remove_callback(
                    "quote_update", self._on_quote_update
                )

                self.subscribed_contracts.clear()
                self.is_connected = False

            except Exception as e:
                self.logger.error(f"Error during disconnect: {e}")
