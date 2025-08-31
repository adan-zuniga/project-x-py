#!/usr/bin/env python3
"""
ProjectX SDK Statistics Usage Example
=====================================

This example demonstrates the comprehensive statistics and monitoring capabilities
introduced in v3.3.0 of the ProjectX SDK.

Key Features Demonstrated:
- Component-level statistics collection
- Multi-format export (JSON, Prometheus, CSV, Datadog)
- Health monitoring and scoring
- Performance metrics tracking
- Error and anomaly detection
- Memory usage monitoring
- Adaptive strategy based on statistics

Version: 3.3.0 - Complete Statistics Module Redesign
Author: TexasCoding
"""

import asyncio
import json
from decimal import Decimal

from project_x_py import Features, TradingSuite, utils


async def main():
    """Main example demonstrating v3.3.0 statistics capabilities."""
    suite = None

    try:
        print("=" * 60)
        print("ProjectX SDK Statistics Usage Example")
        print("=" * 60)

        # =========================================================================
        # 1. INITIALIZE TRADING SUITE WITH STATISTICS FEATURES
        # =========================================================================
        suite = await TradingSuite.create(
            "MNQ",
            features=[Features.ORDERBOOK, Features.RISK_MANAGER],
            timeframes=["1min", "5min"],
            initial_days=1,
        )

        if suite is None:
            print("❌ Failed to initialize trading suite")
            return

        if not suite.instrument_info:
            print("❌ Failed to initialize trading suite")
            return

        if not suite.client:
            print("❌ Failed to initialize trading suite")
            return

        if not suite.data:
            print("❌ Failed to initialize trading suite")
            return

        if not suite.orders:
            print("❌ Failed to initialize trading suite")
            return

        if not suite.positions:
            print("❌ Failed to initialize trading suite")
            return

        if not suite.risk_manager:
            print("❌ Failed to initialize trading suite")
            return

        if not suite.client.account_info:
            print("❌ Failed to initialize trading suite")
            return

        print(f"\n✅ Trading suite initialized for {suite.instrument_info.id}")
        print(f"   Account: {suite.client.account_info.name}")

        # =========================================================================
        # GENERATE SOME TRADING ACTIVITY FOR STATISTICS
        # =========================================================================
        print("\n" + "=" * 60)
        print("1. GENERATING TRADING ACTIVITY FOR STATISTICS")
        print("=" * 60)

        print("\n📈 Placing test orders to generate statistics...")

        # Get current price for placing limit orders
        current_price = await suite.data.get_current_price()
        if not current_price:
            bars = await suite.data.get_data("1min")
            if bars is not None and not bars.is_empty():
                current_price = Decimal(str(bars[-1]["close"]))
            else:
                current_price = Decimal("20000")

        print(f"   Current {suite.instrument_info.id} price: ${current_price:,.2f}")

        # Place some test orders (far from market to avoid fills)
        test_orders = []

        # Buy orders below market
        for i in range(3):
            price = float(current_price) - (50 + i * 50)
            price = utils.round_to_tick_size(
                float(price), suite.instrument_info.tickSize
            )

            print(f"\n   Placing buy limit order at ${price:,.2f}...")
            order = await suite.orders.place_limit_order(
                contract_id=suite.instrument_info.id,
                side=0,  # Buy
                size=1,
                limit_price=float(price),
            )
            test_orders.append(order)
            print(f"   ✅ Order placed: {order.orderId}")

        # Sell orders above market
        for i in range(2):
            price = float(current_price) + (50 + i * 50)
            price = utils.round_to_tick_size(
                float(price), suite.instrument_info.tickSize
            )

            print(f"\n   Placing sell limit order at ${price:,.2f}...")
            order = await suite.orders.place_limit_order(
                contract_id=suite.instrument_info.id,
                side=1,  # Sell
                size=1,
                limit_price=float(price),
            )
            test_orders.append(order)
            print(f"   ✅ Order placed: {order.orderId}")

        # =========================================================================
        # 2. COMPONENT-LEVEL STATISTICS
        # =========================================================================
        print("\n" + "=" * 60)
        print("2. COMPONENT-LEVEL STATISTICS")
        print("=" * 60)

        # Get order manager statistics (v3.3.0 - async API)
        if hasattr(suite.orders, "get_order_statistics_async"):
            order_stats = await suite.orders.get_order_statistics_async()
            print("\n📊 Order Manager Statistics:")
            print(f"  Orders placed: {order_stats.get('orders_placed', 0)}")
            print(f"  Orders filled: {order_stats.get('orders_filled', 0)}")
            print(f"  Orders cancelled: {order_stats.get('orders_cancelled', 0)}")
            print(f"  Orders rejected: {order_stats.get('orders_rejected', 0)}")
            fill_rate = order_stats.get("fill_rate", 0.0)
            print(f"  Fill rate: {fill_rate:.1%}")
            avg_fill_time = order_stats.get("avg_fill_time_ms", 0.0)
            print(f"  Avg fill time: {avg_fill_time:.2f}ms")

        # Get position manager statistics (v3.3.0 - async API)
        if hasattr(suite.positions, "get_position_stats"):
            position_stats = await suite.positions.get_position_stats()
            print("\n📊 Position Manager Statistics:")
            print(f"  Positions tracked: {position_stats.get('total_positions', 0)}")
            total_pnl = position_stats.get("total_pnl", 0.0)
            print(f"  Total P&L: ${total_pnl:.2f}")
            win_rate = position_stats.get("win_rate", 0.0)
            print(f"  Win rate: {win_rate:.1%}")

        # Get data manager statistics (v3.3.0 - sync API for data manager)
        if hasattr(suite.data, "get_memory_stats"):
            data_stats = (
                await suite.data.get_memory_stats()
            )  # Note: sync method for data manager
            print("\n📊 Data Manager Statistics:")
            print(f"  Bars processed: {data_stats.get('total_bars', 0)}")
            print(f"  Ticks processed: {data_stats.get('ticks_processed', 0)}")
            print(f"  Quotes processed: {data_stats.get('quotes_processed', 0)}")
            memory_mb = data_stats.get("memory_usage_mb", 0.0)
            print(f"  Memory usage: {memory_mb:.2f}MB")
            quality_score = data_stats.get("data_quality_score", 100.0)
            print(f"  Data quality score: {quality_score:.1f}/100")

        # =========================================================================
        # 3. AGGREGATED STATISTICS WITH v3.3.0 ARCHITECTURE
        # =========================================================================
        print("\n" + "=" * 60)
        print("3. AGGREGATED STATISTICS (v3.3.0 Feature)")
        print("=" * 60)

        # Use the new v3.3.0 statistics aggregator
        from project_x_py.statistics.aggregator import StatisticsAggregator

        aggregator = StatisticsAggregator()
        comprehensive_stats = await aggregator.get_comprehensive_stats()

        if comprehensive_stats:
            print("\n⚡ System Performance Metrics:")

            # Health metrics
            health = comprehensive_stats.get("health", {})
            if health:
                print(f"  Overall Health Score: {health.get('score', 0)}/100")
                print(f"  System Status: {health.get('status', 'unknown')}")
                print(f"  Component Health: {health.get('component_health', {})}")

            # Performance metrics
            performance = comprehensive_stats.get("performance", {})
            if performance:
                print("\n  Performance Metrics:")
                print(
                    f"    Average Latency: {performance.get('avg_latency_ms', 0):.2f}ms"
                )
                print(
                    f"    Operations/sec: {performance.get('operations_per_second', 0):.2f}"
                )
                print(f"    Success Rate: {performance.get('success_rate', 0):.1%}")

            # Memory metrics
            memory = comprehensive_stats.get("memory", {})
            if memory:
                print("\n  Memory Usage:")
                print(f"    Total: {memory.get('total_mb', 0):.2f}MB")
                print(f"    Available: {memory.get('available_mb', 0):.2f}MB")
                print(f"    Utilization: {memory.get('utilization_percent', 0):.1f}%")

        # =========================================================================
        # 4. MULTI-FORMAT EXPORT (v3.3.0 Feature)
        # =========================================================================
        print("\n" + "=" * 60)
        print("4. MULTI-FORMAT EXPORT")
        print("=" * 60)

        from project_x_py.statistics.export import StatsExporter

        exporter = StatsExporter()

        # Export to JSON
        json_stats = await exporter.export(comprehensive_stats)
        print("\n📄 JSON Export (sample):")
        json_str = json.dumps(json_stats, indent=2)
        for line in json_str.split("\n")[:5]:
            print(f"  {line}")
        print("  ...")

        # Export to Prometheus format
        prom_stats = await exporter.export(comprehensive_stats, format="prometheus")
        print("\n📊 Prometheus Export (first 5 metrics):")
        if isinstance(prom_stats, str):
            for line in prom_stats.split("\n")[:5]:
                if line:
                    print(f"  {line}")
        else:
            # Handle dict return - convert to key=value format
            for i, (key, value) in enumerate(prom_stats.items()):
                if i >= 5:
                    break
                print(f"  {key}={value}")

        # Export to CSV
        csv_stats = await exporter.export(comprehensive_stats, format="csv")
        print("\n📊 CSV Export (header + 2 rows):")
        if isinstance(csv_stats, str):
            for line in csv_stats.split("\n")[:3]:
                if line:
                    print(f"  {line}")
        else:
            # Handle dict return - convert to key=value format
            for i, (key, value) in enumerate(csv_stats.items()):
                if i >= 3:
                    break
                print(f"  {key}={value}")

        # Save to file
        with open("trading_stats.json", "w") as f:
            json.dump(json_stats, f, indent=2)
        print("\n✅ Statistics exported to trading_stats.json")

        # =========================================================================
        # 5. MONITORING & ALERTING
        # =========================================================================
        print("\n" + "=" * 60)
        print("5. MONITORING & ALERTING")
        print("=" * 60)

        # Check for errors in the aggregated statistics
        errors = comprehensive_stats.get("errors", {})
        if errors.get("total_errors", 0) > 0:
            print("\n⚠️ Errors detected:")
            print(f"  Total errors: {errors.get('total_errors', 0)}")
            error_rate = errors.get("error_rate", 0.0)
            print(f"  Error rate: {error_rate:.2%}")
            recent_errors = errors.get("recent_errors", [])
            if recent_errors:
                print("  Recent errors:")
                for error in recent_errors[:3]:
                    print(
                        f"    - {error.get('timestamp', 'N/A')}: {error.get('message', 'N/A')}"
                    )

        # Check system health
        health_score = health.get("score", 100) if health else 100
        if health_score < 80:
            print("\n⚠️ System health below optimal threshold")
            print("  Recommended actions:")
            print("  - Check connection stability")
            print("  - Review error logs")
            print("  - Monitor memory usage")

        # =========================================================================
        # 6. ADAPTIVE STRATEGY EXAMPLE
        # =========================================================================
        print("\n" + "=" * 60)
        print("6. ADAPTIVE STRATEGY BASED ON STATISTICS")
        print("=" * 60)

        # Adjust trading based on system health
        if health_score >= 90:
            print("\n✅ System health excellent - normal trading mode")
            print("  - Full position sizes allowed")
            print("  - Tight stops enabled")
            print("  - All strategies active")
        elif health_score >= 70:
            print("\n⚠️ System health degraded - cautious mode")
            print("  - Reduced position sizes (75%)")
            print("  - Wider stops")
            print("  - Conservative strategies only")
        else:
            print("\n🛑 System health critical - safe mode")
            print("  - Minimal position sizes (25%)")
            print("  - Emergency stops only")
            print("  - Close existing positions")

        # Check performance for latency issues
        if performance and performance.get("avg_latency_ms", 0) > 500:
            print("\n⚠️ High latency detected - optimizing order placement")
            print("  - Switching to limit orders only")
            print("  - Increasing price buffers")
            print("  - Reducing order frequency")

    except Exception as e:
        print(f"\n❌ Error during example execution: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # =========================================================================
        # CLEANUP - ENSURE NO OPEN ORDERS OR POSITIONS
        # =========================================================================
        print("\n" + "=" * 60)
        print("CLEANUP - ENSURING NO OPEN ORDERS OR POSITIONS")
        print("=" * 60)

        if suite:
            try:
                # Cancel test orders
                if "test_orders" in locals() and test_orders:
                    print(f"\n🧹 Cancelling {len(test_orders)} test orders...")
                    for order in test_orders:
                        try:
                            await suite.orders.cancel_order(order.id)
                            print(f"   ✅ Cancelled order {order.id}")
                        except Exception as e:
                            print(f"   ⚠️ Could not cancel order {order.id}: {e}")

                # Check for any remaining open orders
                print("\n🔍 Checking for any remaining open orders...")
                open_orders = await suite.orders.search_open_orders()
                if open_orders:
                    print(f"   ⚠️ Found {len(open_orders)} open orders, cancelling...")
                    for order in open_orders:
                        try:
                            await suite.orders.cancel_order(order.id)
                            print(f"   ✅ Cancelled order {order.id}")
                        except Exception as e:
                            print(f"   ⚠️ Could not cancel order {order.id}: {e}")
                else:
                    print("   ✅ No open orders found")

                # Check for open positions
                print("\n🔍 Checking for open positions...")
                positions = await suite.positions.get_all_positions()
                if positions:
                    print(f"   ⚠️ Found {len(positions)} open positions")
                    for pos in positions:
                        print(f"      - {pos.contractId}: {pos.size} contracts")
                else:
                    print("   ✅ No open positions found")

                print("\n✅ Cleanup successful!")

            except Exception as e:
                print(f"\n⚠️ Error during cleanup: {e}")

            # Disconnect
            print("\n" + "=" * 60)
            print("Disconnecting...")
            await suite.disconnect()
            print("✅ Example complete!")

        print("\nKey Takeaways:")
        print("• SDK provides comprehensive statistics without UI components")
        print("• All statistics are easily accessible via async methods")
        print("• Export formats support external monitoring systems")
        print("• Statistics can drive adaptive strategy behavior")
        print("• Memory and performance metrics help prevent issues")
        print("• Always clean up open orders and positions on exit")


if __name__ == "__main__":
    asyncio.run(main())
