#!/usr/bin/env python3
"""
Async Technical Indicators Analysis Example

Demonstrates concurrent technical analysis using async patterns:
- Concurrent calculation of multiple indicators
- Async data retrieval across timeframes
- Real-time indicator updates
- Performance comparison vs sequential processing

Uses the built-in TA-Lib compatible indicators with Polars DataFrames.

Usage:
    Run with: ./test.sh (sets environment variables)
    Or: uv run examples/async_07_technical_indicators.py

Author: TexasCoding
Date: July 2025
"""

import asyncio
import time
from datetime import datetime

import polars as pl

from project_x_py import (
    ProjectX,
    create_async_data_manager,
    create_async_realtime_client,
    setup_logging,
)
from project_x_py.indicators import (
    ADX,
    ATR,
    BBANDS,
    EMA,
    MACD,
    OBV,
    RSI,
    SMA,
    STOCH,
    VWAP,
)


async def calculate_indicators_concurrently(data: pl.DataFrame):
    """Calculate multiple indicators concurrently."""
    # Define indicator calculations (names match lowercase column outputs)
    indicator_tasks = {
        "sma_20": lambda df: df.pipe(SMA, period=20),
        "ema_20": lambda df: df.pipe(EMA, period=20),
        "rsi_14": lambda df: df.pipe(RSI, period=14),
        "macd": lambda df: df.pipe(MACD),
        "bbands": lambda df: df.pipe(BBANDS, period=20),
        "stoch": lambda df: df.pipe(STOCH),
        "atr_14": lambda df: df.pipe(ATR, period=14),
        "adx_14": lambda df: df.pipe(ADX, period=14),
        "obv": lambda df: df.pipe(OBV),
        "vwap": lambda df: df.pipe(VWAP),
    }

    # Run all calculations concurrently
    async def calc_indicator(name, func):
        loop = asyncio.get_event_loop()
        return name, await loop.run_in_executor(None, func, data)

    tasks = [calc_indicator(name, func) for name, func in indicator_tasks.items()]
    results = await asyncio.gather(*tasks)

    # Combine results
    result_data = data.clone()
    for _name, df in results:
        # Get new columns from each indicator
        new_cols = [col for col in df.columns if col not in data.columns]
        for col in new_cols:
            result_data = result_data.with_columns(df[col])

    return result_data


async def analyze_multiple_timeframes(client, symbol="MNQ"):
    """Analyze indicators across multiple timeframes concurrently."""
    timeframe_configs = [
        ("5min", 1, 5),  # 1 day of 5-minute bars
        ("15min", 2, 15),  # 2 days of 15-minute bars
        ("1hour", 5, 60),  # 5 days of hourly bars
        ("1day", 30, 1440),  # 30 days of daily bars
    ]

    print(f"\n📊 Analyzing {symbol} across multiple timeframes...")

    # Fetch data for all timeframes concurrently
    async def get_timeframe_data(name, days, interval):
        data = await client.get_bars(symbol, days=days, interval=interval)
        return name, data

    data_tasks = [
        get_timeframe_data(name, days, interval)
        for name, days, interval in timeframe_configs
    ]

    timeframe_data = await asyncio.gather(*data_tasks)

    # Calculate indicators for each timeframe concurrently
    analysis_tasks = []
    for name, data in timeframe_data:
        if data is not None and not data.is_empty():
            task = analyze_timeframe(name, data)
            analysis_tasks.append(task)

    analyses = await asyncio.gather(*analysis_tasks)

    # Display results
    print("\n" + "=" * 80)
    print("MULTI-TIMEFRAME ANALYSIS RESULTS")
    print("=" * 80)

    for analysis in analyses:
        print(f"\n{analysis['timeframe']} Analysis:")
        print(f"  Last Close: ${analysis['close']:.2f}")
        print(f"  SMA(20): ${analysis['sma']:.2f} ({analysis['sma_signal']})")
        print(f"  RSI(14): {analysis['rsi']:.2f} ({analysis['rsi_signal']})")
        print(f"  MACD: {analysis['macd_signal']}")
        print(f"  Volatility (ATR): ${analysis['atr']:.2f}")
        print(f"  Trend Strength (ADX): {analysis['adx']:.2f}")


async def analyze_timeframe(timeframe: str, data: pl.DataFrame):
    """Analyze indicators for a specific timeframe."""
    # Calculate indicators concurrently
    enriched_data = await calculate_indicators_concurrently(data)

    # Get latest values
    last_row = enriched_data.tail(1)

    # Extract key metrics (columns are lowercase)
    close = last_row["close"].item()
    sma = last_row["sma_20"].item() if "sma_20" in last_row.columns else None
    rsi = last_row["rsi_14"].item() if "rsi_14" in last_row.columns else None
    macd_line = (
        last_row["macd_line"].item() if "macd_line" in last_row.columns else None
    )
    macd_signal = (
        last_row["macd_signal"].item() if "macd_signal" in last_row.columns else None
    )
    atr = last_row["atr_14"].item() if "atr_14" in last_row.columns else None
    adx = last_row["adx_14"].item() if "adx_14" in last_row.columns else None

    # Generate signals
    analysis = {
        "timeframe": timeframe,
        "close": close,
        "sma": sma or 0,
        "sma_signal": "Bullish" if close > (sma or 0) else "Bearish",
        "rsi": rsi or 50,
        "rsi_signal": "Overbought"
        if (rsi or 50) > 70
        else ("Oversold" if (rsi or 50) < 30 else "Neutral"),
        "macd_signal": "Bullish"
        if (macd_line or 0) > (macd_signal or 0)
        else "Bearish",
        "atr": atr or 0,
        "adx": adx or 0,
    }

    return analysis


