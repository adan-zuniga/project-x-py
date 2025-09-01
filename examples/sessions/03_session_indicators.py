"""
Session-Aware Indicators Example

Demonstrates how to calculate technical indicators with session awareness.
Shows VWAP, anchored VWAP, session levels, and cumulative volume.
"""

import asyncio

from project_x_py import TradingSuite
from project_x_py.indicators import MACD, RSI, SMA
from project_x_py.sessions import (
    SessionConfig,
    SessionType,
    calculate_anchored_vwap,
    calculate_percent_from_open,
    calculate_relative_to_vwap,
    calculate_session_cumulative_volume,
    calculate_session_levels,
    calculate_session_vwap,
)


async def session_indicators_demo():
    """Calculate session-aware technical indicators."""

    print("=" * 60)
    print("SESSION-AWARE INDICATORS EXAMPLE")
    print("=" * 60)

    # Create suite for RTH session
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["5min"],
        session_config=SessionConfig(session_type=SessionType.RTH),
        initial_days=5,
    )

    try:
        mnq_context = suite["MNQ"]

        # Get RTH data
        data = await mnq_context.data.get_session_data("5min", SessionType.RTH)

        if data is None or data.is_empty():
            print("No RTH data available")
            return

        print(f"\nWorking with {len(data):,} RTH bars")

        # 1. Session VWAP
        print("\n1. Session VWAP Calculation:")
        print("-" * 40)

        vwap_data = await calculate_session_vwap(data, SessionType.RTH, "MNQ")

        if "session_vwap" in vwap_data.columns:
            last_vwap = vwap_data["session_vwap"][-1]
            if last_vwap is not None:
                print(f"Current Session VWAP: ${float(last_vwap):.2f}")

            # Check how many bars have VWAP
            vwap_count = vwap_data["session_vwap"].drop_nulls().len()
            print(f"Bars with VWAP: {vwap_count}")

        # 2. Anchored VWAP
        print("\n2. Anchored VWAP (from session open):")
        print("-" * 40)

        anchored_data = await calculate_anchored_vwap(data, anchor_point="session_open")

        if "anchored_vwap" in anchored_data.columns:
            last_anchored = anchored_data["anchored_vwap"][-1]
            if last_anchored is not None:
                print(f"VWAP anchored to session open: ${float(last_anchored):.2f}")

        # 3. Session Levels
        print("\n3. Session High/Low/Open/Close:")
        print("-" * 40)

        levels_data = await calculate_session_levels(data)

        if all(
            col in levels_data.columns
            for col in ["session_high", "session_low", "session_open", "session_close"]
        ):
            # Get the last values
            session_high = levels_data["session_high"][-1]
            session_low = levels_data["session_low"][-1]
            session_open = levels_data["session_open"][-1]
            session_close = levels_data["session_close"][-1]

            if all(
                v is not None
                for v in [session_high, session_low, session_open, session_close]
            ):
                print(f"Session Open:  ${float(session_open):.2f}")
                print(f"Session High:  ${float(session_high):.2f}")
                print(f"Session Low:   ${float(session_low):.2f}")
                print(f"Session Close: ${float(session_close):.2f}")

                # Calculate range
                session_range = float(session_high) - float(session_low)
                print(f"Session Range: ${session_range:.2f}")

        # 4. Cumulative Volume
        print("\n4. Session Cumulative Volume:")
        print("-" * 40)

        volume_data = await calculate_session_cumulative_volume(data)

        if "cumulative_volume" in volume_data.columns:
            total_volume = volume_data["cumulative_volume"][-1]
            if total_volume is not None:
                print(f"Total Session Volume: {int(total_volume):,}")

            # Show volume progression
            quarter_idx = len(volume_data) // 4
            if quarter_idx > 0:
                q1_vol = volume_data["cumulative_volume"][quarter_idx]
                q2_vol = volume_data["cumulative_volume"][quarter_idx * 2]
                q3_vol = volume_data["cumulative_volume"][quarter_idx * 3]

                if all(v is not None for v in [q1_vol, q2_vol, q3_vol]):
                    print(f"  25% of session: {int(q1_vol):,}")
                    print(f"  50% of session: {int(q2_vol):,}")
                    print(f"  75% of session: {int(q3_vol):,}")

        # 5. Relative to VWAP
        print("\n5. Price Relative to VWAP:")
        print("-" * 40)

        relative_data = await calculate_relative_to_vwap(vwap_data)

        if "relative_to_vwap" in relative_data.columns:
            last_relative = relative_data["relative_to_vwap"][-1]
            if last_relative is not None:
                rel_pct = float(last_relative)
                print(f"Current price is {rel_pct:+.2f}% from VWAP")

                if rel_pct > 0:
                    print("  → Price is ABOVE VWAP (bullish)")
                else:
                    print("  → Price is BELOW VWAP (bearish)")

        # 6. Percent from Open
        print("\n6. Percent Change from Session Open:")
        print("-" * 40)

        pct_data = await calculate_percent_from_open(levels_data)

        if "percent_from_open" in pct_data.columns:
            last_pct = pct_data["percent_from_open"][-1]
            if last_pct is not None:
                pct_change = float(last_pct)
                print(f"Change from open: {pct_change:+.2f}%")

                if abs(pct_change) > 1.0:
                    print("  → Significant move from open")

        # 7. Combine with traditional indicators
        print("\n7. Combined with Traditional Indicators:")
        print("-" * 40)

        # Apply multiple indicators
        with_indicators = vwap_data.pipe(SMA, period=20).pipe(RSI, period=14).pipe(MACD)

        # Check signals
        if all(
            col in with_indicators.columns
            for col in ["close", "session_vwap", "sma_20", "rsi_14"]
        ):
            last_close = with_indicators["close"][-1]
            last_vwap = with_indicators["session_vwap"][-1]
            last_sma = with_indicators["sma_20"][-1]
            last_rsi = with_indicators["rsi_14"][-1]

            if all(v is not None for v in [last_close, last_vwap, last_sma, last_rsi]):
                print(f"Current Close: ${float(last_close):.2f}")
                print(f"Session VWAP:  ${float(last_vwap):.2f}")
                print(f"SMA(20):       ${float(last_sma):.2f}")
                print(f"RSI(14):       {float(last_rsi):.1f}")

                # Generate signals
                print("\n📈 Trading Signals:")

                # VWAP signal
                if float(last_close) > float(last_vwap):
                    print("  ✓ Price above VWAP (bullish)")
                else:
                    print("  ✗ Price below VWAP (bearish)")

                # SMA signal
                if float(last_close) > float(last_sma):
                    print("  ✓ Price above SMA(20) (bullish)")
                else:
                    print("  ✗ Price below SMA(20) (bearish)")

                # RSI signal
                rsi_val = float(last_rsi)
                if rsi_val > 70:
                    print(f"  ⚠ RSI overbought ({rsi_val:.1f})")
                elif rsi_val < 30:
                    print(f"  ⚠ RSI oversold ({rsi_val:.1f})")
                else:
                    print(f"  ✓ RSI neutral ({rsi_val:.1f})")

    finally:
        await suite.disconnect()
        print("\n✅ Session indicators example completed")


if __name__ == "__main__":
    asyncio.run(session_indicators_demo())
