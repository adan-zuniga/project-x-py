import asyncio

from project_x_py import EventType, TradingSuite
from project_x_py.event_bus import Event


async def stream_data():
    suite = await TradingSuite.create(["MNQ"], timeframes=["15sec", "1min"])

    mnq = suite["MNQ"]

    # Register event handlers
    async def on_new_bar(event: Event):
        data = event.data
        timeframe = data.get("timeframe")
        bar = data.get("data")
        if bar:
            print(
                f"MNQ New {timeframe} bar: ${bar['close']:,.2f} Vol: {bar['volume']:,}"
            )

    async def on_quote(event: Event):
        quote = event.data

        if quote["bid"] is None or quote["ask"] is None:
            return

        print(f"MNQ Quote: Bid ${quote['bid']:,.2f} Ask ${quote['ask']:,.2f}")

    # Subscribe to events for MNQ
    await mnq.on(EventType.NEW_BAR, on_new_bar)
    await mnq.on(EventType.QUOTE_UPDATE, on_quote)

    # Keep streaming for 30 seconds
    await asyncio.sleep(30)

    await suite.disconnect()


asyncio.run(stream_data())
