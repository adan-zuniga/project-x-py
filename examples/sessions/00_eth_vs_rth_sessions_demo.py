#!/usr/bin/env python3
"""
ETH vs RTH Trading Sessions - Comprehensive Demo

This example demonstrates all features of the ETH vs RTH Trading Sessions system:
- Session configuration and filtering
- Real-time session-aware data processing
- Historical session analysis
- Session-specific indicators and statistics
- Performance comparison between RTH and ETH

Author: ProjectX SDK
Date: 2025-08-28
"""

import asyncio
import logging
from datetime import datetime, timedelta

from project_x_py import TradingSuite
from project_x_py.indicators import EMA, RSI, SMA, VWAP
from project_x_py.sessions import SessionConfig, SessionFilterMixin, SessionType


# Suppress noisy WebSocket connection errors from SignalR
# These errors occur when background threads try to read from closed connections
# They are harmless but make the output noisy
class NullHandler(logging.Handler):
    """Handler that suppresses all log records."""

    def emit(self, record):
        pass


null_handler = NullHandler()
for logger_name in ["SignalRCoreClient", "websocket", "signalrcore"]:
    logger = logging.getLogger(logger_name)
    logger.handlers = [null_handler]
    logger.setLevel(logging.CRITICAL)
    logger.propagate = False


async def demonstrate_basic_session_usage():
    """Basic session configuration and usage."""
    print("=" * 80)
    print("1. BASIC SESSION CONFIGURATION")
    print("=" * 80)

    # Create RTH-only configuration
    rth_config = SessionConfig(session_type=SessionType.RTH)
    print(f"RTH Config: {rth_config.session_type}")

    # Create ETH (24-hour) configuration
    eth_config = SessionConfig(session_type=SessionType.ETH)
    print(f"ETH Config: {eth_config.session_type}")

    # Get session times for different products
    print("\nSession Times by Product:")
    products = ["ES", "NQ", "CL", "GC", "ZN"]
    for product in products:
        session_times = rth_config.get_session_times(product)
        print(f"{product:3}: RTH {session_times.rth_start} - {session_times.rth_end}")

    print("\n✅ Basic session configuration demonstrated")


async def demonstrate_historical_session_analysis():
    """Historical data analysis with session filtering."""
    print("\n" + "=" * 80)
    print("2. HISTORICAL SESSION ANALYSIS")
    print("=" * 80)

    try:
        # Create TradingSuite instances for both session types
        rth_suite = await TradingSuite.create(
            "MNQ",
            timeframes=["1min", "5min"],
            session_config=SessionConfig(session_type=SessionType.RTH),
        )
        print("✅ RTH TradingSuite created")

        eth_suite = await TradingSuite.create(
            "MNQ",
            timeframes=["1min", "5min"],
            session_config=SessionConfig(session_type=SessionType.ETH),
        )
        print("✅ ETH TradingSuite created")

        # Get historical data for both sessions
        print("\nFetching historical data...")

        # Get session-filtered data using the data manager's get_session_data method
        rth_context = rth_suite["MNQ"]
        eth_context = eth_suite["MNQ"]

        # These methods exist on the data manager and filter by session
        rth_data_1min = await rth_context.data.get_session_data("1min", SessionType.RTH)
        rth_data_5min = await rth_context.data.get_session_data("5min", SessionType.RTH)

        eth_data_1min = await eth_context.data.get_session_data("1min", SessionType.ETH)
        eth_data_5min = await eth_context.data.get_session_data("5min", SessionType.ETH)

        if rth_data_1min is None or rth_data_5min is None or eth_data_1min is None or eth_data_5min is None:
            raise ValueError("Failed to get data")
        # Compare data volumes
        print("\nData Comparison (1min):")
        print(f"RTH bars: {len(rth_data_1min):,}")
        print(f"ETH bars: {len(eth_data_1min):,}")
        print(
            f"ETH has {len(eth_data_1min) - len(rth_data_1min):,} more bars ({((len(eth_data_1min) / len(rth_data_1min) - 1) * 100):.1f}% more)"
        )

        print("\nData Comparison (5min):")
        print(f"RTH bars: {len(rth_data_5min):,}")
        print(f"ETH bars: {len(eth_data_5min):,}")
        print(
            f"ETH has {len(eth_data_5min) - len(rth_data_5min):,} more bars ({((len(eth_data_5min) / len(rth_data_5min) - 1) * 100):.1f}% more)"
        )

        # Analyze time ranges
        if not rth_data_1min.is_empty():
            rth_start = rth_data_1min["timestamp"].min()
            rth_end = rth_data_1min["timestamp"].max()
            print(f"\nRTH Time Range: {rth_start} to {rth_end}")

        if not eth_data_1min.is_empty():
            eth_start = eth_data_1min["timestamp"].min()
            eth_end = eth_data_1min["timestamp"].max()
            print(f"ETH Time Range: {eth_start} to {eth_end}")

        await rth_suite.disconnect()
        await asyncio.sleep(0.1)  # Brief delay to avoid connection cleanup race
        await eth_suite.disconnect()
        print("\n✅ Historical session analysis completed")

    except Exception as e:
        print(f"❌ Historical analysis error: {e}")


