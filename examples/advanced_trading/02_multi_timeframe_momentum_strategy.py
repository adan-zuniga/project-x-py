#!/usr/bin/env python
"""
Multi-timeframe momentum strategy with confluence analysis.

This example demonstrates:
- Multi-timeframe analysis (5min, 15min, 1hr)
- Momentum and trend confluence detection
- Technical indicators (RSI, MACD, EMA, ATR)
- Dynamic position sizing based on ATR
- Bracket orders with volatility-based stops
"""

import asyncio
from decimal import Decimal
from typing import Any, Optional

from project_x_py import EventType, TradingSuite
from project_x_py.event_bus import Event
from project_x_py.indicators import ATR, EMA, MACD, RSI
from project_x_py.models import BracketOrderResponse


class MultiTimeframeMomentumStrategy:
    """Multi-timeframe momentum trading strategy."""

    def __init__(self, suite: TradingSuite):
        self.suite = suite
        self.position_size = 1
        self.risk_per_trade = Decimal("0.02")  # 2% risk per trade
        self.account_balance = Decimal("50000")  # Default balance
        self.active_position: Optional[dict[str, Any]] = None

    async def analyze_timeframe(self, timeframe: str) -> Optional[dict[str, Any]]:
        """Analyze a specific timeframe for momentum signals."""
        try:
            # Get bars for the timeframe
            bars = await self.suite["MNQ"].data.get_data(timeframe)

            if bars is None or bars.is_empty():
                print(f"No data available for {timeframe}")
                return None

            if len(bars) < 50:  # Need sufficient data for indicators
                print(f"Insufficient data for {timeframe} (need 50+ bars)")
                return None

            # Calculate indicators using pipe method
            with_rsi = bars.pipe(RSI, period=14)
            with_macd = with_rsi.pipe(
                MACD, fast_period=12, slow_period=26, signal_period=9
            )
            with_ema20 = with_macd.pipe(EMA, period=20)
            with_ema50 = with_ema20.pipe(EMA, period=50)

            # Get the last row for current values
            last_row = with_ema50.tail(1)

            # Extract values from the last row
            current_price = float(last_row["close"][0])
            current_rsi = (
                float(last_row["rsi_14"][0]) if "rsi_14" in last_row.columns else 50.0
            )

            # MACD values
            current_macd = (
                float(last_row["macd"][0]) if "macd" in last_row.columns else 0.0
            )
            macd_signal = (
                float(last_row["macd_signal"][0])
                if "macd_signal" in last_row.columns
                else 0.0
            )

            # EMA values
            current_ema_20 = (
                float(last_row["ema_20"][0])
                if "ema_20" in last_row.columns
                else current_price
            )
            current_ema_50 = (
                float(last_row["ema_50"][0])
                if "ema_50" in last_row.columns
                else current_price
            )

            # Determine trend and momentum
            trend = "bullish" if current_ema_20 > current_ema_50 else "bearish"
            momentum = "positive" if current_macd > macd_signal else "negative"
            rsi_level = (
                "oversold"
                if current_rsi < 30
                else "overbought"
                if current_rsi > 70
                else "neutral"
            )

            return {
                "timeframe": timeframe,
                "price": current_price,
                "trend": trend,
                "momentum": momentum,
                "rsi_level": rsi_level,
                "rsi": current_rsi,
                "macd": current_macd,
                "macd_signal": macd_signal,
                "ema_20": current_ema_20,
                "ema_50": current_ema_50,
            }

        except Exception as e:
            print(f"Error analyzing {timeframe}: {e}")
            return None

    async def check_confluence(self) -> tuple[Optional[str], Optional[list]]:
        """Check for confluence across multiple timeframes."""
        # Analyze all configured timeframes
        analyses = []

        for timeframe in ["5min", "15min", "1hr"]:
            if timeframe in self.suite["MNQ"].data.timeframes:
                analysis = await self.analyze_timeframe(timeframe)
                if analysis:
                    analyses.append(analysis)

        if len(analyses) < 2:
            return None, analyses if analyses else None

        # Count bullish/bearish signals
        bullish_signals = sum(
            1
            for tf in analyses
            if tf["trend"] == "bullish" and tf["momentum"] == "positive"
        )
        bearish_signals = sum(
            1
            for tf in analyses
            if tf["trend"] == "bearish" and tf["momentum"] == "negative"
        )

        # Get the lowest timeframe analysis (usually 5min)
        entry_tf = analyses[0]  # First timeframe for entry conditions

        # Require confluence (majority agreement)
        if bullish_signals >= 2 and entry_tf["rsi"] < 70:  # Not overbought
            return "long", analyses
        elif bearish_signals >= 2 and entry_tf["rsi"] > 30:  # Not oversold
            return "short", analyses

        return None, analyses

    async def calculate_position_size(
        self, entry_price: float, stop_loss: float
    ) -> int:
        """Calculate position size based on risk management."""
        # Calculate risk amount
        risk_amount = float(self.account_balance) * float(self.risk_per_trade)

        # Calculate risk per contract (MNQ = $20 per point)
        price_diff = abs(entry_price - stop_loss)
        risk_per_contract = price_diff * 20

        if risk_per_contract <= 0:
            return 1

        # Calculate position size
        calculated_size = int(risk_amount / risk_per_contract)
        return max(1, min(calculated_size, 5))  # Between 1-5 contracts

    async def calculate_atr_stops(
        self, direction: str, current_price: float, timeframe: str = "5min"
    ) -> tuple[float, float]:
        """Calculate ATR-based stop loss and take profit."""
        try:
            # Get bars for ATR calculation
            bars = await self.suite["MNQ"].data.get_data(timeframe)
            if bars is None or bars.is_empty():
                # Fallback to fixed stops
                if direction == "long":
                    return current_price - 50, current_price + 100
                else:
                    return current_price + 50, current_price - 100

            # Calculate ATR
            with_atr = bars.pipe(ATR, period=14)
            current_atr = float(with_atr["atr_14"].tail(1)[0])

            # Dynamic stops based on volatility (2x ATR stop, 3x ATR target)
            if direction == "long":
                stop_loss = current_price - (current_atr * 2)
                take_profit = current_price + (current_atr * 3)
            else:
                stop_loss = current_price + (current_atr * 2)
                take_profit = current_price - (current_atr * 3)

            return stop_loss, take_profit

        except Exception as e:
            print(f"Error calculating ATR stops: {e}")
            # Fallback to fixed stops
            if direction == "long":
                return current_price - 50, current_price + 100
            else:
                return current_price + 50, current_price - 100

    async def place_momentum_trade(
        self, direction: str, analyses: list
    ) -> Optional[Any]:
        """Place a trade based on momentum confluence."""
        try:
            # Use the entry timeframe price
            current_price = analyses[0]["price"]

            # Calculate ATR-based stops
            stop_loss, take_profit = await self.calculate_atr_stops(
                direction, current_price
            )

            # Calculate position size
            position_size = await self.calculate_position_size(current_price, stop_loss)

            # Display trade setup
            print("\n" + "=" * 60)
            print(f"{direction.upper()} MOMENTUM TRADE SETUP")
            print("=" * 60)
            print(f"Entry Price: ${current_price:.2f}")
            print(
                f"Stop Loss: ${stop_loss:.2f} ({abs(current_price - stop_loss):.2f} points)"
            )
            print(
                f"Take Profit: ${take_profit:.2f} ({abs(take_profit - current_price):.2f} points)"
            )
            print(f"Position Size: {position_size} contracts")

            # Calculate risk/reward
            risk = abs(current_price - stop_loss)
            reward = abs(take_profit - current_price)
            rr_ratio = reward / risk if risk > 0 else 0
            print(f"Risk/Reward: {rr_ratio:.2f}:1")

            # Display confluence analysis
            print("\nConfluence Analysis:")
            for analysis in analyses:
                print(
                    f"  {analysis['timeframe']:5s}: "
                    f"{analysis['trend']:7s} trend, "
                    f"{analysis['momentum']:8s} momentum, "
                    f"RSI: {analysis['rsi']:5.1f}"
                )
            print("=" * 60)

            # Confirm trade
            response = input(f"\nPlace {direction.upper()} momentum trade? (y/N): ")
            if not response.lower().startswith("y"):
                print("Trade cancelled")
                return None

            # Get instrument contract ID
            instrument = self.suite["MNQ"].instrument_info
            contract_id = instrument.id if hasattr(instrument, "id") else "MNQ"

            # Determine side
            side = 0 if direction == "long" else 1  # 0=Buy, 1=Sell

            print("\nPlacing bracket order...")

            # Place bracket order with market entry
            result = await self.suite["MNQ"].orders.place_bracket_order(
                contract_id=contract_id,
                side=side,
                size=position_size,
                entry_price=None,  # Market order
                entry_type="market",
                stop_loss_price=stop_loss,
                take_profit_price=take_profit,
            )

            if result and result.success:
                self.active_position = {
                    "direction": direction,
                    "entry_price": current_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "size": position_size,
                    "bracket_result": result,
                }

                print("\n✅ Momentum trade placed successfully!")
                print(f"  Entry Order: {result.entry_order_id}")
                print(f"  Stop Order: {result.stop_order_id}")
                print(f"  Target Order: {result.target_order_id}")
            else:
                error_msg = result.error_message if result else "Unknown error"
                print(f"\n❌ Failed to place trade: {error_msg}")

            return result

        except Exception as e:
            print(f"Failed to place momentum trade: {e}")
            import traceback

            traceback.print_exc()
            return None


