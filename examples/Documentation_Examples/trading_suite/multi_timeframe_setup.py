import asyncio

from project_x_py import TradingSuite


async def main():
    await multi_timeframe_setup()
    await multi_instrument_timeframes()


async def multi_timeframe_setup():
    # Setup with multiple timeframes for analysis
    suite = await TradingSuite.create(
        ["MNQ"],  # Single instrument with multiple timeframes
        timeframes=["1min", "5min", "15min"],
        initial_days=10,  # Load 10 days of historical data
    )

    mnq = suite["MNQ"]

    # Access different timeframe data
    bars_1min = await mnq.data.get_data("1min")
    bars_5min = await mnq.data.get_data("5min")
    bars_15min = await mnq.data.get_data("15min")

    if bars_1min is None or bars_5min is None or bars_15min is None:
        raise Exception("No data available")

    print(f"MNQ 1min bars: {len(bars_1min)}")
    print(f"MNQ 5min bars: {len(bars_5min)}")
    print(f"MNQ 15min bars: {len(bars_15min)}")

    await suite.disconnect()


# Multi-instrument with multiple timeframes
async def multi_instrument_timeframes():
    suite = await TradingSuite.create(
        ["MNQ", "ES"],  # List of instruments
        timeframes=["1min", "5min", "15min"],
    )

    # Each instrument has all timeframes available
    for symbol, context in suite.items():
        bars_1min = await context.data.get_data("1min")
        bars_5min = await context.data.get_data("5min")
        bars_15min = await context.data.get_data("15min")

        if bars_1min is None or bars_5min is None or bars_15min is None:
            raise Exception("No data available")
        print(f"{symbol} 1min bars: {len(bars_1min)}")
        print(f"{symbol} 5min bars: {len(bars_5min)}")
        print(f"{symbol} 15min bars: {len(bars_15min)}")

    await suite.disconnect()


asyncio.run(main())
