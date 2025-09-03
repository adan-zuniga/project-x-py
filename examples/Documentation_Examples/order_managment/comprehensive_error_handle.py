import asyncio
from decimal import Decimal

from project_x_py import TradingSuite
from project_x_py.exceptions import (
    ProjectXOrderError,
    ProjectXPositionError,
    ProjectXRateLimitError,
)


async def robust_order_placement():
    suite = await TradingSuite.create("MNQ")

    try:
        response = await suite["MNQ"].orders.place_bracket_order(
            contract_id=suite["MNQ"].instrument_info.id,
            side=0,
            size=1,
            entry_price=None,
            entry_type="market",
            stop_loss_price=float(Decimal("50")),
            take_profit_price=float(Decimal("100")),
        )

        print(f"Order 1 placed successfully: {response.entry_order_id}")

        # This will raise an error because if the entry_price is None, the entry_type must be "market"
        response = await suite["MNQ"].orders.place_bracket_order(
            contract_id=suite["MNQ"].instrument_info.id,
            side=1,
            size=1,
            entry_price=None,
            stop_loss_price=float(Decimal("50")),
            take_profit_price=float(Decimal("100")),
        )

    except ProjectXPositionError as e:
        print(f"Insufficient margin: {e}")
        # Reduce position size or add funds

    except ProjectXOrderError as e:
        print(f"Order error: {e}")
        if "invalid price" in str(e).lower():
            # Price alignment issue - check tick size
            instrument = suite["MNQ"].instrument_info
            print(f"Tick size: {instrument.tickSize}")

    except ProjectXRateLimitError as e:
        print(f"Rate limited: {e}")
        # Wait and retry
        await asyncio.sleep(1)
        # Retry logic here...

    except Exception as e:
        print(f"Unexpected error: {e}")

asyncio.run(robust_order_placement())
