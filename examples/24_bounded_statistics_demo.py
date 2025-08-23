"""
Bounded Statistics Demo - Preventing Memory Leaks in Realtime Data

This example demonstrates the new bounded statistics functionality that prevents
memory leaks in high-frequency trading applications. The bounded statistics system
automatically rotates old data, aggregates historical metrics, and maintains
memory usage within configurable limits.

Key Features Demonstrated:
- Bounded counters with automatic rotation
- Circular buffers for timing data
- Automatic cleanup scheduling
- Memory usage monitoring
- High-frequency update performance
- Real-time data manager integration

Author: @TexasCoding
Date: 2025-08-22
"""

import asyncio
import time

from project_x_py.statistics.bounded_statistics import (
    BoundedCounter,
    BoundedStatisticsMixin,
    CircularBuffer,
)


class DemoComponent(BoundedStatisticsMixin):
    """Demo component showcasing bounded statistics."""

    def __init__(self, name: str):
        super().__init__(
            max_recent_metrics=1000,  # Keep 1000 recent data points
            hourly_retention_hours=24,  # 24 hours of hourly summaries
            daily_retention_days=30,  # 30 days of daily summaries
            timing_buffer_size=500,  # 500 timing measurements
            cleanup_interval_minutes=1.0,  # Cleanup every minute
        )
        self.name = name
        self.processed_count = 0

    async def simulate_trading_activity(self, duration_seconds: int = 30):
        """Simulate high-frequency trading activity."""
        print(f"\n🚀 Starting {duration_seconds}s trading simulation for {self.name}")

        start_time = time.time()
        end_time = start_time + duration_seconds

        while time.time() < end_time:
            # Simulate various trading events
            await self._simulate_tick_processing()
            await self._simulate_order_activity()
            await self._simulate_market_data()

            # Brief pause to simulate realistic timing
            await asyncio.sleep(0.01)  # 100 updates per second

            self.processed_count += 1

            # Log progress every 1000 events
            if self.processed_count % 1000 == 0:
                memory_info = await self._get_bounded_memory_usage()
                print(
                    f"  Processed {self.processed_count} events, "
                    f"Memory: {memory_info['total_mb']:.2f}MB"
                )

        elapsed = time.time() - start_time
        rate = self.processed_count / elapsed
        print(
            f"✅ Completed simulation: {self.processed_count} events "
            f"in {elapsed:.1f}s ({rate:.0f} events/sec)"
        )

    async def _simulate_tick_processing(self):
        """Simulate processing market ticks."""
        # Simulate tick processing latency (0.1 to 2.0ms)
        latency = 0.1 + (time.time() % 100) / 50  # Varies between 0.1-2.1ms

        await self.increment_bounded("ticks_processed", 1)
        await self.record_timing_bounded("tick_processing", latency)

        # Simulate occasional price movements
        if self.processed_count % 10 == 0:
            await self.set_gauge_bounded("current_price", 4500.0 + (time.time() % 100))

    async def _simulate_order_activity(self):
        """Simulate order management activity."""
        # Simulate occasional orders
        if self.processed_count % 50 == 0:
            await self.increment_bounded("orders_placed", 1)

            # Simulate order processing time (10-100ms)
            order_latency = 10.0 + (time.time() % 90)
            await self.record_timing_bounded("order_processing", order_latency)

            # Simulate order size (1-10 contracts)
            order_size = 1 + int(time.time() % 10)
            await self.set_gauge_bounded("last_order_size", order_size)

    async def _simulate_market_data(self):
        """Simulate market data processing."""
        # Simulate quotes
        if self.processed_count % 5 == 0:
            await self.increment_bounded("quotes_processed", 1)

            # Simulate bid-ask spread
            spread = 0.25 + (time.time() % 10) / 40  # 0.25-0.5 point spread
            await self.set_gauge_bounded("bid_ask_spread", spread)

        # Simulate trades
        if self.processed_count % 20 == 0:
            await self.increment_bounded("trades_processed", 1)

            # Simulate trade size
            trade_size = 1 + int(time.time() % 100)
            await self.set_gauge_bounded("last_trade_size", trade_size)


