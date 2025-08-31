"""
Advanced DataFrame Operations with Lazy Evaluation

This example demonstrates how to use the new DataFrame optimization features
in the project-x-py SDK for high-performance trading data analysis.

Author: @TexasCoding
Date: 2025-08-22

Key Features Demonstrated:
- Lazy DataFrame operations for memory efficiency
- Query optimization and batching
- Advanced data analysis with Polars expressions
- Performance monitoring and profiling
- Integration with TradingSuite

Requirements:
- PROJECT_X_API_KEY environment variable
- PROJECT_X_USERNAME environment variable
- Active ProjectX Gateway connection

Usage:
    python examples/advanced_dataframe_operations.py
"""

import asyncio
import logging
import time

import polars as pl

from project_x_py import TradingSuite

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demonstrate_lazy_operations(suite: TradingSuite) -> None:
    """Demonstrate lazy DataFrame operations for efficient data processing."""

    print("\n" + "=" * 60)
    print("Lazy DataFrame Operations Demo")
    print("=" * 60)

    # Get some initial data
    data_5m = await suite["MNQ"].data.get_data("5min", bars=200)
    if data_5m is None or data_5m.is_empty():
        print("No 5-minute data available for lazy operations demo")
        return

    print(f"Working with {len(data_5m)} bars of 5-minute data")

    # Example 1: Efficient filtering and selection with lazy operations
    print("\n1. Efficient Filtering and Selection:")
    print("-" * 40)

    start_time = time.time()

    # Use the new lazy operations from the data manager
    if hasattr(suite["MNQ"].data, "get_optimized_bars"):
        filtered_data = await suite["MNQ"].data.get_optimized_bars(
            "5min",
            bars=100,
            columns=["timestamp", "close", "volume"],
            filters=[
                pl.col("volume") > data_5m["volume"].median(),
                pl.col("close") > data_5m["close"].rolling_mean(20),
            ],
        )

        execution_time = (time.time() - start_time) * 1000
        print(
            f"  Filtered {len(data_5m)} → {len(filtered_data) if filtered_data is not None else 0} bars"
        )
        print(f"  Execution time: {execution_time:.2f} ms")
        print("  Memory efficient: Only loaded selected columns")
    else:
        print("  Lazy operations not available (using fallback)")
        filtered_data = data_5m.filter(
            pl.col("volume") > data_5m["volume"].median()
        ).tail(100)
        print(f"  Filtered to {len(filtered_data)} bars using regular operations")


async def demonstrate_batch_queries(suite: TradingSuite) -> None:
    """Demonstrate batch query operations for multi-timeframe analysis."""

    print("\n" + "=" * 60)
    print("Batch Query Operations Demo")
    print("=" * 60)

    # Check if advanced batch operations are available
    if not hasattr(suite["MNQ"].data, "execute_batch_queries"):
        print("Batch query operations not available in this version")
        return

    print("Executing batch queries across multiple timeframes...")

    start_time = time.time()

    # Define complex multi-timeframe analysis
    batch_queries = [
        # 1-minute data: Recent activity analysis
        (
            "1min",
            [
                ("filter", pl.col("volume") > 0),
                (
                    "with_columns",
                    [
                        pl.col("close").rolling_mean(10).alias("sma_10"),
                        pl.col("close").rolling_mean(20).alias("sma_20"),
                        (pl.col("high") - pl.col("low")).alias("range"),
                        pl.col("close").pct_change().alias("returns"),
                    ],
                ),
                ("filter", pl.col("sma_10") > pl.col("sma_20")),  # Uptrend filter
                (
                    "select",
                    [
                        "timestamp",
                        "close",
                        "volume",
                        "sma_10",
                        "sma_20",
                        "range",
                        "returns",
                    ],
                ),
                ("tail", 30),
            ],
        ),
        # 5-minute data: Medium-term trend analysis
        (
            "5min",
            [
                ("filter", pl.col("volume") > 0),
                (
                    "with_columns",
                    [
                        pl.col("close").rolling_mean(50).alias("sma_50"),
                        pl.col("volume").rolling_mean(20).alias("avg_volume"),
                        (pl.col("close") / pl.col("open") - 1).alias("bar_return"),
                    ],
                ),
                (
                    "filter",
                    pl.col("volume") > pl.col("avg_volume"),
                ),  # Above average volume
                (
                    "select",
                    [
                        "timestamp",
                        "close",
                        "volume",
                        "sma_50",
                        "avg_volume",
                        "bar_return",
                    ],
                ),
                ("tail", 20),
            ],
        ),
        # 15-minute data: Longer-term context
        (
            "15min",
            [
                ("filter", pl.col("volume") > 0),
                (
                    "with_columns",
                    [
                        pl.col("close").rolling_mean(20).alias("sma_20"),
                        pl.col("close").rolling_std(20).alias("volatility"),
                        (pl.col("high") - pl.col("close").shift(1)).alias("gap"),
                    ],
                ),
                ("select", ["timestamp", "close", "sma_20", "volatility", "gap"]),
                ("tail", 10),
            ],
        ),
    ]

    # Execute batch queries
    try:
        results = await suite["MNQ"].data.execute_batch_queries(
            batch_queries, use_cache=True
        )

        execution_time = (time.time() - start_time) * 1000
        print(f"Batch execution completed in {execution_time:.2f} ms")

        # Display results
        for timeframe, data in results.items():
            if data is not None and not data.is_empty():
                print(f"\n{timeframe} results: {len(data)} bars")
                print(f"  Columns: {', '.join(data.columns)}")
                if len(data) > 0:
                    latest = data.tail(1)
                    latest_close = latest["close"][0]
                    print(f"  Latest close: ${latest_close:.2f}")
            else:
                print(f"\n{timeframe} results: No data")

    except Exception as e:
        print(f"Batch query error: {e}")


