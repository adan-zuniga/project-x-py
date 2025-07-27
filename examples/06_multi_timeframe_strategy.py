#!/usr/bin/env python3
"""
Multi-Timeframe Trading Strategy Example

Demonstrates a complete multi-timeframe trading strategy using:
- Multiple timeframe analysis (15min, 1hr, 4hr)
- Technical indicators across timeframes
- Trend alignment analysis
- Real-time signal generation
- Order management integration
- Position management and risk control

⚠️  WARNING: This example can place REAL ORDERS based on strategy signals!

Uses MNQ micro contracts for strategy testing.

Usage:
    Run with: ./test.sh (sets environment variables)
    Or: uv run examples/06_multi_timeframe_strategy.py

Author: TexasCoding
Date: July 2025
"""

import time
from decimal import Decimal

from project_x_py import (
    ProjectX,
    create_order_manager,
    create_position_manager,
    create_trading_suite,
    setup_logging,
)


class MultiTimeframeStrategy:
    """
    Simple multi-timeframe trend following strategy.

    Strategy Logic:
    - Long-term trend: 4hr timeframe (50 SMA)
    - Medium-term trend: 1hr timeframe (20 SMA)
    - Entry timing: 15min timeframe (10 SMA crossover)
    - Risk management: 2% account risk per trade
    """

    def __init__(self, data_manager, order_manager, position_manager, client):
        self.data_manager = data_manager
        self.order_manager = order_manager
        self.position_manager = position_manager
        self.client = client
        self.logger = setup_logging(level="INFO")

        # Strategy parameters
        self.timeframes = {
            "long_term": "4hr",
            "medium_term": "1hr",
            "short_term": "15min",
        }

        self.sma_periods = {"long_term": 50, "medium_term": 20, "short_term": 10}

        # Risk management
        self.max_risk_per_trade = 50.0  # $50 risk per trade
        self.max_position_size = 2  # Max 2 contracts

        # Strategy state
        self.signals = {}
        self.last_signal_time = None
        self.active_position = None

    def calculate_sma(self, data, period):
        """Calculate Simple Moving Average."""
        if data is None or data.is_empty() or len(data) < period:
            return None

        closes = data.select("close")
        return float(closes.tail(period).mean().item())

    def analyze_timeframe_trend(self, timeframe, sma_period):
        """Analyze trend for a specific timeframe."""
        try:
            # Get sufficient data for SMA calculation
            data = self.data_manager.get_data(timeframe, bars=sma_period + 10)

            if data is None or data.is_empty() or len(data) < sma_period + 1:
                return {"trend": "unknown", "strength": 0, "price": 0, "sma": 0}

            # Calculate current and previous SMA
            current_sma = self.calculate_sma(data, sma_period)
            previous_data = data.head(-1)  # Exclude last bar
            previous_sma = self.calculate_sma(previous_data, sma_period)

            # Get current price
            current_price = float(data.select("close").tail(1).item())

            if current_sma is None or previous_sma is None:
                return {
                    "trend": "unknown",
                    "strength": 0,
                    "price": current_price,
                    "sma": 0,
                }

            # Determine trend
            if current_price > current_sma and current_sma > previous_sma:
                trend = "bullish"
                strength = min(
                    abs(current_price - current_sma) / current_price * 100, 100
                )
            elif current_price < current_sma and current_sma < previous_sma:
                trend = "bearish"
                strength = min(
                    abs(current_price - current_sma) / current_price * 100, 100
                )
            else:
                trend = "neutral"
                strength = 0

            return {
                "trend": trend,
                "strength": strength,
                "price": current_price,
                "sma": current_sma,
                "previous_sma": previous_sma,
            }

        except Exception as e:
            self.logger.error(f"Error analyzing {timeframe} trend: {e}")
            return {"trend": "unknown", "strength": 0, "price": 0, "sma": 0}

    def generate_signal(self):
        """Generate trading signal based on multi-timeframe analysis."""
        try:
            # Analyze all timeframes
            analysis = {}
            for tf_name, tf in self.timeframes.items():
                period = self.sma_periods[tf_name]
                analysis[tf_name] = self.analyze_timeframe_trend(tf, period)

            self.signals = analysis

            # Check trend alignment
            long_trend = analysis["long_term"]["trend"]
            medium_trend = analysis["medium_term"]["trend"]
            short_trend = analysis["short_term"]["trend"]

            # Generate signal
            signal = None
            confidence = 0

            # Long signal: All timeframes bullish or long/medium bullish with short neutral
            if (
                long_trend == "bullish"
                and medium_trend == "bullish"
                and short_trend == "bullish"
            ):
                signal = "LONG"
                confidence = 100
            elif (
                long_trend == "bullish"
                and medium_trend == "bullish"
                and short_trend == "neutral"
            ):
                signal = "LONG"
                confidence = 75
            # Short signal: All timeframes bearish or long/medium bearish with short neutral
            elif (
                long_trend == "bearish"
                and medium_trend == "bearish"
                and short_trend == "bearish"
            ):
                signal = "SHORT"
                confidence = 100
            elif (
                long_trend == "bearish"
                and medium_trend == "bearish"
                and short_trend == "neutral"
            ):
                signal = "SHORT"
                confidence = 75
            else:
                signal = "NEUTRAL"
                confidence = 0

            return {
                "signal": signal,
                "confidence": confidence,
                "analysis": analysis,
                "timestamp": time.time(),
            }

        except Exception as e:
            self.logger.error(f"Error generating signal: {e}")
            return {
                "signal": "NEUTRAL",
                "confidence": 0,
                "analysis": {},
                "timestamp": time.time(),
            }

    def calculate_position_size(self, entry_price, stop_price):
        """Calculate position size based on risk management."""
        try:
            # Get account balance for risk calculation
            account = self.client.get_account_info()
            if not account:
                return 1

            # Calculate risk per contract
            risk_per_contract = abs(entry_price - stop_price)

            # Calculate maximum position size based on risk
            if risk_per_contract > 0:
                max_size_by_risk = int(self.max_risk_per_trade / risk_per_contract)
                position_size = min(max_size_by_risk, self.max_position_size)
                return max(1, position_size)  # At least 1 contract
            else:
                return 1

        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 1

    def execute_signal(self, signal_data):
        """Execute trading signal with proper risk management."""
        signal = signal_data["signal"]
        confidence = signal_data["confidence"]

        if signal == "NEUTRAL" or confidence < 75:
            return False

        try:
            # Check if we already have a position
            positions = self.position_manager.get_all_positions()
            mnq_positions = [p for p in positions if "MNQ" in p.contractId]

            if mnq_positions:
                print(f"   📊 Already have MNQ position, skipping signal")
                return False

            # Get current market price
            current_price = self.data_manager.get_current_price()
            if not current_price:
                print(f"   ❌ No current price available")
                return False

            current_price = Decimal(str(current_price))

            # Calculate entry and stop prices
            if signal == "LONG":
                entry_price = current_price + Decimal("0.25")  # Slightly above market
                stop_price = current_price - Decimal("10.0")  # $10 stop loss
                target_price = current_price + Decimal(
                    "20.0"
                )  # $20 profit target (2:1 R/R)
                side = 0  # Buy
            else:  # SHORT
                entry_price = current_price - Decimal("0.25")  # Slightly below market
                stop_price = current_price + Decimal("10.0")  # $10 stop loss
                target_price = current_price - Decimal(
                    "20.0"
                )  # $20 profit target (2:1 R/R)
                side = 1  # Sell

            # Calculate position size
            position_size = self.calculate_position_size(
                float(entry_price), float(stop_price)
            )

            # Get contract ID
            instrument = self.client.get_instrument("MNQ")
            if not instrument:
                print(f"   ❌ Could not get MNQ instrument")
                return False

            contract_id = instrument.id

            print(f"   🎯 Executing {signal} signal:")
            print(f"      Entry: ${entry_price:.2f}")
            print(f"      Stop: ${stop_price:.2f}")
            print(f"      Target: ${target_price:.2f}")
            print(f"      Size: {position_size} contracts")
            print(
                f"      Risk: ${abs(float(entry_price) - float(stop_price)):.2f} per contract"
            )
            print(f"      Confidence: {confidence}%")

            # Place bracket order
            bracket_response = self.order_manager.place_bracket_order(
                contract_id=contract_id,
                side=side,
                size=position_size,
                entry_price=float(entry_price),
                stop_loss_price=float(stop_price),
                take_profit_price=float(target_price),
                entry_type="limit",
            )

            if bracket_response.success:
                print(f"   ✅ Bracket order placed successfully!")
                print(f"      Entry Order: {bracket_response.entry_order_id}")
                print(f"      Stop Order: {bracket_response.stop_order_id}")
                print(f"      Target Order: {bracket_response.target_order_id}")

                self.last_signal_time = time.time()
                return True
            else:
                print(
                    f"   ❌ Failed to place bracket order: {bracket_response.error_message}"
                )
                return False

        except Exception as e:
            self.logger.error(f"Error executing signal: {e}")
            print(f"   ❌ Signal execution error: {e}")
            return False


