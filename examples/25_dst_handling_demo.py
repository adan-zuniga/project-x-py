#!/usr/bin/env python3
"""
DST (Daylight Saving Time) Transition Handling Demo

This example demonstrates how the project-x-py SDK automatically handles
DST transitions in real-time trading data. Shows spring forward (missing hour)
and fall back (duplicate hour) scenarios.

Features Demonstrated:
    - Automatic DST transition detection
    - Proper bar alignment during transitions
    - Spring forward handling (skips non-existent times)
    - Fall back handling (disambiguates duplicate times)
    - Cross-DST data integrity
    - DST event logging and monitoring

Author: @TexasCoding
Date: 2025-08-22
"""

import asyncio
import logging
from datetime import datetime, timedelta

import pytz

from project_x_py.realtime_data_manager.dst_handling import DSTHandlingMixin

# Configure logging to show DST events
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Enable DST-specific logging
dst_logger = logging.getLogger("project_x_py.realtime_data_manager.dst_handling.dst")
dst_logger.setLevel(logging.INFO)


class DSTDemoManager(DSTHandlingMixin):
    """Demo class showing DST handling capabilities."""

    def __init__(self, timezone_name="America/Chicago"):
        self.timezone = pytz.timezone(timezone_name)
        self.tick_size = 0.25
        self.logger = logging.getLogger(__name__)
        super().__init__()

    def _calculate_bar_time(self, timestamp, interval, unit):
        """Standard bar time calculation for demo."""
        if self.timezone is None:
            raise ValueError("Timezone is not set")

        if timestamp.tzinfo is None:
            timestamp = self.timezone.localize(timestamp)

        if unit == 2:  # Minutes
            minutes = (timestamp.minute // interval) * interval
            bar_time = timestamp.replace(minute=minutes, second=0, microsecond=0)
        else:
            raise ValueError("Demo only supports minute intervals")

        return bar_time


async def demo_dst_transition_detection():
    """Demonstrate DST transition detection."""
    print("\n" + "=" * 60)
    print("DST TRANSITION DETECTION DEMO")
    print("=" * 60)

    # Test different timezones
    timezones = [
        ("America/Chicago", "CME Futures Timezone"),
        ("America/New_York", "US Eastern Time"),
        ("Europe/London", "UK Time"),
        ("UTC", "Universal Time"),
        ("Asia/Tokyo", "Japan Time (No DST)"),
    ]

    for tz_name, description in timezones:
        print(f"\n{description} ({tz_name}):")
        manager = DSTDemoManager(tz_name)

        # Check DST status
        status = manager.get_dst_status()
        print(f"  Current DST Status: {status.get('is_dst', 'N/A')}")
        print(f"  UTC Offset: {status.get('utc_offset', 'N/A')}")

        # Predict next DST transition
        next_transition = manager.predict_next_dst_transition()
        if next_transition:
            transition_time, transition_type = next_transition
            print(
                f"  Next Transition: {transition_type} on {transition_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            print("  Next Transition: None (timezone doesn't observe DST)")


async def demo_spring_forward_handling():
    """Demonstrate spring forward (missing hour) handling."""
    print("\n" + "=" * 60)
    print("SPRING FORWARD (MISSING HOUR) DEMO")
    print("=" * 60)

    manager = DSTDemoManager("America/Chicago")

    # Spring forward 2025: March 9, 2:00 AM becomes 3:00 AM
    print("Simulating ticks around Spring Forward transition...")
    print("March 9, 2025: 2:00 AM becomes 3:00 AM (missing hour)")

    # Start 30 minutes before transition
    base_time = datetime(2025, 3, 9, 1, 30, 0)

    print("\nProcessing 5-minute bars around transition:")
    print(f"{'Tick Time':<20} {'Bar Time':<20} {'Status'}")
    print("-" * 60)

    for i in range(12):  # 1 hour of 5-minute intervals
        tick_time = base_time + timedelta(minutes=i * 5)

        try:
            bar_time = manager.handle_dst_bar_time(tick_time, 5, 2)

            if bar_time is None:
                status = "SKIPPED (Non-existent)"
                bar_time_str = "N/A"
            else:
                status = "OK"
                bar_time_str = bar_time.strftime("%Y-%m-%d %H:%M:%S")

            tick_time_str = tick_time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{tick_time_str:<20} {bar_time_str:<20} {status}")

        except Exception as e:
            print(f"{tick_time.strftime('%Y-%m-%d %H:%M:%S'):<20} {'ERROR':<20} {e!s}")


async def demo_fall_back_handling():
    """Demonstrate fall back (duplicate hour) handling."""
    print("\n" + "=" * 60)
    print("FALL BACK (DUPLICATE HOUR) DEMO")
    print("=" * 60)

    manager = DSTDemoManager("America/Chicago")

    # Fall back 2025: November 2, 2:00 AM becomes 1:00 AM
    print("Simulating ticks around Fall Back transition...")
    print("November 2, 2025: 2:00 AM becomes 1:00 AM (duplicate hour)")

    # Start before transition
    base_time = datetime(2025, 11, 2, 0, 30, 0)

    print("\nProcessing 5-minute bars around transition:")
    print(f"{'Tick Time':<20} {'Bar Time':<20} {'DST':<5} {'Status'}")
    print("-" * 65)

    for i in range(18):  # 1.5 hours of 5-minute intervals
        tick_time = base_time + timedelta(minutes=i * 5)

        try:
            # First, try to localize the time
            try:
                if manager.timezone is None:
                    raise ValueError("Timezone is not set")
                localized_time = manager.timezone.localize(tick_time)
                is_dst = localized_time.dst() != timedelta(0)
                dst_str = "Yes" if is_dst else "No"
                status = "OK"
            except pytz.AmbiguousTimeError:
                # Duplicate time - use standard time (DST=False)
                if manager.timezone is None:
                    continue

                localized_time = manager.timezone.localize(tick_time, is_dst=False)
                dst_str = "Ambig"
                status = "DISAMBIGUATED"
            except pytz.NonExistentTimeError:
                localized_time = None
                dst_str = "N/A"
                status = "NON-EXISTENT"

            if localized_time:
                bar_time = manager.handle_dst_bar_time(localized_time, 5, 2)
                bar_time_str = (
                    bar_time.strftime("%Y-%m-%d %H:%M:%S") if bar_time else "N/A"
                )
            else:
                bar_time_str = "N/A"

            tick_time_str = tick_time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"{tick_time_str:<20} {bar_time_str:<20} {dst_str:<5} {status}")

        except Exception as e:
            print(
                f"{tick_time.strftime('%Y-%m-%d %H:%M:%S'):<20} {'ERROR':<20} {'N/A':<5} {e!s}"
            )


async def demo_dst_event_logging():
    """Demonstrate DST event logging."""
    print("\n" + "=" * 60)
    print("DST EVENT LOGGING DEMO")
    print("=" * 60)

    manager = DSTDemoManager("America/Chicago")

    # Create a custom handler to capture DST log messages
    log_messages = []

    class LogCapture(logging.Handler):
        def emit(self, record):
            log_messages.append(record.getMessage())

    log_capture = LogCapture()
    manager.dst_logger.addHandler(log_capture)

    # Simulate various DST events
    print("Generating DST events...")

    # Spring forward event
    spring_time = datetime(2025, 3, 9, 2, 30, 0)
    manager.log_dst_event("SPRING_FORWARD", spring_time, "Non-existent time detected")

    # Fall back event
    fall_time = datetime(2025, 11, 2, 1, 30, 0)
    manager.log_dst_event("FALL_BACK", fall_time, "Ambiguous time disambiguated")

    # Transition detected
    manager.log_dst_event("TRANSITION_DETECTED", datetime.now(), "Upcoming DST change")

    # Bar skipped
    manager.log_dst_event(
        "BAR_SKIPPED", spring_time, "5min bar skipped during spring forward"
    )

    print(f"\nCaptured {len(log_messages)} DST log messages:")
    for i, message in enumerate(log_messages, 1):
        print(f"{i:2d}. {message}")


async def demo_performance_monitoring():
    """Demonstrate DST handling performance monitoring."""
    print("\n" + "=" * 60)
    print("DST PERFORMANCE MONITORING DEMO")
    print("=" * 60)

    manager = DSTDemoManager("America/Chicago")

    import time

    # Test performance with many DST checks
    test_times = []
    base_time = datetime(2025, 6, 15, 9, 0, 0)  # Normal trading day

    # Generate 1000 test timestamps
    for i in range(1000):
        test_times.append(base_time + timedelta(seconds=i * 6))  # Every 6 seconds

    print(f"Testing DST detection performance with {len(test_times)} timestamps...")

    start_time = time.time()
    transition_count = 0

    for timestamp in test_times:
        if manager.is_dst_transition_period(timestamp):
            transition_count += 1

    end_time = time.time()
    processing_time = end_time - start_time

    print(f"Processing time: {processing_time:.3f} seconds")
    print(f"Average per timestamp: {processing_time / len(test_times) * 1000:.3f} ms")
    print(f"Transitions detected: {transition_count}")

    # Check cache effectiveness
    status = manager.get_dst_status()
    print(f"Cache entries created: {status['cache_size']}")

    # Test cache hit performance
    print("\nTesting cache hit performance...")
    start_time = time.time()

    for timestamp in test_times[:100]:  # Recheck same times
        manager.is_dst_transition_period(timestamp)

    end_time = time.time()
    cache_time = end_time - start_time

    print(f"Cache lookup time (100 timestamps): {cache_time:.3f} seconds")
    print(f"Cache speedup: {(processing_time / 1000) / (cache_time / 100):.1f}x")


async def demo_trading_integration():
    """Demonstrate DST handling integration with trading suite."""
    print("\n" + "=" * 60)
    print("TRADING SUITE DST INTEGRATION DEMO")
    print("=" * 60)

    print("DST handling is automatically integrated into TradingSuite.")
    print("When you create a TradingSuite, DST transitions are handled transparently:")
    print()
    print("```python")
    print("# DST handling is automatic")
    print("suite = await TradingSuite.create(")
    print("    'ES',  # S&P 500 E-mini futures")
    print("    timeframes=['1min', '5min'],")
    print("    timezone='America/Chicago'  # CME timezone with DST")
    print(")")
    print()
    print("# Real-time data automatically handles DST transitions:")
    print("# - Spring forward: No bars created for missing hour")
    print("# - Fall back: Proper handling of duplicate hour")
    print("# - All transitions logged for monitoring")
    print("```")
    print()
    print("Key Benefits:")
    print("• Transparent DST handling - no code changes needed")
    print("• Data integrity maintained across transitions")
    print("• Comprehensive logging for transition monitoring")
    print("• Performance optimized with intelligent caching")
    print("• Support for all major trading timezones")


async def main():
    """Run all DST handling demonstrations."""
    print("PROJECT-X-PY SDK - DST HANDLING DEMONSTRATION")
    print("=" * 60)
    print("This demo shows how the SDK automatically handles DST transitions")
    print("in real-time trading data processing.")

    # Run all demonstrations
    await demo_dst_transition_detection()
    await demo_spring_forward_handling()
    await demo_fall_back_handling()
    await demo_dst_event_logging()
    await demo_performance_monitoring()
    await demo_trading_integration()

    print("\n" + "=" * 60)
    print("DST HANDLING DEMO COMPLETE")
    print("=" * 60)
    print("The project-x-py SDK provides comprehensive DST handling for")
    print("robust real-time trading data processing across timezone transitions.")


if __name__ == "__main__":
    asyncio.run(main())
