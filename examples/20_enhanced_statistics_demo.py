#!/usr/bin/env python3
"""
Example demonstrating enhanced statistics tracking in ProjectX SDK v3.2.1.

This example shows how to:
1. Track detailed performance metrics across all components
2. Monitor operation timings and success rates
3. Aggregate statistics from multiple managers
4. Export metrics for monitoring systems
"""

import asyncio
import json
import os
from datetime import datetime

from project_x_py import TradingSuite


async def main():
    """Demonstrate enhanced statistics tracking."""
    print("=" * 60)
    print("ProjectX SDK v3.2.1 - Enhanced Statistics Demo")
    print("=" * 60)

    # Check for required environment variables
    if not os.getenv("PROJECT_X_API_KEY") or not os.getenv("PROJECT_X_USERNAME"):
        print(
            "\n❌ Please set PROJECT_X_API_KEY and PROJECT_X_USERNAME environment variables"
        )
        return

    try:
        # Create trading suite with all features enabled
        print("\n📊 Initializing TradingSuite with enhanced statistics...")
        suite = await TradingSuite.create(
            "MNQ",
            timeframes=["1min", "5min", "15min"],
            features=["orderbook", "risk_manager"],
            initial_days=1,
        )

        print(f"✅ Suite initialized for {suite.instrument.name}")
        print(f"   Account: {suite.client.account_info.name}")

        # Perform some operations to generate statistics
        print("\n🔄 Performing operations to generate statistics...")

        # 1. Position operations
        positions = await suite.positions.get_all_positions()
        print(f"   Found {len(positions)} open positions")

        # Check specific positions
        for symbol in ["MNQ", "ES", "NQ"]:
            pos = await suite.positions.get_position(symbol)
            if pos:
                print(f"   {symbol}: {pos.size} contracts @ ${pos.averagePrice:.2f}")

        # 2. Order operations (without actually placing orders)
        print("\n   Checking order capabilities...")
        # This would track stats even for validation checks

        # 3. Data operations
        for tf in ["1min", "5min"]:
            data = await suite.data.get_data(tf)
            if data is not None and not data.is_empty():
                print(f"   {tf} data: {len(data)} bars loaded")

        # Wait a moment for some real-time data to flow
        print("\n⏳ Collecting real-time data for 5 seconds...")
        await asyncio.sleep(5)

        # Get comprehensive statistics
        print("\n📈 Retrieving enhanced statistics...")
        stats = await suite.get_stats()

        # Display component-level statistics
        print("\n=== Component Statistics ===")

        # Client stats
        if stats.client:
            print(f"\n📡 Client Statistics:")
            print(f"   API Calls: {stats.client.api_calls:,}")
            print(f"   Cache Hits: {stats.client.cache_hits:,}")
            print(f"   Cache Hit Rate: {stats.client.cache_hit_rate:.1%}")
            print(f"   Avg Response Time: {stats.client.avg_response_time_ms:.2f}ms")

        # Position Manager stats
        if stats.position_manager:
            print(f"\n💼 Position Manager Statistics:")
            print(f"   Positions Tracked: {stats.position_manager.positions_tracked}")
            print(f"   Total Operations: {stats.position_manager.total_operations:,}")
            print(f"   Cache Hit Rate: {stats.position_manager.cache_hit_rate:.1%}")
            if stats.position_manager.last_update_time:
                print(f"   Last Update: {stats.position_manager.last_update_time}")

        # Order Manager stats
        if stats.order_manager:
            print(f"\n📋 Order Manager Statistics:")
            print(f"   Orders Tracked: {stats.order_manager.orders_tracked}")
            print(f"   Active Orders: {stats.order_manager.active_orders}")
            print(f"   Total Operations: {stats.order_manager.total_operations:,}")

        # Data Manager stats
        if stats.data_manager:
            print(f"\n📊 Data Manager Statistics:")
            print(f"   Ticks Processed: {stats.data_manager.ticks_processed:,}")
            print(f"   Quotes Processed: {stats.data_manager.quotes_processed:,}")
            print(f"   Total Bars: {stats.data_manager.total_bars:,}")
            print(f"   Memory Usage: {stats.data_manager.memory_usage_mb:.2f}MB")
            print(f"   Feed Active: {stats.data_manager.is_running}")

        # Orderbook stats (if enabled)
        if stats.orderbook:
            print(f"\n📖 Orderbook Statistics:")
            print(f"   Bid Levels: {stats.orderbook.bid_levels}")
            print(f"   Ask Levels: {stats.orderbook.ask_levels}")
            print(f"   Recent Trades: {stats.orderbook.trades_count:,}")
            print(f"   Memory Usage: {stats.orderbook.memory_usage_mb:.2f}MB")

        # Risk Manager stats (if enabled)
        if stats.risk_manager:
            print(f"\n⚠️ Risk Manager Statistics:")
            print(f"   Risk Checks: {stats.risk_manager.risk_checks_performed:,}")
            print(f"   Orders Blocked: {stats.risk_manager.orders_blocked}")
            print(f"   Active Limits: {stats.risk_manager.active_limits}")

        # System-wide metrics
        print(f"\n=== System Metrics ===")
        print(f"   Total Memory: {stats.total_memory_mb:.2f}MB")
        print(f"   Health Score: {stats.health_score}/100")
        print(f"   Uptime: {stats.uptime_seconds:.1f} seconds")

        # Get detailed performance metrics from a specific component
        print("\n=== Detailed Performance Metrics ===")
        perf_metrics = await suite.positions.get_performance_metrics()

        if "operation_stats" in perf_metrics:
            print("\n📊 Position Manager Operation Statistics:")
            for op_name, op_stats in perf_metrics["operation_stats"].items():
                print(f"\n   {op_name}:")
                print(f"      Count: {op_stats['count']:,}")
                print(f"      Avg: {op_stats.get('avg_ms', 0):.2f}ms")
                print(f"      P50: {op_stats.get('p50_ms', 0):.2f}ms")
                print(f"      P95: {op_stats.get('p95_ms', 0):.2f}ms")

        # Export metrics for monitoring (e.g., Prometheus)
        print("\n📤 Exporting metrics...")

        # Get Prometheus-compatible metrics
        if hasattr(suite, "_stats_aggregator"):
            prometheus_metrics = await suite._stats_aggregator.export_prometheus()

            # Save to file
            with open("/tmp/projectx_metrics.txt", "w") as f:
                f.write(prometheus_metrics)
            print(f"   Metrics exported to /tmp/projectx_metrics.txt")

            # Show sample of exported metrics
            print("\n   Sample Prometheus metrics:")
            for line in prometheus_metrics.split("\n")[:10]:
                if line and not line.startswith("#"):
                    print(f"      {line}")

        # Demonstrate data quality tracking
        if hasattr(suite.data, "track_data_quality"):
            print("\n📊 Data Quality Metrics:")
            await suite.data.track_data_quality(
                total_points=1000,
                invalid_points=2,
                missing_points=1,
                duplicate_points=0,
            )
            print("   Data quality tracked successfully")

        print("\n✅ Enhanced statistics demonstration complete!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Clean disconnect
        if "suite" in locals():
            await suite.disconnect()
            print("\n👋 Disconnected from ProjectX")


if __name__ == "__main__":
    asyncio.run(main())
