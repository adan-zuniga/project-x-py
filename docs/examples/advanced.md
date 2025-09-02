# Advanced Trading Examples

This page demonstrates sophisticated trading strategies and advanced features of the ProjectX Python SDK v3.5.7. These examples include order placement with automatic price alignment, risk management, and complex event-driven trading systems with proper multi-instrument event forwarding.

!!! warning "Live Trading Alert"
    **These examples place REAL ORDERS on the market!**

    - Only use with demo/simulated accounts for testing
    - All examples use MNQ (micro contracts) to minimize risk
    - Always monitor positions and orders closely
    - Include proper risk management and stop losses

## 1. Advanced Bracket Order Strategy

Bracket orders combine entry, stop loss, and take profit in a single operation:

```python
#!/usr/bin/env python
"""
Advanced bracket order strategy with dynamic stops based on ATR.

This example demonstrates:
- ATR-based dynamic stop loss and take profit levels
- RSI and SMA-based entry signals
- Bracket orders with automatic price alignment
- Real-time order monitoring and management
- Event-driven trade execution
"""

import asyncio
from decimal import Decimal
from typing import Optional

from project_x_py import EventType, TradingSuite
from project_x_py.event_bus import Event
from project_x_py.indicators import ATR, RSI, SMA
from project_x_py.models import BracketOrderResponse


class ATRBracketStrategy:
    """Advanced bracket order strategy using ATR for dynamic stops."""

    def __init__(self, suite: TradingSuite):
        self.suite = suite
        self.atr_period = 14
        self.rsi_period = 14
        self.sma_period = 20
        self.position_size = 1
        self.active_orders: list[BracketOrderResponse] = []
        self.max_positions = 1  # Limit concurrent positions

    async def calculate_dynamic_levels(self) -> tuple[float, float]:
        """Calculate stop and target levels based on ATR."""
        try:
            # Get bars for ATR calculation
            bars = await self.suite["MNQ"].data.get_data("5min")

            if bars is None or bars.is_empty():
                print("No data available for ATR calculation")
                # Return default values
                return 50.0, 100.0

            # Calculate ATR for volatility-based stops
            with_atr = bars.pipe(ATR, period=self.atr_period)

            # Get current ATR value
            atr_column = f"atr_{self.atr_period}"
            if atr_column not in with_atr.columns:
                print(f"ATR column {atr_column} not found")
                return 50.0, 100.0

            current_atr = float(with_atr[atr_column].tail(1)[0])

            # Dynamic stop loss: 2x ATR
            stop_offset = current_atr * 2

            # Dynamic take profit: 3x ATR (1.5:1 reward:risk)
            target_offset = current_atr * 3

            return stop_offset, target_offset

        except Exception as e:
            print(f"Error calculating ATR levels: {e}")
            # Return default values on error
            return 50.0, 100.0

    async def check_entry_conditions(self) -> tuple[Optional[str], Optional[float]]:
        """Check if conditions are met for entry."""
        try:
            bars = await self.suite["MNQ"].data.get_data("5min")

            if bars is None or bars.is_empty():
                return None, None

            # Ensure we have enough data for indicators
            if len(bars) < max(self.rsi_period, self.sma_period, self.atr_period):
                return None, None

            # Calculate indicators using pipe method
            with_rsi = bars.pipe(RSI, period=self.rsi_period)
            with_sma = with_rsi.pipe(SMA, period=self.sma_period)

            # Get current values from the last row
            last_row = with_sma.tail(1)

            current_price = float(last_row["close"][0])

            # Get RSI value
            rsi_column = f"rsi_{self.rsi_period}"
            current_rsi = (
                float(last_row[rsi_column][0])
                if rsi_column in last_row.columns
                else 50.0
            )

            # Get SMA value
            sma_column = f"sma_{self.sma_period}"
            current_sma = (
                float(last_row[sma_column][0])
                if sma_column in last_row.columns
                else current_price
            )

            # Long signal: Price above SMA and RSI oversold recovery
            if current_price > current_sma and 30 < current_rsi < 50:
                return "long", current_price

            # Short signal: Price below SMA and RSI overbought decline
            elif current_price < current_sma and 50 < current_rsi < 70:
                return "short", current_price

            return None, None

        except Exception as e:
            print(f"Error checking entry conditions: {e}")
            return None, None

    async def place_bracket_order(
        self, direction: str
    ) -> Optional[BracketOrderResponse]:
        """Place a bracket order based on strategy conditions."""
        try:
            # Get current price
            current_price = await self.suite["MNQ"].data.get_current_price()
            if not current_price:
                print("Could not get current price")
                return None

            # Calculate dynamic stop and target levels (offsets)
            stop_offset, target_offset = await self.calculate_dynamic_levels()

            # Calculate actual price levels
            if direction == "long":
                stop_loss_price = current_price - stop_offset
                take_profit_price = current_price + target_offset
                side = 0  # Buy
            else:  # short
                stop_loss_price = current_price + stop_offset
                take_profit_price = current_price - target_offset
                side = 1  # Sell

            # Display trade setup
            print("\n" + "=" * 60)
            print(f"{direction.upper()} BRACKET ORDER SETUP")
            print("=" * 60)
            print(f"Current Price: ${current_price:.2f}")
            print(f"Position Size: {self.position_size} contracts")
            print(f"Stop Loss: ${stop_loss_price:.2f} ({stop_offset:.2f} points)")
            print(f"Take Profit: ${take_profit_price:.2f} ({target_offset:.2f} points)")

            # Calculate risk/reward
            risk = abs(current_price - stop_loss_price)
            reward = abs(take_profit_price - current_price)
            rr_ratio = reward / risk if risk > 0 else 0
            print(f"Risk/Reward Ratio: {rr_ratio:.2f}:1")
            print("=" * 60)

            # Get instrument contract ID
            instrument = self.suite["MNQ"].instrument_info
            contract_id = instrument.id if hasattr(instrument, "id") else "MNQ"

            print("\nPlacing bracket order...")

            # Place bracket order with market entry
            # Prices will be automatically aligned to tick size
            result = await self.suite["MNQ"].orders.place_bracket_order(
                contract_id=contract_id,
                side=side,
                size=self.position_size,
                entry_price=None,  # Market order
                entry_type="market",
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
            )

            if result and result.success:
                print("\n✅ Bracket order placed successfully!")
                print(f"  Entry Order ID: {result.entry_order_id}")
                print(f"  Stop Order ID: {result.stop_order_id}")
                print(f"  Target Order ID: {result.target_order_id}")

                self.active_orders.append(result)
                return result
            else:
                error_msg = result.error_message if result else "Unknown error"
                print(f"\n❌ Failed to place bracket order: {error_msg}")
                return None

        except Exception as e:
            print(f"Failed to place bracket order: {e}")
            import traceback

            traceback.print_exc()
            return None

    async def monitor_orders(self):
        """Monitor active orders and handle fills/cancellations."""
        if not self.active_orders:
            return

        # Copy list to allow modification during iteration
        for bracket in self.active_orders[:]:
            try:
                if bracket is None:
                    continue

                # For this example, we'll just track the count
                # In production, you would check order status via the API

                # Note: The actual order monitoring would typically be done
                # through event handlers rather than polling

            except Exception as e:
                print(f"Error monitoring orders: {e}")

    def remove_completed_order(self, order_id: int):
        """Remove a completed order from tracking."""
        self.active_orders = [
            bracket
            for bracket in self.active_orders
            if bracket and bracket.entry_order_id != order_id
        ]


async def main():
    """Main function to run the ATR bracket strategy."""
    print("Initializing Advanced Bracket Order Strategy...")

    # Create trading suite with required timeframes
    suite = await TradingSuite.create(
        ["MNQ"],
        timeframes=["1min", "5min"],
        initial_days=10,  # Need historical data for indicators
        features=["risk_manager"],
    )

    # Initialize strategy
    strategy = ATRBracketStrategy(suite)
    mnq_context = suite["MNQ"]

    # Track last bar time to avoid duplicate processing
    last_bar_time = {}

    # Set up event handlers for real-time monitoring
    async def on_new_bar(event: Event):
        """Handle new bar events."""
        timeframe = event.data.get("timeframe", "unknown")

        if timeframe == "5min":
            # Avoid duplicate processing
            current_time = event.data.get("timestamp", "")
            if current_time == last_bar_time.get(timeframe):
                return
            last_bar_time[timeframe] = current_time

            # Get bar data
            bar_data = event.data.get("data", {})
            close_price = bar_data.get("close", 0)

            if close_price:
                print(f"\nNew 5min bar: ${close_price:.2f}")

            # Check if we can take a new position
            if len(strategy.active_orders) >= strategy.max_positions:
                return

            # Check for entry signals
            direction, price = await strategy.check_entry_conditions()
            if direction:
                print(
                    f"\n🎯 Entry signal detected: {direction.upper()} at ${price:.2f}"
                )

                # Auto-confirm for demo, or ask user
                if False:  # Set to True for auto-trading
                    await strategy.place_bracket_order(direction)
                else:
                    # Confirm with user before placing order
                    response = input(
                        f"Place {direction.upper()} bracket order? (y/N): "
                    )
                    if response.lower().startswith("y"):
                        await strategy.place_bracket_order(direction)

    # Register event handlers
    await mnq_context.on(EventType.NEW_BAR, on_new_bar)

    print("\n" + "=" * 60)
    print("ADVANCED BRACKET ORDER STRATEGY ACTIVE")
    print("=" * 60)
    print("Strategy Settings:")
    print(f"  ATR Period: {strategy.atr_period}")
    print(f"  RSI Period: {strategy.rsi_period}")
    print(f"  SMA Period: {strategy.sma_period}")
    print(f"  Position Size: {strategy.position_size} contracts")
    print(f"  Max Positions: {strategy.max_positions}")
    print("\nMonitoring for entry signals on 5-minute bars...")
    print("Press Ctrl+C to exit")
    print("=" * 60)

    try:
        while True:
            await asyncio.sleep(30)  # Status update every 30 seconds

            # Monitor active orders
            await strategy.monitor_orders()

            # Display current market info
            current_price = await mnq_context.data.get_current_price()
            if current_price:
                active_count = len(strategy.active_orders)
                print(
                    f"\nStatus: Price=${current_price:.2f} | Active Orders={active_count}"
                )

    except KeyboardInterrupt:
        print("\n\nShutting down strategy...")

        # Cancel any remaining orders
        for bracket in strategy.active_orders:
            if bracket:
                try:
                    # Cancel stop and target orders
                    if bracket.stop_order_id:
                        await mnq_context.orders.cancel_order(bracket.stop_order_id)
                        print(f"Cancelled stop order {bracket.stop_order_id}")
                    if bracket.target_order_id:
                        await mnq_context.orders.cancel_order(bracket.target_order_id)
                        print(f"Cancelled target order {bracket.target_order_id}")
                except Exception as e:
                    print(f"Error cancelling orders: {e}")

    finally:
        # Disconnect from real-time feeds
        await suite.disconnect()
        print("Strategy disconnected. Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
```

