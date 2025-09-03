import asyncio
from decimal import Decimal

from project_x_py import TradingSuite


async def place_limit_order():
    suite = await TradingSuite.create("MNQ")

    # Get current market price for context
    current_price = await suite["MNQ"].data.get_current_price()

    # Place buy limit order below market
    limit_price = Decimal(str(current_price)) - Decimal("2.00")  # $2.00 below market

    response = await suite["MNQ"].orders.place_limit_order(
        contract_id=suite["MNQ"].instrument_info.id,
        side=0,  # Buy
        size=1,
        limit_price=float(limit_price),
    )

    print(f"Limit order placed at ${limit_price}")
    print(f"Order ID: {response.orderId}")

    # Monitor order status
    while True:
        status = await suite["MNQ"].orders.get_order_by_id(response.orderId)
        if status is None:
            continue

        if status.status in [2, 3, 4]:
            print(
                f"Status: {'FILLED' if status.status == 2 else 'CANCELLED' if status.status == 3 else 'EXPIRED' if status.status == 4 else 'PENDING'}"
            )
            break

        await asyncio.sleep(5)  # Check every 5 seconds


asyncio.run(place_limit_order())