async def demonstrate_bounded_counters():
    """Demonstrate BoundedCounter functionality."""
    print("\n📊 Bounded Counter Demonstration")
    print("=" * 50)

    # Create a bounded counter with small limits for demo
    counter = BoundedCounter(
        max_size=100,  # Keep only 100 recent values
        ttl_seconds=10.0,  # 10-second TTL for demo
        name="demo_counter",
    )

    print("Adding 150 values to a counter with max_size=100...")

    # Add more values than the limit
    for i in range(150):
        await counter.increment(float(i + 1))
        if i % 30 == 0:
            current_count = await counter.get_current_count()
            current_sum = await counter.get_current_sum()
            print(
                f"  Added {i + 1} values, stored: {current_count}, sum: {current_sum:.0f}"
            )

    # Show final statistics
    stats = await counter.get_statistics()
    print("\nFinal Statistics:")
    print(f"  Current count: {stats['current_count']}")
    print(f"  Current sum: {stats['current_sum']:.0f}")
    print(f"  Current avg: {stats['current_avg']:.1f}")
    print(f"  Lifetime total: {stats['total_lifetime_count']}")
    print(f"  Memory usage: {stats['memory_usage_bytes']} bytes")

    # Demonstrate TTL expiration
    print("\nWaiting 12 seconds for TTL expiration...")
    await asyncio.sleep(12)

    expired_count = await counter.get_current_count()
    expired_sum = await counter.get_current_sum()
    print(f"After TTL expiration: count={expired_count}, sum={expired_sum}")


async def demonstrate_circular_buffers():
    """Demonstrate CircularBuffer functionality."""
    print("\n🔄 Circular Buffer Demonstration")
    print("=" * 50)

    # Create a circular buffer with small size for demo
    buffer = CircularBuffer(max_size=10, name="demo_buffer")

    print("Adding 15 values to a buffer with max_size=10...")

    # Add more values than the buffer size
    for i in range(15):
        await buffer.append(float(i + 1))
        size = await buffer.get_size()
        print(f"  Added value {i + 1}, buffer size: {size}")

    # Show recent values
    recent_values = await buffer.get_recent(3600)  # All values
    print(f"\nStored values: {recent_values}")

    # Show statistics
    stats = await buffer.get_statistics()
    print("\nBuffer Statistics:")
    print(f"  Count: {stats['count']}")
    print(f"  Sum: {stats['sum']:.0f}")
    print(f"  Average: {stats['avg']:.1f}")
    print(f"  Min: {stats['min']:.0f}")
    print(f"  Max: {stats['max']:.0f}")
    print(f"  Std Dev: {stats['std_dev']:.2f}")


async def demonstrate_high_frequency_performance():
    """Demonstrate performance with high-frequency updates."""
    print("\n⚡ High-Frequency Performance Test")
    print("=" * 50)

    component = DemoComponent("HighFrequencyDemo")

    # Test high-frequency updates
    num_updates = 10000
    print(f"Performing {num_updates:,} high-frequency updates...")

    start_time = time.time()

    for i in range(num_updates):
        await component.increment_bounded("high_freq_counter", 1)
        await component.record_timing_bounded("operation_time", float(i % 100))

        if i % 1000 == 0 and i > 0:
            elapsed = time.time() - start_time
            rate = i / elapsed
            print(f"  {i:,} updates in {elapsed:.1f}s ({rate:.0f} ops/sec)")

    end_time = time.time()
    total_duration = end_time - start_time
    final_rate = num_updates / total_duration

    print("\nPerformance Results:")
    print(f"  Total updates: {num_updates:,}")
    print(f"  Total time: {total_duration:.2f} seconds")
    print(f"  Average rate: {final_rate:.0f} operations/second")

    # Check final memory usage
    memory_info = await component._get_bounded_memory_usage()
    print(f"  Final memory usage: {memory_info['total_mb']:.2f}MB")

    # Show final statistics
    counter_stats = await component.get_bounded_counter_stats("high_freq_counter")
    timing_stats = await component.get_bounded_timing_stats("operation_time")

    if counter_stats:
        print("\nFinal Counter Stats:")
        print(f"  Stored count: {counter_stats['current_count']:,}")
        print(f"  Total lifetime: {counter_stats['total_lifetime_count']:,}")

    if timing_stats:
        print("\nFinal Timing Stats:")
        print(f"  Stored measurements: {timing_stats['count']:,}")
        print(f"  Average time: {timing_stats['avg']:.1f}ms")


