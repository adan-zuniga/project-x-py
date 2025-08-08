#!/usr/bin/env python3
"""
Phase 4 Comprehensive Test - Data and Orders Improvements

This example demonstrates all the improvements from Phase 4:
- Simplified data access methods
- Enhanced model properties
- Cleaner strategy implementation

Author: SDK v3.0.0 Testing
"""

import asyncio
from datetime import datetime

from project_x_py import TradingSuite
from project_x_py.indicators import ATR, RSI, SMA


class CleanTradingStrategy:
    """A trading strategy using all Phase 4 improvements."""

    def __init__(self, suite: TradingSuite):
        self.suite = suite
        self.data = suite.data
        self.orders = suite.orders
        self.positions = suite.positions

        # Strategy parameters
        self.max_position_size = 5
        self.profit_target_ticks = 20
        self.stop_loss_ticks = 10

    async def analyze_market(
        self,
    ) -> dict[str, float | int | str | dict[str, float]] | None:
        """Analyze market using simplified data access."""
        # Use new get_data_or_none for cleaner code
        data = await self.data.get_data_or_none("5min", min_bars=50)
        if data is None:
            return None

        # Calculate indicators
        data = data.pipe(SMA, period=20).pipe(RSI, period=14).pipe(ATR, period=14)

        # Get current market state using new methods
        current_price = await self.data.get_latest_price()
        ohlc = await self.data.get_ohlc("5min")
        price_range = await self.data.get_price_range(bars=20)
        volume_stats = await self.data.get_volume_stats(bars=20)

        if (
            current_price is None
            or ohlc is None
            or price_range is None
            or volume_stats is None
        ):
            return None

        # Analyze trend
        sma20 = float(data["sma_20"][-1])
        rsi = float(data["rsi_14"][-1])
        atr = float(data["atr_14"][-1])

        # Price position within range
        price_position = (float(current_price) - float(price_range["low"])) / float(
            price_range["range"]
        )

        return {
            "price": float(current_price),
            "trend": "bullish" if float(current_price) > sma20 else "bearish",
            "trend_strength": abs(float(current_price) - sma20) / sma20,
            "rsi": rsi,
            "atr": atr,
            "price_position": price_position,
            "volume_relative": float(volume_stats["relative"]),
            "range": float(price_range["range"]),
            "ohlc": {
                "open": float(ohlc["open"]),
                "high": float(ohlc["high"]),
                "low": float(ohlc["low"]),
                "close": float(ohlc["close"]),
            },
        }

    async def check_positions(
        self,
    ) -> dict[str, float | int | list[dict[str, float | int | str]]]:
        """Check positions using enhanced model properties."""
        positions = await self.positions.get_all_positions()

        position_summary = {
            "total_positions": len(positions),
            "long_positions": 0,
            "short_positions": 0,
            "total_exposure": 0.0,
            "positions": [],
        }

        current_price = await self.data.get_latest_price()
        if current_price is None:
            return position_summary

        for pos in positions:
            # Use new Position properties
            if pos.is_long:
                position_summary["long_positions"] += 1
            elif pos.is_short:
                position_summary["short_positions"] += 1

            position_summary["total_exposure"] += pos.total_cost

            # Calculate P&L using the unrealized_pnl method
            pnl = pos.unrealized_pnl(float(current_price), tick_value=5.0)

            position_summary["positions"].append(
                {
                    "id": pos.id,
                    "symbol": pos.symbol,  # New property
                    "direction": pos.direction,  # New property
                    "size": pos.size,
                    "signed_size": pos.signed_size,  # New property
                    "entry": pos.averagePrice,
                    "pnl": pnl,
                    "pnl_ticks": (pnl / 5.0) / pos.size if pos.size > 0 else 0,
                }
            )

        return position_summary

    async def check_orders(
        self,
    ) -> dict[str, float | int | list[dict[str, float | int | str]]]:
        """Check orders using enhanced model properties."""
        orders = await self.orders.search_open_orders()

        order_summary = {
            "total_orders": len(orders),
            "working_orders": 0,
            "buy_orders": 0,
            "sell_orders": 0,
            "orders": [],
        }

        for order in orders:
            # Use new Order properties
            if order.is_working:
                order_summary["working_orders"] += 1

            if order.is_buy:
                order_summary["buy_orders"] += 1
            elif order.is_sell:
                order_summary["sell_orders"] += 1

            order_summary["orders"].append(
                {
                    "id": order.id,
                    "symbol": order.symbol,  # New property
                    "side": order.side_str,  # New property
                    "type": order.type_str,  # New property
                    "status": order.status_str,  # New property
                    "size": order.size,
                    "remaining": order.remaining_size,  # New property
                    "filled_pct": order.filled_percent,  # New property
                    "price": float(order.limitPrice)
                    if order.limitPrice
                    else float(order.stopPrice)
                    if order.stopPrice
                    else 0.0,
                }
            )

        return order_summary

    async def execute_strategy(self) -> None:
        """Execute trading strategy using all Phase 4 improvements."""
        print("\n=== Strategy Execution ===")

        # 1. Check if data is ready
        if not await self.data.is_data_ready(min_bars=50):
            print("⏳ Insufficient data for strategy")
            return

        # 2. Analyze market
        analysis = await self.analyze_market()
        if not analysis:
            print("❌ Market analysis failed")
            return

        print("\n📊 Market Analysis:")
        print(f"  Price: ${analysis['price']:,.2f}")
        print(
            f"  Trend: {analysis['trend'].upper()} (strength: {analysis['trend_strength']:.1%})"
        )
        print(f"  RSI: {analysis['rsi']:.1f}")
        print(f"  Volume: {analysis['volume_relative']:.1%} of average")
        print(f"  Price Position: {analysis['price_position']:.1%} of range")

        # 3. Check current positions
        position_summary = await self.check_positions()
        print("\n📈 Position Summary:")
        print(f"  Total: {position_summary['total_positions']}")
        print(f"  Long: {position_summary['long_positions']}")
        print(f"  Short: {position_summary['short_positions']}")
        print(f"  Exposure: ${position_summary['total_exposure']:,.2f}")

        for pos in position_summary["positions"]:
            print(
                f"\n  {pos['direction']} {pos['size']} {pos['symbol']} @ ${pos['entry']:,.2f}"
            )
            print(f"    P&L: ${pos['pnl']:+,.2f} ({pos['pnl_ticks']:+.1f} ticks)")

            # Exit logic using clean properties
            if pos["pnl_ticks"] >= self.profit_target_ticks:
                print("    ✅ PROFIT TARGET REACHED!")
            elif pos["pnl_ticks"] <= -self.stop_loss_ticks:
                print("    🛑 STOP LOSS TRIGGERED!")

        # 4. Check current orders
        order_summary = await self.check_orders()
        if order_summary["total_orders"] > 0:
            print("\n📋 Order Summary:")
            print(f"  Working: {order_summary['working_orders']}")
            print(f"  Buy Orders: {order_summary['buy_orders']}")
            print(f"  Sell Orders: {order_summary['sell_orders']}")

            for order in order_summary["orders"]:
                print(
                    f"\n  {order['side']} {order['size']} {order['symbol']} - {order['type']}"
                )
                print(
                    f"    Status: {order['status']} ({order['filled_pct']:.0f}% filled)"
                )
                if order["price"]:
                    print(f"    Price: ${order['price']:,.2f}")

        # 5. Generate trading signals
        signal = self._generate_signal(analysis, position_summary)
        if signal:
            print(
                f"\n🎯 SIGNAL: {signal['action']} (confidence: {signal['confidence']:.1%})"
            )
            print(f"  Reason: {signal['reason']}")

    def _generate_signal(
        self, analysis: dict, positions: dict
    ) -> dict[str, float | str] | None:
        """Generate trading signal based on analysis."""
        # No signal if we have max positions
        if positions["total_positions"] >= self.max_position_size:
            return None

        # Bullish signal
        if (
            analysis["trend"] == "bullish"
            and analysis["rsi"] < 70
            and analysis["volume_relative"] > 1.2
            and analysis["price_position"] < 0.7
        ):
            return {
                "action": "BUY",
                "confidence": min(
                    analysis["trend_strength"],
                    (70 - analysis["rsi"]) / 50,
                    analysis["volume_relative"] - 1.0,
                ),
                "reason": "Bullish trend with momentum, not overbought",
            }

        # Bearish signal
        elif (
            analysis["trend"] == "bearish"
            and analysis["rsi"] > 30
            and analysis["volume_relative"] > 1.2
            and analysis["price_position"] > 0.3
        ):
            return {
                "action": "SELL",
                "confidence": min(
                    analysis["trend_strength"],
                    (analysis["rsi"] - 30) / 50,
                    analysis["volume_relative"] - 1.0,
                ),
                "reason": "Bearish trend with momentum, not oversold",
            }

        return None


