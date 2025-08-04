#!/usr/bin/env python3
"""
Async Multi-Timeframe Trading Strategy Example

Demonstrates a complete async multi-timeframe trading strategy using:
- Concurrent analysis across multiple timeframes (15min, 1hr, 4hr)
- Async technical indicator calculations
- Real-time signal generation with async callbacks
- Non-blocking order placement
- Async position management and risk control

⚠️  WARNING: This example can place REAL ORDERS based on strategy signals!

Uses MNQ micro contracts for strategy testing.

Updated for v3.0.0: Uses new TradingSuite for simplified initialization.

Usage:
    Run with: ./test.sh (sets environment variables)
    Or: uv run examples/06_multi_timeframe_strategy.py

Author: TexasCoding
Date: July 2025
"""

import asyncio
import logging
import signal
from datetime import datetime
from typing import TYPE_CHECKING

from project_x_py import (
    TradingSuite,
    setup_logging,
)
from project_x_py.indicators import RSI, SMA
from project_x_py.models import BracketOrderResponse, Position

if TYPE_CHECKING:
    pass


class MultiTimeframeStrategy:
    """
    Async multi-timeframe trend following strategy.

    Strategy Logic:
    - Long-term trend: 4hr timeframe (50 SMA)
    - Medium-term trend: 1hr timeframe (20 SMA)
    - Entry timing: 15min timeframe (10 SMA crossover)
    - All timeframes analyzed concurrently
    - Risk management: 2% account risk per trade
    """

    def __init__(
        self,
        trading_suite: TradingSuite,
        symbol: str = "MNQ",
        max_position_size: int = 2,
        risk_percentage: float = 0.02,
    ):
        self.suite = trading_suite
        self.client = trading_suite.client
        self.symbol = symbol
        self.max_position_size = max_position_size
        self.risk_percentage = risk_percentage

        # Extract components
        self.data_manager = trading_suite.data
        self.order_manager = trading_suite.orders
        self.position_manager = trading_suite.positions
        self.orderbook = trading_suite.orderbook

        # Strategy state
        self.is_running = False
        self.signal_count = 0
        self.last_signal_time = None

        # Async lock for thread safety
        self.strategy_lock = asyncio.Lock()

        self.logger = logging.getLogger(__name__)

    async def analyze_timeframes_concurrently(self):
        """Analyze all timeframes concurrently for maximum efficiency."""
        # Create tasks for each timeframe analysis
        tasks = {
            "4hr": self._analyze_longterm_trend(),
            "1hr": self._analyze_medium_trend(),
            "15min": self._analyze_short_term(),
            "orderbook": self._analyze_orderbook(),
        }

        # Run all analyses concurrently
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        # Map results back to timeframes
        analysis = {}
        for (timeframe, _), result in zip(tasks.items(), results, strict=False):
            if isinstance(result, Exception):
                self.logger.error(f"Error analyzing {timeframe}: {result}")
                analysis[timeframe] = None
            else:
                analysis[timeframe] = result

        return analysis

    async def _analyze_longterm_trend(self):
        """Analyze 4hr timeframe for overall trend direction."""
        data = await self.data_manager.get_data("4hr")
        if data is None or len(data) < 50:
            return None

        # Calculate indicators
        data = data.pipe(SMA, period=50)

        last_close = data["close"].tail(1).item()
        last_sma = data["sma_50"].tail(1).item()

        return {
            "trend": "bullish" if last_close > last_sma else "bearish",
            "strength": abs(last_close - last_sma) / last_sma,
            "close": last_close,
            "sma": last_sma,
        }

    async def _analyze_medium_trend(self):
        """Analyze 1hr timeframe for medium-term trend."""
        data = await self.data_manager.get_data("1hr")
        if data is None or len(data) < 20:
            return None

        # Calculate indicators
        data = data.pipe(SMA, period=20)
        data = data.pipe(RSI, period=14)

        last_close = data["close"].tail(1).item()
        last_sma = data["sma_20"].tail(1).item()
        last_rsi = data["rsi_14"].tail(1).item()

        return {
            "trend": "bullish" if last_close > last_sma else "bearish",
            "momentum": "strong" if last_rsi > 50 else "weak",
            "rsi": last_rsi,
            "close": last_close,
            "sma": last_sma,
        }

    async def _analyze_short_term(self):
        """Analyze 15min timeframe for entry signals."""
        data = await self.data_manager.get_data("15min")
        if data is None or len(data) < 20:
            return None

        # Calculate fast and slow SMAs
        data = data.pipe(SMA, period=10)
        data = data.rename({"sma_10": "sma_fast"})
        data = data.pipe(SMA, period=20)
        data = data.rename({"sma_20": "sma_slow"})

        # Get last two bars for crossover detection
        recent = data.tail(2)

        prev_fast = recent["sma_fast"].item(0)
        curr_fast = recent["sma_fast"].item(1)
        prev_slow = recent["sma_slow"].item(0)
        curr_slow = recent["sma_slow"].item(1)

        # Detect crossovers
        bullish_cross = prev_fast <= prev_slow and curr_fast > curr_slow
        bearish_cross = prev_fast >= prev_slow and curr_fast < curr_slow

        return {
            "signal": "buy" if bullish_cross else ("sell" if bearish_cross else None),
            "fast_sma": curr_fast,
            "slow_sma": curr_slow,
            "close": recent["close"].item(1),
        }

    async def _analyze_orderbook(self):
        """Analyze orderbook for market microstructure."""
        # Check if orderbook is available
        if not self.orderbook:
            return None

        best_bid_ask = await self.orderbook.get_best_bid_ask()
        imbalance = await self.orderbook.get_market_imbalance()

        return {
            "spread": best_bid_ask.get("spread", 0),
            "spread_percentage": best_bid_ask.get("spread_percentage", 0),
            "imbalance": imbalance.get("ratio", 0),
            "imbalance_side": imbalance.get("side", "neutral"),
        }

    async def generate_trading_signal(self):
        """Generate trading signal based on multi-timeframe analysis."""
        async with self.strategy_lock:
            # Analyze all timeframes concurrently
            analysis = await self.analyze_timeframes_concurrently()

            # Extract results
            longterm = analysis.get("4hr")
            medium = analysis.get("1hr")
            shortterm = analysis.get("15min")
            orderbook = analysis.get("orderbook")

            # Check if we have all required data
            if not longterm or not medium or not shortterm:
                return None

            # Strategy logic: All timeframes must align
            signal = None
            confidence = 0.0

            if shortterm["signal"] == "buy":
                if longterm["trend"] == "bullish" and medium["trend"] == "bullish":
                    signal = "BUY"
                    confidence = min(longterm["strength"] * 100, 100)

                    # Boost confidence if momentum is strong
                    if medium["momentum"] == "strong":
                        confidence = min(confidence * 1.2, 100)

            elif (
                shortterm["signal"] == "sell"
                and longterm["trend"] == "bearish"
                and medium["trend"] == "bearish"
            ):
                signal = "SELL"
                confidence = min(longterm["strength"] * 100, 100)

                # Boost confidence if momentum is strong
                if medium["momentum"] == "weak":
                    confidence = min(confidence * 1.2, 100)

            if signal:
                self.signal_count += 1
                self.last_signal_time = datetime.now()

                return {
                    "signal": signal,
                    "confidence": confidence,
                    "price": shortterm["close"],
                    "spread": orderbook["spread"] if orderbook else None,
                    "timestamp": self.last_signal_time,
                    "analysis": {
                        "longterm": longterm,
                        "medium": medium,
                        "shortterm": shortterm,
                        "orderbook": orderbook,
                    },
                }

            return None

    async def execute_signal(self, signal_data: dict):
        """Execute trading signal with proper risk management."""
        # Check current position
        positions: list[Position] = await self.position_manager.get_all_positions()
        current_position = next(
            (pos for pos in positions if pos.contractId == self.symbol), None
        )

        # Position size limits
        if current_position and abs(current_position.size) >= self.max_position_size:
            self.logger.info("Max position size reached, skipping signal")
            return

        # Get account info for position sizing
        account_balance = (
            float(self.client.account_info.balance) if self.client.account_info else 0
        )

        # Calculate position size based on risk
        entry_price = signal_data["price"]
        stop_distance = entry_price * 0.01  # 1% stop loss

        if signal_data["signal"] == "BUY":
            stop_price = entry_price - stop_distance
            side = 0  # Buy
        else:
            stop_price = entry_price + stop_distance
            side = 1  # Sell

        # Simple position sizing based on risk
        # Calculate the dollar risk per contract
        tick_size = 0.25  # MNQ tick size
        tick_value = 0.50  # MNQ tick value

        # Risk in ticks
        risk_in_ticks = stop_distance / tick_size
        # Risk in dollars per contract
        risk_per_contract = risk_in_ticks * tick_value

        # Position size based on account risk
        max_risk_dollars = account_balance * self.risk_percentage
        position_size = int(max_risk_dollars / risk_per_contract)

        # Limit position size
        position_size = min(position_size, self.max_position_size)

        if position_size == 0:
            self.logger.warning("Position size calculated as 0, skipping order")
            return

        # Get active contract
        instrument = await self.client.get_instrument(self.symbol)
        if not instrument:
            self.logger.error(f"Could not find instrument {self.symbol}")
            return

        contract_id = instrument.id

        # Place bracket order
        self.logger.info(
            f"Placing {signal_data['signal']} order: "
            f"Size={position_size}, Entry=${entry_price:.2f}, Stop=${stop_price:.2f}"
        )

        # Calculate take profit (2:1 risk/reward)
        if side == 0:  # Buy
            take_profit = entry_price + (2 * stop_distance)
        else:  # Sell
            take_profit = entry_price - (2 * stop_distance)

        try:
            response = await self.order_manager.place_bracket_order(
                contract_id=contract_id,
                side=side,
                size=position_size,
                entry_price=entry_price,
                stop_loss_price=stop_price,
                take_profit_price=take_profit,
            )

            if not isinstance(response, BracketOrderResponse):
                self.logger.error(f"❌ Unexpected order type: {type(response)}")
                return

            if response and response.success:
                self.logger.info(
                    f"✅ Order placed successfully: {response.entry_order_id}"
                )
            else:
                self.logger.error("❌ Order placement failed")

        except Exception as e:
            self.logger.error(f"Error placing order: {e}")

    async def run_strategy_loop(self, check_interval: int = 60):
        """Run the strategy loop with specified check interval."""
        self.is_running = True
        self.logger.info(
            f"🚀 Strategy started, checking every {check_interval} seconds"
        )

        while self.is_running:
            try:
                # Generate signal
                signal = await self.generate_trading_signal()

                if signal:
                    self.logger.info(
                        f"📊 Signal generated: {signal['signal']} "
                        f"(Confidence: {signal['confidence']:.1f}%)"
                    )

                    # Execute if confidence is high enough
                    if signal["confidence"] >= 70:
                        await self.execute_signal(signal)
                    else:
                        self.logger.info("Signal confidence too low, skipping")

                # Display strategy status
                await self._display_status()

                # Wait for next check
                await asyncio.sleep(check_interval)

            except Exception as e:
                self.logger.error(f"Strategy error: {e}", exc_info=True)
                await asyncio.sleep(check_interval)

    async def _display_status(self):
        """Display current strategy status."""
        positions = await self.position_manager.get_all_positions()
        portfolio_pnl = await self.position_manager.get_portfolio_pnl()

        print(f"\n📊 Strategy Status at {datetime.now().strftime('%H:%M:%S')}")
        print(f"  Signals Generated: {self.signal_count}")
        print(f"  Open Positions: {len(positions)}")
        if isinstance(portfolio_pnl, dict):
            total_pnl = portfolio_pnl.get("total_pnl", 0)
            print(f"  Portfolio P&L: ${total_pnl:.2f}")
        else:
            print(f"  Portfolio P&L: ${portfolio_pnl:.2f}")

        if self.last_signal_time:
            time_since = (datetime.now() - self.last_signal_time).seconds
            print(f"  Last Signal: {time_since}s ago")

    def stop(self):
        """Stop the strategy."""
        self.is_running = False
        self.logger.info("🛑 Strategy stopped")


