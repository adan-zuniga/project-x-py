"""
Example demonstrating comprehensive statistics collection and monitoring.

This example shows how to:
1. Collect real-time performance metrics
2. Monitor error rates and types
3. Track memory usage across components
4. Export statistics for external monitoring
5. Use statistics to make strategy decisions

Author: SDK Team
Date: 2024-12-20
"""

import asyncio

from project_x_py import TradingSuite


async def cleanup_trading_activity(suite, orders_placed):
    """Clean up any open orders and positions."""
    print("\n" + "=" * 60)
    print("CLEANUP - ENSURING NO OPEN ORDERS OR POSITIONS")
    print("=" * 60)

    cleanup_successful = True

    # Cancel any open orders
    if orders_placed:
        print(f"\n🧹 Cancelling {len(orders_placed)} test orders...")
        for order_id in orders_placed:
            try:
                await suite.orders.cancel_order(order_id)
                print(f"   ✅ Cancelled order {order_id}")
            except Exception as e:
                print(f"   ⚠️ Error cancelling order {order_id}: {e}")
                cleanup_successful = False

    # Check for any remaining open orders
    try:
        print("\n🔍 Checking for any remaining open orders...")
        open_orders = await suite.orders.search_open_orders()
        if open_orders:
            print(f"   Found {len(open_orders)} open orders, cancelling all...")
            cancelled = await suite.orders.cancel_all_orders()
            print(f"   ✅ Cancelled {cancelled} orders")
    except Exception as e:
        print(f"   ⚠️ Error checking/cancelling open orders: {e}")
        cleanup_successful = False

    # Close any open positions
    try:
        print("\n🔍 Checking for open positions...")
        positions = await suite.positions.get_all_positions()
        if positions:
            print(f"   Found {len(positions)} open positions")
            for position in positions:
                try:
                    print(f"   Closing position in {position.symbol}...")
                    # Place market order to close position
                    close_size = abs(position.netPos)
                    close_side = (
                        1 if position.netPos > 0 else 0
                    )  # Sell if long, Buy if short

                    response = await suite.orders.place_market_order(
                        contract_id=position.contractId,
                        side=close_side,
                        size=close_size,
                    )
                    if response.success:
                        print(f"   ✅ Placed closing order for {position.symbol}")
                    else:
                        print(f"   ⚠️ Failed to close position: {response.message}")
                        cleanup_successful = False
                except Exception as e:
                    print(f"   ⚠️ Error closing position {position.symbol}: {e}")
                    cleanup_successful = False
        else:
            print("   ✅ No open positions found")
    except Exception as e:
        print(f"   ⚠️ Error checking positions: {e}")
        cleanup_successful = False

    # Wait for orders to process
    if not cleanup_successful:
        print("\n⏳ Waiting for cleanup to process...")
        await asyncio.sleep(2)

    return cleanup_successful