async def demonstrate_advanced_analysis(suite: TradingSuite) -> None:
    """Demonstrate advanced trading analysis using optimized operations."""

    print("\n" + "=" * 60)
    print("Advanced Trading Analysis Demo")
    print("=" * 60)

    # Get comprehensive data
    data_1m = await suite["MNQ"].data.get_data("1min", bars=500)
    if data_1m is None or data_1m.is_empty():
        print("No 1-minute data available for advanced analysis")
        return

    print(f"Analyzing {len(data_1m)} bars of 1-minute data...")

    # Example: Multi-timeframe momentum analysis
    print("\n1. Multi-Timeframe Momentum Analysis:")
    print("-" * 40)

    # Calculate multiple momentum indicators efficiently
    momentum_analysis = (
        data_1m.lazy()
        .with_columns(
            [
                # Price momentum
                pl.col("close").pct_change(5).alias("mom_5"),
                pl.col("close").pct_change(10).alias("mom_10"),
                pl.col("close").pct_change(20).alias("mom_20"),
                # Moving averages
                pl.col("close").rolling_mean(10).alias("sma_10"),
                pl.col("close").rolling_mean(20).alias("sma_20"),
                pl.col("close").rolling_mean(50).alias("sma_50"),
                # Volatility measures
                pl.col("close").rolling_std(20).alias("volatility_20"),
                (pl.col("high") - pl.col("low")).rolling_mean(10).alias("avg_range"),
                # Volume analysis
                pl.col("volume").rolling_mean(20).alias("avg_volume"),
                (pl.col("volume") / pl.col("volume").rolling_mean(20)).alias(
                    "volume_ratio"
                ),
            ]
        )
        .with_columns(
            [
                # Trend signals
                (pl.col("sma_10") > pl.col("sma_20")).alias("short_term_bullish"),
                (pl.col("sma_20") > pl.col("sma_50")).alias("medium_term_bullish"),
                (pl.col("close") > pl.col("sma_10")).alias("above_short_ma"),
                # Momentum signals
                (pl.col("mom_5") > 0).alias("mom_5_positive"),
                (pl.col("mom_10") > 0).alias("mom_10_positive"),
                (pl.col("mom_20") > 0).alias("mom_20_positive"),
                # Volume signals
                (pl.col("volume_ratio") > 1.5).alias("high_volume"),
                (pl.col("volume_ratio") > 2.0).alias("very_high_volume"),
            ]
        )
        .filter(pl.col("timestamp").is_not_null())  # Remove any null timestamps
        .collect()
    )

    print(f"  Generated {len(momentum_analysis.columns)} analytical columns")
    print(f"  Latest close: ${momentum_analysis['close'][-1]:.2f}")

    # Find confluence signals (multiple conditions align)
    confluence_signals = (
        momentum_analysis.lazy()
        .with_columns(
            [
                # Bullish confluence score
                (
                    pl.col("short_term_bullish").cast(pl.Int32)
                    + pl.col("medium_term_bullish").cast(pl.Int32)
                    + pl.col("above_short_ma").cast(pl.Int32)
                    + pl.col("mom_5_positive").cast(pl.Int32)
                    + pl.col("mom_10_positive").cast(pl.Int32)
                    + pl.col("high_volume").cast(pl.Int32)
                ).alias("bullish_score"),
                # Signal strength
                (pl.col("mom_5").abs() + pl.col("mom_10").abs()).alias(
                    "momentum_strength"
                ),
            ]
        )
        .filter(pl.col("bullish_score") >= 4)  # Strong bullish confluence
        .sort("timestamp")
        .collect()
    )

    if not confluence_signals.is_empty():
        print(f"  Found {len(confluence_signals)} strong bullish confluence signals")
        latest_signal = confluence_signals.tail(1)
        if not latest_signal.is_empty():
            score = latest_signal["bullish_score"][0]
            strength = latest_signal["momentum_strength"][0]
            print(f"  Latest signal strength: {score}/6 (momentum: {strength:.4f})")
    else:
        print("  No strong confluence signals in recent data")


