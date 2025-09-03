import asyncio
from decimal import Decimal

from project_x_py import TradingSuite
from project_x_py.models import BracketOrderResponse


async def place_bracket_order():
    suite = await TradingSuite.create("MNQ")

    current_price = await suite["MNQ"].data.get_current_price()

    # Complete bracket order setup
    response = await suite["MNQ"].orders.place_bracket_order(
        contract_id=suite["MNQ"].instrument_info.id,
        side=0,  # Buy entry
        size=1,
        # Entry order (optional - if None, uses market order)
        entry_type="market",
        entry_price=None,
        # Risk management
        stop_loss_price=float(
            Decimal(str(current_price)) - Decimal("4")
        ),  # Stop loss $4 from entry
        take_profit_price=float(
            Decimal(str(current_price)) + Decimal("8")
        ),  # Take profit $8 from entry
        # Order timing
    )


    print("Bracket order placed:")
    print(f"  Entry: {response.entry_order_id}")
    print(f"  Stop Loss: {response.stop_order_id}")
    print(f"  Take Profit: {response.target_order_id}")

    # Monitor bracket order progress
    await monitor_bracket_order(suite, response)


async def monitor_bracket_order(
    suite: TradingSuite, bracket_response: BracketOrderResponse
):
    """Monitor all three orders in a bracket."""

    while True:
        if bracket_response.entry_order_id is None:
            continue
        # Check main order status
        main_status = await suite["MNQ"].orders.get_order_by_id(
            bracket_response.entry_order_id
        )

        print(f"Entry order: {main_status}")

        if main_status == "FILLED":
            print("Entry filled! Monitoring exit orders...")

            # Now monitor the exit orders
            while True:
                if bracket_response.stop_order_id is None:
                    continue
                stop_status = await suite["MNQ"].orders.get_order_by_id(
                    bracket_response.stop_order_id
                )
                if bracket_response.target_order_id is None:
                    continue
                target_status = await suite["MNQ"].orders.get_order_by_id(
                    bracket_response.target_order_id
                )

                if stop_status is None:
                    continue
                if target_status is None:
                    continue
                if stop_status.status == 2:
                    print("Stop loss triggered!")
                    break
                elif target_status.status == 2:
                    print("Take profit hit!")
                    break

                await asyncio.sleep(2)
            break

        elif main_status in ["CANCELLED", "REJECTED"]:
            print(f"Entry order {main_status}")
            break

        await asyncio.sleep(5)


asyncio.run(place_bracket_order())
