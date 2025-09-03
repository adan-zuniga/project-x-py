import asyncio
from decimal import Decimal

from project_x_py import TradingSuite


async def cancel_orders():
    suite = await TradingSuite.create("MNQ")

    # Place multiple orders
    orders: list[int] = []
    current_price = await suite["MNQ"].data.get_current_price()

    for i in range(3):
        price = Decimal(str(current_price)) - Decimal(str(10 * (i + 1)))
        response = await suite["MNQ"].orders.place_limit_order(
            contract_id=suite["MNQ"].instrument_info.id,
            side=0,
            size=1,
            limit_price=float(price),
        )
        orders.append(response.orderId)

    print(f"Placed {len(orders)} orders")

    # Cancel individual order
    await suite["MNQ"].orders.cancel_order(order_id=orders[0])
    print("Cancelled first order")

    # Cancel multiple orders
    for order in orders[1:]:
        await suite["MNQ"].orders.cancel_order(order_id=order)
    print("Cancelled remaining orders")

    # Cancel all open orders (nuclear option)
    await suite["MNQ"].orders.cancel_all_orders(contract_id=suite["MNQ"].instrument_info.id)
    print("All orders cancelled")


asyncio.run(cancel_orders())