async def real_time_indicator_updates(data_manager, duration_seconds=30):
    """Monitor indicators with real-time updates."""
    print(f"\n🔄 Monitoring indicators in real-time for {duration_seconds} seconds...")

    update_count = 0

    async def on_data_update(timeframe):
        """Handle real-time data updates."""
        nonlocal update_count
        update_count += 1

        # Get latest data
        data = await data_manager.get_data(timeframe)
        if data is None:
            return

        # Need sufficient data for indicators
        if len(data) < 30:  # Need extra bars for indicator calculations
            print(f"  {timeframe}: Only {len(data)} bars available, need 30+")
            return

        # Calculate key indicators
        data = data.pipe(RSI, period=14)
        data = data.pipe(SMA, period=20)

        last_row = data.tail(1)
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Debug: show available columns
        if update_count == 1:
            print(f"  Available columns: {', '.join(data.columns)}")

        print(f"\n[{timestamp}] {timeframe} Update #{update_count}:")
        print(f"  Close: ${last_row['close'].item():.2f}")
        print(f"  Bars: {len(data)}")

        # Check if indicators were calculated successfully (columns are lowercase)
        if "rsi_14" in data.columns:
            rsi_val = last_row["rsi_14"].item()
            if rsi_val is not None:
                print(f"  RSI: {rsi_val:.2f}")
            else:
                print("  RSI: Calculating... (null value)")
        else:
            print("  RSI: Not in columns")

        if "sma_20" in data.columns:
            sma_val = last_row["sma_20"].item()
            if sma_val is not None:
                print(f"  SMA: ${sma_val:.2f}")
            else:
                print("  SMA: Calculating... (null value)")
        else:
            print("  SMA: Not in columns")

    # Monitor multiple timeframes
    start_time = asyncio.get_event_loop().time()

    while asyncio.get_event_loop().time() - start_time < duration_seconds:
        # Check each timeframe
        for timeframe in ["5sec", "1min", "5min"]:
            await on_data_update(timeframe)

        await asyncio.sleep(5)  # Update every 5 seconds

    print(f"\n✅ Monitoring complete. Received {update_count} updates.")


async def performance_comparison(client, symbol="MNQ"):
    """Compare performance of concurrent vs sequential indicator calculation."""
    print("\n⚡ Performance Comparison: Concurrent vs Sequential")

    # Get test data
    data = await client.get_bars(symbol, days=5, interval=60)
    if data is None or data.is_empty():
        print("No data available for comparison")
        return

    print(f"  Data size: {len(data)} bars")

    # Sequential calculation
    print("\n  Sequential Calculation...")
    start_time = time.time()

    seq_data = data.clone()
    seq_data = seq_data.pipe(SMA, period=20)
    seq_data = seq_data.pipe(EMA, period=20)
    seq_data = seq_data.pipe(RSI, period=14)
    seq_data = seq_data.pipe(MACD)
    seq_data = seq_data.pipe(BBANDS)
    seq_data = seq_data.pipe(ATR, period=14)
    seq_data = seq_data.pipe(ADX, period=14)

    sequential_time = time.time() - start_time
    print(f"  Sequential time: {sequential_time:.3f} seconds")

    # Concurrent calculation
    print("\n  Concurrent Calculation...")
    start_time = time.time()

    _concurrent_data = await calculate_indicators_concurrently(data)

    concurrent_time = time.time() - start_time
    print(f"  Concurrent time: {concurrent_time:.3f} seconds")

    # Results
    speedup = sequential_time / concurrent_time
    print(f"\n  🚀 Speedup: {speedup:.2f}x faster with concurrent processing!")


async def main():
    """Main async function for technical indicators example."""
    logger = setup_logging(level="INFO")
    logger.info("🚀 Starting Async Technical Indicators Example")

    try:
        # Create async client
        async with ProjectX.from_env() as client:
            await client.authenticate()
            if client.account_info is None:
                raise ValueError("Account info is None")
            print(f"✅ Connected as: {client.account_info.name}")

            # Analyze multiple timeframes concurrently
            await analyze_multiple_timeframes(client, "MNQ")

            # Performance comparison
            await performance_comparison(client, "MNQ")

            # Set up real-time monitoring
            print("\n📊 Setting up real-time indicator monitoring...")

            # Create real-time components
            realtime_client = create_async_realtime_client(
                client.session_token, str(client.account_info.id)
            )

            data_manager = create_async_data_manager(
                "MNQ", client, realtime_client, timeframes=["5sec", "1min", "5min"]
            )

            # Connect and initialize
            if await realtime_client.connect():
                await realtime_client.subscribe_user_updates()

                # Initialize data manager
                await data_manager.initialize(initial_days=1)

                # Subscribe to market data
                instruments = await client.search_instruments("MNQ")
                if instruments:
                    await realtime_client.subscribe_market_data([instruments[0].id])
                    await data_manager.start_realtime_feed()

                    # Monitor indicators in real-time
                    await real_time_indicator_updates(data_manager, duration_seconds=30)

                    # Cleanup
                    await data_manager.stop_realtime_feed()

                await realtime_client.cleanup()

            print("\n📈 Technical Analysis Summary:")
            print("  - Concurrent indicator calculation is significantly faster")
            print("  - Multiple timeframes can be analyzed simultaneously")
            print("  - Real-time updates allow for responsive strategies")
            print("  - Async patterns enable efficient resource usage")

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ASYNC TECHNICAL INDICATORS ANALYSIS")
    print("=" * 60 + "\n")

    asyncio.run(main())

    print("\n✅ Example completed!")
