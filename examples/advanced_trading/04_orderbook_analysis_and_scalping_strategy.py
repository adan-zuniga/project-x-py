#!/usr/bin/env python
"""
Advanced order book analysis and scalping strategy.

This example demonstrates:
- Level 2 order book analysis and imbalance detection
- Tape reading for momentum confirmation
- Market microstructure analysis for scalping
- Iceberg order detection
- Volume profile analysis
- Tight risk management for scalping
"""

import asyncio
from collections import deque
from typing import Any, Optional

from project_x_py import EventType, TradingSuite
from project_x_py.event_bus import Event
from project_x_py.models import BracketOrderResponse


class OrderBookScalpingStrategy:
    """Scalping strategy based on order book analysis."""

    def __init__(self, suite: TradingSuite):
        self.suite = suite
        self.orderbook = None
        self.tick_history = deque(maxlen=100)
        self.imbalance_threshold = 0.70  # 70% imbalance threshold
        self.min_size_edge = 50  # Minimum size difference for edge
        self.active_orders: list[dict[str, Any]] = []
        self.scalp_profit_ticks = 2  # Target 2 ticks profit
        self.max_positions = 2  # Max concurrent scalps

    async def initialize_orderbook(self) -> bool:
        """Initialize order book for analysis."""
        try:
            # Access orderbook through InstrumentContext
            mnq_context = self.suite["MNQ"]
            if hasattr(mnq_context, "orderbook") and mnq_context.orderbook:
                self.orderbook = mnq_context.orderbook
                print("✅ Order book initialized successfully")
                return True
            else:
                print(
                    "❌ Order book not available - ensure suite was created with 'orderbook' feature"
                )
                return False
        except Exception as e:
            print(f"Failed to initialize order book: {e}")
            return False

    async def analyze_order_book_imbalance(self) -> Optional[dict]:
        """Analyze order book for size imbalances."""
        if not self.orderbook:
            return None

        try:
            # Get market imbalance using the correct method
            imbalance_data = await self.orderbook.get_market_imbalance(levels=5)

            if imbalance_data:
                # LiquidityAnalysisResponse is a TypedDict, access with brackets
                if "imbalance_ratio" in imbalance_data:
                    ratio = float(imbalance_data["imbalance_ratio"])

                    if abs(ratio) >= self.imbalance_threshold:
                        return {
                            "direction": "bullish" if ratio > 0 else "bearish",
                            "strength": abs(ratio),
                            "bid_liquidity": imbalance_data.get("bid_liquidity", 0),
                            "ask_liquidity": imbalance_data.get("ask_liquidity", 0),
                            "spread": imbalance_data.get("spread", 0),
                            "levels": 5,
                        }

            # Fallback to orderbook snapshot
            snapshot = await self.orderbook.get_orderbook_snapshot(levels=5)

            if snapshot:
                # OrderbookSnapshot is a TypedDict, access with brackets
                bids = snapshot.get("bids", [])
                asks = snapshot.get("asks", [])

                # Calculate imbalance from snapshot
                bid_sizes = sum(level.get("size", 0) for level in bids) if bids else 0
                ask_sizes = sum(level.get("size", 0) for level in asks) if asks else 0

                if bid_sizes + ask_sizes > 0:
                    bid_ratio = bid_sizes / (bid_sizes + ask_sizes)

                    if bid_ratio >= self.imbalance_threshold:
                        return {
                            "direction": "bullish",
                            "strength": bid_ratio,
                            "bid_size": bid_sizes,
                            "ask_size": ask_sizes,
                            "spread": float(snapshot.get("spread") or 0),
                            "levels": 5,
                        }
                    elif bid_ratio <= (1 - self.imbalance_threshold):
                        return {
                            "direction": "bearish",
                            "strength": 1 - bid_ratio,
                            "bid_size": bid_sizes,
                            "ask_size": ask_sizes,
                            "spread": float(snapshot.get("spread") or 0),
                            "levels": 5,
                        }

            return None

        except Exception as e:
            print(f"Error analyzing order book: {e}")
            return None

    async def check_for_iceberg_orders(self) -> Optional[dict]:
        """Detect potential iceberg orders in the book."""
        if not self.orderbook:
            return None

        try:
            # Use orderbook's iceberg detection with correct parameters
            iceberg_info = await self.orderbook.detect_iceberg_orders(
                min_refreshes=3, volume_threshold=100, time_window_minutes=5
            )

            if iceberg_info and iceberg_info.get("detected"):
                detections = iceberg_info.get("detections", [])
                if detections:
                    # Get the most confident detection
                    best_detection = max(
                        detections, key=lambda x: x.get("confidence", 0)
                    )
                    return {
                        "detected": True,
                        "side": best_detection.get("side", "unknown"),
                        "price_level": best_detection.get("price", 0),
                        "confidence": best_detection.get("confidence", 0),
                        "refill_count": best_detection.get("refill_count", 0),
                    }

            return None

        except Exception as e:
            print(f"Error detecting iceberg orders: {e}")
            return None

    async def analyze_volume_profile(self) -> Optional[dict]:
        """Analyze volume profile for key levels."""
        if not self.orderbook:
            return None

        try:
            # Get volume profile with correct parameters
            profile = await self.orderbook.get_volume_profile(
                time_window_minutes=60, price_bins=10
            )

            if profile:
                # Check if profile has the expected structure
                poc = profile.get("poc")
                value_area = profile.get("value_area")

                if poc:
                    return {
                        "poc": float(poc.get("price", 0)),
                        "poc_volume": poc.get("volume", 0),
                        "value_area_high": float(value_area.get("high", 0))
                        if value_area
                        else 0,
                        "value_area_low": float(value_area.get("low", 0))
                        if value_area
                        else 0,
                        "total_volume": profile.get("total_volume", 0),
                    }

            # If no profile data, return None
            return None

        except Exception as e:
            print(f"Error analyzing volume profile: {e}")
            return None

    async def analyze_tape_reading(self) -> Optional[dict]:
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
                "buy_volume": buy_volume,
                "sell_volume": sell_volume,
            }
        elif buy_ratio <= 0.30:
            return {
                "direction": "bearish",
                "strength": 1 - buy_ratio,
                "volume": total_volume,
                "buy_volume": buy_volume,
                "sell_volume": sell_volume,
            }

        return None

    async def place_scalp_order(
        self, direction: str, analysis_data: dict
    ) -> Optional[BracketOrderResponse]:
        """Place a scalping order with tight stops."""
        try:
            mnq_context = self.suite["MNQ"]

            # Get current price
            current_price = await mnq_context.data.get_current_price()
            if not current_price:
                print("Could not get current price")
                return None

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

            # Display scalp setup
            print("\n" + "=" * 60)
            print(f"SCALP SETUP ({direction.upper()})")
            print("=" * 60)
            print(f"Entry: ${entry_price:.2f}")
            print(
                f"Stop: ${stop_loss:.2f} ({abs(entry_price - stop_loss) / tick_size:.0f} ticks)"
            )
            print(
                f"Target: ${take_profit:.2f} ({abs(take_profit - entry_price) / tick_size:.0f} ticks)"
            )

            # Display analysis details
            if "orderbook" in analysis_data:
                ob = analysis_data["orderbook"]
                print("\nOrder Book Analysis:")
                print(f"  Imbalance: {ob['strength']:.2%} {ob['direction']}")
                if "bid_size" in ob:
                    print(f"  Bid Size: {ob['bid_size']}, Ask Size: {ob['ask_size']}")
                elif "bid_liquidity" in ob:
                    print(
                        f"  Bid Liquidity: {ob['bid_liquidity']}, Ask Liquidity: {ob['ask_liquidity']}"
                    )
                print(f"  Spread: ${ob['spread']:.2f}")

            if "tape" in analysis_data:
                tape = analysis_data["tape"]
                print("\nTape Reading:")
                print(f"  Momentum: {tape['strength']:.2%} {tape['direction']}")
                print(f"  Volume: Buy={tape['buy_volume']}, Sell={tape['sell_volume']}")

            if "iceberg" in analysis_data and analysis_data["iceberg"]:
                ice = analysis_data["iceberg"]
                print(
                    f"\n⚠️  Iceberg Detected: {ice['side']} @ ${ice['price_level']:.2f}"
                )

            print("=" * 60)

            # Quick confirmation for scalping
            response = input(f"\nExecute {direction.upper()} scalp? (y/N): ")
            if not response.lower().startswith("y"):
                return None

            # Get instrument contract ID
            instrument = mnq_context.instrument_info
            contract_id = instrument.id if hasattr(instrument, "id") else "MNQ"

            print("\nPlacing scalp order...")

            # Place bracket order with tight parameters
            # Prices will be automatically aligned to tick size
            result = await mnq_context.orders.place_bracket_order(
                contract_id=contract_id,
                side=side,
                size=1,  # Small size for scalping
                entry_price=None,  # Market order for quick fills
                entry_type="market",
                stop_loss_price=stop_loss,
                take_profit_price=take_profit,
            )

            if result and result.success:
                scalp_record = {
                    "direction": direction,
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "bracket": result,
                    "analysis": analysis_data,
                    "timestamp": asyncio.get_event_loop().time(),
                }

                self.active_orders.append(scalp_record)

                print("✅ Scalp order placed successfully!")
                print(f"  Entry Order: {result.entry_order_id}")
                print(f"  Stop Order: {result.stop_order_id}")
                print(f"  Target Order: {result.target_order_id}")

                return result
            else:
                error_msg = result.error_message if result else "Unknown error"
                print(f"❌ Failed to place scalp order: {error_msg}")
                return None

        except Exception as e:
            print(f"Failed to place scalp order: {e}")
            import traceback

            traceback.print_exc()
            return None

    async def monitor_scalps(self):
        """Monitor active scalping positions."""
        mnq_context = self.suite["MNQ"]

        for scalp in self.active_orders[:]:
            try:
                elapsed_time = asyncio.get_event_loop().time() - scalp["timestamp"]

                # Time-based cancellation (scalps should be quick)
                if elapsed_time > 300:  # 5 minutes
                    print("\nCancelling stale scalp order (>5 min old)")

                    # Cancel stop and target orders
                    bracket: BracketOrderResponse = scalp["bracket"]
                    if bracket.stop_order_id:
                        await mnq_context.orders.cancel_order(bracket.stop_order_id)
                    if bracket.target_order_id:
                        await mnq_context.orders.cancel_order(bracket.target_order_id)

                    self.active_orders.remove(scalp)

            except Exception as e:
                print(f"Error monitoring scalp: {e}")