async def main():
    """Demonstrate statistics usage throughout the SDK."""

    print("=" * 60)
    print("ProjectX SDK Statistics Usage Example")
    print("=" * 60)

    suite = None
    orders_placed = []

    try:
        # Create trading suite with all components
        suite = await TradingSuite.create(
            instrument="MNQ",
            timeframes=["1min", "5min"],
            features=["orderbook", "risk_manager"],  # All features enabled
            initial_days=1,
        )

        print(f"\n✅ Trading suite initialized for {suite.instrument}")
        if suite.client.account_info:
            print(f"   Account: {suite.client.account_info.name}")

        # =========================================================================
        # 1. GENERATE REAL TRADING ACTIVITY
        # =========================================================================
        print("\n" + "=" * 60)
        print("1. GENERATING TRADING ACTIVITY FOR STATISTICS")
        print("=" * 60)

        print("\n📈 Placing test orders to generate statistics...")

        # Get current market price
        current_price = await suite.data.get_current_price()
        if current_price:
            print(f"   Current {suite.instrument} price: ${current_price:,.2f}")
        else:
            # Fallback to a reasonable test price if market is closed
            current_price = 20000.0
            print(f"   Using test price: ${current_price:,.2f}")

        # Place buy limit orders below market
        for i in range(3):
            offset = 50 * (i + 1)  # 50, 100, 150 points below
            limit_price = current_price - offset

            print(f"\n   Placing buy limit order at ${limit_price:,.2f}...")
            response = await suite.orders.place_limit_order(
                contract_id=str(suite.instrument_id),
                side=0,  # Buy
                size=1,
                limit_price=limit_price,
            )

            if response.success:
                orders_placed.append(response.orderId)
                print(f"   ✅ Order placed: {response.orderId}")

                # Track custom operation
                if hasattr(suite.orders, "track_operation"):
                    await suite.orders.track_operation(
                        "example_limit_order",
                        15.5 + i * 2,  # Simulate varying latencies
                        success=True,
                        metadata={"offset": offset},
                    )
            else:
                print(f"   ❌ Order failed: {response.errorMessage}")
                # Track error
                if hasattr(suite.orders, "track_error"):
                    await suite.orders.track_error(
                        ValueError(f"Order placement failed: {response.errorMessage}"),
                        context="example_order_placement",
                    )

        # Place sell limit orders above market
        for i in range(2):
            offset = 50 * (i + 1)
            limit_price = current_price + offset

            print(f"\n   Placing sell limit order at ${limit_price:,.2f}...")
            response = await suite.orders.place_limit_order(
                contract_id=str(suite.instrument_id),
                side=1,  # Sell
                size=1,
                limit_price=limit_price,
            )

            if response.success:
                orders_placed.append(response.orderId)
                print(f"   ✅ Order placed: {response.orderId}")

        # =========================================================================
        # 2. COMPONENT-LEVEL STATISTICS
        # =========================================================================
        print("\n" + "=" * 60)
        print("2. COMPONENT-LEVEL STATISTICS")
        print("=" * 60)

        # Get order manager statistics
        if hasattr(suite.orders, "get_order_statistics"):
            order_stats = suite.orders.get_order_statistics()
            print("\n📊 Order Manager Statistics:")
            print(f"  Orders placed: {order_stats['orders_placed']}")
            print(f"  Orders filled: {order_stats['orders_filled']}")
            print(f"  Orders cancelled: {order_stats['orders_cancelled']}")
            print(f"  Orders rejected: {order_stats['orders_rejected']}")
            print(f"  Fill rate: {order_stats['fill_rate']:.1%}")
            print(f"  Avg fill time: {order_stats['avg_fill_time_ms']:.2f}ms")

        # Get position manager statistics
        if hasattr(suite.positions, "get_position_statistics"):
            position_stats = suite.positions.get_position_statistics()
            print("\n📊 Position Manager Statistics:")
            print(f"  Positions tracked: {position_stats['total_positions']}")
            print(f"  Total P&L: ${position_stats['total_pnl']:.2f}")
            print(f"  Win rate: {position_stats['win_rate']:.1%}")

        # Get data manager statistics
        if hasattr(suite.data, "get_memory_stats"):
            data_stats = suite.data.get_memory_stats()
            print("\n📊 Data Manager Statistics:")
            print(f"  Bars processed: {data_stats.get('total_bars', 0)}")
            print(f"  Ticks processed: {data_stats.get('ticks_processed', 0)}")
            print(f"  Quotes processed: {data_stats.get('quotes_processed', 0)}")
            print(f"  Memory usage: {data_stats.get('memory_usage_mb', 0):.2f}MB")

        # =========================================================================
        # 3. ENHANCED PERFORMANCE METRICS
        # =========================================================================
        print("\n" + "=" * 60)
        print("3. ENHANCED PERFORMANCE METRICS")
        print("=" * 60)

        if hasattr(suite.orders, "get_performance_metrics"):
            perf_metrics = suite.orders.get_performance_metrics()

            print("\n⚡ Order Manager Performance:")

            # Operation-level metrics
            if "operation_stats" in perf_metrics:
                for op_name, op_stats in perf_metrics["operation_stats"].items():
                    print(f"\n  {op_name}:")
                    print(f"    Count: {op_stats['count']}")
                    print(f"    Avg: {op_stats['avg_ms']:.2f}ms")
                    print(f"    P50: {op_stats['p50_ms']:.2f}ms")
                    print(f"    P95: {op_stats['p95_ms']:.2f}ms")
                    print(f"    P99: {op_stats['p99_ms']:.2f}ms")

            # Network performance
            if "network_stats" in perf_metrics:
                net_stats = perf_metrics["network_stats"]
                print("\n  Network Performance:")
                print(f"    Total requests: {net_stats['total_requests']}")
                print(f"    Success rate: {net_stats['success_rate']:.1%}")
                print(f"    WebSocket reconnects: {net_stats['websocket_reconnects']}")

        # =========================================================================
        # 4. AGGREGATED SUITE STATISTICS
        # =========================================================================
        print("\n" + "=" * 60)
        print("4. AGGREGATED SUITE STATISTICS")
        print("=" * 60)

        # Get aggregated statistics from all components
        suite_stats = await suite.get_stats()

        print("\n🎯 Trading Suite Overview:")
        print(f"  Health Score: {suite_stats.get('health_score', 0):.1f}/100")
        print(f"  Total API Calls: {suite_stats.get('total_api_calls', 0)}")
        print(f"  Cache Hit Rate: {suite_stats.get('cache_hit_rate', 0):.1%}")
        print(f"  Active Subscriptions: {suite_stats.get('active_subscriptions', 0)}")
        print(f"  WebSocket Connected: {suite_stats.get('realtime_connected', False)}")

        # Cross-component metrics
        print("\n🔄 Cross-Component Metrics:")
        total_operations = sum(
            len(comp.get("performance_metrics", {}).get("operation_stats", {}))
            for comp in suite_stats.get("components", {}).values()
            if isinstance(comp, dict)
        )
        print(f"  Total operations: {total_operations}")

        error_rate = suite_stats.get("total_errors", 0) / max(
            suite_stats.get("total_api_calls", 1), 1
        )
        print(f"  Overall error rate: {error_rate:.2%}")
        print(f"  Total memory: {suite_stats.get('memory_usage_mb', 0):.2f}MB")

        # =========================================================================
        # 5. EXPORT FOR EXTERNAL MONITORING
        # =========================================================================
        print("\n" + "=" * 60)
        print("5. EXPORT FOR EXTERNAL MONITORING")
        print("=" * 60)

        # Export statistics in different formats
        if hasattr(suite.orders, "export_stats"):
            # JSON export for logging/storage
            json_stats = suite.orders.export_stats("json")

            print("\n📄 JSON Export (sample):")
            # Show a subset of the JSON export
            if isinstance(json_stats, dict):
                export_sample = {
                    "timestamp": json_stats.get("timestamp"),
                    "component": json_stats.get("component"),
                    "performance": {
                        "uptime_seconds": json_stats.get("performance", {}).get(
                            "uptime_seconds"
                        ),
                        "api_stats": {
                            "count": len(
                                json_stats.get("performance", {})
                                .get("operation_stats", {})
                                .keys()
                            )
                        },
                    },
                    "errors": {
                        "total_errors": json_stats.get("errors", {}).get(
                            "total_errors"
                        ),
                        "errors_last_hour": json_stats.get("errors", {}).get(
                            "errors_last_hour"
                        ),
                    },
                }
            else:
                export_sample = {"error": "Invalid export format"}
                print("  Error: JSON export returned unexpected format")

            import json

            print(json.dumps(export_sample, indent=2))

            # Prometheus export for monitoring systems
            prometheus_stats = suite.orders.export_stats("prometheus")

            print("\n📊 Prometheus Export (sample):")
            # Show first few lines of Prometheus format
            lines = (
                prometheus_stats.split("\n")[:5]
                if isinstance(prometheus_stats, str)
                else []
            )
            for line in lines:
                print(f"  {line}")

        # =========================================================================
        # 6. ERROR TRACKING
        # =========================================================================
        print("\n" + "=" * 60)
        print("6. ERROR TRACKING")
        print("=" * 60)

        if hasattr(suite.orders, "get_error_stats"):
            error_stats = suite.orders.get_error_stats()

            print("\n❌ Error Statistics:")
            print(f"  Total errors: {error_stats['total_errors']}")
            print(f"  Errors in last hour: {error_stats['errors_last_hour']}")

            if error_stats["error_types"]:
                print(f"  Error types: {', '.join(error_stats['error_types'].keys())}")
            else:
                print("  Error types: None")

            if error_stats.get("recent_errors"):
                print("\n  Recent errors:")
                for error in error_stats["recent_errors"][-3:]:  # Show last 3 errors
                    print(f"    - {error['error_type']}: {error['message']}")

        # =========================================================================
        # 7. MEMORY MANAGEMENT
        # =========================================================================
        print("\n" + "=" * 60)
        print("7. MEMORY MANAGEMENT")
        print("=" * 60)

        print("\n💾 Memory Usage by Component:")

        # Check memory for each component
        total_memory = 0.0
        components = [
            ("Orders", suite.orders),
            ("Positions", suite.positions),
            ("Data", suite.data),
            ("Risk", suite.risk_manager),
            ("OrderBook", suite.orderbook),
        ]

        for name, component in components:
            if not component:
                continue

            if hasattr(component, "get_enhanced_memory_stats"):
                mem_stats = component.get_enhanced_memory_stats()
                memory_mb = mem_stats["current_memory_mb"]
                total_memory += memory_mb
                print(f"  {name}: {memory_mb:.3f}MB")
            elif hasattr(component, "get_memory_stats"):
                # get_memory_stats is now consistently synchronous across all components
                mem_stats = component.get_memory_stats()
                memory_mb = mem_stats.get("memory_usage_mb", 0)
                total_memory += memory_mb
                print(f"  {name}: {memory_mb:.3f}MB")

        print(f"  Total: {total_memory:.3f}MB")

        # =========================================================================
        # 8. DATA QUALITY METRICS
        # =========================================================================
        print("\n" + "=" * 60)
        print("8. DATA QUALITY METRICS")
        print("=" * 60)

        if hasattr(suite.data, "get_data_quality_stats"):
            quality_stats = suite.data.get_data_quality_stats()

            print("\n📊 Data Quality:")
            print(f"  Quality Score: {quality_stats['quality_score']:.1f}%")
            print(f"  Invalid Rate: {quality_stats['invalid_rate']:.2%}")
            print(f"  Total Points: {quality_stats['total_data_points']}")
            print(f"  Invalid Points: {quality_stats['invalid_data_points']}")

        # =========================================================================
        # 9. FINAL STATISTICS SUMMARY
        # =========================================================================
        print("\n" + "=" * 60)
        print("9. FINAL STATISTICS SUMMARY")
        print("=" * 60)

        # Get final statistics after all operations
        final_order_stats = suite.orders.get_order_statistics()

        print("\n📊 Session Summary:")
        print(f"  Total orders placed: {final_order_stats['orders_placed']}")
        print(f"  Total orders cancelled: {final_order_stats['orders_cancelled']}")
        print(
            f"  Session duration: {suite.orders.get_performance_metrics().get('uptime_seconds', 0):.1f}s"
        )

        # Show how statistics can be used in strategy decisions
        print("\n💡 Using Statistics for Strategy Decisions:")

        if hasattr(suite.orders, "get_performance_metrics"):
            perf = suite.orders.get_performance_metrics()

            # Check network performance
            if "network_stats" in perf:
                success_rate = perf["network_stats"].get("success_rate", 0)

                if success_rate < 0.95:
                    print(f"  ⚠️ Low API success rate ({success_rate:.1%})")
                    print("     → Strategy should reduce order frequency")
                else:
                    print(f"  ✅ High API success rate ({success_rate:.1%})")
                    print("     → Strategy can maintain normal operation")

        # Check error rates
        if hasattr(suite.orders, "get_error_stats"):
            errors = suite.orders.get_error_stats()
            if errors["errors_last_hour"] > 10:
                print(f"  ⚠️ High error rate ({errors['errors_last_hour']} errors/hour)")
                print("     → Strategy should switch to safe mode")
            else:
                print(f"  ✅ Low error rate ({errors['errors_last_hour']} errors/hour)")
                print("     → Strategy can continue normal trading")

        # Check memory usage
        suite_stats = await suite.get_stats()
        total_mem = suite_stats.get("total_memory_mb", 0)
        if total_mem > 100:
            print(f"  ⚠️ High memory usage ({total_mem:.1f}MB)")
            print("     → Trigger cleanup or reduce data retention")
        else:
            print(f"  ✅ Normal memory usage ({total_mem:.1f}MB)")
            print("     → No memory concerns")

    except Exception as e:
        print(f"\n❌ Error during example execution: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Always clean up, even if there was an error
        if suite:
            # Perform cleanup
            cleanup_success = await cleanup_trading_activity(suite, orders_placed)

            if cleanup_success:
                print("\n✅ Cleanup successful!")
            else:
                print("\n⚠️ Cleanup completed with warnings")

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