async def demonstrate_realtime_integration():
    """Demonstrate integration with RealtimeDataManager."""
    print("\n🔌 RealtimeDataManager Integration")
    print("=" * 50)

    try:
        # Note: This would normally use real ProjectX client
        print("Creating RealtimeDataManager with bounded statistics enabled...")

        # For demo purposes, we'll just show the configuration
        config = {
            "use_bounded_statistics": True,
            "max_recent_metrics": 3600,  # 1 hour at 1 update/second
            "hourly_retention_hours": 24,
            "daily_retention_days": 30,
            "timing_buffer_size": 1000,
            "cleanup_interval_minutes": 5.0,
        }

        print("Configuration:")
        for key, value in config.items():
            print(f"  {key}: {value}")

        print("\nBounded statistics configuration prevents memory leaks by:")
        print("  • Limiting recent metrics to 3,600 values (1 hour)")
        print("  • Keeping 24 hours of hourly summaries")
        print("  • Keeping 30 days of daily summaries")
        print("  • Using circular buffers for timing data")
        print("  • Automatic cleanup every 5 minutes")
        print("  • Memory-bounded operation under high load")

    except Exception as e:
        print(f"Note: Full integration demo requires ProjectX authentication: {e}")


async def demonstrate_memory_bounded_operation():
    """Demonstrate that memory usage stays bounded under load."""
    print("\n🧠 Memory-Bounded Operation Test")
    print("=" * 50)

    component = DemoComponent("MemoryBoundedDemo")

    print("Running extended simulation to verify memory bounds...")

    # Track memory usage over time
    memory_measurements = []

    for cycle in range(5):
        print(f"\nCycle {cycle + 1}/5: Processing 5,000 events...")

        # Simulate high load
        for i in range(5000):
            await component.increment_bounded("events_processed", 1)
            await component.record_timing_bounded("event_latency", float(i % 1000))
            await component.set_gauge_bounded("active_connections", 10 + (i % 50))

        # Measure memory usage
        memory_info = await component._get_bounded_memory_usage()
        memory_measurements.append(memory_info["total_mb"])

        print(f"  Memory usage: {memory_info['total_mb']:.2f}MB")
        print(f"  Active counters: {memory_info['num_counters']}")
        print(f"  Active timing ops: {memory_info['num_timing_operations']}")
        print(f"  Active gauges: {memory_info['num_gauges']}")

    print("\nMemory Usage Summary:")
    print(f"  Initial: {memory_measurements[0]:.2f}MB")
    print(f"  Final: {memory_measurements[-1]:.2f}MB")
    print(f"  Peak: {max(memory_measurements):.2f}MB")
    print(f"  Average: {sum(memory_measurements) / len(memory_measurements):.2f}MB")

    if max(memory_measurements) < 10.0:  # Reasonable bound
        print("✅ Memory usage remained bounded under load")
    else:
        print("⚠️  Memory usage exceeded expected bounds")


async def main():
    """Run all bounded statistics demonstrations."""
    print("🎯 ProjectX SDK - Bounded Statistics Demonstration")
    print("=" * 60)
    print("This demo shows how bounded statistics prevent memory leaks")
    print("in high-frequency trading applications.")

    try:
        # Run individual demonstrations
        await demonstrate_bounded_counters()
        await demonstrate_circular_buffers()
        await demonstrate_high_frequency_performance()
        await demonstrate_memory_bounded_operation()
        await demonstrate_realtime_integration()

        print("\n🎉 All demonstrations completed successfully!")
        print("\nKey Benefits of Bounded Statistics:")
        print("  ✅ Prevents unlimited memory growth")
        print("  ✅ Maintains historical summaries")
        print("  ✅ Supports high-frequency updates")
        print("  ✅ Automatic cleanup and rotation")
        print("  ✅ Configurable memory limits")
        print("  ✅ Production-ready performance")

    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main())