async def main():
    """Main function to run the scalping strategy."""
    print("Initializing Order Book Scalping Strategy...")

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
        await suite.disconnect()
        return

    # Track tick count for analysis frequency
    tick_count = 0

    # Event handlers
    async def on_tick(event: Event):
        """Handle tick updates."""
        nonlocal tick_count
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

        tick_count += 1

        # Analyze every 10th tick to avoid over-trading
        if (
            tick_count % 10 == 0
            and len(strategy.active_orders) < strategy.max_positions
        ):
            # Check for order book imbalances
            ob_analysis = await strategy.analyze_order_book_imbalance()
            tape_analysis = await strategy.analyze_tape_reading()
            iceberg_check = await strategy.check_for_iceberg_orders()

            # Look for confluence between order book and tape
            if ob_analysis and tape_analysis:
                if ob_analysis["direction"] == tape_analysis["direction"]:
                    print("\n🎯 Scalping signal detected!")
                    print(
                        f"  Order Book: {ob_analysis['direction']} "
                        f"({ob_analysis['strength']:.2%})"
                    )
                    print(
                        f"  Tape: {tape_analysis['direction']} "
                        f"({tape_analysis['strength']:.2%})"
                    )

                    if iceberg_check:
                        print(
                            f"  ⚠️  Iceberg: {iceberg_check['side']} "
                            f"@ ${iceberg_check['price_level']:.2f}"
                        )

                    await strategy.place_scalp_order(
                        ob_analysis["direction"],
                        {
                            "orderbook": ob_analysis,
                            "tape": tape_analysis,
                            "iceberg": iceberg_check,
                        },
                    )

    async def on_order_filled(event: Event):
        """Handle order fill events."""
        order_data = event.data
        print(
            f"\n✅ SCALP FILL: Order {order_data.get('order_id')} "
            f"filled at ${order_data.get('fill_price', 0):.2f}"
        )

        # Update active orders
        for scalp in strategy.active_orders[:]:
            bracket: BracketOrderResponse = scalp["bracket"]
            if bracket.entry_order_id == order_data.get("order_id"):
                print(f"  Entry filled for {scalp['direction']} scalp")
                break

    async def on_orderbook_update(_event: Event):
        """Handle order book updates."""
        # Could use this for more real-time analysis

    # Register events
    await mnq_context.on(EventType.QUOTE_UPDATE, on_tick)
    await mnq_context.on(EventType.ORDER_FILLED, on_order_filled)
    await mnq_context.on(EventType.ORDERBOOK_UPDATE, on_orderbook_update)

    print("\n" + "=" * 60)
    print("ORDER BOOK SCALPING STRATEGY ACTIVE")
    print("=" * 60)
    print("Strategy Settings:")
    print(f"  Imbalance Threshold: {strategy.imbalance_threshold:.0%}")
    print(f"  Profit Target: {strategy.scalp_profit_ticks} ticks")
    print("  Stop Loss: 3 ticks")
    print(f"  Max Positions: {strategy.max_positions}")
    print("\nAnalyzing market microstructure for scalping opportunities...")
    print("Press Ctrl+C to exit")
    print("=" * 60)

    try:
        while True:
            await asyncio.sleep(10)  # Status update every 10 seconds

            # Monitor active scalps
            await strategy.monitor_scalps()

            # Display status
            current_price = await mnq_context.data.get_current_price()
            if current_price:
                active_scalps = len(strategy.active_orders)
                recent_ticks = len(strategy.tick_history)

                # Get volume profile if available
                volume_profile = await strategy.analyze_volume_profile()

                print("\nStatus Update:")
                print(f"  Price: ${current_price:.2f}")
                print(f"  Active Scalps: {active_scalps}/{strategy.max_positions}")
                print(f"  Tick Buffer: {recent_ticks}/100")

                if volume_profile:
                    print(f"  POC: ${volume_profile['poc']:.2f}")
                    print(
                        f"  Value Area: ${volume_profile['value_area_low']:.2f} - "
                        f"${volume_profile['value_area_high']:.2f}"
                    )

    except KeyboardInterrupt:
        print("\n\nShutting down scalping strategy...")

        # Cancel any active orders
        for scalp in strategy.active_orders:
            try:
                bracket: BracketOrderResponse = scalp["bracket"]
                if bracket.stop_order_id:
                    await mnq_context.orders.cancel_order(bracket.stop_order_id)
                    print(f"Cancelled stop order {bracket.stop_order_id}")
                if bracket.target_order_id:
                    await mnq_context.orders.cancel_order(bracket.target_order_id)
                    print(f"Cancelled target order {bracket.target_order_id}")
            except Exception as e:
                print(f"Error cancelling order: {e}")

    finally:
        # Disconnect from real-time feeds
        await suite.disconnect()
        print("Strategy disconnected. Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
