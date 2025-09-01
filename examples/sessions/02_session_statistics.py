"""
Session Statistics Example

Demonstrates how to calculate and compare statistics between RTH and ETH sessions.
Shows volume analysis, price ranges, and volatility comparisons.
"""

import asyncio

from project_x_py import TradingSuite
from project_x_py.sessions import (
    SessionAnalytics,
    SessionConfig,
    SessionStatistics,
    SessionType,
)


async def session_statistics_demo():
    """Calculate and compare session-specific statistics."""

    print("=" * 60)
    print("SESSION STATISTICS EXAMPLE")
    print("=" * 60)

    # Create suite with ETH to get all data (both RTH and ETH)
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["1min", "5min"],
        session_config=SessionConfig(session_type=SessionType.ETH),
        initial_days=5,
    )

    try:
        mnq_context = suite["MNQ"]

        # Method 1: Using data manager's built-in statistics
        print("\n1. Data Manager Session Statistics:")
        print("-" * 40)

        stats = await mnq_context.data.get_session_statistics("1min")

        if stats:
            print("\n📊 Session Metrics:")

            # Volume comparison
            if "rth_volume" in stats and "eth_volume" in stats:
                rth_vol = stats["rth_volume"]
                eth_vol = stats["eth_volume"]
                print("\nVolume Analysis:")
                print(f"  RTH Volume: {rth_vol:,}")
                print(f"  ETH Volume: {eth_vol:,}")
                if eth_vol > 0:
                    ratio = rth_vol / eth_vol
                    print(f"  RTH/ETH Ratio: {ratio:.2f}x")

            # VWAP comparison
            if "rth_vwap" in stats and "eth_vwap" in stats:
                print("\nVWAP Analysis:")
                print(f"  RTH VWAP: ${stats['rth_vwap']:.2f}")
                print(f"  ETH VWAP: ${stats['eth_vwap']:.2f}")
                diff = abs(stats["rth_vwap"] - stats["eth_vwap"])
                print(f"  Difference: ${diff:.2f}")

            # Range comparison
            if "rth_range" in stats and "eth_range" in stats:
                print("\nRange Analysis:")
                print(f"  RTH Range: ${stats['rth_range']:.2f}")
                print(f"  ETH Range: ${stats['eth_range']:.2f}")

        # Method 2: Using SessionStatistics class directly
        print("\n2. SessionStatistics Class:")
        print("-" * 40)

        # Get the data
        data = await mnq_context.data.get_data("5min")

        if data is not None and not data.is_empty():
            # Initialize statistics calculator
            session_stats = SessionStatistics()

            # Calculate comprehensive statistics
            detailed_stats = await session_stats.calculate_session_stats(data, "MNQ")

            print("\nDetailed Session Statistics:")
            for key, value in detailed_stats.items():
                if value is not None:
                    if isinstance(value, (int, float)):
                        if "volume" in key:
                            print(f"  {key}: {value:,.0f}")
                        elif (
                            "vwap" in key
                            or "high" in key
                            or "low" in key
                            or "range" in key
                        ):
                            print(f"  {key}: ${value:.2f}")
                        else:
                            print(f"  {key}: {value}")

        # Method 3: Using SessionAnalytics for advanced analysis
        print("\n3. Advanced Session Analytics:")
        print("-" * 40)

        if data is not None and not data.is_empty():
            # Initialize analytics
            analytics = SessionAnalytics()

            # Compare sessions
            comparison = await analytics.compare_sessions(data, "MNQ")

            if comparison:
                print("\nSession Comparison Results:")

                if "rth_vs_eth_volume_ratio" in comparison:
                    print(
                        f"  Volume Ratio (RTH/ETH): {comparison['rth_vs_eth_volume_ratio']:.2f}x"
                    )

                if (
                    "rth_volatility" in comparison
                    and "eth_volatility" in comparison
                    and isinstance(comparison["rth_volatility"], (int, float))
                    and isinstance(comparison["eth_volatility"], (int, float))
                ):
                    print("\nVolatility Analysis:")
                    print(f"  RTH Volatility: {comparison['rth_volatility']:.2%}")
                    print(f"  ETH Volatility: {comparison['eth_volatility']:.2%}")

                    if comparison["rth_volatility"] > comparison["eth_volatility"]:
                        print("  → RTH is more volatile")
                    else:
                        print("  → ETH is more volatile")

            # Get volume profile by hour
            print("\nHourly Volume Profile:")
            volume_profile = await analytics.get_session_volume_profile(data, "MNQ")

            if volume_profile and isinstance(volume_profile, dict):
                # Filter out any non-numeric values and ensure we have valid hour keys
                try:
                    # Show top 5 volume hours
                    valid_items = [
                        (k, v)
                        for k, v in volume_profile.items()
                        if isinstance(k, (int, str)) and isinstance(v, (int, float))
                    ]
                    if valid_items:
                        sorted_hours = sorted(
                            valid_items, key=lambda x: x[1], reverse=True
                        )[:5]

                        print("  Top 5 Volume Hours:")
                        for hour, volume in sorted_hours:
                            if isinstance(hour, str):
                                hour = int(hour) if hour.isdigit() else 0
                            print(f"    {hour:02d}:00 - {int(volume):,} contracts")
                    else:
                        print("  No valid volume data available")
                except (TypeError, ValueError) as e:
                    print(f"  Error processing volume profile: {e}")

            # Analyze session gaps
            gaps = await analytics.analyze_session_gaps(data, "MNQ")

            if gaps and isinstance(gaps, dict):
                print("\nSession Gap Analysis:")
                if "average_gap" in gaps and isinstance(
                    gaps["average_gap"], (int, float)
                ):
                    print(f"  Average Gap: ${abs(gaps['average_gap']):.2f}")
                if "max_gap" in gaps and isinstance(gaps["max_gap"], (int, float)):
                    print(f"  Max Gap: ${abs(gaps['max_gap']):.2f}")
                if "gap_frequency" in gaps and isinstance(
                    gaps["gap_frequency"], (int, float)
                ):
                    print(f"  Gap Frequency: {gaps['gap_frequency']:.1%}")

            # Calculate efficiency metrics
            efficiency = await analytics.calculate_efficiency_metrics(data, "MNQ")

            if efficiency and isinstance(efficiency, dict):
                print("\nEfficiency Metrics:")
                if "rth_efficiency" in efficiency and isinstance(
                    efficiency["rth_efficiency"], (int, float)
                ):
                    print(f"  RTH Efficiency: {efficiency['rth_efficiency']:.2f}")
                if "eth_efficiency" in efficiency and isinstance(
                    efficiency["eth_efficiency"], (int, float)
                ):
                    print(f"  ETH Efficiency: {efficiency['eth_efficiency']:.2f}")

    finally:
        await suite.disconnect()
        print("\n✅ Session statistics example completed")


if __name__ == "__main__":
    asyncio.run(session_statistics_demo())
