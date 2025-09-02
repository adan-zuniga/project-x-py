import asyncio

from project_x_py import TradingSuite


async def multi_instrument_setup():
    # Create suite for multiple instruments
    suite = await TradingSuite.create(
        instruments=["MNQ", "ES", "MGC"],  # Multiple futures
        timeframes=["1min", "5min"],
        features=["orderbook", "risk_manager"],
    )

    print(f"Managing {len(suite)} instruments: {list(suite.keys())}")

    # Access individual instruments
    for symbol, context in suite.items():
        current_price = await context.data.get_current_price()
        print(f"{symbol}: ${current_price:,.2f}")

    await suite.disconnect()


asyncio.run(multi_instrument_setup())
