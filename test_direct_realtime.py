#!/usr/bin/env python3
"""
Test direct realtime client callbacks to understand the data flow.
"""

import asyncio
import logging

from project_x_py import TradingSuite

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_realtime_callbacks():
    """Test realtime callbacks directly."""
    logger.info("Testing realtime callbacks...")

    # Create trading suite
    suite = await TradingSuite.create("MNQ", timeframes=["1min"])

    # Track callbacks
    count = 0

    async def on_quote(data):
        nonlocal count
        count += 1
        logger.info(f"Direct realtime quote #{count}:")
        logger.info(f"  Type: {type(data)}")
        logger.info(f"  Data: {data}")
        if isinstance(data, dict):
            logger.info(f"  Keys: {list(data.keys())}")
            if "data" in data:
                logger.info(f"  data['data']: {data['data']}")

        if count >= 3:
            await suite.realtime.remove_callback("quote_update", on_quote)

    # Add callback directly to realtime client
    await suite.realtime.add_callback("quote_update", on_quote)

    # Wait
    await asyncio.sleep(5)

    # Cleanup
    await suite.disconnect()

    logger.info(f"Test complete. Received {count} quotes.")


if __name__ == "__main__":
    asyncio.run(test_realtime_callbacks())
