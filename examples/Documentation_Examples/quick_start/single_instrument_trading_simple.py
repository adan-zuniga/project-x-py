import asyncio

from project_x_py import TradingSuite


async def trading_example():
    suite = await TradingSuite.create(["MNQ"])  # List notation
    mnq = suite["MNQ"]  # Get instrument context

    # Place a market order
    order = await mnq.orders.place_market_order(
        contract_id=mnq.instrument_info.id,
        side=0,  # 0=Buy, 1=Sell
        size=1,
    )
    print(f"Order placed: {order.orderId}")

    # Check position
    position = await mnq.positions.get_position("MNQ")
    if position:
        print(f"Position: {position.size} @ ${position.averagePrice:,.2f}")

    # Place a stop loss
    if position and position.size > 0:
        stop_order = await mnq.orders.place_stop_order(
            contract_id=mnq.instrument_info.id,
            side=1,  # Sell
            size=position.size,
            stop_price=position.averagePrice - 20,  # 20 points below entry
        )
        print(f"Stop loss placed: {stop_order.orderId}")

    await suite.disconnect()

asyncio.run(trading_example())
