#!/usr/bin/env python3
"""
Technical Indicators Usage Example

Demonstrates comprehensive technical indicator usage with the ProjectX indicators library:
- Trend indicators (SMA, EMA, MACD)
- Momentum indicators (RSI, Stochastic)
- Volatility indicators (Bollinger Bands, ATR)
- Volume indicators (OBV, Volume SMA)
- Multi-timeframe indicator analysis
- Real-time indicator updates

Uses MNQ market data for indicator calculations.

Usage:
    Run with: ./test.sh (sets environment variables)
    Or: uv run examples/07_technical_indicators.py

Author: TexasCoding
Date: July 2025
"""

import time

from project_x_py import (
    ProjectX,
    create_data_manager,
    create_realtime_client,
    setup_logging,
)
from project_x_py.indicators import (
    ATR,
    BBANDS,
    EMA,
    MACD,
    OBV,
    RSI,
    SMA,
    STOCH,
)


def demonstrate_trend_indicators(data):
    """Demonstrate trend-following indicators."""
    print("\n📈 TREND INDICATORS")
    print("=" * 40)

    if data is None or data.is_empty() or len(data) < 50:
        print("   ❌ Insufficient data for trend indicators")
        return

    try:
        # Simple Moving Averages
        print("📊 Moving Averages:")

        # Calculate SMAs using the pipe method
        data_with_sma = (
            data.pipe(SMA, period=10, column="close")
            .pipe(SMA, period=20, column="close")
            .pipe(SMA, period=50, column="close")
        )

        # Get latest values
        latest = data_with_sma.tail(1)
        for row in latest.iter_rows(named=True):
            price = row["close"]
            sma_10 = row.get("sma_10", 0)
            sma_20 = row.get("sma_20", 0)
            sma_50 = row.get("sma_50", 0)

            print(f"   Current Price: ${price:.2f}")
            print(f"   SMA(10): ${sma_10:.2f}")
            print(f"   SMA(20): ${sma_20:.2f}")
            print(f"   SMA(50): ${sma_50:.2f}")

            # Trend analysis
            if sma_10 > sma_20 > sma_50:
                print("   📈 Strong Uptrend (SMA alignment)")
            elif sma_10 < sma_20 < sma_50:
                print("   📉 Strong Downtrend (SMA alignment)")
            else:
                print("   ➡️  Mixed trend signals")

        # Exponential Moving Averages
        print("\n📊 Exponential Moving Averages:")

        data_with_ema = data.pipe(EMA, period=12, column="close").pipe(
            EMA, period=26, column="close"
        )

        latest_ema = data_with_ema.tail(1)
        for row in latest_ema.iter_rows(named=True):
            ema_12 = row.get("ema_12", 0)
            ema_26 = row.get("ema_26", 0)

            print(f"   EMA(12): ${ema_12:.2f}")
            print(f"   EMA(26): ${ema_26:.2f}")

            if ema_12 > ema_26:
                print("   📈 Bullish EMA crossover")
            else:
                print("   📉 Bearish EMA crossover")

        # MACD
        print("\n📊 MACD (Moving Average Convergence Divergence):")

        data_with_macd = data.pipe(
            MACD, fast_period=12, slow_period=26, signal_period=9
        )

        latest_macd = data_with_macd.tail(1)
        for row in latest_macd.iter_rows(named=True):
            macd_line = row.get("macd", 0)
            signal_line = row.get("macd_signal", 0)
            histogram = row.get("macd_histogram", 0)

            print(f"   MACD Line: {macd_line:.3f}")
            print(f"   Signal Line: {signal_line:.3f}")
            print(f"   Histogram: {histogram:.3f}")

            if macd_line > signal_line and histogram > 0:
                print("   📈 Bullish MACD signal")
            elif macd_line < signal_line and histogram < 0:
                print("   📉 Bearish MACD signal")
            else:
                print("   ➡️  Neutral MACD signal")

    except Exception as e:
        print(f"   ❌ Trend indicators error: {e}")


