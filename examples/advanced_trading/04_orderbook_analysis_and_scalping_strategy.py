#!/usr/bin/env python
"""
Advanced order book analysis and scalping strategy
"""

import asyncio
from collections import deque
from decimal import Decimal

from project_x_py import EventType, TradingSuite


class OrderBookScalpingStrategy:
    def __init__(self, suite: TradingSuite):
        self.suite = suite
        self.orderbook = None
        self.tick_history = deque(maxlen=100)
        self.imbalance_threshold = 0.70  # 70% imbalance threshold
        self.min_size_edge = 50  # Minimum size difference for edge
        self.active_orders = []
        self.scalp_profit_ticks = 2  # Target 2 ticks profit

    async def initialize_orderbook(self):
        """Initialize order book for analysis."""
        try:
            # Access orderbook if available
            if hasattr(self.suite, "orderbook") and self.suite.orderbook:
                self.orderbook = self.suite.orderbook
                print("Order book initialized successfully")
                return True
            else:
                print(
                    "Order book not available - create suite with 'orderbook' feature"
                )
                return False
        except Exception as e:
            print(f"Failed to initialize order book: {e}")
            return False

    async def analyze_order_book_imbalance(self):
        """Analyze order book for size imbalances."""
        if not self.orderbook:
            return None

        try:
            # Get current bid/ask levels
            book_data = await self.orderbook.get_book_snapshot()

            if not book_data or "bids" not in book_data or "asks" not in book_data:
                return None

            bids = book_data["bids"][:5]  # Top 5 levels
            asks = book_data["asks"][:5]

            # Calculate size at each level
            total_bid_size = sum(level["size"] for level in bids)
            total_ask_size = sum(level["size"] for level in asks)

            if total_bid_size + total_ask_size == 0:
                return None

            # Calculate imbalance ratio
            bid_ratio = total_bid_size / (total_bid_size + total_ask_size)
            ask_ratio = total_ask_size / (total_bid_size + total_ask_size)

            # Determine imbalance direction
            if bid_ratio >= self.imbalance_threshold:
                return {
                    "direction": "bullish",
                    "strength": bid_ratio,
                    "bid_size": total_bid_size,
                    "ask_size": total_ask_size,
                    "spread": asks[0]["price"] - bids[0]["price"]
                    if bids and asks
                    else 0,
                }
            elif ask_ratio >= self.imbalance_threshold:
                return {
                    "direction": "bearish",
                    "strength": ask_ratio,
                    "bid_size": total_bid_size,
                    "ask_size": total_ask_size,
                    "spread": asks[0]["price"] - bids[0]["price"]
                    if bids and asks
                    else 0,
                }

            return None

        except Exception as e:
            print(f"Error analyzing order book: {e}")
            return None

    async def analyze_tape_reading(self):
        """Analyze recent trades for momentum."""
        if len(self.tick_history) < 10:
            return None

        recent_ticks = list(self.tick_history)[-10:]

        # Analyze trade aggressiveness
        buy_volume = sum(
            tick["size"] for tick in recent_ticks if tick.get("aggressor") == "buy"
        )
        sell_volume = sum(
            tick["size"] for tick in recent_ticks if tick.get("aggressor") == "sell"
        )

        total_volume = buy_volume + sell_volume
        if total_volume == 0:
            return None

        buy_ratio = buy_volume / total_volume

        # Strong buying/selling pressure
        if buy_ratio >= 0.70:
            return {
                "direction": "bullish",
                "strength": buy_ratio,
                "volume": total_volume,
            }
        elif buy_ratio <= 0.30:
            return {
                "direction": "bearish",
                "strength": 1 - buy_ratio,
                "volume": total_volume,
            }

        return None

    async def place_scalp_order(self, direction: str, analysis_data: dict):
        """Place a scalping order with tight stops."""
        try:
            current_price = await self.suite.data.get_current_price()
            tick_size = 0.25  # MNQ tick size

            if direction == "long":
                entry_price = float(current_price)
                stop_loss = entry_price - (tick_size * 3)  # 3 tick stop
                take_profit = entry_price + (tick_size * self.scalp_profit_ticks)
                side = 0
            else:
                entry_price = float(current_price)
                stop_loss = entry_price + (tick_size * 3)  # 3 tick stop
                take_profit = entry_price - (tick_size * self.scalp_profit_ticks)
                side = 1

            print(f"\nScalp Setup ({direction.upper()}):")
            print(f"  Entry: ${entry_price:.2f}")
            print(
                f"  Stop: ${stop_loss:.2f} ({abs(entry_price - stop_loss) / tick_size:.0f} ticks)"
            )
            print(
                f"  Target: ${take_profit:.2f} ({abs(take_profit - entry_price) / tick_size:.0f} ticks)"
            )
            print(f"  Analysis: {analysis_data}")

            # Quick confirmation for scalping
            response = input(f"Execute {direction.upper()} scalp? (y/N): ")
            if not response.lower().startswith("y"):
                return None

            # Place bracket order with tight parameters
            result = await self.suite.orders.place_bracket_order(
                contract_id=self.suite.instrument_info.id,
                side=side,
                size=1,  # Small size for scalping
                stop_offset=Decimal(str(abs(entry_price - stop_loss))),
                target_offset=Decimal(str(abs(take_profit - entry_price))),
            )

            scalp_record = {
                "direction": direction,
                "entry_price": entry_price,
                "bracket": result,
                "analysis": analysis_data,
                "timestamp": asyncio.get_event_loop().time(),
            }

            self.active_orders.append(scalp_record)
            print(f"Scalp order placed: {result.main_order_id}")
            return result

        except Exception as e:
            print(f"Failed to place scalp order: {e}")
            return None

    async def monitor_scalps(self):
        """Monitor active scalping positions."""
        for scalp in self.active_orders[:]:
            try:
                # Check if orders are still active
                main_status = await self.suite.orders.get_order_status(
                    scalp["bracket"].main_order_id
                )

                if main_status.status in ["Filled", "Cancelled", "Rejected"]:
                    print(
                        f"Scalp completed: {scalp['direction']} - {main_status.status}"
                    )
                    self.active_orders.remove(scalp)

                # Time-based cancellation (scalps should be quick)
                elif (
                    asyncio.get_event_loop().time() - scalp["timestamp"]
                ) > 300:  # 5 minutes
                    print(
                        f"Cancelling stale scalp order: {scalp['bracket'].main_order_id}"
                    )
                    await self.suite.orders.cancel_order(scalp["bracket"].main_order_id)
                    self.active_orders.remove(scalp)

            except Exception as e:
                print(f"Error monitoring scalp: {e}")


