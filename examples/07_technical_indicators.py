#!/usr/bin/env python3
"""
Technical Indicators Analysis Example

Demonstrates concurrent technical analysis using async patterns:
- Concurrent calculation of multiple indicators
- Async data retrieval across timeframes
- Real-time indicator updates
- Performance comparison vs sequential processing

Uses the built-in TA-Lib compatible indicators with Polars DataFrames.

Updated for v3.0.0: Uses new TradingSuite for simplified initialization.

Usage:
    Run with: ./test.sh (sets environment variables)
    Or: uv run examples/07_technical_indicators.py

Author: TexasCoding
Date: July 2025
"""

import asyncio
import sys
import time
from collections.abc import Callable
from datetime import datetime

import polars as pl

from project_x_py import (
    TradingSuite,
    setup_logging,
)
from project_x_py.indicators import (
    ADX,
    AROON,
    ATR,
    BBANDS,
    CCI,
    EMA,
    FVG,
    MACD,
    MFI,
    OBV,
    ORDERBLOCK,
    PPO,
    RSI,
    SMA,
    STOCH,
    ULTOSC,
    VWAP,
    WAE,
    WILLR,
)
from project_x_py.realtime_data_manager.core import RealtimeDataManager


async def calculate_indicators_concurrently(data: pl.DataFrame):
    """Calculate multiple indicators concurrently."""
    # Define indicator calculations (names match lowercase column outputs)
    indicator_tasks = {
        # Overlap Studies
        "sma_20": lambda df: df.pipe(SMA, period=20),
        "ema_20": lambda df: df.pipe(EMA, period=20),
        "bbands": lambda df: df.pipe(BBANDS, period=20),
        # Momentum Indicators
        "rsi_14": lambda df: df.pipe(RSI, period=14),
        "macd": lambda df: df.pipe(MACD),
        "stoch": lambda df: df.pipe(STOCH),
        "cci_20": lambda df: df.pipe(CCI, period=20),
        "willr_14": lambda df: df.pipe(WILLR, period=14),
        "ppo": lambda df: df.pipe(PPO),
        "aroon": lambda df: df.pipe(AROON, period=14),
        "ultosc": lambda df: df.pipe(ULTOSC),
        # Volatility Indicators
        "atr_14": lambda df: df.pipe(ATR, period=14),
        "adx_14": lambda df: df.pipe(ADX, period=14),
        # Volume Indicators
        "obv": lambda df: df.pipe(OBV),
        "vwap": lambda df: df.pipe(VWAP),
        "mfi_14": lambda df: df.pipe(MFI, period=14),
        # Pattern Indicators
        "fvg": lambda df: df.pipe(FVG, min_gap_size=0.001),
        "orderblock": lambda df: df.pipe(ORDERBLOCK, min_volume_percentile=75),
        "wae": lambda df: df.pipe(WAE),
    }

    # Run all calculations concurrently
    async def calc_indicator(
        name: str, func: Callable[[pl.DataFrame], pl.DataFrame]
    ) -> tuple[str, pl.DataFrame]:
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


