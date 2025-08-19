#!/usr/bin/env python3
"""
Test script for enhanced statistics tracking in v3.2.1.

This script creates a TradingSuite and tests the new statistics
aggregation functionality.
"""

import asyncio
import json
from datetime import datetime

from project_x_py import TradingSuite


async def main():
    """Test enhanced statistics."""
    print("Testing Enhanced Statistics Tracking (v3.2.1)")
    print("=" * 60)

    # Create suite with all features
    print("\n1. Creating TradingSuite...")
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["1min", "5min"],
        features=["orderbook", "risk_manager"],
        initial_days=1,
    )
    print(f"   ✓ Suite created for: {suite.client.account_info.name}")

    # Wait for some data to accumulate
    print("\n2. Letting data accumulate...")
    await asyncio.sleep(3)

    # Get comprehensive stats
    print("\n3. Getting aggregated statistics...")
    stats = await suite.get_stats()

    # Display key metrics
    print("\n4. Key Metrics:")
    print(f"   - Instrument: {stats.get('instrument', 'N/A')}")
    print(f"   - Status: {stats.get('status', 'N/A')}")
    print(f"   - Connected: {stats.get('connected', False)}")
    print(f"   - Uptime: {stats.get('uptime_seconds', 0)} seconds")
    print(f"   - Health Score: {stats.get('health_score', 0):.1f}/100")

    # Display component stats
    print("\n5. Component Statistics:")
    components = stats.get("components", {})
    for comp_name, comp_stats in components.items():
        print(f"\n   {comp_stats.get('name', comp_name)}:")
        print(f"     - Status: {comp_stats.get('status', 'N/A')}")
        print(f"     - Memory: {comp_stats.get('memory_usage_mb', 0):.2f} MB")
        print(f"     - Errors: {comp_stats.get('error_count', 0)}")

        # Show performance metrics if available
        perf = comp_stats.get("performance_metrics", {})
        if perf:
            print(f"     - Performance Metrics:")
            for key, value in perf.items():
                if isinstance(value, (int, float)):
                    print(f"       • {key}: {value}")

    # Display network stats
    print("\n6. Network Statistics:")
    print(f"   - Total API Calls: {stats.get('total_api_calls', 0)}")
    print(f"   - Successful: {stats.get('successful_api_calls', 0)}")
    print(f"   - Failed: {stats.get('failed_api_calls', 0)}")
    print(f"   - Cache Hit Rate: {stats.get('cache_hit_rate', 0):.1%}")
    print(f"   - Avg Response Time: {stats.get('avg_response_time_ms', 0):.2f} ms")

    # Display realtime connection stats
    print("\n7. Real-time Connection:")
    print(f"   - WebSocket Connected: {stats.get('realtime_connected', False)}")
    print(f"   - User Hub: {stats.get('user_hub_connected', False)}")
    print(f"   - Market Hub: {stats.get('market_hub_connected', False)}")
    print(f"   - Active Subscriptions: {stats.get('active_subscriptions', 0)}")

    # Test placing an order to generate stats
    print("\n8. Testing order placement for stats...")
    try:
        # Get current price
        current_price = await suite.data.get_current_price()
        if current_price:
            print(f"   Current price: ${current_price:,.2f}")

            # Place a limit order well below market
            order = await suite.orders.place_limit_order(
                contract_id=suite.instrument_id,
                side=0,  # Buy
                size=1,
                limit_price=current_price - 500,  # Far from market
            )
            print(f"   ✓ Order placed: {order.orderId}")

            # Cancel it immediately
            await suite.orders.cancel_order(order.orderId)
            print(f"   ✓ Order cancelled")

            # Get updated stats
            await asyncio.sleep(1)
            updated_stats = await suite.get_stats()

            # Show OrderManager stats
            om_stats = updated_stats.get("components", {}).get("order_manager", {})
            if om_stats:
                print(f"\n   Updated OrderManager Stats:")
                print(f"     - Memory: {om_stats.get('memory_usage_mb', 0):.2f} MB")
                print(f"     - Errors: {om_stats.get('error_count', 0)}")

                perf = om_stats.get("performance_metrics", {})
                if perf and "operation_stats" in perf:
                    op_stats = perf["operation_stats"]
                    if "place_order" in op_stats:
                        po_stats = op_stats["place_order"]
                        print(f"     - Place Order Performance:")
                        print(f"       • Count: {po_stats.get('count', 0)}")
                        print(f"       • Avg: {po_stats.get('avg_ms', 0):.2f} ms")
                        print(f"       • Min: {po_stats.get('min_ms', 0):.2f} ms")
                        print(f"       • Max: {po_stats.get('max_ms', 0):.2f} ms")
    except Exception as e:
        print(f"   ⚠️ Order test failed: {e}")

    # Export stats in different formats
    print("\n9. Exporting statistics...")

    # Get JSON export
    if hasattr(suite.orders, "export_stats"):
        json_export = await suite.orders.export_stats(format="json")
        print(f"   ✓ JSON export available ({len(json.dumps(json_export))} bytes)")

        # Get Prometheus export
        prom_export = await suite.orders.export_stats(format="prometheus")
        print(f"   ✓ Prometheus export available ({len(prom_export)} bytes)")
    else:
        print("   ⚠️ Export not available (will be in next update)")

    # Clean up
    print("\n10. Cleaning up...")
    await suite.disconnect()
    print("   ✓ Suite disconnected")

    print("\n" + "=" * 60)
    print("✅ Enhanced Statistics Test Complete!")
    print(f"   Total Memory Usage: {stats.get('memory_usage_mb', 0):.2f} MB")
    print(f"   Health Score: {stats.get('health_score', 0):.1f}/100")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