## 2. Multi-Timeframe Momentum Strategy

Advanced strategy using multiple timeframes for confirmation:

```python
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
            bracket_result: BracketOrderResponse = strategy.active_position.get("bracket_result", {})
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
```

## 3. Advanced Risk Management System

Comprehensive risk management with position sizing and portfolio limits:

```python
#!/usr/bin/env python
"""
Advanced risk management system with portfolio-level controls.

This example demonstrates:
- Position sizing based on risk parameters
- Portfolio risk monitoring
- Bracket orders with automatic stop-loss and take-profit
- Real-time P&L tracking
- Risk limit enforcement
"""

import asyncio
from datetime import datetime
from decimal import Decimal

from project_x_py import EventType, TradingSuite
from project_x_py.event_bus import Event


class AdvancedRiskManager:
    """Advanced risk management system for trading."""

    def __init__(self, suite: TradingSuite):
        self.suite = suite

        # Risk parameters
        self.max_risk_per_trade = Decimal("0.02")  # 2% per trade
        self.max_daily_risk = Decimal("0.06")  # 6% per day
        self.max_portfolio_risk = Decimal("0.20")  # 20% total portfolio
        self.max_positions = 3  # Maximum open positions

        # Tracking
        self.account_balance = Decimal("50000")  # Default demo balance
        self.daily_pnl = Decimal("0")
        self.active_trades = []
        self.daily_reset_time = datetime.now().date()

    async def update_account_info(self):
        """Update account information."""
        try:
            # Try to get positions to calculate P&L
            positions = await self.suite["MNQ"].positions.get_all_positions()

            # Calculate total P&L from positions
            total_pnl = Decimal("0")
            # Note: Actual P&L calculation would depend on position attributes
            # This is a placeholder for demonstration

            # Update daily P&L
            current_date = datetime.now().date()
            if current_date > self.daily_reset_time:
                self.daily_pnl = Decimal("0")
                self.daily_reset_time = current_date
                print(f"Daily P&L reset for {current_date}")

            self.daily_pnl += total_pnl

        except Exception as e:
            print(f"Could not update account info: {e}")

    async def calculate_position_size(
        self, entry_price: float, stop_loss: float
    ) -> int:
        """Calculate optimal position size based on risk parameters."""
        # Calculate risk amount
        risk_amount = self.account_balance * self.max_risk_per_trade

        # Calculate risk per contract (MNQ = $20 per point)
        price_diff = abs(Decimal(str(entry_price)) - Decimal(str(stop_loss)))
        risk_per_contract = price_diff * 20

        if risk_per_contract <= 0:
            return 0

        # Calculate position size
        calculated_size = int(risk_amount / risk_per_contract)

        # Apply position limits
        max_size = 10  # Hard limit
        return max(1, min(calculated_size, max_size))

    async def check_risk_limits(self, proposed_size: int) -> tuple[bool, list[str]]:
        """Check if proposed trade violates risk limits."""
        errors = []

        # Check maximum positions
        positions = await self.suite["MNQ"].positions.get_all_positions()
        active_positions = [p for p in positions if p.size != 0]

        if len(active_positions) >= self.max_positions:
            errors.append(f"Maximum positions reached ({self.max_positions})")

        # Check daily risk limit
        if abs(self.daily_pnl) >= (self.account_balance * self.max_daily_risk):
            errors.append(f"Daily risk limit reached ({self.max_daily_risk * 100}%)")

        # Check portfolio risk
        total_position_size = sum(abs(p.size) for p in active_positions)
        if total_position_size + proposed_size > 20:  # Max 20 contracts total
            errors.append("Portfolio size limit reached (20 contracts max)")

        return len(errors) == 0, errors

    async def place_risk_managed_trade(
        self, direction: str, stop_offset: float = 50, target_offset: float = 100
    ):
        """Place a trade with full risk management."""
        try:
            # Get current price
            current_price = await self.suite["MNQ"].data.get_current_price()
            if not current_price:
                print("Could not get current price")
                return None

            # Calculate entry, stop, and target prices
            if direction == "long":
                entry_price = current_price
                stop_loss = current_price - stop_offset
                take_profit = current_price + target_offset
                side = 0  # Buy
            else:
                entry_price = current_price
                stop_loss = current_price + stop_offset
                take_profit = current_price - target_offset
                side = 1  # Sell

            # Calculate position size
            position_size = await self.calculate_position_size(entry_price, stop_loss)

            if position_size == 0:
                print("Position size calculated as 0 - trade rejected")
                return None

            # Check risk limits
            risk_ok, risk_errors = await self.check_risk_limits(position_size)

            if not risk_ok:
                print("Trade rejected due to risk limits:")
                for error in risk_errors:
                    print(f"  - {error}")
                return None

            # Calculate trade risk
            risk_per_contract = abs(entry_price - stop_loss) * 20  # MNQ multiplier
            total_risk = risk_per_contract * position_size
            risk_pct = float((total_risk / float(self.account_balance)) * 100)

            # Display trade details
            print("\n" + "=" * 50)
            print("RISK-MANAGED TRADE SETUP")
            print("=" * 50)
            print(f"Direction: {direction.upper()}")
            print(f"Current Price: ${entry_price:.2f}")
            print(f"Stop Loss: ${stop_loss:.2f} ({stop_offset} points)")
            print(f"Take Profit: ${take_profit:.2f} ({target_offset} points)")
            print(f"Position Size: {position_size} contracts")
            print(f"Risk Amount: ${total_risk:.2f} ({risk_pct:.2f}% of account)")
            print(f"R:R Ratio: {target_offset / stop_offset:.1f}:1")

            # Show current status
            positions = await self.suite["MNQ"].positions.get_all_positions()
            active_positions = [p for p in positions if p.size != 0]
            print("\nCurrent Status:")
            print(f"  Active Positions: {len(active_positions)}")
            print(f"  Daily P&L: ${self.daily_pnl:.2f}")
            print("=" * 50)

            # Confirm trade
            response = input(f"\nProceed with {direction.upper()} trade? (y/N): ")
            if not response.lower().startswith("y"):
                print("Trade cancelled")
                return None

            # Place bracket order
            print("\nPlacing bracket order...")

            # Get the instrument contract ID
            instrument = self.suite["MNQ"].instrument_info
            contract_id = instrument.id if hasattr(instrument, "id") else "MNQ"

            result = await self.suite["MNQ"].orders.place_bracket_order(
                contract_id=contract_id,
                side=side,
                size=position_size,
                entry_price=None,  # Market entry
                entry_type="market",
                stop_loss_price=stop_loss,
                take_profit_price=take_profit,
            )

            if result and result.success:
                # Track the trade
                trade_record = {
                    "direction": direction,
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "size": position_size,
                    "risk_amount": total_risk,
                    "bracket_result": result,
                    "timestamp": datetime.now(),
                    "status": "active",
                }
                self.active_trades.append(trade_record)

                print("\n✅ Risk-managed trade placed successfully!")
                print(f"  Entry Order: {result.entry_order_id}")
                print(f"  Stop Order: {result.stop_order_id}")
                print(f"  Target Order: {result.target_order_id}")
            else:
                error_msg = result.error_message if result else "Unknown error"
                print(f"\n❌ Failed to place trade: {error_msg}")

            return result

        except Exception as e:
            print(f"Failed to place risk-managed trade: {e}")
            import traceback

            traceback.print_exc()
            return None

    async def generate_risk_report(self):
        """Generate comprehensive risk report."""
        await self.update_account_info()

        print("\n" + "=" * 60)
        print("RISK MANAGEMENT REPORT")
        print("=" * 60)

        print(f"Account Balance: ${self.account_balance:,.2f}")
        print(
            f"Daily P&L: ${self.daily_pnl:.2f} ({(self.daily_pnl / self.account_balance) * 100:.2f}%)"
        )

        # Get current positions
        positions = await self.suite["MNQ"].positions.get_all_positions()
        active_positions = [p for p in positions if p.size != 0]

        print(f"\nActive Positions: {len(active_positions)}")
        for i, pos in enumerate(active_positions, 1):
            side = "LONG" if pos.size > 0 else "SHORT"
            print(f"  {i}. {side} {abs(pos.size)} contracts")

        print("\nRisk Limits:")
        print(
            f"  Per Trade: {self.max_risk_per_trade * 100:.1f}% (${self.account_balance * self.max_risk_per_trade:.2f})"
        )
        print(
            f"  Daily: {self.max_daily_risk * 100:.1f}% (${self.account_balance * self.max_daily_risk:.2f})"
        )
        print(f"  Portfolio: {self.max_portfolio_risk * 100:.1f}%")
        print(f"  Max Positions: {self.max_positions}")

        if self.active_trades:
            print("\nRecent Trades:")
            for i, trade in enumerate(self.active_trades[-5:], 1):  # Show last 5
                print(
                    f"  {i}. {trade['direction'].upper()} - "
                    f"${trade['entry_price']:.2f} "
                    f"(Risk: ${trade['risk_amount']:.2f}) - "
                    f"{trade['status'].upper()}"
                )

        print("=" * 60)


async def main():
    """Main function to run the risk management system."""
    print("Initializing Advanced Risk Management System...")

    # Create TradingSuite with risk management features
    suite = await TradingSuite.create(
        ["MNQ"],
        timeframes=["1min", "5min"],
        initial_days=1,
        features=["risk_manager"],  # Enable risk manager feature
    )

    # Create risk manager
    risk_manager = AdvancedRiskManager(suite)
    mnq_context = suite["MNQ"]

    # Set up event handlers
    async def on_new_bar(_event: Event):
        """Handle new bar events to update P&L."""
        # Update account info on each new bar
        await risk_manager.update_account_info()

    async def on_quote(_event: Event):
        """Handle quote updates."""
        # Could use this for real-time P&L updates
        # Placeholder for future real-time updates

    # Register event handlers
    await mnq_context.on(EventType.NEW_BAR, on_new_bar)
    await mnq_context.on(EventType.QUOTE_UPDATE, on_quote)

    print("\n" + "=" * 60)
    print("ADVANCED RISK MANAGEMENT SYSTEM ACTIVE")
    print("=" * 60)
    print("\nCommands:")
    print("  'long'  - Place risk-managed LONG trade")
    print("  'short' - Place risk-managed SHORT trade")
    print("  'report' - Generate risk report")
    print("  'quit'  - Exit system")
    print("=" * 60)

    try:
        while True:
            # Get user input
            command = input("\nEnter command: ").strip().lower()

            if command == "quit":
                break
            elif command == "report":
                await risk_manager.generate_risk_report()
            elif command == "long":
                await risk_manager.place_risk_managed_trade("long")
            elif command == "short":
                await risk_manager.place_risk_managed_trade("short")
            elif command:
                print(f"Unknown command: {command}")

            # Brief pause to allow async operations
            await asyncio.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\nShutting down risk management system...")
    finally:
        # Disconnect from real-time feeds
        await suite.disconnect()
        print("System disconnected. Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
```