async def demonstrate_session_indicators():
    """Session-aware technical indicators."""
    print("\n" + "=" * 80)
    print("3. SESSION-AWARE INDICATORS")
    print("=" * 80)

    try:
        # Create RTH-only suite for indicator analysis
        suite = await TradingSuite.create(
            "MNQ",
            timeframes=["5min"],
            session_config=SessionConfig(session_type=SessionType.RTH),
        )
        print("✅ RTH TradingSuite created for indicators")

        # Get RTH data using data manager's session method
        mnq_context = suite["MNQ"]
        rth_data = await mnq_context.data.get_session_data("5min", SessionType.RTH)

        if rth_data is None:
            print("No RTH data available")
            await suite.disconnect()
            return

        print(f"Retrieved {len(rth_data):,} RTH bars")

        if not rth_data.is_empty():
            # Apply multiple indicators to RTH-only data
            print("\nApplying session-aware indicators...")
            with_indicators = (
                rth_data.pipe(SMA, period=20)
                .pipe(EMA, period=12)
                .pipe(RSI, period=14)
                .pipe(VWAP)
            )

            print(f"Available columns: {with_indicators.columns}")

            # Calculate indicator statistics
            if "sma_20" in with_indicators.columns:
                sma_stats = with_indicators["sma_20"].drop_nulls()
                if len(sma_stats) > 0:
                    print("\nSMA(20) Stats (RTH only):")
                    sma_mean = sma_stats.mean()
                    sma_min = sma_stats.min()
                    sma_max = sma_stats.max()
                    # Cast to float, handling potential None or complex types
                    if sma_mean is not None:
                        mean_val = float(str(sma_mean)) if not isinstance(sma_mean, (int, float)) else float(sma_mean)
                        print(f"  Mean: ${mean_val:.2f}")
                    if sma_min is not None:
                        min_val = float(str(sma_min)) if not isinstance(sma_min, (int, float)) else float(sma_min)
                        print(f"  Min:  ${min_val:.2f}")
                    if sma_max is not None:
                        max_val = float(str(sma_max)) if not isinstance(sma_max, (int, float)) else float(sma_max)
                        print(f"  Max:  ${max_val:.2f}")

            if "rsi_14" in with_indicators.columns:
                rsi_stats = with_indicators["rsi_14"].drop_nulls()
                if len(rsi_stats) > 0:
                    print("\nRSI(14) Stats (RTH only):")
                    rsi_mean = rsi_stats.mean()
                    rsi_min = rsi_stats.min()
                    rsi_max = rsi_stats.max()
                    # Cast to float, handling potential None or complex types
                    if rsi_mean is not None:
                        mean_val = float(str(rsi_mean)) if not isinstance(rsi_mean, (int, float)) else float(rsi_mean)
                        print(f"  Mean: {mean_val:.1f}")
                    if rsi_min is not None:
                        min_val = float(str(rsi_min)) if not isinstance(rsi_min, (int, float)) else float(rsi_min)
                        print(f"  Min:  {min_val:.1f}")
                    if rsi_max is not None:
                        max_val = float(str(rsi_max)) if not isinstance(rsi_max, (int, float)) else float(rsi_max)
                        print(f"  Max:  {max_val:.1f}")

            # Compare with ETH indicators - need to create ETH suite
            print("\nComparing RTH vs ETH indicators...")
            eth_suite = await TradingSuite.create(
                "MNQ",
                timeframes=["5min"],
                session_config=SessionConfig(session_type=SessionType.ETH),
            )
            eth_context = eth_suite["MNQ"]
            eth_data = await eth_context.data.get_session_data("5min", SessionType.ETH)

            if eth_data is not None and not eth_data.is_empty():
                eth_indicators = eth_data.pipe(SMA, period=20).pipe(RSI, period=14)

                if "sma_20" in eth_indicators.columns:
                    eth_sma = eth_indicators["sma_20"].drop_nulls()
                    if len(eth_sma) > 0:
                        eth_mean_val = eth_sma.mean()
                        if eth_mean_val is not None and 'sma_stats' in locals() and len(sma_stats) > 0:
                            rth_mean_val = sma_stats.mean()
                            if rth_mean_val is not None:
                                # Safely convert to float
                                eth_sma_mean = float(str(eth_mean_val)) if not isinstance(eth_mean_val, (int, float)) else float(eth_mean_val)
                                rth_sma_mean = float(str(rth_mean_val)) if not isinstance(rth_mean_val, (int, float)) else float(rth_mean_val)
                                print("\nSMA(20) Comparison:")
                                print(f"  RTH Mean: ${rth_sma_mean:.2f}")
                                print(f"  ETH Mean: ${eth_sma_mean:.2f}")
                                print(f"  Difference: ${abs(eth_sma_mean - rth_sma_mean):.2f}")

            await eth_suite.disconnect()

        await suite.disconnect()
        await asyncio.sleep(0.1)  # Brief delay to avoid connection cleanup race
        print("\n✅ Session-aware indicators demonstrated")

    except Exception as e:
        print(f"❌ Indicator analysis error: {e}")


