#!/usr/bin/env python3
"""
Simplified trading strategy example using TradingSuite v3.

This example demonstrates how TradingSuite dramatically reduces boilerplate code
compared to the old factory functions.

Updated for v3.0.0: Uses new TradingSuite for simplified initialization.
"""

import asyncio
import logging
import signal
from datetime import datetime

from project_x_py import TradingSuite, setup_logging
from project_x_py.indicators import RSI, SMA
from project_x_py.models import Position


class SimplifiedStrategy:
    """A simple momentum strategy using TradingSuite v3."""

    def __init__(self, trading_suite: TradingSuite, symbol: str):
        self.suite = trading_suite
        self.symbol = symbol
        self.instrument = trading_suite[symbol].instrument_info
        self.data_manager = trading_suite[symbol].data
        self.order_manager = trading_suite[symbol].orders
        self.position_manager = trading_suite[symbol].positions
        self.is_running = False
        self.logger = logging.getLogger(__name__)

    async def check_signal(self):
        """Check for trading signals."""
        # Get 5-minute data
        if not self.data_manager:
            raise ValueError("Data manager not initialized")
        data = await self.data_manager.get_data(timeframe="5min", bars=50)
        if data is None or len(data) < 50:
            return None

        # Calculate indicators
        data = data.pipe(SMA, period=20).pipe(RSI, period=14)

        last_close = data["close"].tail(1).item()
        last_sma = data["sma_20"].tail(1).item()
        last_rsi = data["rsi_14"].tail(1).item()

        # Simple momentum signal
        if last_close > last_sma and last_rsi < 70:
            return {"signal": "BUY", "confidence": min(80, last_rsi)}
        elif last_close < last_sma and last_rsi > 30:
            return {"signal": "SELL", "confidence": min(80, 100 - last_rsi)}

        return None

    async def run_loop(self, check_interval: int = 30):
        """Run the strategy loop."""
        self.is_running = True
        self.logger.info(f"🚀 Strategy started for {self.symbol}")

        while self.is_running:
            try:
                signal = await self.check_signal()
                if signal:
                    self.logger.info(
                        f"📊 Signal: {signal['signal']} "
                        f"(Confidence: {signal['confidence']:.1f}%)"
                    )

                # Display status
                positions: list[
                    Position
                ] = await self.position_manager.get_all_positions()
                print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')}")
                print(f"  Positions: {len(positions)}")

                await asyncio.sleep(check_interval)

            except Exception as e:
                self.logger.error(f"Strategy error: {e}")
                await asyncio.sleep(check_interval)

    def stop(self):
        """Stop the strategy."""
        self.is_running = False
        self.logger.info("🛑 Strategy stopped")


async def main():
    """Main function demonstrating simplified setup."""
    logger = setup_logging(level="INFO")

    # Signal handler for graceful shutdown
    stop_event = asyncio.Event()

    def signal_handler(_signum, _frame):
        print("\n⚠️  Shutdown signal received...")
        stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)

    try:
        # LOOK HOW SIMPLE THIS IS NOW! 🎉
        # One line to create a fully initialized trading suite!
        suite = await TradingSuite.create(
            "MNQ",
            timeframes=["5min", "15min", "1hr"],
            initial_days=3,
        )

        print("✅ TradingSuite v3 initialized!")

        account = suite.client.account_info
        if not account:
            print("❌ No account info found")
            await suite.disconnect()
            return

        print(f"   Connected as: {account.name}")

        # That's it! Everything is connected and ready to use:
        # ✅ Client authenticated
        # ✅ Realtime client connected
        # ✅ User updates subscribed
        # ✅ Historical data loaded
        # ✅ Market data subscribed
        # ✅ Realtime feeds started
        # ✅ All components wired together

        # Get the instrument info
        instrument = suite["MNQ"].instrument_info

        print("\n🎯 Trading suite fully initialized!")
        print(f"  Instrument: {instrument.symbolId if instrument else 'Unknown'}")
        print(f"  Contract: {instrument.activeContract if instrument else 'Unknown'}")
        print("  Components: All connected and subscribed")

        # Create and run strategy
        strategy = SimplifiedStrategy(suite, "MNQ")

        # Run until stopped
        strategy_task = asyncio.create_task(strategy.run_loop())
        await stop_event.wait()

        # Cleanup
        strategy.stop()
        strategy_task.cancel()

        # Disconnect TradingSuite
        await suite.disconnect()

        print("\n✅ Clean shutdown completed")

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SIMPLIFIED TRADING STRATEGY EXAMPLE (v3.0.0)")
    print("=" * 60)
    print("\nThis example shows TradingSuite v3 features:")
    print("- Single line to create trading suite")
    print("- Automatic connection and subscription handling")
    print("- No boilerplate setup code needed!")
    print("- Everything wired together automatically")
    print("\nPress Ctrl+C to stop\n")

    asyncio.run(main())