def display_strategy_analysis(strategy):
    """Display current strategy analysis."""
    signal_data = strategy.generate_signal()

    print(f"\n📊 Multi-Timeframe Analysis:")
    print(
        f"   Signal: {signal_data['signal']} (Confidence: {signal_data['confidence']}%)"
    )

    analysis = signal_data.get("analysis", {})
    for tf_name, tf_data in analysis.items():
        tf = strategy.timeframes[tf_name]
        trend = tf_data["trend"]
        strength = tf_data["strength"]
        price = tf_data["price"]
        sma = tf_data["sma"]

        trend_emoji = (
            "📈" if trend == "bullish" else "📉" if trend == "bearish" else "➡️"
        )

        print(f"   {tf_name.replace('_', ' ').title()} ({tf}):")
        print(f"     {trend_emoji} Trend: {trend.upper()} (Strength: {strength:.1f}%)")
        print(f"     Price: ${price:.2f}, SMA: ${sma:.2f}")

    return signal_data


def wait_for_user_confirmation(message: str) -> bool:
    """Wait for user confirmation before proceeding."""
    print(f"\n⚠️  {message}")
    try:
        response = input("Continue? (y/N): ").strip().lower()
        return response == "y"
    except EOFError:
        # Handle EOF when input is piped (default to no for safety)
        print("N (EOF detected - defaulting to No for safety)")
        return False