async def analyze_multiple_timeframes(suite: TradingSuite, symbol: str = "MNQ") -> None:
    """Analyze indicators across multiple timeframes concurrently."""
    timeframe_configs = [
        ("5min", 7, 5),  # 1 day of 5-minute bars
        ("15min", 10, 15),  # 2 days of 15-minute bars
        ("1hour", 20, 60),  # 5 days of hourly bars
        ("1day", 102, 1440),  # 30 days of daily bars
    ]

    print(f"\n📊 Analyzing {symbol} across multiple timeframes...")

    # Fetch data for all timeframes concurrently
    async def get_timeframe_data(
        name: str, days: int, interval: int
    ) -> tuple[str, pl.DataFrame | None]:
        data = await suite.client.get_bars(symbol, days=days, interval=interval)
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

        # Trend Indicators
        print("\n  📈 Trend Indicators:")
        print(f"    SMA(20): ${analysis['sma']:.2f} ({analysis['sma_signal']})")
        print(f"    ADX(14): {analysis['adx']:.2f} (Trend Strength)")
        print(f"    Aroon: {analysis['aroon_trend']}")

        # Momentum Indicators
        print("\n  ⚡ Momentum Indicators:")
        print(f"    RSI(14): {analysis['rsi']:.2f} ({analysis['rsi_signal']})")
        print(f"    CCI(20): {analysis['cci']:.2f} ({analysis['cci_signal']})")
        print(f"    Williams %R: {analysis['willr']:.2f} ({analysis['willr_signal']})")
        print(f"    MFI(14): {analysis['mfi']:.2f} ({analysis['mfi_signal']})")
        print(f"    MACD: {analysis['macd_signal']}")

        # Volatility
        print("\n  📊 Volatility:")
        print(f"    ATR(14): ${analysis['atr']:.2f}")

        # Pattern Recognition
        print("\n  🎯 Pattern Recognition:")
        print(f"    Fair Value Gap: {analysis['fvg']}")
        print(f"    Order Block: {analysis['orderblock']}")
        print(f"    WAE Signal: {analysis['wae_signal']}")


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

    # New indicators
    cci = last_row["cci_20"].item() if "cci_20" in last_row.columns else None
    willr = last_row["willr_14"].item() if "willr_14" in last_row.columns else None
    aroon_up = last_row["aroon_up"].item() if "aroon_up" in last_row.columns else None
    aroon_down = (
        last_row["aroon_down"].item() if "aroon_down" in last_row.columns else None
    )
    mfi = last_row["mfi_14"].item() if "mfi_14" in last_row.columns else None

    # Pattern indicators
    fvg_bullish = (
        last_row["fvg_bullish"].item() if "fvg_bullish" in last_row.columns else False
    )
    fvg_bearish = (
        last_row["fvg_bearish"].item() if "fvg_bearish" in last_row.columns else False
    )
    ob_bullish = (
        last_row["ob_bullish"].item() if "ob_bullish" in last_row.columns else False
    )
    ob_bearish = (
        last_row["ob_bearish"].item() if "ob_bearish" in last_row.columns else False
    )
    wae_trend = (
        last_row["wae_trend"].item() if "wae_trend" in last_row.columns else None
    )
    wae_explosion = (
        last_row["wae_explosion"].item()
        if "wae_explosion" in last_row.columns
        else None
    )

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
        "cci": cci or 0,
        "cci_signal": "Overbought"
        if (cci or 0) > 100
        else ("Oversold" if (cci or 0) < -100 else "Neutral"),
        "willr": willr or -50,
        "willr_signal": "Overbought"
        if (willr or -50) > -20
        else ("Oversold" if (willr or -50) < -80 else "Neutral"),
        "aroon_trend": "Bullish" if (aroon_up or 0) > (aroon_down or 0) else "Bearish",
        "mfi": mfi or 50,
        "mfi_signal": "Overbought"
        if (mfi or 50) > 80
        else ("Oversold" if (mfi or 50) < 20 else "Neutral"),
        "fvg": "Bullish Gap"
        if fvg_bullish
        else ("Bearish Gap" if fvg_bearish else "None"),
        "orderblock": "Bullish OB"
        if ob_bullish
        else ("Bearish OB" if ob_bearish else "None"),
        "wae_signal": "Strong Bullish"
        if (wae_trend or 0) == 1 and (wae_explosion or 0) > 0
        else (
            "Strong Bearish"
            if (wae_trend or 0) == -1 and (wae_explosion or 0) > 0
            else "Neutral"
        ),
    }

    return analysis


