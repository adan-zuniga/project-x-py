import asyncio

from project_x_py import TradingSuite


async def place_market_order():
    suite = await TradingSuite.create("MNQ")

    try:
        # Place buy market order
        response = await suite["MNQ"].orders.place_market_order(
            contract_id=suite["MNQ"].instrument_info.id,  # Or use suite.instrument_info.id
            side=0,  # 0 = Buy, 1 = Sell
            size=1,  # Number of contracts
        )

        print(f"Market order placed: {response.orderId}")
        print(f"Status: {response.success}")

        # Wait for fill confirmation
        await asyncio.sleep(2)
        order_status = await suite["MNQ"].orders.get_order_statistics_async()
        print(f"Final status: {order_status}")

    except Exception as e:
        print(f"Order failed: {e}")
    finally:
        await suite.disconnect()


asyncio.run(place_market_order())