async def main():
    # Create suite with order book feature
    suite = await TradingSuite.create(
        ["MNQ"],
        timeframes=["15sec", "1min"],
        features=["orderbook"],  # Essential for order book analysis
        initial_days=1,
    )
    mnq_context = suite["MNQ"]

    strategy = OrderBookScalpingStrategy(suite)

    # Initialize order book
    if not await strategy.initialize_orderbook():
        print("Cannot proceed without order book data")
        return

    # Event handlers
    async def on_tick(event):
        tick_data = event.data

        # Store tick for analysis
        strategy.tick_history.append(
            {
                "price": tick_data.get("price", 0),
                "size": tick_data.get("size", 0),
                "aggressor": tick_data.get("aggressor", "unknown"),
                "timestamp": asyncio.get_event_loop().time(),
            }
        )

        # Analyze every 10th tick to avoid over-trading
        if len(strategy.tick_history) % 10 == 0:
            # Check for order book imbalances
            ob_analysis = await strategy.analyze_order_book_imbalance()
            tape_analysis = await strategy.analyze_tape_reading()

            # Look for confluence between order book and tape
            if ob_analysis and tape_analysis:
                if (
                    ob_analysis["direction"] == tape_analysis["direction"]
                    and len(strategy.active_orders) == 0
                ):  # No active scalps
                    print("\nScalping signal detected:")
                    print(
                        f"  Order Book: {ob_analysis['direction']} ({ob_analysis['strength']:.2f})"
                    )
                    print(
                        f"  Tape: {tape_analysis['direction']} ({tape_analysis['strength']:.2f})"
                    )

                    await strategy.place_scalp_order(
                        ob_analysis["direction"],
                        {"orderbook": ob_analysis, "tape": tape_analysis},
                    )

    async def on_order_filled(event):
        order_data = event.data
        print(
            f"SCALP FILL: {order_data.get('order_id')} at ${order_data.get('fill_price', 0):.2f}"
        )

    # Register events
    await mnq_context.on(EventType.QUOTE_UPDATE, on_tick)
    await mnq_context.on(EventType.ORDER_FILLED, on_order_filled)

    print("Order Book Scalping Strategy Active")
    print("Analyzing market microstructure for scalping opportunities...")
    print("Press Ctrl+C to exit")

    try:
        while True:
            await asyncio.sleep(5)

            # Monitor active scalps
            await strategy.monitor_scalps()

            # Display status
            current_price = await mnq_context.data.get_current_price()
            active_scalps = len(strategy.active_orders)
            recent_ticks = len(strategy.tick_history)

            print(
                f"Price: ${current_price:.2f} | Active Scalps: {active_scalps} | Ticks: {recent_ticks}"
            )

    except KeyboardInterrupt:
        print("\nShutting down scalping strategy...")

        # Cancel any active orders
        for scalp in strategy.active_orders:
            try:
                await mnq_context.orders.cancel_order(scalp["bracket"].main_order_id)
                print(f"Cancelled scalp order: {scalp['bracket'].main_order_id}")
            except Exception as e:
                print(f"Error cancelling order: {e}")


if __name__ == "__main__":
    asyncio.run(main())
