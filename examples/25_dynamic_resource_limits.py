#!/usr/bin/env python3
"""
Example: Dynamic Resource Limits with Adaptive Buffer Sizing

This example demonstrates the new dynamic resource limits feature that automatically
adjusts buffer sizes, cache limits, and concurrent task limits based on real-time
system resource availability.

Key Features Demonstrated:
- Automatic memory pressure detection
- Adaptive buffer sizing based on available memory
- Resource monitoring and statistics
- Manual override capabilities for production tuning

Author: @TexasCoding
Date: 2025-08-22
"""

import asyncio
import time

from project_x_py import TradingSuite


async def monitor_resource_usage(suite: TradingSuite, duration_seconds: int = 60):
    """
    Monitor resource usage over time and display statistics.

    Args:
        suite: TradingSuite instance
        duration_seconds: How long to monitor
    """
    print(f"\n📊 Monitoring resource usage for {duration_seconds} seconds...")
    print("=" * 60)

    start_time = time.time()
    iteration = 0

    while time.time() - start_time < duration_seconds:
        iteration += 1

        # Get current resource statistics
        resource_stats = await suite["MNQ"].data.get_resource_stats()
        memory_stats = await suite["MNQ"].data.get_memory_stats()

        print(f"\n📈 Iteration {iteration} ({time.time() - start_time:.1f}s elapsed)")
        print("-" * 40)

        # Display dynamic limits status
        if resource_stats.get("dynamic_limits_enabled"):
            current_limits = resource_stats.get("current_limits", {})
            system_resources = resource_stats.get("system_resources", {})

            print(f"🧠 Memory Pressure: {current_limits.get('memory_pressure', 0):.2f}")
            print(f"💻 CPU Pressure: {current_limits.get('cpu_pressure', 0):.2f}")
            print(
                f"📦 Buffer Limit: {current_limits.get('max_bars_per_timeframe', 'N/A'):,}"
            )
            print(f"⚡ Tick Buffer: {current_limits.get('tick_buffer_size', 'N/A'):,}")
            print(
                f"🔄 Concurrent Tasks: {current_limits.get('max_concurrent_tasks', 'N/A')}"
            )
            print(f"💾 Memory Limit: {current_limits.get('memory_limit_mb', 0):.1f} MB")
            print(
                f"📊 Scaling Reason: {current_limits.get('scaling_reason', 'unknown')}"
            )

            if system_resources:
                print(
                    f"🖥️  System Memory: {system_resources.get('memory_percent', 0):.1f}% used"
                )
                print(f"⚙️  System CPU: {system_resources.get('cpu_percent', 0):.1f}%")
                print(
                    f"🏭 Process Memory: {system_resources.get('process_memory_mb', 0):.1f} MB"
                )
        else:
            print("⚠️  Dynamic limits disabled - using static configuration")

        # Display current data usage
        print(f"📊 Total Bars Stored: {memory_stats.get('total_bars_stored', 0):,}")
        print(f"🎯 Buffer Utilization: {memory_stats.get('buffer_utilization', 0):.1%}")
        print(f"📈 Bars Processed: {memory_stats.get('bars_processed', 0):,}")
        print(f"⚡ Ticks Processed: {memory_stats.get('ticks_processed', 0):,}")

        # Wait before next iteration
        await asyncio.sleep(10)


async def simulate_memory_pressure(suite: TradingSuite):
    """
    Simulate memory pressure by requesting large amounts of data.

    Args:
        suite: TradingSuite instance
    """
    print("\n🧪 Simulating memory pressure...")
    print("Requesting large amounts of historical data to trigger adaptive scaling")

    try:
        # Request progressively larger amounts of data
        for days in [5, 10, 20, 30]:
            print(f"📥 Loading {days} days of historical data...")

            # This will load data and potentially trigger resource adjustments
            bars = await suite.client.get_bars(
                suite["MNQ"].instrument_info.symbolId, days=days
            )

            # Get updated resource stats
            resource_stats = await suite["MNQ"].data.get_resource_stats()
            current_limits = resource_stats.get("current_limits", {})

            print(f"   → Loaded {len(bars):,} bars")
            print(
                f"   → Memory pressure: {current_limits.get('memory_pressure', 0):.2f}"
            )
            print(
                f"   → Buffer limit: {current_limits.get('max_bars_per_timeframe', 'N/A'):,}"
            )

            await asyncio.sleep(2)

    except Exception as e:
        print(f"❌ Error during simulation: {e}")


