"""
Multi-Instrument Session Management Example

Demonstrates how to manage sessions across multiple instruments simultaneously.
Shows synchronized analysis and cross-instrument comparisons.
"""
# type: ignore

import asyncio

from project_x_py import TradingSuite
from project_x_py.sessions import SessionConfig, SessionType


async def multi_instrument_sessions_demo():
    """Manage sessions for multiple instruments."""

    print("=" * 60)
    print("MULTI-INSTRUMENT SESSION MANAGEMENT")
    print("=" * 60)

    # Define instruments to track
    instruments = ["MNQ", "MES", "MCL"]

    # Create suite with multiple instruments
    print(f"\nCreating TradingSuite for {', '.join(instruments)}...")

    suite = await TradingSuite.create(
        instruments,  # Pass list of instruments
        timeframes=["5min"],
        session_config=SessionConfig(session_type=SessionType.RTH),
        initial_days=5,
    )

    try:
        print(f"Suite created with {len(suite)} instruments")

        # 1. Access each instrument's session data
        print("\n1. PER-INSTRUMENT SESSION DATA")
        print("-" * 40)

        for symbol, context in suite.items():
            # Get session data for each instrument
            data = await context.data.get_session_data("5min", SessionType.RTH)

            if data is not None and not data.is_empty():
                print(f"\n{symbol}:")
                print(f"  RTH bars: {len(data):,}")
                print(f"  First: {data['timestamp'][0]}")
                print(f"  Last: {data['timestamp'][-1]}")

                # Calculate basic metrics
                high = data["high"].max()
                low = data["low"].min()
                volume = data["volume"].sum()

                if high is not None and low is not None:
                    range_val = float(high) - float(low) # type: ignore
                    print(f"  Range: ${range_val:.2f}")
                if volume is not None:
                    print(f"  Volume: {int(volume):,}")

        # 2. Batch session data retrieval
        print("\n2. BATCH SESSION DATA RETRIEVAL")
        print("-" * 40)

        # Get session data for all instruments at once
        all_session_data = await suite.get_session_data("5min", SessionType.RTH)

        if isinstance(all_session_data, dict):
            print("\nSession data retrieved for all instruments:")
            for symbol, data in all_session_data.items():
                if data is not None:
                    print(f"  {symbol}: {len(data):,} bars")

        # 3. Cross-instrument comparison
        print("\n3. CROSS-INSTRUMENT COMPARISON")
        print("-" * 40)

        volumes = {}
        ranges = {}

        for symbol, context in suite.items():
            data = await context.data.get_session_data("5min", SessionType.RTH)

            if data is not None and not data.is_empty():
                # Calculate metrics
                volumes[symbol] = data["volume"].sum()

                high = data["high"].max()
                low = data["low"].min()
                if high is not None and low is not None:
                    ranges[symbol] = float(high) - float(low) # type: ignore

        # Compare volumes
        if volumes:
            print("\nVolume Comparison:")
            sorted_volumes = sorted(volumes.items(), key=lambda x: x[1], reverse=True)
            for symbol, volume in sorted_volumes:
                print(f"  {symbol}: {int(volume):,}")

            # Find most active
            most_active = sorted_volumes[0][0]
            print(f"\nMost Active: {most_active}")

        # Compare ranges
        if ranges:
            print("\nRange Comparison:")
            sorted_ranges = sorted(ranges.items(), key=lambda x: x[1], reverse=True)
            for symbol, range_val in sorted_ranges:
                print(f"  {symbol}: ${range_val:.2f}")

            # Find most volatile
            most_volatile = sorted_ranges[0][0]
            print(f"\nMost Volatile: {most_volatile}")

        # 4. Session statistics for all instruments
        print("\n4. MULTI-INSTRUMENT SESSION STATISTICS")
        print("-" * 40)

        # Get statistics for all instruments
        all_stats = await suite.get_session_statistics("5min")

        if isinstance(all_stats, dict):
            print("\nSession Statistics Summary:")

            for symbol, stats in all_stats.items():
                if stats:
                    print(f"\n{symbol}:")
                    if "rth_volume" in stats:
                        print(f"  RTH Volume: {stats['rth_volume']:,}")
                    if "rth_vwap" in stats:
                        print(f"  RTH VWAP: ${stats['rth_vwap']:.2f}")
                    if "rth_range" in stats:
                        print(f"  RTH Range: ${stats['rth_range']:.2f}")

        # 5. Synchronized session switching
        print("\n5. SYNCHRONIZED SESSION SWITCHING")
        print("-" * 40)

        # Switch all instruments to ETH
        print("\nSwitching all instruments to ETH session...")
        await suite.set_session_type(SessionType.ETH)

        # Get ETH data for all
        eth_data = await suite.get_session_data("5min", SessionType.ETH)

        if isinstance(eth_data, dict):
            print("\nETH Session Data:")
            for symbol, data in eth_data.items():
                if data is not None:
                    print(f"  {symbol}: {len(data):,} ETH bars")

        # 6. Correlations during sessions
        print("\n6. SESSION CORRELATIONS")
        print("-" * 40)

        # Calculate correlations between instruments
        if len(suite) >= 2:

            # Get RTH data for correlation
            await suite.set_session_type(SessionType.RTH)

            # Get close prices for each instrument
            close_prices = {}
            for symbol, context in suite.items():
                data = await context.data.get_session_data("5min", SessionType.RTH)
                if data is not None and not data.is_empty():
                    close_prices[symbol] = data["close"]

            # Calculate simple correlation between first two instruments
            if len(close_prices) >= 2:
                keys = list(close_prices.keys())

                # Get returns
                returns1 = close_prices[keys[0]].pct_change().drop_nulls()
                returns2 = close_prices[keys[1]].pct_change().drop_nulls()

                # Ensure same length
                min_len = min(len(returns1), len(returns2))
                if min_len > 0:
                    returns1 = returns1[:min_len]
                    returns2 = returns2[:min_len]

                    # Calculate correlation using Polars
                    import polars as pl

                    # Create a DataFrame with both series for correlation calculation
                    corr_df = pl.DataFrame({
                        "returns1": returns1,
                        "returns2": returns2
                    })

                    # Calculate correlation
                    correlation_matrix = corr_df.corr()
                    if correlation_matrix is not None:
                        # Get the correlation value (off-diagonal element)
                        correlation = correlation_matrix["returns1"][1]  # type: ignore

                        if correlation is not None:
                            print(f"\nCorrelation {keys[0]} vs {keys[1]}:")
                            print(f"  RTH Session: {float(correlation):.3f}")  # type: ignore

                            if abs(float(correlation)) > 0.7:  # type: ignore
                                print("  → Strong correlation")
                            elif abs(float(correlation)) > 0.4:  # type: ignore
                                print("  → Moderate correlation")
                            else:
                                print("  → Weak correlation")

        # 7. Trading signals across instruments
        print("\n7. MULTI-INSTRUMENT TRADING SIGNALS")
        print("-" * 40)

        signals = {}

        for symbol, context in suite.items():
            data = await context.data.get_session_data("5min", SessionType.RTH)

            if data is not None and not data.is_empty():
                # Simple signal: price above 20-period average
                if len(data) >= 20:
                    sma20 = data["close"].rolling_mean(20)
                    last_close = data["close"][-1]
                    last_sma = sma20[-1]

                    if last_close is not None and last_sma is not None:
                        if float(last_close) > float(last_sma):
                            signals[symbol] = "BULLISH"
                        else:
                            signals[symbol] = "BEARISH"

        if signals:
            print("\nTrading Signals (RTH):")
            for symbol, signal in signals.items():
                emoji = "📈" if signal == "BULLISH" else "📉"
                print(f"  {symbol}: {emoji} {signal}")

            # Overall market sentiment
            bullish_count = sum(1 for s in signals.values() if s == "BULLISH")
            total_count = len(signals)

            print(f"\nMarket Sentiment: {bullish_count}/{total_count} bullish")

            if bullish_count == total_count:
                print("  → Strong bullish alignment")
            elif bullish_count == 0:
                print("  → Strong bearish alignment")
            else:
                print("  → Mixed signals")

    finally:
        await suite.disconnect()
        print("\n✅ Multi-instrument session management completed")


if __name__ == "__main__":
    asyncio.run(multi_instrument_sessions_demo())
