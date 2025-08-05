#!/usr/bin/env python3
"""
Test EventBus quote events to debug the data structure.
"""

import asyncio
import json
import logging

from project_x_py import TradingSuite
from project_x_py.event_bus import EventType

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_eventbus_quotes():
    """Test EventBus quote updates."""
    logger.info("Testing EventBus quote structure...")

    # Create trading suite
    suite = await TradingSuite.create("MNQ", timeframes=["1min"])

    # Track events
    count = 0

    async def on_quote(event):
        nonlocal count
        count += 1
        logger.info(f"\nEventBus Quote #{count}:")
        logger.info(f"  event: {event}")
        logger.info(f"  event.type: {event.type}")
        logger.info(f"  event.source: {event.source}")
        logger.info(f"  event.data type: {type(event.data)}")
        logger.info(f"  event.data: {json.dumps(event.data, default=str, indent=2)}")

        if count >= 3:
            await suite.off(EventType.QUOTE_UPDATE, on_quote)

    # Register handler via EventBus
    await suite.on(EventType.QUOTE_UPDATE, on_quote)

    # Wait
    await asyncio.sleep(5)

    # Cleanup
    await suite.disconnect()

    logger.info(f"Test complete. Received {count} quotes.")


if __name__ == "__main__":
    asyncio.run(test_eventbus_quotes())
