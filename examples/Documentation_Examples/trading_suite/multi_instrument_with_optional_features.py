import asyncio

from project_x_py import TradingSuite
from project_x_py.trading_suite import Features


async def feature_setup():
    # Enable optional features for multiple instruments
    suite = await TradingSuite.create(
        ["MNQ", "MES"],  # List of instruments
        timeframes=["1min", "5min"],
        features=[Features.ORDERBOOK, Features.RISK_MANAGER],
    )

    # Wait for 120 seconds to ensure features are initialized
    await asyncio.sleep(20)

    # Each instrument has its own feature instances
    total_exposure = 0.0
    for symbol, context in suite.items():
        print(f"\n{symbol} Features:")

        # Level 2 order book data (per instrument)
        if context.orderbook:
            snapshot = await context.orderbook.get_orderbook_snapshot()

            print(snapshot)
            print(
                f"  Order book depth: {len(snapshot['bids'])} bids, {len(snapshot['asks'])} asks"
            )

        # Risk management tools (per instrument)
        if context.risk_manager:
            # Access risk configuration
            config = context.risk_manager.config
            print(f"  Max position size: {config.max_position_size}")

            # Get current risk metrics
            metrics = await context.risk_manager.get_risk_metrics()
            print(f"  Current risk: ${metrics['current_risk']:,.2f}")
            print(f"  Margin used: ${metrics['margin_used']:,.2f}")
            total_exposure += metrics["margin_used"]

    # Portfolio-level risk summary
    print(f"\nTotal Portfolio Exposure: ${total_exposure:,.2f}")

    await suite.disconnect()


asyncio.run(feature_setup())
