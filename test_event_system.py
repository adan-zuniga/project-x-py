#!/usr/bin/env python3
"""
Quick test of the unified event system fix.
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
    logger.info("Testing quote updates...")

    # Create trading suite
    suite = await TradingSuite.create("MNQ", timeframes=["1min"])

    # Track quote updates
    quote_count = 0

    async def on_quote(event):
        nonlocal quote_count
        quote_count += 1
        data = event.data
        logger.info(
            f"Quote #{quote_count}: Bid={data.get('bid')} Ask={data.get('ask')} Last={data.get('last')}"
        )

    # Register handler
    await suite.on(EventType.QUOTE_UPDATE, on_quote)

    # Wait for quotes
    logger.info("Waiting for quotes...")
    await asyncio.sleep(10)

    # Cleanup
    await suite.disconnect()

    logger.info(f"Test complete. Received {quote_count} quotes.")


if __name__ == "__main__":
    asyncio.run(test_quotes())