async def real_time_indicator_updates(
    data_manager: RealtimeDataManager, duration_seconds: int = 30
) -> None:
    """Monitor indicators with real-time updates."""
    print(f"\n🔄 Monitoring indicators in real-time for {duration_seconds} seconds...")

    update_count = 0

    async def on_data_update(timeframe: str) -> None:
        """Handle real-time data updates."""
        nonlocal update_count
        update_count += 1

        # Get latest data
        data: pl.DataFrame | None = await data_manager.get_data(timeframe)
        if data is None:
            return

        # Need sufficient data for indicators
        if len(data) < 30:  # Need extra bars for indicator calculations
            print(f"  {timeframe}: Only {len(data)} bars available, need 30+")
            return

        # Calculate key indicators
        data = (
            data.pipe(RSI, period=14)
            .pipe(SMA, period=20)
            .pipe(FVG, min_gap_size=0.001)
            .pipe(WAE)
        )

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

        # Pattern indicators
        if "fvg_bullish" in data.columns and last_row["fvg_bullish"].item():
            print("  📈 Bullish FVG detected!")
        if "fvg_bearish" in data.columns and last_row["fvg_bearish"].item():
            print("  📉 Bearish FVG detected!")
        if "wae_explosion" in data.columns:
            wae_val = last_row["wae_explosion"].item()
            if wae_val is not None and wae_val > 0:
                trend = "Bullish" if last_row["wae_trend"].item() == 1 else "Bearish"
                print(f"  💥 WAE {trend} Explosion: {wae_val:.2f}")

    # Monitor multiple timeframes
    start_time = asyncio.get_event_loop().time()

    while asyncio.get_event_loop().time() - start_time < duration_seconds:
        # Check each timeframe
        for timeframe in ["5sec", "1min", "5min"]:
            await on_data_update(timeframe)

        await asyncio.sleep(5)  # Update every 5 seconds

    print(f"\n✅ Monitoring complete. Received {update_count} updates.")


async def analyze_pattern_indicators(suite: TradingSuite, symbol: str = "MNQ") -> None:
    """Demonstrate pattern recognition indicators in detail."""
    print("\n🎯 Pattern Recognition Analysis...")

    # Get hourly data for pattern analysis
    data = await suite.client.get_bars(symbol, days=10, interval=60)
    if data is None or data.is_empty():
        print("No data available for pattern analysis")
        return

    print(f"  Analyzing {len(data)} hourly bars for patterns...")

    # Calculate pattern indicators
    pattern_data = (
        data.pipe(FVG, min_gap_size=0.001, check_mitigation=True)
        .pipe(ORDERBLOCK, min_volume_percentile=70, check_mitigation=True)
        .pipe(WAE, sensitivity=150)
    )

    # Count pattern occurrences
    fvg_bullish_count = pattern_data["fvg_bullish"].sum()
    fvg_bearish_count = pattern_data["fvg_bearish"].sum()
    ob_bullish_count = pattern_data["ob_bullish"].sum()
    ob_bearish_count = pattern_data["ob_bearish"].sum()

    print("\n  Pattern Summary:")
    print("    Fair Value Gaps:")
    print(f"      - Bullish FVGs: {fvg_bullish_count}")
    print(f"      - Bearish FVGs: {fvg_bearish_count}")
    print("    Order Blocks:")
    print(f"      - Bullish OBs: {ob_bullish_count}")
    print(f"      - Bearish OBs: {ob_bearish_count}")

    # Find recent patterns
    recent_patterns = pattern_data.tail(20)

    print("\n  Recent Pattern Signals (last 20 bars):")
    for row in recent_patterns.iter_rows(named=True):
        timestamp = row["timestamp"]
        patterns_found = []

        if row.get("fvg_bullish", False):
            gap_size = row.get("fvg_gap_size", 0)
            patterns_found.append(f"Bullish FVG (gap: ${gap_size:.2f})")
        if row.get("fvg_bearish", False):
            gap_size = row.get("fvg_gap_size", 0)
            patterns_found.append(f"Bearish FVG (gap: ${gap_size:.2f})")
        if row.get("ob_bullish", False):
            patterns_found.append("Bullish Order Block")
        if row.get("ob_bearish", False):
            patterns_found.append("Bearish Order Block")
        if row.get("wae_explosion", 0) > 0:
            trend = "Bullish" if row.get("wae_trend", 0) == 1 else "Bearish"
            patterns_found.append(f"WAE {trend} Explosion")

        if patterns_found:
            print(f"    {timestamp}: {', '.join(patterns_found)}")

    # Analyze current market structure
    last_row = pattern_data.tail(1)
    print("\n  Current Market Structure:")
    print(f"    Price: ${last_row['close'].item():.2f}")

    if (
        "fvg_nearest_bullish" in last_row.columns
        and last_row["fvg_nearest_bullish"].item() is not None
    ):
        print(f"    Nearest Bullish FVG: ${last_row['fvg_nearest_bullish'].item():.2f}")
    if (
        "fvg_nearest_bearish" in last_row.columns
        and last_row["fvg_nearest_bearish"].item() is not None
    ):
        print(f"    Nearest Bearish FVG: ${last_row['fvg_nearest_bearish'].item():.2f}")

    if (
        "ob_nearest_bullish" in last_row.columns
        and last_row["ob_nearest_bullish"].item() is not None
    ):
        print(f"    Nearest Bullish OB: ${last_row['ob_nearest_bullish'].item():.2f}")
    if (
        "ob_nearest_bearish" in last_row.columns
        and last_row["ob_nearest_bearish"].item() is not None
    ):
        print(f"    Nearest Bearish OB: ${last_row['ob_nearest_bearish'].item():.2f}")


