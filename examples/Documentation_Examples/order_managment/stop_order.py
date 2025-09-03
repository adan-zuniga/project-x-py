import asyncio
from decimal import Decimal

from project_x_py import TradingSuite


async def place_stop_order():
    suite = await TradingSuite.create("MNQ")

    current_price = await suite["MNQ"].data.get_current_price()

    # Stop loss order (sell stop below current price)
    stop_price = Decimal(str(current_price)) - Decimal("2.00")  # $2.00 below market

    response = await suite["MNQ"].orders.place_stop_order(
        contract_id=suite["MNQ"].instrument_info.id,
        side=1,  # Sell (for stop loss)
        size=1,
        stop_price=float(stop_price),
    )

    print(f"Stop order placed at ${stop_price}")

    # Or stop entry order (buy stop above current price for breakouts)
    breakout_price = Decimal(str(current_price)) + Decimal("2.00")

    breakout_response = await suite["MNQ"].orders.place_stop_order(
        contract_id=suite["MNQ"].instrument_info.id,
        side=0,  # Buy
        size=1,
        stop_price=float(breakout_price),
    )

    print(f"Breakout order placed at ${breakout_price}")


asyncio.run(place_stop_order())
