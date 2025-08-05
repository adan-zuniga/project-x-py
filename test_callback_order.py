#!/usr/bin/env python3
"""
Test callback registration order.
"""

import asyncio
import logging

from project_x_py import TradingSuite
from project_x_py.event_bus import EventType

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_callbacks():
    """Test callback registration."""
    logger.info("Testing callback registration order...")

    # Create trading suite
    suite = await TradingSuite.create("MNQ", timeframes=["1min"])

    # Track all callbacks
    call_count = 0

    # Handler 1
    async def handler1(event):
        nonlocal call_count
        call_count += 1
        logger.info(f"Handler1 #{call_count}: data={event.data}")

    # Handler 2
    async def handler2(event):
        logger.info(
            f"Handler2: data.get('bid')={event.data.get('bid')}, data.get('ask')={event.data.get('ask')}"
        )

    # Register handlers
    await suite.on(EventType.QUOTE_UPDATE, handler1)
    await suite.on(EventType.QUOTE_UPDATE, handler2)

    # Wait for a few quotes
    await asyncio.sleep(3)

    # Cleanup
    await suite.disconnect()

    logger.info(f"Test complete. Received {call_count} callbacks.")


if __name__ == "__main__":
    asyncio.run(test_callbacks())
