#!/usr/bin/env python3
"""
Example 15: Risk Management with TradingSuite

Demonstrates the comprehensive risk management features of the SDK v3.0.2:
- Position sizing based on risk parameters
- Trade validation against risk rules
- Automatic stop-loss and take-profit attachment
- Managed trades with context manager
- Risk metrics and analysis

Author: @TexasCoding
Date: 2025-08-04
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from project_x_py import TradingSuite
from project_x_py.models import Order
from project_x_py.types import OrderSide, OrderType


async def main() -> None:
    """Demonstrate risk management features."""
    print("=== ProjectX SDK v3.0.2 - Risk Management Example ===\n")

    # Create trading suite with risk management enabled
    print("Creating TradingSuite with risk management...")
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["5min", "15min"],
        features=["risk_manager"],  # Enable risk management
        initial_days=5,
    )

    print(f"✓ Suite created for {suite['MNQ'].instrument_info.symbolId}")
    print(f"✓ Risk manager enabled: {suite['MNQ'].risk_manager is not None}")

    # Wait for data to be ready
    print("\nWaiting for data...")
    await asyncio.sleep(3)

    # Get current market price
    latest_bar = await suite["MNQ"].data.get_latest_bars(1, "5min")
    if latest_bar is None or latest_bar.is_empty():
        print("No data available yet")
        return

    current_price = float(latest_bar["close"][-1])
    print(f"\nCurrent price: ${current_price:,.2f}")

    # 1. Calculate position size based on risk
    print("\n=== Position Sizing ===")

    stop_loss = current_price - 50  # $50 stop loss

    # Calculate size for 1% risk
    assert suite["MNQ"].risk_manager is not None
    sizing = await suite["MNQ"].risk_manager.calculate_position_size(
        entry_price=current_price,
        stop_loss=stop_loss,
        risk_percent=0.01,  # Risk 1% of account
    )

    print(f"Entry price: ${sizing['entry_price']:,.2f}")
    print(f"Stop loss: ${sizing['stop_loss']:,.2f}")
    print(f"Risk amount: ${sizing['risk_amount']:,.2f}")
    print(f"Position size: {sizing['position_size']} contracts")
    print(f"Account balance: ${sizing['account_balance']:,.2f}")

    # 2. Validate trade against risk rules
    print("\n=== Trade Validation ===")

    # Create a mock order for validation
    mock_order = Order(
        id=0,
        accountId=0,
        contractId=suite["MNQ"].symbol,
        creationTimestamp=datetime.now().isoformat(),
        updateTimestamp=None,
        status=1,  # Open
        type=OrderType.LIMIT.value,
        side=OrderSide.BUY.value,
        size=sizing["position_size"],
        limitPrice=current_price,
    )

    validation = await suite["MNQ"].risk_manager.validate_trade(mock_order)

    print(f"Trade valid: {validation['is_valid']}")
    if validation["reasons"]:
        print(f"Rejection reasons: {validation['reasons']}")
    if validation["warnings"]:
        print(f"Warnings: {validation['warnings']}")
    print(f"Daily trades: {validation['daily_trades']}")
    print(f"Daily loss: ${validation['daily_loss']:,.2f}")
    print(f"Position count: {validation['position_count']}")

    # 3. Get current risk metrics
    print("\n=== Risk Metrics ===")

    risk_metrics = await suite["MNQ"].risk_manager.get_risk_metrics()

    print(f"Current risk: {risk_metrics['current_risk'] * 100:.2f}%")
    print(f"Max risk allowed: {risk_metrics['max_risk'] * 100:.2f}%")
    print(f"Daily loss: ${risk_metrics['daily_loss']:,.2f}")
    print(f"Daily loss limit: {risk_metrics['daily_loss_limit'] * 100:.2f}%")
    print(
        f"Daily trades: {risk_metrics['daily_trades']}/{risk_metrics['daily_trade_limit']}"
    )
    print(f"Win rate: {risk_metrics['win_rate'] * 100:.1f}%")
    print(f"Profit factor: {risk_metrics['profit_factor']:.2f}")
    print(f"Sharpe ratio: {risk_metrics['sharpe_ratio']:.2f}")

    # 4. Demonstrate managed trade (simulation only)
    print("\n=== Managed Trade Example (Simulation) ===")

    print("\nManaged trade would execute:")
    print("1. Calculate position size based on risk")
    print("2. Validate trade against risk rules")
    print("3. Place entry order")
    print(f"4. Automatically attach stop-loss at ${stop_loss:,.2f}")
    print(f"5. Automatically attach take-profit at ${current_price + 100:,.2f}")
    print("6. Monitor position and adjust stops if configured")
    print("7. Clean up on exit")

    # Show example code
    print("\nExample code:")
    print("""
    async with suite["MNQ"].managed_trade(max_risk_percent=0.01) as trade:
        result = await trade.enter_long(
            stop_loss=current_price - 50,
            take_profit=current_price + 100,
        )

        # Optional: Scale in if conditions are met
        if favorable_conditions:
            await trade.scale_in(additional_size=1)

        # Optional: Adjust stop to breakeven
        if price_moved_favorably:
            await trade.adjust_stop(new_stop_loss=entry_price)
    """)

    # 5. Risk configuration overview
    print("\n=== Risk Configuration ===")

    config = suite["MNQ"].risk_manager.config
    print(f"Max risk per trade: {config.max_risk_per_trade * 100:.1f}%")
    print(f"Max daily loss: {config.max_daily_loss * 100:.1f}%")
    print(f"Max positions: {config.max_positions}")
    print(f"Max position size: {config.max_position_size}")
    print(f"Use stop loss: {config.use_stop_loss}")
    print(f"Use take profit: {config.use_take_profit}")
    print(f"Use trailing stops: {config.use_trailing_stops}")
    print(f"Default R:R ratio: 1:{config.default_risk_reward_ratio}")

    # Show stats
    stats = await suite.get_stats()
    rm_stats = stats["components"].get("risk_manager") if stats["components"] else None
    rm_status = rm_stats["status"] if rm_stats else "N/A"
    print(f"\n✓ Risk manager active: {rm_status}")

    # Cleanup
    await suite.disconnect()
    print("\n✓ Suite disconnected")


if __name__ == "__main__":
    # Check for required environment variables
    if not os.getenv("PROJECT_X_API_KEY") or not os.getenv("PROJECT_X_USERNAME"):
        print(
            "Error: Please set PROJECT_X_API_API_KEY and PROJECT_X_USERNAME environment variables"
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
