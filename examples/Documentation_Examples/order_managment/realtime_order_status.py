import asyncio
from decimal import Decimal

from project_x_py import EventType, TradingSuite
from project_x_py.event_bus import Event


def on_order_update(event: Event):
    order_data = event.data
    print(f"Order {order_data['order_id']} status: {order_data['status']}")

    if order_data["status"] == "FILLED":
        print(f"  Filled at ${order_data['fill_price']}")
        print(f"  Quantity: {order_data['filled_quantity']}")


async def setup_order_tracking():
    suite = await TradingSuite.create("MNQ")

    # Event-driven tracking (recommended)
    async def on_order_update(event: Event):
        order_data = event.data

        print(order_data)
        print(f"Order {order_data['order_id']} status: {order_data['new_status']}")

        if order_data["status"] == "FILLED":
            print(f"  Filled at ${order_data['filledPrice']}")
            print(f"  Quantity: {order_data['filled_quantity']}")
        if order_data["status"] == "MODIFIED":
            print(f"  Modified at ${order_data['limitPrice']}")
            print(f"  Quantity: {order_data['size']}")

    current_price = await suite["MNQ"].data.get_current_price()
    if current_price:
        limit_price = Decimal(str(current_price)) - Decimal("2.0")
    else:
        return

    # Place an order to demonstrate tracking
    response = await suite["MNQ"].orders.place_limit_order(
        contract_id=suite["MNQ"].instrument_info.id,
        side=0,
        size=1,
        limit_price=float(limit_price),
    )
    print(f"Tracking order: {response.orderId}")

    await suite.on(EventType.ORDER_FILLED, on_order_update)
    await suite.on(EventType.ORDER_MODIFIED, on_order_update)

    # Keep connection alive for events
    await asyncio.sleep(30)


asyncio.run(setup_order_tracking())
