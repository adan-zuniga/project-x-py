import asyncio

from project_x_py import TradingSuite


async def pairs_trading_example():
    suite = await TradingSuite.create(["ES", "MNQ"])  # S&P 500 vs NASDAQ

    es_context = suite["ES"]
    mnq_context = suite["MNQ"]

    # Get current prices
    es_price = await es_context.data.get_current_price()
    mnq_price = await mnq_context.data.get_current_price()

    if es_price is None or mnq_price is None:
        raise Exception("No price data available")

    # Calculate spread (normalize by contract values)
    spread = (es_price * 50) - (mnq_price * 20)
    print(f"ES/MNQ Spread: ${spread:.2f}")

    # Simple spread trading logic
    if spread > 500:  # ES expensive relative to MNQ
        await es_context.orders.place_market_order(
            contract_id=es_context.instrument_info.id,
            side=1,
            size=1,  # Sell ES
        )
        await mnq_context.orders.place_market_order(
            contract_id=mnq_context.instrument_info.id,
            side=0,
            size=1,  # Buy MNQ
        )
        print("Executed pairs trade: Short ES, Long MNQ")

    await suite.disconnect()


asyncio.run(pairs_trading_example())