def demonstrate_momentum_indicators(data):
    """Demonstrate momentum oscillators."""
    print("\n⚡ MOMENTUM INDICATORS")
    print("=" * 40)

    if data is None or data.is_empty() or len(data) < 30:
        print("   ❌ Insufficient data for momentum indicators")
        return

    try:
        # RSI (Relative Strength Index)
        print("📊 RSI (Relative Strength Index):")

        data_with_rsi = data.pipe(RSI, period=14)

        latest_rsi = data_with_rsi.tail(1)
        for row in latest_rsi.iter_rows(named=True):
            rsi = row.get("rsi_14", 0)

            print(f"   RSI(14): {rsi:.2f}")

            if rsi > 70:
                print("   🔴 Overbought condition (RSI > 70)")
            elif rsi < 30:
                print("   🟢 Oversold condition (RSI < 30)")
            elif rsi > 50:
                print("   📈 Bullish momentum (RSI > 50)")
            else:
                print("   📉 Bearish momentum (RSI < 50)")

        # Stochastic Oscillator
        print("\n📊 Stochastic Oscillator:")

        data_with_stoch = data.pipe(STOCH, k_period=14, d_period=3)

        latest_stoch = data_with_stoch.tail(1)
        for row in latest_stoch.iter_rows(named=True):
            stoch_k = row.get("stoch_k_14", 0)
            stoch_d = row.get("stoch_d_3", 0)

            print(f"   %K: {stoch_k:.2f}")
            print(f"   %D: {stoch_d:.2f}")

            if stoch_k > 80 and stoch_d > 80:
                print("   🔴 Overbought condition (>80)")
            elif stoch_k < 20 and stoch_d < 20:
                print("   🟢 Oversold condition (<20)")
            elif stoch_k > stoch_d:
                print("   📈 Bullish stochastic crossover")
            else:
                print("   📉 Bearish stochastic crossover")

    except Exception as e:
        print(f"   ❌ Momentum indicators error: {e}")


def demonstrate_volatility_indicators(data):
    """Demonstrate volatility indicators."""
    print("\n📊 VOLATILITY INDICATORS")
    print("=" * 40)

    if data is None or data.is_empty() or len(data) < 30:
        print("   ❌ Insufficient data for volatility indicators")
        return

    try:
        # Bollinger Bands
        print("📊 Bollinger Bands:")

        data_with_bb = data.pipe(BBANDS, period=20, std_dev=2)

        latest_bb = data_with_bb.tail(1)
        for row in latest_bb.iter_rows(named=True):
            price = row["close"]
            bb_upper = row.get("bb_upper_20", 0)
            bb_middle = row.get("bb_middle_20", 0)
            bb_lower = row.get("bb_lower_20", 0)

            print(f"   Current Price: ${price:.2f}")
            print(f"   Upper Band: ${bb_upper:.2f}")
            print(f"   Middle Band (SMA): ${bb_middle:.2f}")
            print(f"   Lower Band: ${bb_lower:.2f}")

            # Band position analysis
            if bb_upper > bb_lower and bb_lower > 0:
                band_width = bb_upper - bb_lower
                price_position = (price - bb_lower) / band_width * 100
                print(f"   Price Position: {price_position:.1f}% of band width")
            else:
                print("   Price Position: Cannot calculate (invalid band data)")

            if price >= bb_upper:
                print("   🔴 Price at upper band (potential sell signal)")
            elif price <= bb_lower:
                print("   🟢 Price at lower band (potential buy signal)")
            elif price > bb_middle:
                print("   📈 Price above middle band")
            else:
                print("   📉 Price below middle band")

        # Average True Range (ATR)
        print("\n📊 Average True Range (ATR):")

        data_with_atr = data.pipe(ATR, period=14)

        latest_atr = data_with_atr.tail(1)
        for row in latest_atr.iter_rows(named=True):
            atr = row.get("atr_14", 0)
            price = row["close"]

            print(f"   ATR(14): ${atr:.2f}")
            print(f"   ATR as % of Price: {(atr / price) * 100:.2f}%")

            # Volatility interpretation
            if atr > price * 0.02:  # ATR > 2% of price
                print("   🔥 High volatility environment")
            elif atr < price * 0.01:  # ATR < 1% of price
                print("   😴 Low volatility environment")
            else:
                print("   ➡️  Normal volatility environment")

    except Exception as e:
        print(f"   ❌ Volatility indicators error: {e}")


