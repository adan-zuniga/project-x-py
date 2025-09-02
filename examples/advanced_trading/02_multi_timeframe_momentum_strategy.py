#!/usr/bin/env python
"""
Multi-timeframe momentum strategy with confluence analysis
"""

import asyncio
from decimal import Decimal

from project_x_py import EventType, TradingSuite
from project_x_py.indicators import ATR, EMA, MACD, RSI
from project_x_py.models import BracketOrderResponse


class MultiTimeframeMomentumStrategy:
    def __init__(self, suite: TradingSuite):
        self.suite = suite
        self.position_size = 1
        self.risk_per_trade = Decimal("0.02")  # 2% risk per trade
        self.active_position = None

    async def analyze_timeframe(self, timeframe: str):
        """Analyze a specific timeframe for momentum signals."""
        bars = await self.suite["MNQ"].data.get_data(timeframe)

        if bars is None:
            return None

        if len(bars) < 50:  # Need sufficient data
            return None

        # Calculate indicators
        rsi = bars.pipe(RSI, period=14)
        macd_result = bars.pipe(MACD, fast_period=12, slow_period=26, signal_period=9)
        ema_20 = bars.pipe(EMA, period=20)
        ema_50 = bars.pipe(EMA, period=50)

        current_price = bars["close"][-1]
        current_rsi = rsi["rsi_14"][-1]
        current_macd = macd_result["macd"][-1]
        macd_signal = macd_result["signal"][-1]
        current_ema_20 = ema_20["ema_20"][-1]
        current_ema_50 = ema_50["ema_50"][-1]

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

    async def check_confluence(self):
        """Check for confluence across multiple timeframes."""
        # Analyze all timeframes
        tf_5min = await self.analyze_timeframe("5min")
        tf_15min = await self.analyze_timeframe("15min")  # Add 15min if available
        tf_1hr = await self.analyze_timeframe("1hr")  # Add 1hr if available

        if tf_5min is None:
            return None, None

        analyses = [tf for tf in [tf_5min, tf_15min, tf_1hr] if tf is not None]

        if len(analyses) < 2:
            return None, None

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

        # Require confluence (majority agreement)
        if (
            bullish_signals >= 2 and tf_5min["rsi"] < 70
        ):  # Not overbought on entry timeframe
            return "long", analyses
        elif (
            bearish_signals >= 2 and tf_5min["rsi"] > 30
        ):  # Not oversold on entry timeframe
            return "short", analyses

        return None, analyses

    async def calculate_position_size(self, entry_price: float, stop_loss: float):
        """Calculate position size based on risk management."""
        account_info = self.suite.client.get_account_info()
        account_balance = float(account_info.balance)

        # Calculate risk amount
        risk_amount = account_balance * float(self.risk_per_trade)

        # Calculate risk per contract
        price_diff = abs(entry_price - stop_loss)
        risk_per_contract = price_diff * 20  # MNQ multiplier

        # Calculate position size
        calculated_size = int(risk_amount / risk_per_contract)
        return max(1, min(calculated_size, 5))  # Between 1-5 contracts

    async def place_momentum_trade(self, direction: str, analyses: list):
        """Place a trade based on momentum confluence."""
        try:
            current_price = analyses[0]["price"]  # Use 5min price

            # Calculate ATR-based stop loss
            bars_5min = await self.suite.data.get_data("5min")
            atr = bars_5min.pipe(ATR, period=14)
            current_atr = float(atr[-1])

            # Dynamic stops based on volatility
            if direction == "long":
                stop_loss = current_price - (current_atr * 2)
                take_profit = current_price + (current_atr * 3)
                side = 0  # Buy
            else:
                stop_loss = current_price + (current_atr * 2)
                take_profit = current_price - (current_atr * 3)
                side = 1  # Sell

            # Calculate position size
            position_size = await self.calculate_position_size(current_price, stop_loss)

            print(f"\n{direction.upper()} Momentum Trade Setup:")
            print(f"  Entry Price: ${current_price:.2f}")
            print(f"  Stop Loss: ${stop_loss:.2f}")
            print(f"  Take Profit: ${take_profit:.2f}")
            print(f"  Position Size: {position_size} contracts")
            print(
                f"  Risk/Reward: {abs(take_profit - current_price) / abs(current_price - stop_loss):.2f}:1"
            )

            # Display confluence analysis
            print("\nConfluence Analysis:")
            for analysis in analyses:
                print(
                    f"  {analysis['timeframe']}: {analysis['trend']} trend, {analysis['momentum']} momentum, RSI: {analysis['rsi']:.1f}"
                )

            # Confirm trade
            response = input(f"\nPlace {direction.upper()} momentum trade? (y/N): ")
            if not response.lower().startswith("y"):
                return None

            # Place bracket order
            result: BracketOrderResponse = await self.suite[
                "MNQ"
            ].orders.place_bracket_order(
                contract_id=self.suite["MNQ"].instrument_info.id,
                side=side,
                size=position_size,
                entry_price=None,
                stop_loss_price=stop_loss,
                take_profit_price=take_profit,
            )

            self.active_position = {
                "direction": direction,
                "entry_price": current_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "size": position_size,
                "bracket": result,
            }

            print("Momentum trade placed successfully!")
            return result

        except Exception as e:
            print(f"Failed to place momentum trade: {e}")
            return None