async def demonstrate_performance_monitoring(suite: TradingSuite) -> None:
    """Demonstrate performance monitoring and optimization statistics."""

    print("\n" + "=" * 60)
    print("Performance Monitoring Demo")
    print("=" * 60)

    # Check if optimization features are available
    if not hasattr(suite["MNQ"].data, "get_optimization_stats"):
        print("Performance monitoring not available in this version")
        return

    # Get optimization statistics
    try:
        opt_stats = suite["MNQ"].data.get_optimization_stats()

        print("DataFrame Optimization Statistics:")
        print("-" * 40)
        print(f"  Operations optimized: {opt_stats.get('operations_optimized', 0)}")
        print(
            f"  Average operation time: {opt_stats.get('avg_operation_time_ms', 0):.2f} ms"
        )
        print(
            f"  Batch operations executed: {opt_stats.get('batch_operations_executed', 0)}"
        )

        # Cache performance
        cache_stats = opt_stats.get("cache_stats", {})
        if cache_stats:
            print("\nCache Performance:")
            print(f"  Cache hits: {cache_stats.get('hits', 0)}")
            print(f"  Cache misses: {cache_stats.get('misses', 0)}")
            print(f"  Hit rate: {cache_stats.get('hit_rate', 0):.1%}")
            print(f"  Cache size: {cache_stats.get('cache_size', 0)}")

        # Optimizer statistics
        optimizer_stats = opt_stats.get("optimizer_stats", {})
        if optimizer_stats:
            print("\nQuery Optimizer:")
            print(f"  Queries optimized: {optimizer_stats.get('queries_optimized', 0)}")
            print(f"  Filters combined: {optimizer_stats.get('filters_combined', 0)}")
            print(
                f"  Operations reduced: {optimizer_stats.get('operations_reduced', 0)}"
            )

        # Memory profiling
        if hasattr(suite["MNQ"].data, "profile_memory_usage"):
            memory_profile = await suite["MNQ"].data.profile_memory_usage()
            print("\nMemory Usage:")
            print(
                f"  Current memory: {memory_profile.get('current_memory_mb', 0):.2f} MB"
            )
            print(
                f"  Average memory: {memory_profile.get('average_memory_mb', 0):.2f} MB"
            )
            print(f"  Memory trend: {memory_profile.get('memory_trend_mb', 0):+.2f} MB")

    except Exception as e:
        print(f"Error getting performance statistics: {e}")


async def main():
    """Main function demonstrating advanced DataFrame operations."""

    print("Advanced DataFrame Operations with Lazy Evaluation")
    print("=" * 60)
    print("This example demonstrates the new DataFrame optimization features")
    print("for high-performance trading data analysis.\n")

    try:
        # Create TradingSuite with multiple timeframes
        print("Initializing TradingSuite with optimization features...")

        suite = await TradingSuite.create(
            "MNQ",  # E-mini NASDAQ futures
            timeframes=["1min", "5min", "15min"],
            initial_days=2,  # Get 2 days of historical data
        )

        print(
            f"✓ Connected to {suite['MNQ'].instrument_info.symbolId} with {len(['1min', '5min', '15min'])} timeframes"
        )

        # Wait for some real-time data
        print("\nWaiting for real-time data updates...")
        await asyncio.sleep(5)

        # Check data availability
        data_stats = {}
        for tf in ["1min", "5min", "15min"]:
            data = await suite["MNQ"].data.get_data(tf)
            data_stats[tf] = len(data) if data is not None else 0

        print(f"Data availability: {data_stats}")

        # Run demonstrations if we have sufficient data
        min_bars_available = min(data_stats.values())
        if min_bars_available < 50:
            print(
                f"\nNeed more data for demonstrations (have {min_bars_available}, need 50+ bars)"
            )
            print("Please wait for more real-time data or increase initial_days")
        else:
            # Run the demonstrations
            await demonstrate_lazy_operations(suite)
            await demonstrate_batch_queries(suite)
            await demonstrate_advanced_analysis(suite)
            await demonstrate_performance_monitoring(suite)

        # Show final statistics
        print("\n" + "=" * 60)
        print("Final Statistics")
        print("=" * 60)

        # Memory statistics
        memory_stats = await suite["MNQ"].data.get_memory_stats()
        print(f"Total bars processed: {memory_stats['bars_processed']}")
        print(f"Ticks processed: {memory_stats['ticks_processed']}")
        print(f"Memory usage: {memory_stats['memory_usage_mb']:.2f} MB")
        print(f"Buffer utilization: {memory_stats['buffer_utilization']:.1%}")

        print("\n✓ DataFrame optimization demonstration completed successfully!")

    except KeyboardInterrupt:
        print("\n\nReceived interrupt signal. Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise
    finally:
        # Cleanup
        if "suite" in locals():
            try:
                await suite.disconnect()
                print("✓ Disconnected from TradingSuite")
            except Exception as e:
                print(f"Error during cleanup: {e}")


if __name__ == "__main__":
    asyncio.run(main())
