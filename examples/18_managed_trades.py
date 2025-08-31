#!/usr/bin/env python3
"""
Example 16: Managed Trades with Automatic Risk Management

Demonstrates the ManagedTrade context manager for simplified trading:
- Automatic position sizing based on risk
- Entry order placement with validation
- Automatic stop-loss and take-profit attachment
- Position scaling capabilities
- Clean resource management

Author: @TexasCoding
Date: 2025-08-04
"""

import asyncio
import os
import sys

# Add the src directory to the Python path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from project_x_py import TradingSuite


async def simple_long_trade(suite: TradingSuite) -> None:
    """Execute a simple long trade with risk management."""
    print("\n=== Simple Long Trade with Risk Management ===")

    # Get current price
    latest_bars = await suite["MNQ"].data.get_latest_bars(count=1, timeframe="5min")
    if latest_bars is None or latest_bars.is_empty():
        print("No data available")
        return

    current_price = float(latest_bars["close"][0])
    print(f"Current price: ${current_price:,.2f}")

    # Execute managed trade
    print("\nExecuting managed long trade (simulation)...")

    # In a real scenario, this would execute:
    try:
        # Create managed trade context
        # async with suite["MNQ"].managed_trade(max_risk_percent=0.01) as trade:
        #     # Enter long with automatic position sizing
        #     result = await trade.enter_long(
        #         stop_loss=current_price - 50,      # $50 stop
        #         take_profit=current_price + 100,   # $100 target (2:1 R:R)
        #     )
        #
        #     print(f"✓ Entry order placed: {result['entry_order'].orderId}")
        #     print(f"✓ Stop order attached: {result['stop_order'].orderId}")
        #     print(f"✓ Target order attached: {result['target_order'].orderId}")
        #     print(f"✓ Position size: {result['size']} contracts")
        #     print(f"✓ Risk amount: ${result['risk_amount']:,.2f}")

        # For demo purposes, show what would happen
        print("Trade execution steps:")
        print("1. Calculate position size for 1% risk")
        print("2. Validate trade against risk rules")
        print("3. Place market/limit entry order")
        print(f"4. Attach stop-loss at ${current_price - 50:,.2f}")
        print(f"5. Attach take-profit at ${current_price + 100:,.2f}")
        print("6. Monitor position until exit")

    except ValueError as e:
        print(f"Trade rejected: {e}")


async def advanced_trade_management(suite: TradingSuite) -> None:
    """Demonstrate advanced trade management features."""
    print("\n=== Advanced Trade Management ===")

    # Get current price
    latest_bars = await suite["MNQ"].data.get_latest_bars(count=1, timeframe="5min")
    if latest_bars is None or latest_bars.is_empty():
        print("No data available")
        return

    current_price = float(latest_bars["close"][0])
    entry_price = current_price - 10  # Limit order below market

    print(f"Current price: ${current_price:,.2f}")
    print(f"Planned entry: ${entry_price:,.2f}")

    # Advanced trade example (simulation)
    print("\nAdvanced trade features (simulation):")

    # Show what the code would do
    example_code = """
    async with suite["MNQ"].managed_trade(max_risk_percent=0.01) as trade:
        # Enter with limit order
        result = await trade.enter_long(
            entry_price=entry_price,        # Limit order
            stop_loss=entry_price - 30,     # $30 stop
            order_type=OrderType.LIMIT,
        )

        # Wait for fill
        await suite.wait_for(EventType.ORDER_FILLED, timeout=300)

        # Scale in if price dips
        if current_price < entry_price - 5:
            await trade.scale_in(
                additional_size=1,
                new_stop_loss=entry_price - 25,  # Tighten stop
            )

        # Move stop to breakeven after profit
        if current_price > entry_price + 20:
            await trade.adjust_stop(new_stop_loss=entry_price)

        # Scale out partial position
        if current_price > entry_price + 40:
            await trade.scale_out(
                exit_size=1,
                limit_price=current_price + 5,
            )
    """

    print("Advanced features demonstrated:")
    print("1. Limit order entry")
    print("2. Scaling into position")
    print("3. Adjusting stop-loss dynamically")
    print("4. Scaling out of position")
    print("5. Automatic cleanup on exit")

    print("\nExample code:")
    print(example_code)


async def risk_validation_demo(suite: TradingSuite) -> None:
    """Demonstrate risk validation and rejection."""
    print("\n=== Risk Validation Demo ===")

    # Get current price
    latest_bars = await suite["MNQ"].data.get_latest_bars(count=1, timeframe="5min")
    if latest_bars is None or latest_bars.is_empty():
        print("No data available")
        return

    current_price = float(latest_bars["close"][0])

    # Show various validation scenarios
    print("\nRisk validation scenarios:")

    # 1. Valid trade
    print("\n1. Valid trade (1% risk):")
    assert suite["MNQ"].risk_manager is not None
    sizing = await suite["MNQ"].risk_manager.calculate_position_size(
        entry_price=current_price,
        stop_loss=current_price - 50,
        risk_percent=0.01,
    )
    print(f"   Position size: {sizing['position_size']} contracts")
    print(f"   Risk amount: ${sizing['risk_amount']:,.2f}")
    print("   ✓ Would pass validation")

    # 2. Excessive position size
    print("\n2. Excessive position size:")
    print("   Requested: 15 contracts")
    print(f"   Max allowed: {suite['MNQ'].risk_manager.config.max_position_size}")
    print("   ✗ Would be rejected")

    # 3. Too many positions
    print("\n3. Too many open positions:")
    print("   Current positions: 3")
    print(f"   Max allowed: {suite['MNQ'].risk_manager.config.max_positions}")
    print("   ✗ Would be rejected")

    # 4. Daily loss limit
    print("\n4. Daily loss limit reached:")
    print("   Daily loss: 3.5%")
    print(f"   Max allowed: {suite['MNQ'].risk_manager.config.max_daily_loss * 100}%")
    print("   ✗ Would be rejected")


async def main() -> None:
    """Run risk management examples."""
    print("=== ProjectX SDK v3.0.2 - Managed Trades Example ===\n")

    # Create trading suite with risk management
    print("Creating TradingSuite with risk management...")
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["5min", "15min"],
        features=["risk_manager"],
        initial_days=5,
    )

    print(f"✓ Suite created for {suite['MNQ'].instrument_info.id}")
    print("✓ Risk manager enabled")

    # Wait for data
    print("\nWaiting for data...")
    await asyncio.sleep(3)

    # Run examples
    await simple_long_trade(suite)
    await advanced_trade_management(suite)
    await risk_validation_demo(suite)

    # Show risk manager benefits
    print("\n=== Risk Manager Benefits ===")
    print("✓ Automatic position sizing based on account risk")
    print("✓ Trade validation before execution")
    print("✓ Automatic stop-loss attachment")
    print("✓ Position monitoring and management")
    print("✓ Daily loss and trade limits")
    print("✓ Clean resource management")
    print("✓ Reduced code complexity")

    # Cleanup
    await suite.disconnect()
    print("\n✓ Suite disconnected")


if __name__ == "__main__":
    # Check for required environment variables
    if not os.getenv("PROJECT_X_API_KEY") or not os.getenv("PROJECT_X_USERNAME"):
        print(
            "Error: Please set PROJECT_X_API_KEY and PROJECT_X_USERNAME environment variables"
        )
        sys.exit(1)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExample interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