async def main():
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
    async def on_new_bar(event):
        if event.data.get("timeframe") == "5min":  # Only act on 5min bars
            # Check for confluence signals
            direction, analyses = await strategy.check_confluence()

            if analyses is None:
                return

            if direction and not strategy.active_position:
                print(f"\n=== MOMENTUM CONFLUENCE DETECTED: {direction.upper()} ===")
                await strategy.place_momentum_trade(direction, analyses)
            elif analyses:
                # Display current analysis
                print("\nCurrent Analysis (no confluence):")
                for analysis in analyses:
                    if analysis:
                        print(
                            f"  {analysis['timeframe']}: {analysis['trend']}/{analysis['momentum']} (RSI: {analysis['rsi']:.1f})"
                        )

    async def on_order_filled(event):
        if strategy.active_position:
            order_id = event.data.get("order_id")
            fill_price = event.data.get("fill_price", 0)

            # Check if it's our stop or target
            bracket: BracketOrderResponse = strategy.active_position["bracket"]
            if bracket is None:
                return

            if order_id in [bracket.stop_order_id, bracket.target_order_id]:
                result = (
                    "STOP LOSS" if order_id == bracket.stop_order_id else "TAKE PROFIT"
                )
                print(f"\n{result} HIT: Order {order_id} filled at ${fill_price:.2f}")
                strategy.active_position = None  # Clear position

    # Register events
    await mnq_context.on(EventType.NEW_BAR, on_new_bar)
    await mnq_context.on(EventType.ORDER_FILLED, on_order_filled)

    print("Multi-Timeframe Momentum Strategy Active")
    print("Analyzing 5min, 15min, and 1hr timeframes for confluence...")
    print("Press Ctrl+C to exit")

    try:
        while True:
            await asyncio.sleep(10)

            # Display status
            current_price = await mnq_context.data.get_current_price()
            position_status = "ACTIVE" if strategy.active_position else "FLAT"
            print(f"Price: ${current_price:.2f} | Position: {position_status}")

    except KeyboardInterrupt:
        print("\nShutting down strategy...")

        # Cancel active orders if any
        if strategy.active_position:
            bracket: BracketOrderResponse = strategy.active_position["bracket"]
            try:
                await mnq_context.orders.cancel_order(bracket.entry_order_id)
                print("Cancelled active orders")
            except Exception as e:
                print(f"Error cancelling orders: {e}")


if __name__ == "__main__":
    asyncio.run(main())
