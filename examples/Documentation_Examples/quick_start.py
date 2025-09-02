import asyncio

from project_x_py import TradingSuite
from project_x_py.indicators import MACD, RSI, SMA


async def main():
    # V3.5.4: Multi-instrument TradingSuite with chaos theory indicators
    suite = await TradingSuite.create(
        instruments=["MNQ", "ES", "MGC"],  # Multiple instruments
        timeframes=["1min", "5min"],
        features=["orderbook", "risk_manager"],
    )

    # Access specific instruments
    mnq_context = suite["MNQ"]
    es_context = suite["ES"]

    # Get market data with technical analysis
    mnq_data = await mnq_context.data.get_data("1min", bars=100)
    if mnq_data is None:
        raise Exception("No data available")

    mnq_data = mnq_data.pipe(RSI, period=14).pipe(SMA, period=20)

    print(f"MNQ RSI(14): {mnq_data['rsi_14'][-1]:.2f}")
    print(f"MNQ SMA(20): {mnq_data['sma_20'][-1]:.2f}")

    # Multi-instrument trading
    await mnq_context.orders.place_limit_order(
        contract_id=mnq_context.instrument_info.id, side=0, size=1, limit_price=21050.0
    )

    # Portfolio-level analytics
    for symbol, context in suite.items():
        price = await context.data.get_current_price()
        print(f"{symbol}: ${price:.2f}")

    await suite.disconnect()


# Run the async function
asyncio.run(main())