def demonstrate_volume_indicators(data):
    """Demonstrate volume-based indicators."""
    print("\n📦 VOLUME INDICATORS")
    print("=" * 40)

    if data is None or data.is_empty() or len(data) < 30:
        print("   ❌ Insufficient data for volume indicators")
        return

    try:
        # On-Balance Volume (OBV)
        print("📊 On-Balance Volume (OBV):")

        data_with_obv = data.pipe(OBV)

        # Get last few values to see trend
        recent_obv = data_with_obv.tail(5)
        obv_values = recent_obv["obv"].to_list()

        current_obv = obv_values[-1] if obv_values else 0
        previous_obv = obv_values[-2] if len(obv_values) > 1 else 0

        print(f"   Current OBV: {current_obv:,.0f}")

        if current_obv > previous_obv:
            print("   📈 OBV trending up (buying pressure)")
        elif current_obv < previous_obv:
            print("   📉 OBV trending down (selling pressure)")
        else:
            print("   ➡️  OBV flat (balanced volume)")

        # Volume SMA
        print("\n📊 Volume Moving Average:")

        data_with_vol_sma = data.pipe(SMA, period=20, column="volume")

        latest_vol = data_with_vol_sma.tail(1)
        for row in latest_vol.iter_rows(named=True):
            current_volume = row["volume"]
            avg_volume = row.get("sma_20", 0)

            print(f"   Current Volume: {current_volume:,}")
            print(f"   20-period Avg: {avg_volume:,.0f}")

            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0

            if volume_ratio > 1.5:
                print(f"   🔥 High volume ({volume_ratio:.1f}x average)")
            elif volume_ratio < 0.5:
                print(f"   😴 Low volume ({volume_ratio:.1f}x average)")
            else:
                print(f"   ➡️  Normal volume ({volume_ratio:.1f}x average)")

    except Exception as e:
        print(f"   ❌ Volume indicators error: {e}")


def demonstrate_multi_timeframe_indicators(data_manager):
    """Demonstrate indicators across multiple timeframes."""
    print("\n🕐 MULTI-TIMEFRAME INDICATOR ANALYSIS")
    print("=" * 50)

    timeframes = ["5min", "15min", "1hr"]

    for tf in timeframes:
        print(f"\n📊 {tf.upper()} Timeframe Analysis:")
        print("-" * 30)

        try:
            # Get data for this timeframe
            tf_data = data_manager.get_data(tf, bars=50)

            if tf_data is None or tf_data.is_empty():
                print(f"   ❌ No data available for {tf}")
                continue

            # Calculate key indicators
            data_with_indicators = (
                tf_data.pipe(SMA, period=20, column="close")
                .pipe(RSI, period=14)
                .pipe(MACD, fast_period=12, slow_period=26, signal_period=9)
            )

            # Get latest values
            latest = data_with_indicators.tail(1)
            for row in latest.iter_rows(named=True):
                price = row["close"]
                sma_20 = row.get("sma_20", 0)
                rsi = row.get("rsi_14", 0)
                macd = row.get("macd", 0)
                macd_signal = row.get("macd_signal", 0)

                print(f"   Price: ${price:.2f}")
                print(f"   SMA(20): ${sma_20:.2f}")
                print(f"   RSI: {rsi:.1f}")
                print(f"   MACD: {macd:.3f}")

                # Simple trend assessment
                trend_signals = 0

                if price > sma_20:
                    trend_signals += 1
                if rsi > 50:
                    trend_signals += 1
                if macd > macd_signal:
                    trend_signals += 1

                if trend_signals >= 2:
                    print(f"   📈 Bullish bias ({trend_signals}/3 signals)")
                elif trend_signals <= 1:
                    print(f"   📉 Bearish bias ({trend_signals}/3 signals)")
                else:
                    print(f"   ➡️  Neutral ({trend_signals}/3 signals)")

        except Exception as e:
            print(f"   ❌ Error analyzing {tf}: {e}")


