import asyncio
from decimal import Decimal

from project_x_py import TradingSuite


async def main():
    # Initialize with order management capabilities
    suite = await TradingSuite.create("MNQ")

    mnq_context = suite["MNQ"]
    # Order manager is automatically available
    order_manager = mnq_context.orders

    # Get instrument information for proper pricing
    instrument = mnq_context.instrument_info
    print(f"Tick size: ${instrument.tickSize}")


asyncio.run(main())