async def demonstrate_session_statistics():
    """Session-specific statistics and analytics."""
    print("\n" + "=" * 80)
    print("4. SESSION STATISTICS")
    print("=" * 80)

    try:
        suite = await TradingSuite.create(
            "MNQ",
            timeframes=["1min"],
            session_config=SessionConfig(
                session_type=SessionType.ETH
            ),  # ETH to get both sessions
        )
        print("✅ ETH TradingSuite created for statistics")

        # Get session statistics using data manager's method
        print("\nCalculating session statistics...")
        try:
            # Get the statistics directly from data manager
            mnq_context = suite["MNQ"]
            stats = await mnq_context.data.get_session_statistics("1min")

            print("\n📊 Session Statistics:")
            print(f"RTH Volume: {stats.get('rth_volume', 'N/A'):,}")
            print(f"ETH Volume: {stats.get('eth_volume', 'N/A'):,}")

            if stats.get("rth_volume") and stats.get("eth_volume"):
                ratio = stats["rth_volume"] / stats["eth_volume"]
                print(f"Volume Ratio (RTH/ETH): {ratio:.2f}")

            print(f"RTH VWAP: ${stats.get('rth_vwap', 0):.2f}")
            print(f"ETH VWAP: ${stats.get('eth_vwap', 0):.2f}")
            print(f"RTH Range: ${stats.get('rth_range', 0):.2f}")
            print(f"ETH Range: ${stats.get('eth_range', 0):.2f}")

        except Exception as e:
            print(f"Statistics calculation error: {e}")
            print("This is expected if no recent session data is available")

        await suite.disconnect()
        await asyncio.sleep(0.1)  # Brief delay to avoid connection cleanup race
        print("\n✅ Session statistics demonstrated")

    except Exception as e:
        print(f"❌ Statistics error: {e}")


