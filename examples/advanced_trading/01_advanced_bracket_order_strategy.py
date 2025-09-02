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
