import asyncio

from project_x_py import TradingSuite


async def main():
    # Traditional single instrument (still supported)
    suite = await TradingSuite.create(["MNQ"])  # List notation recommended
    mnq = suite["MNQ"]  # Access instrument context

    # Everything is ready:
    # - Client authenticated
    # - Real-time data connected
    # - Order and position managers initialized

    # Get current price
    price = await mnq.data.get_current_price()
    print(f"MNQ Current Price: ${price:.2f}")

    # Clean shutdown
    await suite.disconnect()


asyncio.run(main())