async def main():
    """Main function to run the momentum strategy."""
    print("Initializing Multi-Timeframe Momentum Strategy...")

    # Create suite with multiple timeframes
    suite = await TradingSuite.create(
        ["MNQ"],
        timeframes=["5min", "15min", "1hr"],
        initial_days=15,  # More historical data for higher timeframes
        features=["risk_manager"],
    )

    mnq_context = suite["MNQ"]
    strategy = MultiTimeframeMomentumStrategy(suite)

    # Event handlers
    last_bar_time = {}

    async def on_new_bar(event: Event):
        """Handle new bar events."""
        # Get timeframe from event data
        timeframe = event.data.get("timeframe", "unknown")

        # Only act on 5min bars for trade decisions
        if timeframe == "5min":
            # Avoid duplicate processing
            current_time = event.data.get("timestamp", "")
            if current_time == last_bar_time.get(timeframe):
                return
            last_bar_time[timeframe] = current_time

            # Check for confluence signals
            direction, analyses = await strategy.check_confluence()

            if analyses and not strategy.active_position:
                if direction:
                    print(f"\n{'=' * 60}")
                    print(f"MOMENTUM CONFLUENCE DETECTED: {direction.upper()}")
                    print(f"{'=' * 60}")
                    await strategy.place_momentum_trade(direction, analyses)
                else:
                    # Display current analysis (no confluence)
                    print("\nCurrent Market Analysis (No Confluence):")
                    for analysis in analyses:
                        print(
                            f"  {analysis['timeframe']:5s}: "
                            f"{analysis['trend']:7s}/{analysis['momentum']:8s} "
                            f"(RSI: {analysis['rsi']:5.1f})"
                        )

    # Register event handlers
    await mnq_context.on(EventType.NEW_BAR, on_new_bar)

    print("\n" + "=" * 60)
    print("MULTI-TIMEFRAME MOMENTUM STRATEGY ACTIVE")
    print("=" * 60)
    print("Analyzing 5min, 15min, and 1hr timeframes for confluence")
    print("Looking for aligned trend and momentum signals")
    print("Using ATR-based dynamic stops and targets")
    print("\nPress Ctrl+C to exit")
    print("=" * 60)

    try:
        while True:
            await asyncio.sleep(30)  # Status update every 30 seconds

            # Display status
            current_price = await mnq_context.data.get_current_price()
            if current_price:
                position_status = "ACTIVE" if strategy.active_position else "FLAT"

                print("\nStatus Update:")
                print(f"  Price: ${current_price:.2f}")
                print(f"  Position: {position_status}")

                if strategy.active_position:
                    pos = strategy.active_position
                    print(f"  Direction: {pos['direction'].upper()}")
                    print(f"  Entry: ${pos['entry_price']:.2f}")
                    print(f"  Stop: ${pos['stop_loss']:.2f}")
                    print(f"  Target: ${pos['take_profit']:.2f}")

    except KeyboardInterrupt:
        print("\n\nShutting down strategy...")

        # Cancel active orders if any
        if strategy.active_position:
            bracket_result: BracketOrderResponse = strategy.active_position.get(
                "bracket_result", {}
            )
            if bracket_result:
                try:
                    # Cancel stop and target orders
                    if bracket_result.stop_order_id:
                        await mnq_context.orders.cancel_order(
                            bracket_result.stop_order_id
                        )
                    if bracket_result.target_order_id:
                        await mnq_context.orders.cancel_order(
                            bracket_result.target_order_id
                        )
                    print("Cancelled active orders")
                except Exception as e:
                    print(f"Error cancelling orders: {e}")

    finally:
        # Disconnect from real-time feeds
        await suite.disconnect()
        print("Strategy disconnected. Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