async def performance_comparison(suite: TradingSuite, symbol: str = "MNQ") -> None:
    """Compare performance of concurrent vs sequential indicator calculation."""
    print("\n⚡ Performance Comparison: Concurrent vs Sequential")

    # Get test data - need more for WAE indicator
    data = await suite.client.get_bars(symbol, days=20, interval=60)
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
    seq_data = seq_data.pipe(CCI, period=20)
    seq_data = seq_data.pipe(MFI, period=14)
    seq_data = seq_data.pipe(FVG, min_gap_size=0.001)
    seq_data = seq_data.pipe(ORDERBLOCK, min_volume_percentile=75)
    seq_data = seq_data.pipe(WAE)

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


async def main() -> int | None:
    """Main async function for technical indicators example."""
    logger = setup_logging(level="INFO")
    logger.info("🚀 Starting Async Technical Indicators Example (v3.0.0)")

    try:
        # Create TradingSuite v3 with real-time data
        print("\n🏗️ Creating TradingSuite v3...")
        suite = await TradingSuite.create(
            instrument="MNQ",
            timeframes=["5sec", "1min", "5min"],
            initial_days=7,
        )

        print("✅ TradingSuite initialized successfully!")

        account = suite.client.account_info
        if not account:
            print("❌ No account info found")
            await suite.disconnect()
            return 1

        print(f"   Connected as: {account.name}")

        # Analyze multiple timeframes concurrently
        await analyze_multiple_timeframes(suite, "MNQ")

        # Analyze pattern indicators
        await analyze_pattern_indicators(suite, "MNQ")

        # Performance comparison
        await performance_comparison(suite, "MNQ")

        # Monitor indicators in real-time
        print("\n📊 Monitoring indicators in real-time...")

        # Check if we have data_manager
        if "MNQ" in suite and suite["MNQ"].data:
            await real_time_indicator_updates(suite["MNQ"].data, duration_seconds=30)
        else:
            print("   Real-time monitoring not available in this configuration")

        print("\n📈 Technical Analysis Summary:")
        print("  - Concurrent indicator calculation is significantly faster")
        print("  - Multiple timeframes can be analyzed simultaneously")
        print("  - Real-time updates allow for responsive strategies")
        print("  - Async patterns enable efficient resource usage")

        # Cleanup
        await suite.disconnect()

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return 0


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ASYNC TECHNICAL INDICATORS ANALYSIS")
    print("=" * 60 + "\n")

    success = asyncio.run(main())
    sys.exit(0 if success else 1)

    print("\n✅ Example completed!")
