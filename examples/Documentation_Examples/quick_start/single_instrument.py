import asyncio

from project_x_py import TradingSuite


async def main():
    # Create a trading suite for single instrument
    suite = await TradingSuite.create(
        instruments=["MNQ"],  # List notation (recommended)
        timeframes=["1min", "5min"],
        features=["orderbook"],  # Optional features
        initial_days=5,  # Historical data to load
    )

    # Access the instrument context
    mnq = suite["MNQ"]

    if suite.client.account_info is None:
        raise Exception("Account info is None")

    # Everything is now connected and ready
    print(f"Connected to: {suite.client.account_info.name}")

    # Access current market data
    current_price = await mnq.data.get_current_price()
    print(f"MNQ Current price: ${current_price:,.2f}")

    # Clean shutdown
    await suite.disconnect()


# Run the async function
asyncio.run(main())