async def demonstrate_realtime_session_filtering():
    """Real-time data with session filtering."""
    print("\n" + "=" * 80)
    print("5. REAL-TIME SESSION FILTERING")
    print("=" * 80)

    try:
        # Create RTH-only suite for real-time data
        suite = await TradingSuite.create(
            "MNQ",
            timeframes=["1min"],
            session_config=SessionConfig(session_type=SessionType.RTH),
        )
        print("✅ RTH TradingSuite created for real-time demo")

        # Check connection status
        print(f"Real-time connected: {suite['MNQ'].data.get_realtime_validation_status().get('is_running', False)}")

        # Set up event counters
        event_counts = {"new_bar": 0, "tick": 0, "quote": 0}

        async def count_rth_events(event):
            """Count RTH-only events."""
            event_counts[event.event_type.value] += 1
            if event_counts["new_bar"] % 5 == 0 and event_counts["new_bar"] > 0:
                data = event.data
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(
                    f"[{timestamp}] RTH Bar #{event_counts['new_bar']}: ${data.get('close', 0):.2f}"
                )

        # Register for RTH-only events
        from project_x_py import EventType

        await suite.on(EventType.NEW_BAR, count_rth_events)
        print("✅ Event handlers registered for RTH-only data")

        # Monitor for a short time
        print("\nMonitoring RTH-only events for 10 seconds...")
        await asyncio.sleep(10)

        print("\n📊 Event Summary (RTH only):")
        print(f"New Bars: {event_counts['new_bar']}")
        print(f"Ticks: {event_counts['tick']}")
        print(f"Quotes: {event_counts['quote']}")

        # Test session switching
        print("\nSwitching to ETH (24-hour) mode...")
        await suite.set_session_type(SessionType.ETH)

        # Reset counters and monitor ETH data
        event_counts = {"new_bar": 0, "tick": 0, "quote": 0}
        print("Monitoring ETH events for 5 seconds...")
        await asyncio.sleep(5)

        print("\n📊 Event Summary (ETH):")
        print(f"New Bars: {event_counts['new_bar']}")
        print(f"Ticks: {event_counts['tick']}")
        print(f"Quotes: {event_counts['quote']}")

        await suite.disconnect()
        await asyncio.sleep(0.1)  # Brief delay to avoid connection cleanup race
        print("\n✅ Real-time session filtering demonstrated")

    except Exception as e:
        print(f"❌ Real-time demo error: {e}")


async def demonstrate_session_filtering_direct():
    """Direct session filtering using SessionFilterMixin."""
    print("\n" + "=" * 80)
    print("6. DIRECT SESSION FILTERING")
    print("=" * 80)

    try:
        # Create a session filter directly
        session_filter = SessionFilterMixin(
            config=SessionConfig(session_type=SessionType.RTH)
        )
        print("✅ SessionFilterMixin created")

        # Create sample data for demonstration
        from datetime import timezone

        import polars as pl

        # Generate mixed session sample data (simplified)
        timestamps = []
        prices = []
        volumes = []

        base_time = datetime.now(timezone.utc).replace(
            hour=13, minute=0, second=0, microsecond=0
        )  # 8 AM ET

        # Add some sample data across different hours
        for hour_offset in range(12):  # 12 hours of data
            for minute in [0, 30]:
                ts = base_time + timedelta(hours=hour_offset, minutes=minute)
                timestamps.append(ts)
                prices.append(4800.0 + hour_offset * 2 + minute * 0.1)
                volumes.append(100 + hour_offset * 10)

        sample_data = pl.DataFrame(
            {
                "timestamp": timestamps,
                "open": prices,
                "high": [p + 1.0 for p in prices],
                "low": [p - 1.0 for p in prices],
                "close": prices,
                "volume": volumes,
            }
        )

        print(f"Created sample data: {len(sample_data)} bars")

        # Filter to RTH only
        rth_filtered = await session_filter.filter_by_session(
            sample_data, SessionType.RTH, "MNQ"
        )

        # Filter to ETH
        eth_filtered = await session_filter.filter_by_session(
            sample_data, SessionType.ETH, "MNQ"
        )

        print("\nFiltering Results:")
        print(f"Original data: {len(sample_data)} bars")
        print(f"RTH filtered: {len(rth_filtered)} bars")
        print(f"ETH filtered: {len(eth_filtered)} bars")
        print(
            f"RTH is {(len(rth_filtered) / len(sample_data) * 100):.1f}% of total data"
        )

        # Show time ranges
        if not rth_filtered.is_empty():
            rth_start = rth_filtered["timestamp"].min()
            rth_end = rth_filtered["timestamp"].max()
            print(f"RTH time range: {rth_start} to {rth_end}")

        if not eth_filtered.is_empty():
            eth_start = eth_filtered["timestamp"].min()
            eth_end = eth_filtered["timestamp"].max()
            print(f"ETH time range: {eth_start} to {eth_end}")

        print("\n✅ Direct session filtering demonstrated")

    except Exception as e:
        print(f"❌ Direct filtering error: {e}")