def main():
    """Demonstrate multi-timeframe trading strategy."""
    logger = setup_logging(level="INFO")
    print("🚀 Multi-Timeframe Trading Strategy Example")
    print("=" * 60)

    # Safety warning
    print("⚠️  WARNING: This strategy can place REAL ORDERS!")
    print("   - Uses MNQ micro contracts")
    print("   - Implements risk management")
    print("   - Only use in simulated/demo accounts")
    print("   - Monitor positions closely")

    if not wait_for_user_confirmation("This strategy may place REAL ORDERS. Proceed?"):
        print("❌ Strategy example cancelled for safety")
        return False

    try:
        # Initialize client
        print("\n🔑 Initializing ProjectX client...")
        client = ProjectX.from_env()

        account = client.get_account_info()
        if not account:
            print("❌ Could not get account information")
            return False

        print(f"✅ Connected to account: {account.name}")
        print(f"   Balance: ${account.balance:,.2f}")
        print(f"   Simulated: {account.simulated}")

        # Create trading suite (integrated components)
        print("\n🏗️ Creating integrated trading suite...")
        try:
            jwt_token = client.get_session_token()

            # Define strategy timeframes
            timeframes = ["15min", "1hr", "4hr"]

            trading_suite = create_trading_suite(
                instrument="MNQ",
                project_x=client,
                jwt_token=jwt_token,
                account_id=str(account.id),
                timeframes=timeframes,
            )

            data_manager = trading_suite["data_manager"]
            order_manager = trading_suite["order_manager"]
            position_manager = trading_suite["position_manager"]

            print("✅ Trading suite created successfully")
            print(f"   Timeframes: {', '.join(timeframes)}")

        except Exception as e:
            print(f"❌ Failed to create trading suite: {e}")
            return False

        # Initialize with historical data
        print("\n📚 Initializing with historical data...")
        if data_manager.initialize(initial_days=10):
            print("✅ Historical data loaded (10 days)")
        else:
            print("❌ Failed to load historical data")
            return False

        # Start real-time feed
        print("\n🌐 Starting real-time data feed...")
        if data_manager.start_realtime_feed():
            print("✅ Real-time feed started")
        else:
            print("❌ Failed to start real-time feed")
            return False

        # Wait for data to stabilize
        print("\n⏳ Waiting for data to stabilize...")
        time.sleep(5)

        # Create strategy instance
        print("\n🧠 Initializing multi-timeframe strategy...")
        strategy = MultiTimeframeStrategy(
            data_manager, order_manager, position_manager, client
        )
        print("✅ Strategy initialized")

        # Show initial portfolio state
        print("\n" + "=" * 50)
        print("📊 INITIAL PORTFOLIO STATE")
        print("=" * 50)

        positions = position_manager.get_all_positions()
        print(f"Current Positions: {len(positions)}")
        for pos in positions:
            direction = "LONG" if pos.type == 1 else "SHORT"
            print(
                f"   {pos.contractId}: {direction} {pos.size} @ ${pos.averagePrice:.2f}"
            )

        # Show initial strategy analysis
        print("\n" + "=" * 50)
        print("🧠 INITIAL STRATEGY ANALYSIS")
        print("=" * 50)

        initial_signal = display_strategy_analysis(strategy)

        # Strategy monitoring loop
        print("\n" + "=" * 50)
        print("👀 STRATEGY MONITORING")
        print("=" * 50)

        print("Monitoring strategy for signals...")
        print("Strategy will analyze market every 30 seconds")
        print("Press Ctrl+C to stop")

        monitoring_cycles = 0
        signals_generated = 0
        orders_placed = 0

        try:
            # Run strategy for 5 minutes (10 cycles of 30 seconds)
            for cycle in range(10):
                cycle_start = time.time()

                print(f"\n⏰ Strategy Cycle {cycle + 1}/10")
                print("-" * 30)

                # Generate and display current signal
                signal_data = display_strategy_analysis(strategy)

                # Check for high-confidence signals
                if (
                    signal_data["signal"] != "NEUTRAL"
                    and signal_data["confidence"] >= 75
                ):
                    signals_generated += 1
                    print(f"\n🚨 HIGH CONFIDENCE SIGNAL DETECTED!")
                    print(f"   Signal: {signal_data['signal']}")
                    print(f"   Confidence: {signal_data['confidence']}%")

                    # Ask user before executing (safety)
                    if wait_for_user_confirmation(
                        f"Execute {signal_data['signal']} signal?"
                    ):
                        if strategy.execute_signal(signal_data):
                            orders_placed += 1
                            print(f"   ✅ Signal executed successfully")
                        else:
                            print(f"   ❌ Signal execution failed")
                    else:
                        print(f"   ℹ️  Signal execution skipped by user")

                # Show current positions and orders
                positions = position_manager.get_all_positions()
                orders = order_manager.search_open_orders()

                print(f"\n📊 Current Status:")
                print(f"   Open Positions: {len(positions)}")
                print(f"   Open Orders: {len(orders)}")

                # Check for filled orders
                filled_orders = []
                for order in orders:
                    if order_manager.is_order_filled(order.id):
                        filled_orders.append(order.id)

                if filled_orders:
                    print(f"   🎯 Recently Filled Orders: {filled_orders}")

                monitoring_cycles += 1

                # Wait for next cycle
                cycle_time = time.time() - cycle_start
                remaining_time = max(0, 30 - cycle_time)

                if cycle < 9:  # Don't sleep after last cycle
                    print(f"\n⏳ Waiting {remaining_time:.1f}s for next cycle...")
                    if remaining_time > 0:
                        time.sleep(remaining_time)

        except KeyboardInterrupt:
            print(f"\n⏹️ Strategy monitoring stopped by user")

        # Final analysis and statistics
        print("\n" + "=" * 50)
        print("📊 STRATEGY PERFORMANCE SUMMARY")
        print("=" * 50)

        print(f"Strategy Statistics:")
        print(f"   Monitoring Cycles: {monitoring_cycles}")
        print(f"   Signals Generated: {signals_generated}")
        print(f"   Orders Placed: {orders_placed}")

        # Show final portfolio state
        final_positions = position_manager.get_all_positions()
        final_orders = order_manager.search_open_orders()

        print(f"\nFinal Portfolio State:")
        print(f"   Open Positions: {len(final_positions)}")
        print(f"   Open Orders: {len(final_orders)}")

        if final_positions:
            print(f"   Position Details:")
            for pos in final_positions:
                direction = "LONG" if pos.type == 1 else "SHORT"
                pnl_info = position_manager.get_position_pnl(pos.contractId)
                pnl = pnl_info.get("unrealized_pnl", 0) if pnl_info else 0
                print(
                    f"     {pos.contractId}: {direction} {pos.size} @ ${pos.averagePrice:.2f} (P&L: ${pnl:+.2f})"
                )

        # Show final signal analysis
        print(f"\n🧠 Final Strategy Analysis:")
        final_signal = display_strategy_analysis(strategy)

        # Risk metrics
        try:
            risk_metrics = position_manager.get_risk_metrics()
            print(f"\n⚖️ Risk Metrics:")
            print(f"   Total Exposure: ${risk_metrics['total_exposure']:.2f}")
            print(
                f"   Largest Position Risk: {risk_metrics['largest_position_risk']:.2%}"
            )
        except Exception as e:
            print(f"   ❌ Risk metrics error: {e}")

        print("\n✅ Multi-timeframe strategy example completed!")
        print("\n📝 Key Features Demonstrated:")
        print("   ✅ Multi-timeframe trend analysis")
        print("   ✅ Technical indicator integration")
        print("   ✅ Signal generation and confidence scoring")
        print("   ✅ Risk management and position sizing")
        print("   ✅ Real-time strategy monitoring")
        print("   ✅ Integrated order and position management")

        print("\n📚 Next Steps:")
        print("   - Try examples/07_technical_indicators.py for indicator details")
        print("   - Review your positions in the trading platform")
        print("   - Study strategy performance and refine parameters")

        return True

    except KeyboardInterrupt:
        print("\n⏹️ Example interrupted by user")
        return False
    except Exception as e:
        logger.error(f"❌ Multi-timeframe strategy example failed: {e}")
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