## 4. Order Book Analysis and Scalping Strategy

Advanced market microstructure analysis for scalping:

```python
#!/usr/bin/env python
"""
Advanced order book analysis and scalping strategy
"""
import asyncio
from collections import deque
from decimal import Decimal
from project_x_py import TradingSuite, EventType

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
            if hasattr(self.suite, 'orderbook') and self.suite.orderbook:
                self.orderbook = self.suite.orderbook
                print("Order book initialized successfully")
                return True
            else:
                print("Order book not available - create suite with 'orderbook' feature")
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

            if not book_data or 'bids' not in book_data or 'asks' not in book_data:
                return None

            bids = book_data['bids'][:5]  # Top 5 levels
            asks = book_data['asks'][:5]

            # Calculate size at each level
            total_bid_size = sum(level['size'] for level in bids)
            total_ask_size = sum(level['size'] for level in asks)

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
                    "spread": asks[0]['price'] - bids[0]['price'] if bids and asks else 0
                }
            elif ask_ratio >= self.imbalance_threshold:
                return {
                    "direction": "bearish",
                    "strength": ask_ratio,
                    "bid_size": total_bid_size,
                    "ask_size": total_ask_size,
                    "spread": asks[0]['price'] - bids[0]['price'] if bids and asks else 0
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
        buy_volume = sum(tick['size'] for tick in recent_ticks if tick.get('aggressor') == 'buy')
        sell_volume = sum(tick['size'] for tick in recent_ticks if tick.get('aggressor') == 'sell')

        total_volume = buy_volume + sell_volume
        if total_volume == 0:
            return None

        buy_ratio = buy_volume / total_volume

        # Strong buying/selling pressure
        if buy_ratio >= 0.70:
            return {"direction": "bullish", "strength": buy_ratio, "volume": total_volume}
        elif buy_ratio <= 0.30:
            return {"direction": "bearish", "strength": 1 - buy_ratio, "volume": total_volume}

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
            print(f"  Stop: ${stop_loss:.2f} ({abs(entry_price - stop_loss) / tick_size:.0f} ticks)")
            print(f"  Target: ${take_profit:.2f} ({abs(take_profit - entry_price) / tick_size:.0f} ticks)")
            print(f"  Analysis: {analysis_data}")

            # Quick confirmation for scalping
            response = input(f"Execute {direction.upper()} scalp? (y/N): ")
            if not response.lower().startswith('y'):
                return None

            # Place bracket order with tight parameters
            result = await self.suite.orders.place_bracket_order(
                contract_id=self.suite.instrument_info.id,
                side=side,
                size=1,  # Small size for scalping
                stop_offset=Decimal(str(abs(entry_price - stop_loss))),
                target_offset=Decimal(str(abs(take_profit - entry_price)))
            )

            scalp_record = {
                "direction": direction,
                "entry_price": entry_price,
                "bracket": result,
                "analysis": analysis_data,
                "timestamp": asyncio.get_event_loop().time()
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
                main_status = await self.suite.orders.get_order_status(scalp['bracket'].main_order_id)

                if main_status.status in ["Filled", "Cancelled", "Rejected"]:
                    print(f"Scalp completed: {scalp['direction']} - {main_status.status}")
                    self.active_orders.remove(scalp)

                # Time-based cancellation (scalps should be quick)
                elif (asyncio.get_event_loop().time() - scalp['timestamp']) > 300:  # 5 minutes
                    print(f"Cancelling stale scalp order: {scalp['bracket'].main_order_id}")
                    await self.suite.orders.cancel_order(scalp['bracket'].main_order_id)
                    self.active_orders.remove(scalp)

            except Exception as e:
                print(f"Error monitoring scalp: {e}")

async def main():
    # Create suite with order book feature
    suite = await TradingSuite.create(
        ["MNQ"],
        timeframes=["15sec", "1min"],
        features=["orderbook"],  # Essential for order book analysis
        initial_days=1
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
        strategy.tick_history.append({
            'price': tick_data.get('price', 0),
            'size': tick_data.get('size', 0),
            'aggressor': tick_data.get('aggressor', 'unknown'),
            'timestamp': asyncio.get_event_loop().time()
        })

        # Analyze every 10th tick to avoid over-trading
        if len(strategy.tick_history) % 10 == 0:
            # Check for order book imbalances
            ob_analysis = await strategy.analyze_order_book_imbalance()
            tape_analysis = await strategy.analyze_tape_reading()

            # Look for confluence between order book and tape
            if ob_analysis and tape_analysis:
                if (ob_analysis['direction'] == tape_analysis['direction'] and
                    len(strategy.active_orders) == 0):  # No active scalps

                    print(f"\nScalping signal detected:")
                    print(f"  Order Book: {ob_analysis['direction']} ({ob_analysis['strength']:.2f})")
                    print(f"  Tape: {tape_analysis['direction']} ({tape_analysis['strength']:.2f})")

                    await strategy.place_scalp_order(ob_analysis['direction'], {
                        'orderbook': ob_analysis,
                        'tape': tape_analysis
                    })

    async def on_order_filled(event):
        order_data = event.data
        print(f"SCALP FILL: {order_data.get('order_id')} at ${order_data.get('fill_price', 0):.2f}")

    # Register events
    await mnq_context.on(EventType.TICK, on_tick)
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

            print(f"Price: ${current_price:.2f} | Active Scalps: {active_scalps} | Ticks: {recent_ticks}")

    except KeyboardInterrupt:
        print("\nShutting down scalping strategy...")

        # Cancel any active orders
        for scalp in strategy.active_orders:
            try:
                await mnq_context.orders.cancel_order(scalp['bracket'].main_order_id)
                print(f"Cancelled scalp order: {scalp['bracket'].main_order_id}")
            except Exception as e:
                print(f"Error cancelling order: {e}")


if __name__ == "__main__":
    asyncio.run(main())
```

