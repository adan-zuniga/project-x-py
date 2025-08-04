#!/usr/bin/env python3
"""
Example 10: Unified Event System with EventBus

This example demonstrates the new unified event system in ProjectX SDK v3.0.0.
Instead of registering callbacks with individual components, all events flow
through a single EventBus accessible via the TradingSuite.

Key Features Demonstrated:
1. Single interface for all events: suite.on()
2. Type-safe event registration with EventType enum
3. Unified handling of market data, order, and position events
4. One-time event handlers with suite.once()
5. Event removal with suite.off()
6. Waiting for specific events with suite.wait_for()

Author: ProjectX SDK Team
Date: 2025-08-04
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from project_x_py import TradingSuite
from project_x_py.event_bus import EventType
from project_x_py.types.trading import OrderSide

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class UnifiedEventDemo:
    """Demonstrates the unified event system."""

    def __init__(self):
        self.suite: TradingSuite | None = None
        self.event_count = {
            "bars": 0,
            "quotes": 0,
            "trades": 0,
            "orders": 0,
            "positions": 0,
        }

    async def setup(self, instrument: str = "MNQ"):
        """Initialize the trading suite."""
        logger.info(f"Setting up TradingSuite for {instrument}")

        # Single-line initialization with all components
        self.suite = await TradingSuite.create(
            instrument,
            timeframes=["1min", "5min"],
            features=["orderbook"],
        )

        # Register all event handlers through unified interface
        await self._register_event_handlers()

        logger.info("Setup complete - all event handlers registered")

    async def _register_event_handlers(self):
        """Register handlers for various event types."""

        # Market Data Events
        await self.suite.on(EventType.NEW_BAR, self._on_new_bar)
        await self.suite.on(EventType.QUOTE_UPDATE, self._on_quote_update)
        await self.suite.on(EventType.TRADE_TICK, self._on_trade_tick)

        # Order Events
        await self.suite.on(EventType.ORDER_PLACED, self._on_order_placed)
        await self.suite.on(EventType.ORDER_FILLED, self._on_order_filled)
        await self.suite.on(EventType.ORDER_CANCELLED, self._on_order_cancelled)
        await self.suite.on(EventType.ORDER_REJECTED, self._on_order_rejected)

        # Position Events
        await self.suite.on(EventType.POSITION_OPENED, self._on_position_opened)
        await self.suite.on(EventType.POSITION_CLOSED, self._on_position_closed)
        await self.suite.on(EventType.POSITION_UPDATED, self._on_position_updated)

        # System Events
        await self.suite.on(EventType.CONNECTED, self._on_connected)
        await self.suite.on(EventType.DISCONNECTED, self._on_disconnected)
        await self.suite.on(EventType.ERROR, self._on_error)

        # OrderBook Events (if enabled)
        if self.suite.orderbook:
            await self.suite.on(EventType.ORDERBOOK_UPDATE, self._on_orderbook_update)
            await self.suite.on(EventType.MARKET_DEPTH_UPDATE, self._on_market_depth)

    # Market Data Event Handlers
    async def _on_new_bar(self, event: Any):
        """Handle new OHLCV bar events."""
        self.event_count["bars"] += 1
        data = event.data
        logger.info(
            f"📊 New {data['timeframe']} bar: "
            f"O={data['data']['open']:.2f} H={data['data']['high']:.2f} "
            f"L={data['data']['low']:.2f} C={data['data']['close']:.2f} "
            f"V={data['data']['volume']}"
        )

    async def _on_quote_update(self, event: Any):
        """Handle quote update events."""
        self.event_count["quotes"] += 1
        if self.event_count["quotes"] % 10 == 0:  # Log every 10th quote
            data = event.data
            logger.info(f"💱 Quote: Bid={data.get('bid')} Ask={data.get('ask')}")

    async def _on_trade_tick(self, event: Any):
        """Handle trade tick events."""
        self.event_count["trades"] += 1
        data = event.data
        logger.info(
            f"💹 Trade: {data.get('volume')} @ {data.get('price')} "
            f"({'BUY' if data.get('side') == 0 else 'SELL'})"
        )

    # Order Event Handlers
    async def _on_order_placed(self, event: Any):
        """Handle order placed events."""
        self.event_count["orders"] += 1
        data = event.data
        logger.info(
            f"📝 Order Placed: ID={data['order_id']} "
            f"{'BUY' if data['side'] == OrderSide.BUY else 'SELL'} "
            f"{data['size']} @ {data.get('limit_price', 'MARKET')}"
        )

    async def _on_order_filled(self, event: Any):
        """Handle order filled events."""
        data = event.data
        logger.info(
            f"✅ Order Filled: ID={data['order_id']} "
            f"@ {data['order_data'].get('averagePrice', 'N/A')}"
        )

    async def _on_order_cancelled(self, event: Any):
        """Handle order cancelled events."""
        logger.info(f"❌ Order Cancelled: ID={event.data['order_id']}")

    async def _on_order_rejected(self, event: Any):
        """Handle order rejected events."""
        logger.warning(
            f"🚫 Order Rejected: ID={event.data['order_id']} "
            f"Reason: {event.data.get('reason', 'Unknown')}"
        )

    # Position Event Handlers
    async def _on_position_opened(self, event: Any):
        """Handle position opened events."""
        self.event_count["positions"] += 1
        data = event.data
        logger.info(
            f"🟢 Position Opened: {data['contractId']} "
            f"Size={data['size']} AvgPrice={data.get('averagePrice', 'N/A')}"
        )

    async def _on_position_closed(self, event: Any):
        """Handle position closed events."""
        data = event.data
        logger.info(
            f"🔴 Position Closed: {data['contractId']} "
            f"P&L={data.get('realizedPnl', 'N/A')}"
        )

    async def _on_position_updated(self, event: Any):
        """Handle position updated events."""
        data = event.data
        logger.info(
            f"🔄 Position Updated: {data['contractId']} "
            f"Size={data['size']} UnrealizedP&L={data.get('unrealizedPnl', 'N/A')}"
        )

    # System Event Handlers
    async def _on_connected(self, event: Any):
        """Handle connection events."""
        logger.info("🔗 System Connected")

    async def _on_disconnected(self, event: Any):
        """Handle disconnection events."""
        logger.warning("🔌 System Disconnected")

    async def _on_error(self, event: Any):
        """Handle error events."""
        logger.error(f"❗ Error: {event.data}")

    # OrderBook Event Handlers
    async def _on_orderbook_update(self, event: Any):
        """Handle orderbook update events."""
        # Log periodically to avoid spam
        if hasattr(self, "_orderbook_updates"):
            self._orderbook_updates += 1
            if self._orderbook_updates % 100 == 0:
                logger.info(f"📚 Orderbook updates: {self._orderbook_updates}")
        else:
            self._orderbook_updates = 1

    async def _on_market_depth(self, event: Any):
        """Handle market depth update events."""
        data = event.data
        logger.info(
            f"📊 Market Depth: "
            f"Bids={len(data.get('bids', []))} "
            f"Asks={len(data.get('asks', []))}"
        )

    async def demonstrate_advanced_features(self):
        """Demonstrate advanced event system features."""
        logger.info("\n=== Advanced Event Features ===")

        # 1. One-time event handler
        logger.info("1. Registering one-time handler for next order fill...")

        async def one_time_fill_handler(event):
            logger.info(f"🎯 One-time handler: Order {event.data['order_id']} filled!")

        await self.suite.once(EventType.ORDER_FILLED, one_time_fill_handler)

        # 2. Wait for specific event with timeout
        logger.info("2. Waiting for next position event (10s timeout)...")
        try:
            event = await self.suite.wait_for(EventType.POSITION_OPENED, timeout=10)
            logger.info(f"✅ Position event received: {event.data}")
        except asyncio.TimeoutError:
            logger.info("⏱️ No position event within timeout")

        # 3. Remove specific handler
        logger.info("3. Removing quote update handler to reduce noise...")
        await self.suite.off(EventType.QUOTE_UPDATE, self._on_quote_update)

        # 4. Event history (if enabled)
        if self.suite.events._history_enabled:
            history = self.suite.events.get_history()
            logger.info(f"4. Event history: {len(history)} events recorded")

    async def run_demo(self, duration: int = 30):
        """Run the event system demo."""
        logger.info(
            f"\n🚀 Starting unified event system demo for {duration} seconds..."
        )

        # Let events flow for the specified duration
        await asyncio.sleep(duration)

        # Demonstrate advanced features
        await self.demonstrate_advanced_features()

        # Wait a bit more for advanced features
        await asyncio.sleep(10)

        # Print statistics
        self._print_statistics()

    def _print_statistics(self):
        """Print event statistics."""
        logger.info("\n📊 Event Statistics:")
        logger.info(f"  New Bars: {self.event_count['bars']}")
        logger.info(f"  Quote Updates: {self.event_count['quotes']}")
        logger.info(f"  Trade Ticks: {self.event_count['trades']}")
        logger.info(f"  Order Events: {self.event_count['orders']}")
        logger.info(f"  Position Events: {self.event_count['positions']}")

        total_handlers = self.suite.events.get_handler_count()
        logger.info(f"\n  Total Event Handlers: {total_handlers}")

    async def cleanup(self):
        """Clean up resources."""
        if self.suite:
            logger.info("\n🧹 Cleaning up...")
            await self.suite.disconnect()


async def main():
    """Main demo function."""
    demo = UnifiedEventDemo()

    try:
        # Setup
        await demo.setup("MNQ")

        # Run demo
        await demo.run_demo(duration=30)

    except Exception as e:
        logger.error(f"Demo error: {e}", exc_info=True)
    finally:
        # Cleanup
        await demo.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