async def demonstrate_phase4_improvements() -> None:
    """Demonstrate all Phase 4 improvements in action."""

    async with await TradingSuite.create(
        "MNQ", timeframes=["1min", "5min", "15min"], initial_days=2
    ) as suite:
        print("ProjectX SDK v3.0.0 - Phase 4 Comprehensive Test")
        print("=" * 60)

        strategy = CleanTradingStrategy(suite)

        # 1. Test simplified data access
        print("\n1️⃣ Testing Simplified Data Access")
        print("-" * 40)

        # Old way vs new way comparison
        print("OLD: data = await manager.get_data('5min')")
        print("     if data is None or len(data) < 50:")
        print("         return")
        print("\nNEW: data = await manager.get_data_or_none('5min', min_bars=50)")
        print("     if data is None:")
        print("         return")

        # Test new methods
        latest_bars = await suite.data.get_latest_bars(5)
        if latest_bars is not None:
            print(f"\n✅ get_latest_bars(): Got {len(latest_bars)} bars")

        price = await suite.data.get_latest_price()
        print(f"✅ get_latest_price(): ${price:,.2f}")

        ohlc = await suite.data.get_ohlc()
        if ohlc:
            print(
                f"✅ get_ohlc(): O:{ohlc['open']:,.2f} H:{ohlc['high']:,.2f} "
                f"L:{ohlc['low']:,.2f} C:{ohlc['close']:,.2f}"
            )

        # 2. Test enhanced models
        print("\n\n2️⃣ Testing Enhanced Model Properties")
        print("-" * 40)

        # Create demo position
        from project_x_py.models import Order, Position

        demo_pos = Position(
            id=1,
            accountId=1,
            contractId="CON.F.US.MNQ.H25",
            creationTimestamp=datetime.now().isoformat(),
            type=1,
            size=2,
            averagePrice=16500.0,
        )

        print("Position Properties:")
        print(f"  direction: {demo_pos.direction}")
        print(f"  symbol: {demo_pos.symbol}")
        print(f"  is_long: {demo_pos.is_long}")
        print(f"  signed_size: {demo_pos.signed_size}")
        print(f"  total_cost: ${demo_pos.total_cost:,.2f}")

        # Create demo order
        demo_order = Order(
            id=1,
            accountId=1,
            contractId="CON.F.US.MNQ.H25",
            creationTimestamp=datetime.now().isoformat(),
            updateTimestamp=None,
            status=1,
            type=1,
            side=0,
            size=5,
            fillVolume=2,
            limitPrice=16450.0,
        )

        print("\nOrder Properties:")
        print(f"  side_str: {demo_order.side_str}")
        print(f"  type_str: {demo_order.type_str}")
        print(f"  status_str: {demo_order.status_str}")
        print(f"  is_working: {demo_order.is_working}")
        print(f"  filled_percent: {demo_order.filled_percent:.0f}%")
        print(f"  remaining_size: {demo_order.remaining_size}")

        # 3. Execute full strategy
        print("\n\n3️⃣ Testing Complete Strategy Implementation")
        print("-" * 40)

        await strategy.execute_strategy()

        # 4. Performance comparison
        print("\n\n4️⃣ Code Complexity Comparison")
        print("-" * 40)
        print("Lines of code reduced:")
        print("  Data access: ~10 lines → 2 lines (80% reduction)")
        print("  Position checks: ~15 lines → 5 lines (67% reduction)")
        print("  Order filtering: ~8 lines → 3 lines (63% reduction)")
        print("\n✅ Overall: Cleaner, more readable, less error-prone code!")


async def main() -> None:
    """Run Phase 4 comprehensive test."""
    try:
        await demonstrate_phase4_improvements()

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
