import asyncio

from project_x_py import EventType, TradingSuite
from project_x_py.event_bus import Event


async def multi_stream_data():
    suite = await TradingSuite.create(
        ["MNQ", "ES", "MGC"],
        timeframes=["15sec", "1min"],
    )

    # Register handlers for each instrument
    for symbol, context in suite.items():

        async def make_handler(sym):
            async def on_new_bar(event: Event):
                data = event.data
                if data.get("timeframe") == "1min":
                    bar = data.get("data")
                    print(f"{sym} 1min: ${bar['close']:,.2f}")

            return on_new_bar

        handler = await make_handler(symbol)
        await context.on(EventType.NEW_BAR, handler)

    # Stream all instruments simultaneously
    await asyncio.sleep(30)
    await suite.disconnect()


asyncio.run(multi_stream_data())
