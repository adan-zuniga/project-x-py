import asyncio

from project_x_py import TradingSuite


async def multi_instrument_main():
    # Revolutionary multi-instrument support
    suite = await TradingSuite.create(
        instruments=["MNQ", "ES", "MGC"],  # Multiple futures
        timeframes=["1min", "5min"],
        features=["orderbook", "risk_manager"],
    )

    print(f"Managing {len(suite)} instruments: {list(suite.keys())}")

    # Dictionary-like access to each instrument
    mnq_context = suite["MNQ"]
    es_context = suite["ES"]
    mgc_context = suite["MGC"]

    # Get prices for all instruments
    for symbol, context in suite.items():
        price = await context.data.get_current_price()
        print(f"{symbol}: ${price:.2f}")

    await suite.disconnect()


asyncio.run(multi_instrument_main())