def create_comprehensive_analysis(data):
    """Create a comprehensive technical analysis summary."""
    print("\n🎯 COMPREHENSIVE TECHNICAL ANALYSIS")
    print("=" * 50)

    if data is None or data.is_empty() or len(data) < 50:
        print("   ❌ Insufficient data for comprehensive analysis")
        return

    try:
        # Calculate all indicators
        data_with_all = (
            data.pipe(SMA, period=20, column="close")
            .pipe(EMA, period=12, column="close")
            .pipe(RSI, period=14)
            .pipe(MACD, fast_period=12, slow_period=26, signal_period=9)
            .pipe(BBANDS, period=20, std_dev=2)
            .pipe(ATR, period=14)
            .pipe(STOCH, k_period=14, d_period=3)
        )

        # Get latest values
        latest = data_with_all.tail(1)

        bullish_signals = 0
        bearish_signals = 0
        total_signals = 0

        for row in latest.iter_rows(named=True):
            price = row["close"]

            print("📊 Technical Analysis Summary:")
            print(f"   Current Price: ${price:.2f}")

            # Trend Analysis
            sma_20 = row.get("sma_20", 0)
            ema_12 = row.get("ema_12", 0)

            print("\n🔍 Trend Indicators:")
            if price > sma_20:
                print("   ✅ Price above SMA(20): Bullish")
                bullish_signals += 1
            else:
                print("   ❌ Price below SMA(20): Bearish")
                bearish_signals += 1
            total_signals += 1

            if price > ema_12:
                print("   ✅ Price above EMA(12): Bullish")
                bullish_signals += 1
            else:
                print("   ❌ Price below EMA(12): Bearish")
                bearish_signals += 1
            total_signals += 1

            # MACD
            macd = row.get("macd", 0)
            macd_signal = row.get("macd_signal", 0)

            if macd > macd_signal:
                print("   ✅ MACD above signal: Bullish")
                bullish_signals += 1
            else:
                print("   ❌ MACD below signal: Bearish")
                bearish_signals += 1
            total_signals += 1

            # Momentum Analysis
            rsi = row.get("rsi", 0)

            print("\n⚡ Momentum Indicators:")
            if 30 < rsi < 70:
                if rsi > 50:
                    print(f"   ✅ RSI ({rsi:.1f}): Bullish momentum")
                    bullish_signals += 1
                else:
                    print(f"   ❌ RSI ({rsi:.1f}): Bearish momentum")
                    bearish_signals += 1
                total_signals += 1
            else:
                if rsi > 70:
                    print(f"   ⚠️  RSI ({rsi:.1f}): Overbought")
                else:
                    print(f"   ⚠️  RSI ({rsi:.1f}): Oversold")

            # Volatility Analysis
            bb_upper = row.get("bb_upper_20", 0)
            bb_lower = row.get("bb_lower_20", 0)

            print("\n📊 Volatility Analysis:")
            if bb_lower < price < bb_upper:
                print("   ℹ️  Price within Bollinger Bands: Normal")
            elif price >= bb_upper:
                print("   ⚠️  Price at upper BB: Potential reversal")
            else:
                print("   ⚠️  Price at lower BB: Potential reversal")

            atr = row.get("atr_14", 0)
            volatility_pct = (atr / price) * 100
            print(f"   ATR: ${atr:.2f} ({volatility_pct:.2f}% of price)")

        # Overall Assessment
        print("\n🎯 OVERALL ASSESSMENT:")
        print(f"   Bullish Signals: {bullish_signals}/{total_signals}")
        print(f"   Bearish Signals: {bearish_signals}/{total_signals}")

        if bullish_signals > bearish_signals:
            strength = (bullish_signals / total_signals) * 100
            print(f"   📈 BULLISH BIAS ({strength:.0f}% strength)")
        elif bearish_signals > bullish_signals:
            strength = (bearish_signals / total_signals) * 100
            print(f"   📉 BEARISH BIAS ({strength:.0f}% strength)")
        else:
            print("   ➡️  NEUTRAL (conflicting signals)")

    except Exception as e:
        print(f"   ❌ Comprehensive analysis error: {e}")


def monitor_indicator_updates(data_manager, duration_seconds=60):
    """Monitor real-time indicator updates."""
    print(f"\n👀 Real-time Indicator Monitoring ({duration_seconds}s)")
    print("=" * 50)

    start_time = time.time()

    try:
        while time.time() - start_time < duration_seconds:
            elapsed = time.time() - start_time

            # Update every 15 seconds
            if int(elapsed) % 15 == 0 and int(elapsed) > 0:
                remaining = duration_seconds - elapsed
                print(f"\n⏰ Update {int(elapsed // 15)} - {remaining:.0f}s remaining")
                print("-" * 30)

                # Get latest 1-minute data
                data = data_manager.get_data("1min", bars=30)

                if data is not None and not data.is_empty():
                    # Quick indicator update
                    data_with_indicators = data.pipe(
                        SMA, period=10, column="close"
                    ).pipe(RSI, period=14)

                    latest = data_with_indicators.tail(1)
                    for row in latest.iter_rows(named=True):
                        price = row["close"]
                        sma_10 = row.get("sma_10", 0)
                        rsi = row.get("rsi_14", 0)

                        print(f"   Price: ${price:.2f}")
                        print(f"   SMA(10): ${sma_10:.2f}")
                        print(f"   RSI: {rsi:.1f}")

                        # Quick trend assessment
                        if price > sma_10 and rsi > 50:
                            print("   📈 Short-term bullish")
                        elif price < sma_10 and rsi < 50:
                            print("   📉 Short-term bearish")
                        else:
                            print("   ➡️  Mixed signals")
                else:
                    print("   ❌ No data available")

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n⏹️ Monitoring stopped by user")


