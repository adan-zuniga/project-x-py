import asyncio

from project_x_py import TradingSuite


async def multi_instrument_setup():
    # Create suite with multiple instruments

    suite = await TradingSuite.create(
        ["MNQ", "MES", "MCL"],  # List of instruments
        timeframes=["1min", "5min"],
    )

    # Suite acts as a dictionary
    print(f"Managing {len(suite)} instruments")
    print(f"Instruments: {list(suite.keys())}")

    # Access each instrument context
    for symbol in suite:
        context = suite[symbol]
        print(f"{symbol}: {context.instrument_info.name}")

    await suite.disconnect()

asyncio.run(multi_instrument_setup())
