#!/usr/bin/env python
"""
Advanced bracket order strategy with dynamic stops based on ATR
"""

import asyncio
from decimal import Decimal

from project_x_py import EventType, TradingSuite
from project_x_py.indicators import ATR, RSI, SMA
from project_x_py.models import BracketOrderResponse


class ATRBracketStrategy:
    def __init__(self, suite: TradingSuite):
        self.suite = suite
        self.atr_period = 14
        self.rsi_period = 14
        self.sma_period = 20
        self.position_size = 1
        self.active_orders: list[BracketOrderResponse] = []

    async def calculate_dynamic_levels(self):
        """Calculate stop and target levels based on ATR."""
        bars = await self.suite["MNQ"].data.get_data("5min")

        if bars is None:
            raise Exception("No data available")

        # Calculate ATR for volatility-based stops
        atr_values = bars.pipe(ATR, period=self.atr_period)
        current_atr = float(atr_values["atr_14"][-1])

        # Dynamic stop loss: 2x ATR
        stop_offset = Decimal(str(current_atr * 2))

        # Dynamic take profit: 3x ATR (1.5:1 reward:risk)
        target_offset = Decimal(str(current_atr * 3))

        return stop_offset, target_offset

    async def check_entry_conditions(self):
        """Check if conditions are met for entry."""
        bars = await self.suite["MNQ"].data.get_data("5min")

        if bars is None:
            raise Exception("No data available")

        if len(bars) < max(self.rsi_period, self.sma_period, self.atr_period):
            return None, None

        # Calculate indicators
        rsi = bars.pipe(RSI, period=self.rsi_period)
        sma = bars.pipe(SMA, period=self.sma_period)
        current_price = bars["close"][-1]
        current_rsi = rsi[f"rsi_{self.rsi_period}"][-1]
        current_sma = sma[f"sma_{self.sma_period}"][-1]

        # Long signal: Price above SMA and RSI oversold recovery
        if current_price > current_sma and 30 < current_rsi < 50:
            return "long", current_price

        # Short signal: Price below SMA and RSI overbought decline
        elif current_price < current_sma and 50 < current_rsi < 70:
            return "short", current_price

        return None, None

    async def place_bracket_order(self, direction: str):
        """Place a bracket order based on strategy conditions."""
        try:
            # Calculate dynamic stop and target levels
            stop_offset, target_offset = await self.calculate_dynamic_levels()

            # Determine side (0=Buy, 1=Sell)
            side = 0 if direction == "long" else 1

            print(f"Placing {direction.upper()} bracket order:")
            print(f"  Size: {self.position_size} contracts")
            print(f"  Stop Loss: {stop_offset} points")
            print(f"  Take Profit: {target_offset} points")

            # Place bracket order
            result = await self.suite["MNQ"].orders.place_bracket_order(
                contract_id=self.suite["MNQ"].instrument_info.id,
                side=side,
                size=self.position_size,
                entry_price=None,
                stop_loss_price=float(stop_offset),
                take_profit_price=float(target_offset),
            )

            print("Bracket order placed successfully:")
            print(f"  Main Order ID: {result.entry_order_id}")
            print(f"  Stop Order ID: {result.stop_order_id}")
            print(f"  Target Order ID: {result.target_order_id}")

            self.active_orders.append(result)
            return result

        except Exception as e:
            print(f"Failed to place bracket order: {e}")
            return None

    async def monitor_orders(self):
        """Monitor active orders and handle fills/cancellations."""
        for bracket in self.active_orders[:]:  # Copy list to modify during iteration
            try:
                if bracket is None:
                    continue

                # Check main order status
                main_status = await self.suite["MNQ"].orders.get_tracked_order_status(
                    str(bracket.entry_order_id)
                )

                if main_status is None:
                    continue

                if main_status["status"] == "Filled":
                    print(
                        f"Main order {bracket.entry_order_id} filled at ${main_status['fill_price']}"
                    )

                elif main_status["status"] in ["Cancelled", "Rejected"]:
                    print(
                        f"Main order {bracket.entry_order_id} {main_status['status']}"
                    )
                    self.active_orders.remove(bracket)

            except Exception as e:
                print(f"Error monitoring order {bracket.entry_order_id}: {e}")


async def main():
    # Create trading suite with required timeframes
    suite = await TradingSuite.create(
        ["MNQ"],
        timeframes=["1min", "5min"],
        initial_days=10,  # Need historical data for indicators
        features=["risk_manager"],
    )

    # Initialize strategy
    strategy = ATRBracketStrategy(suite)

    # Set up event handlers for real-time monitoring
    async def on_new_bar(event):
        if event.data.get("timeframe") == "5min":
            print(f"New 5min bar: ${event.data['close']:.2f}")

            # Check for entry signals
            direction, price = await strategy.check_entry_conditions()
            if direction and len(strategy.active_orders) == 0:  # No active positions
                print(f"Entry signal detected: {direction.upper()} at ${price:.2f}")

                # Confirm with user before placing order
                response = input(f"Place {direction.upper()} bracket order? (y/N): ")
                if response.lower().startswith("y"):
                    await strategy.place_bracket_order(direction)

    async def on_order_filled(event):
        order_data = event.data
        print(
            f"ORDER FILLED: {order_data.get('order_id')} at ${order_data.get('fill_price', 0):.2f}"
        )

    # Register event handlers
    await suite["MNQ"].on(EventType.NEW_BAR, on_new_bar)
    await suite["MNQ"].on(EventType.ORDER_FILLED, on_order_filled)

    print("Advanced Bracket Order Strategy Active")
    print("Monitoring for entry signals on 5-minute bars...")
    print("Press Ctrl+C to exit")

    try:
        while True:
            await asyncio.sleep(5)

            # Monitor active orders
            await strategy.monitor_orders()

            # Display current market info
            current_price = await suite["MNQ"].data.get_current_price()
            active_count = len(strategy.active_orders)
            print(f"Price: ${current_price:.2f} | Active Orders: {active_count}")

    except KeyboardInterrupt:
        print("\nShutting down strategy...")

        # Cancel any remaining orders
        for bracket in strategy.active_orders:
            try:
                await suite["MNQ"].orders.cancel_order(bracket.entry_order_id)
                print(f"Cancelled order {bracket.entry_order_id}")
            except Exception as e:
                print(f"Error cancelling order: {e}")


if __name__ == "__main__":
    asyncio.run(main())
