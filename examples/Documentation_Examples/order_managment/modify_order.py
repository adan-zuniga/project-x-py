import asyncio
from decimal import Decimal

from project_x_py import TradingSuite


async def modify_orders():
    suite = await TradingSuite.create("MNQ")

    # Place initial limit order
    current_price = await suite["MNQ"].data.get_current_price()
    initial_price = Decimal(str(current_price)) - Decimal("50")

    response = await suite["MNQ"].orders.place_limit_order(
        contract_id=suite["MNQ"].instrument_info.id,
        side=0,
        size=1,
        limit_price=float(initial_price),
    )

    order_id = response.orderId
    print(f"Initial order at ${initial_price}")

    # Wait a moment
    await asyncio.sleep(5)

    # Modify the order price (move closer to market)
    new_price = Decimal(str(current_price)) - Decimal("25")

    modify_response = await suite["MNQ"].orders.modify_order(
        order_id=order_id,
        limit_price=float(new_price),
        size=2,  # Also increase size
    )

    print(f"Order modified to ${new_price}, size: 2")

    # Modify only specific fields
    await suite["MNQ"].orders.modify_order(
        order_id=order_id,
        size=3,  # Only change size
    )


asyncio.run(modify_orders())