async def demonstrate_manual_overrides(suite: TradingSuite):
    """
    Demonstrate manual resource override capabilities.

    Args:
        suite: TradingSuite instance
    """
    print("\n⚙️  Demonstrating manual resource overrides...")

    # Get current limits
    resource_stats = await suite["MNQ"].data.get_resource_stats()
    current_limits = resource_stats.get("current_limits", {})
    original_buffer_size = current_limits.get("max_bars_per_timeframe", 1000)

    print(f"📊 Original buffer size: {original_buffer_size:,}")

    # Apply manual override
    new_buffer_size = original_buffer_size * 2
    overrides = {
        "max_bars_per_timeframe": new_buffer_size,
        "tick_buffer_size": 5000,
    }

    print(f"🔧 Applying manual override: buffer size → {new_buffer_size:,}")
    await suite["MNQ"].data.override_resource_limits(overrides, duration_seconds=30)

    # Check updated limits
    resource_stats = await suite["MNQ"].data.get_resource_stats()
    current_limits = resource_stats.get("current_limits", {})

    print(
        f"✅ Override applied: {current_limits.get('max_bars_per_timeframe', 'N/A'):,}"
    )
    print("⏰ Override will expire in 30 seconds...")

    # Wait for override to expire
    await asyncio.sleep(35)

    # Check if override expired
    resource_stats = await suite["MNQ"].data.get_resource_stats()
    current_limits = resource_stats.get("current_limits", {})

    print(f"🔄 After expiry: {current_limits.get('max_bars_per_timeframe', 'N/A'):,}")


async def main():
    """Main example demonstrating dynamic resource limits."""
    print("=" * 60)
    print("🚀 Dynamic Resource Limits Example")
    print("=" * 60)
    print()
    print("This example demonstrates adaptive buffer sizing that automatically")
    print("adjusts based on system memory and CPU availability.")
    print()

    try:
        # Create TradingSuite with dynamic resource limits enabled
        print("🔗 Creating TradingSuite with dynamic resource limits...")
        suite = await TradingSuite.create(
            "MNQ",  # E-mini NASDAQ futures
            timeframes=["1min", "5min"],
            initial_days=5,
            # Dynamic resource configuration is enabled by default
            data_manager_config={
                "enable_dynamic_limits": True,
                "resource_config": {
                    "memory_target_percent": 20.0,  # Use 20% of available memory
                    "memory_pressure_threshold": 0.7,  # Scale down at 70% pressure
                    "monitoring_interval": 15.0,  # Monitor every 15 seconds
                },
            },
        )

        print("✅ TradingSuite created successfully!")

        # Display initial resource configuration
        resource_stats = await suite["MNQ"].data.get_resource_stats()
        config = resource_stats.get("configuration", {})

        print("\n⚙️  Resource Configuration:")
        print(f"   Memory Target: {config.get('memory_target_percent', 0):.1f}%")
        print(
            f"   Pressure Threshold: {config.get('memory_pressure_threshold', 0):.1f}"
        )
        print(f"   Monitoring Interval: {config.get('monitoring_interval', 0):.1f}s")

        # Wait for initial resource monitoring
        print("\n⏳ Waiting for initial resource monitoring...")
        await asyncio.sleep(5)

        # Show current resource status
        resource_stats = await suite["MNQ"].data.get_resource_stats()
        if resource_stats.get("current_limits"):
            current_limits = resource_stats["current_limits"]
            print("\n📊 Initial Resource Limits:")
            print(
                f"   Buffer Size: {current_limits.get('max_bars_per_timeframe', 'N/A'):,}"
            )
            print(f"   Tick Buffer: {current_limits.get('tick_buffer_size', 'N/A'):,}")
            print(f"   Memory Limit: {current_limits.get('memory_limit_mb', 0):.1f} MB")
            print(f"   Memory Pressure: {current_limits.get('memory_pressure', 0):.2f}")

        # Monitor resource usage over time
        await monitor_resource_usage(suite, duration_seconds=60)

        # Simulate memory pressure
        await simulate_memory_pressure(suite)

        # Demonstrate manual overrides
        await demonstrate_manual_overrides(suite)

        # Final resource statistics
        print("\n📊 Final Resource Statistics:")
        print("-" * 40)
        resource_stats = await suite["MNQ"].data.get_resource_stats()

        stats_summary = {
            "Resource Adjustments": resource_stats.get("resource_adjustments", 0),
            "Pressure Events": resource_stats.get("pressure_events", 0),
            "Scale Down Events": resource_stats.get("scale_down_events", 0),
            "Scale Up Events": resource_stats.get("scale_up_events", 0),
            "Override Events": resource_stats.get("override_events", 0),
            "Monitoring Errors": resource_stats.get("monitoring_errors", 0),
        }

        for metric, value in stats_summary.items():
            print(f"{metric}: {value}")

        print("\n✅ Dynamic resource limits demonstration completed!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Cleanup
        if "suite" in locals():
            print("\n🧹 Cleaning up...")
            await suite.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
