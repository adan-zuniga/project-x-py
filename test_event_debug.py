#!/usr/bin/env python3
"""
Debug the event system data structure.
"""

import asyncio
import logging

from project_x_py import TradingSuite
from project_x_py.event_bus import EventType

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_quotes():
    """Test quote updates."""
    logger.info("Testing quote event structure...")

    # Create trading suite
    suite = await TradingSuite.create("MNQ", timeframes=["1min"])

    # Track quote updates
    quote_count = 0

    async def on_quote(event):
        nonlocal quote_count
        quote_count += 1
        logger.info(f"Quote #{quote_count}:")
        logger.info(f"  Event type: {type(event)}")
        logger.info(f"  Event attributes: {dir(event)}")
        logger.info(f"  Event.data type: {type(event.data)}")
        logger.info(f"  Event.data: {event.data}")
        if hasattr(event, "type"):
            logger.info(f"  Event.type: {event.type}")
        if hasattr(event, "source"):
            logger.info(f"  Event.source: {event.source}")

        # Only show first 3 for brevity
        if quote_count >= 3:
            suite.events.off(EventType.QUOTE_UPDATE, on_quote)

    # Register handler
    await suite.on(EventType.QUOTE_UPDATE, on_quote)

    # Wait for quotes
    logger.info("Waiting for quotes...")
    await asyncio.sleep(5)

    # Cleanup
    await suite.disconnect()

    logger.info(f"Test complete. Received {quote_count} quotes.")


if __name__ == "__main__":
    asyncio.run(test_quotes())