## Safety Guidelines for Advanced Trading

!!! danger "Critical Safety Reminders"

    1. **Demo Accounts Only**: Always test with simulated accounts first
    2. **Position Sizing**: Never risk more than 2% per trade
    3. **Stop Losses**: Always use stop losses - never trade without them
    4. **Market Hours**: Be aware of futures market hours and rollover dates
    5. **Margin Requirements**: Ensure sufficient margin for all positions
    6. **Monitoring**: Never leave positions unmonitored
    7. **Risk Management**: Implement portfolio-level risk controls
    8. **Paper Trading**: Thoroughly test all strategies before live trading

## Common Pitfalls to Avoid

- **Over-leveraging**: Using too much leverage relative to account size
- **Over-trading**: Placing too many trades based on marginal signals
- **Ignoring Risk Management**: Not implementing proper stop losses and position sizing
- **Chasing Markets**: Entering trades after big moves have already occurred
- **Emotional Trading**: Making decisions based on fear or greed
- **Inadequate Testing**: Not thoroughly backtesting strategies before live trading
- **Poor Timing**: Trading during low liquidity periods or major news events

## Next Steps

After mastering these advanced examples:

1. **Develop Your Own Strategies**: Combine different techniques to create unique approaches
2. **Implement Backtesting**: Test strategies on historical data before live trading
3. **Build Risk Management Systems**: Create comprehensive risk controls
4. **Optimize Performance**: Fine-tune parameters based on market conditions
5. **Scale Gradually**: Start small and gradually increase position sizes as you gain confidence

For more examples, see:
- [Real-time Data Processing](realtime.md)
- [Backtesting Strategies](backtesting.md)
- [Basic Usage Examples](basic.md)