async def demonstrate_multi_product_sessions():
    """Session configurations across different products."""
    print("\n" + "=" * 80)
    print("7. MULTI-PRODUCT SESSION CONFIGURATIONS")
    print("=" * 80)

    products_and_symbols = [
        ("ES", "Equity futures (S&P 500)"),
        ("CL", "Energy futures (Crude Oil)"),
        ("GC", "Metal futures (Gold)"),
        ("ZN", "Treasury futures (10-Year Note)"),
    ]

    print("Session Times by Product Category:")
    print("-" * 50)

    config = SessionConfig(session_type=SessionType.RTH)

    for product, description in products_and_symbols:
        try:
            session_times = config.get_session_times(product)
            print(
                f"{product:3} | {description:25} | {session_times.rth_start} - {session_times.rth_end}"
            )
        except Exception as e:
            print(f"{product:3} | {description:25} | Error: {e}")

    print("\nMaintenance Break Schedule:")
    print("-" * 30)

    # Create filter to show maintenance breaks
    session_filter = SessionFilterMixin()

    for product, _description in products_and_symbols:
        breaks = session_filter._get_maintenance_breaks(product)
        if breaks:
            break_times = ", ".join([f"{start}-{end}" for start, end in breaks])
            print(f"{product:3} | {break_times}")
        else:
            print(f"{product:3} | No maintenance breaks")

    print("\n✅ Multi-product sessions demonstrated")


async def demonstrate_performance_features():
    """Performance optimization features."""
    print("\n" + "=" * 80)
    print("8. PERFORMANCE OPTIMIZATIONS")
    print("=" * 80)

    try:
        # Create filter with caching
        session_filter = SessionFilterMixin()
        print("✅ SessionFilterMixin with caching created")

        # Test caching
        print(f"Cache size: {len(session_filter._session_boundary_cache)}")

        # Demonstrate boundary caching
        boundaries = session_filter._get_cached_session_boundaries(
            "test_hash", "ES", "RTH"
        )
        print(f"Cached boundaries: {boundaries}")
        print(f"Cache size after: {len(session_filter._session_boundary_cache)}")

        # Test with different data sizes
        from datetime import timezone

        import polars as pl

        small_data = pl.DataFrame(
            {
                "timestamp": [datetime.now(timezone.utc)] * 100,
                "open": [4800.0] * 100,
                "high": [4801.0] * 100,
                "low": [4799.0] * 100,
                "close": [4800.0] * 100,
                "volume": [100] * 100,
            }
        )

        large_data = pl.DataFrame(
            {
                "timestamp": [datetime.now(timezone.utc)] * 150_000,
                "open": [4800.0] * 150_000,
                "high": [4801.0] * 150_000,
                "low": [4799.0] * 150_000,
                "close": [4800.0] * 150_000,
                "volume": [100] * 150_000,
            }
        )

        print("\nTesting optimization strategies:")
        print(f"Small dataset ({len(small_data):,} rows): Standard processing")
        small_optimized = session_filter._optimize_filtering(small_data)
        print(f"Result: {len(small_optimized):,} rows")

        print(f"Large dataset ({len(large_data):,} rows): Lazy evaluation")
        large_optimized = session_filter._optimize_filtering(large_data)
        print(f"Result: {len(large_optimized):,} rows")

        print("\n✅ Performance optimizations demonstrated")

    except Exception as e:
        print(f"❌ Performance demo error: {e}")


async def main():
    """Run comprehensive ETH vs RTH Sessions demonstration."""
    print("🚀 ETH vs RTH Trading Sessions - Comprehensive Demo")
    print(f"Started at: {datetime.now()}")

    try:
        # Run all demonstrations
        await demonstrate_basic_session_usage()
        await demonstrate_historical_session_analysis()
        await demonstrate_session_indicators()
        await demonstrate_session_statistics()
        await demonstrate_realtime_session_filtering()
        await demonstrate_session_filtering_direct()
        await demonstrate_multi_product_sessions()
        await demonstrate_performance_features()

        print("\n" + "=" * 80)
        print("🎉 DEMO COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print("\n📋 Summary of demonstrated features:")
        print("✅ Basic session configuration (ETH vs RTH)")
        print("✅ Historical session data analysis")
        print("✅ Session-aware technical indicators")
        print("✅ Session statistics and analytics")
        print("✅ Real-time session filtering")
        print("✅ Direct SessionFilterMixin usage")
        print("✅ Multi-product session configurations")
        print("✅ Performance optimization features")

        print(f"\n🏁 Demo completed at: {datetime.now()}")

    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Run the comprehensive demo
    asyncio.run(main())
