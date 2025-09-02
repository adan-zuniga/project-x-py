#!/usr/bin/env python
"""
Multi-timeframe real-time data synchronization
"""

import asyncio
from collections import defaultdict
from datetime import datetime

from project_x_py import EventType, TradingSuite
from project_x_py.indicators import RSI, SMA


class MultiTimeframeDataProcessor:
    def __init__(self, suite: TradingSuite):
        self.suite = suite
        self.timeframes = ["1min", "5min", "15min"]
        self.data_cache = defaultdict(list)
        self.last_analysis = defaultdict(dict)
        self.analysis_count = 0

    async def process_new_bar(self, event):
        """Process incoming bar data for all timeframes."""
        bar_data = event.data.get("data", event.data)
        timeframe = event.data.get("timeframe", "unknown")

        if timeframe not in self.timeframes:
            return

        # Store the bar
        self.data_cache[timeframe].append(bar_data)

        # Keep only recent bars (memory management)
        if len(self.data_cache[timeframe]) > 200:
            self.data_cache[timeframe] = self.data_cache[timeframe][-100:]

        print(
            f"New {timeframe} bar: ${bar_data['close']:.2f} @ {bar_data.get('timestamp')}"
        )

        # Perform analysis on this timeframe
        await self.analyze_timeframe(timeframe)

        # Check for multi-timeframe confluence
        if timeframe == "1min":  # Trigger confluence check on fastest timeframe
            await self.check_confluence()

    async def analyze_timeframe(self, timeframe: str):
        """Analyze a specific timeframe with technical indicators."""
        try:
            # Get fresh data from suite
            bars = await self.suite["MNQ"].data.get_data(timeframe)

            if bars is None:
                return

            if len(bars) < 50:  # Need enough data for indicators
                return

            # Calculate indicators
            bars = bars.pipe(SMA, period=20).pipe(RSI, period=14)

            current_price = bars["close"][-1]
            current_sma = bars["sma_20"][-1]
            current_rsi = bars["rsi_14"][-1]

            # Determine trend and momentum
            trend = "bullish" if current_price > current_sma else "bearish"
            momentum = (
                "strong"
                if (trend == "bullish" and current_rsi > 50)
                or (trend == "bearish" and current_rsi < 50)
                else "weak"
            )

            # Store analysis
            self.last_analysis[timeframe] = {
                "price": current_price,
                "sma_20": current_sma,
                "rsi": current_rsi,
                "trend": trend,
                "momentum": momentum,
                "timestamp": datetime.now(),
            }

            print(
                f"  {timeframe} Analysis - Trend: {trend}, RSI: {current_rsi:.1f}, Momentum: {momentum}"
            )

        except Exception as e:
            print(f"Error analyzing {timeframe}: {e}")

    async def check_confluence(self):
        """Check for confluence across all timeframes."""
        self.analysis_count += 1

        # Only check confluence every 5th analysis to avoid spam
        if self.analysis_count % 5 != 0:
            return

        if len(self.last_analysis) < len(self.timeframes):
            return

        # Count bullish/bearish signals
        bullish_count = sum(
            1
            for analysis in self.last_analysis.values()
            if analysis.get("trend") == "bullish"
        )
        bearish_count = sum(
            1
            for analysis in self.last_analysis.values()
            if analysis.get("trend") == "bearish"
        )

        # Check for strong confluence
        total_timeframes = len(self.last_analysis)

        if bullish_count >= total_timeframes * 0.8:  # 80% agreement
            print(
                f"\n= BULLISH CONFLUENCE DETECTED ({bullish_count}/{total_timeframes})"
            )
            await self.display_confluence_analysis("BULLISH")
        elif bearish_count >= total_timeframes * 0.8:
            print(
                f"\n=4 BEARISH CONFLUENCE DETECTED ({bearish_count}/{total_timeframes})"
            )
            await self.display_confluence_analysis("BEARISH")

    async def display_confluence_analysis(self, signal_type: str):
        """Display detailed confluence analysis."""
        print(f"{signal_type} CONFLUENCE ANALYSIS:")
        print("-" * 40)

        for tf, analysis in self.last_analysis.items():
            trend_emoji = "=" if analysis["trend"] == "bullish" else "="
            momentum_emoji = "=" if analysis["momentum"] == "strong" else "="

            print(
                f"  {tf:>5} {trend_emoji} {analysis['trend']:>8} | RSI: {analysis['rsi']:>5.1f} | {momentum_emoji} {analysis['momentum']}"
            )

        print("-" * 40)

        # Get current market data
        current_price = await self.suite["MNQ"].data.get_current_price()
        print(f"Current Price: ${current_price:.2f}")
        print()


async def main():
    # Create suite with multiple timeframes
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["1min", "5min", "15min"],
        initial_days=3,  # Enough data for indicators
    )

    processor = MultiTimeframeDataProcessor(suite)

    # Register event handler
    await suite.on(EventType.NEW_BAR, processor.process_new_bar)

    print("Multi-Timeframe Data Processor Active")
    print("Monitoring 1min, 5min, and 15min timeframes...")
    print("Press Ctrl+C to exit")

    try:
        while True:
            await asyncio.sleep(15)

            # Display periodic status
            print(f"\nStatus Update - {datetime.now().strftime('%H:%M:%S')}")
            for tf in processor.timeframes:
                cached_bars = len(processor.data_cache[tf])
                analysis = processor.last_analysis.get(tf, {})
                trend = analysis.get("trend", "unknown")
                rsi = analysis.get("rsi", 0)
                print(
                    f"  {tf}: {cached_bars} bars cached, {trend} trend, RSI: {rsi:.1f}"
                )

    except KeyboardInterrupt:
        print("\nShutting down multi-timeframe processor...")


if __name__ == "__main__":
    asyncio.run(main())