def main():
    """Demonstrate comprehensive technical indicator usage."""
    logger = setup_logging(level="INFO")
    print("🚀 Technical Indicators Usage Example")
    print("=" * 60)

    try:
        # Initialize client
        print("🔑 Initializing ProjectX client...")
        client = ProjectX.from_env()

        account = client.get_account_info()
        if not account:
            print("❌ Could not get account information")
            return False

        print(f"✅ Connected to account: {account.name}")

        # Create real-time data manager
        print("\n🏗️ Creating real-time data manager...")
        try:
            jwt_token = client.get_session_token()
            realtime_client = create_realtime_client(jwt_token, str(account.id))

            # Connect the realtime client to WebSocket hubs
            print("   Connecting to real-time WebSocket feeds...")
            if realtime_client.connect():
                print("   ✅ Real-time client connected successfully")
            else:
                print(
                    "   ⚠️ Real-time client connection failed - continuing with limited functionality"
                )

            data_manager = create_data_manager(
                instrument="MNQ",
                project_x=client,
                realtime_client=realtime_client,
                timeframes=["1min", "5min", "15min", "1hr"],
            )
            print("✅ Data manager created for MNQ")
        except Exception as e:
            print(f"❌ Failed to create data manager: {e}")
            return False

        # Initialize with historical data
        print("\n📚 Initializing with historical data...")
        if data_manager.initialize(initial_days=7):
            print("✅ Historical data loaded (7 days)")
        else:
            print("❌ Failed to load historical data")
            return False

        # Get base data for analysis
        print("\n📊 Loading data for indicator analysis...")
        base_data = data_manager.get_data("15min", bars=100)  # 15-min data for analysis

        if base_data is None or base_data.is_empty():
            print("❌ No base data available")
            return False

        print(f"✅ Loaded {len(base_data)} bars of 15-minute data")

        # Demonstrate each category of indicators
        print("\n" + "=" * 60)
        print("📈 TECHNICAL INDICATOR DEMONSTRATIONS")
        print("=" * 60)

        demonstrate_trend_indicators(base_data)
        demonstrate_momentum_indicators(base_data)
        demonstrate_volatility_indicators(base_data)
        demonstrate_volume_indicators(base_data)

        # Multi-timeframe analysis
        demonstrate_multi_timeframe_indicators(data_manager)

        # Comprehensive analysis
        create_comprehensive_analysis(base_data)

        # Start real-time feed for live updates
        print("\n🌐 Starting real-time feed for live indicator updates...")
        if data_manager.start_realtime_feed():
            print("✅ Real-time feed started")

            # Monitor real-time indicator updates
            monitor_indicator_updates(data_manager, duration_seconds=45)
        else:
            print("❌ Failed to start real-time feed")

        # Final comprehensive analysis with latest data
        print("\n" + "=" * 60)
        print("🎯 FINAL ANALYSIS WITH LATEST DATA")
        print("=" * 60)

        final_data = data_manager.get_data("15min", bars=50)
        if final_data is not None and not final_data.is_empty():
            create_comprehensive_analysis(final_data)
        else:
            print("❌ No final data available")

        print("\n✅ Technical indicators example completed!")
        print("\n📝 Key Features Demonstrated:")
        print("   ✅ Trend indicators (SMA, EMA, MACD)")
        print("   ✅ Momentum indicators (RSI, Stochastic)")
        print("   ✅ Volatility indicators (Bollinger Bands, ATR)")
        print("   ✅ Volume indicators (OBV, Volume SMA)")
        print("   ✅ Multi-timeframe analysis")
        print("   ✅ Real-time indicator updates")
        print("   ✅ Comprehensive technical analysis")

        print("\n📚 Next Steps:")
        print("   - Test individual examples: 01_basic_client_connection.py")
        print("   - Study indicator combinations for your trading style")
        print("   - Review indicators documentation for advanced features")
        print("   - Integrate indicators into your trading strategies")

        return True

    except KeyboardInterrupt:
        print("\n⏹️ Example interrupted by user")
        return False
    except Exception as e:
        logger.error(f"❌ Technical indicators example failed: {e}")
        print(f"❌ Error: {e}")
        return False
    finally:
        # Cleanup
        if "data_manager" in locals():
            try:
                data_manager.stop_realtime_feed()
                print("🧹 Real-time feed stopped")
            except Exception as e:
                print(f"⚠️  Cleanup warning: {e}")


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