async def main():
    """Main async function for multi-timeframe strategy."""
    logger = setup_logging(level="INFO")
    logger.info("🚀 Starting Async Multi-Timeframe Strategy (v3.0.0)")

    # Signal handler for graceful shutdown
    stop_event = asyncio.Event()

    def signal_handler(signum, frame):
        print("\n⚠️  Shutdown signal received...")
        stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Create TradingSuite v3 with multi-timeframe support
        print("\n🏗️ Creating TradingSuite v3 with multi-timeframe support...")
        suite = await TradingSuite.create(
            instrument="MNQ",
            timeframes=["15min", "1hr", "4hr"],
            features=["orderbook", "realtime_tracking"],
            initial_days=5,
        )

        print("✅ TradingSuite initialized successfully!")

        account = suite.client.account_info
        if not account:
            print("❌ No account info found")
            await suite.disconnect()
            return

        print(f"   Connected as: {account.name}")
        print(f"   Account ID: {account.id}")
        print(f"   Balance: ${account.balance:,.2f}")

        # Create and configure strategy
        strategy = MultiTimeframeStrategy(
            trading_suite=suite,
            symbol="MNQ",
            max_position_size=2,
            risk_percentage=0.02,
        )

        print("\n" + "=" * 60)
        print("ASYNC MULTI-TIMEFRAME STRATEGY ACTIVE")
        print("=" * 60)
        print("\nStrategy Configuration:")
        print("  Symbol: MNQ")
        print("  Max Position Size: 2 contracts")
        print("  Risk per Trade: 2%")
        print("  Timeframes: 15min, 1hr, 4hr")
        print("\n⚠️  This strategy can place REAL ORDERS!")
        print("Press Ctrl+C to stop\n")

        # Run strategy until stopped
        strategy_task = asyncio.create_task(
            strategy.run_strategy_loop(check_interval=30)
        )

        # Wait for stop signal
        await stop_event.wait()

        # Stop strategy
        strategy.stop()
        strategy_task.cancel()

        # Cleanup
        print("\n🧹 Cleaning up...")
        await suite.disconnect()

        print("\n✅ Strategy stopped successfully")

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ASYNC MULTI-TIMEFRAME TRADING STRATEGY")
    print("=" * 60 + "\n")

    asyncio.run(main())
