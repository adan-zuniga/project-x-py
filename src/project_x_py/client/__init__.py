"""
Async ProjectX Python SDK - Core Async Client Module

This module contains the async version of the ProjectX client class for the ProjectX Python SDK.
It provides a comprehensive asynchronous interface for interacting with the ProjectX Trading Platform
Gateway API, enabling developers to build high-performance trading applications.

The async client handles authentication, account management, market data retrieval, and basic
trading operations using async/await patterns for improved performance and concurrency.

Key Features:
- Async multi-account authentication and management
- Concurrent API operations with httpx
- Async historical market data retrieval with caching
- Non-blocking position tracking and trade history
- Async error handling and connection management
- HTTP/2 support for improved performance

For advanced trading operations, use the specialized managers:
- OrderManager: Complete order lifecycle management
- PositionManager: Portfolio analytics and risk management
- ProjectXRealtimeDataManager: Real-time multi-timeframe OHLCV data
- OrderBook: Level 2 market depth and microstructure analysis
"""

from project_x_py.client.base import ProjectXBase
from project_x_py.client.rate_limiter import RateLimiter


class ProjectX(ProjectXBase):
    """
    Async core ProjectX client for the ProjectX Python SDK.

    This class provides the async foundation for building trading applications by offering
    comprehensive asynchronous access to the ProjectX Trading Platform Gateway API. It handles
    core functionality including:

    - Multi-account authentication and JWT token management
    - Async instrument search and contract selection with caching
    - High-performance historical market data retrieval
    - Non-blocking position and trade history access
    - Automatic retry logic and connection pooling
    - Rate limiting and error handling

    The async client is designed for high-performance applications requiring concurrent
    operations, real-time data processing, or integration with async frameworks like
    FastAPI, aiohttp, or Discord.py.

    For order management and real-time data, use the specialized async managers from the
    project_x_py.async_api module which integrate seamlessly with this client.

    Example:
        >>> # Basic async SDK usage with environment variables (recommended)
        >>> import asyncio
        >>> from project_x_py import ProjectX
        >>>
        >>> async def main():
        >>> # Create and authenticate client
        >>>     async with ProjectX.from_env() as client:
        >>>         await client.authenticate()
        >>>
        >>> # Get account info
        >>>         print(f"Account: {client.account_info.name}")
        >>>         print(f"Balance: ${client.account_info.balance:,.2f}")
        >>>
        >>> # Search for gold futures
        >>>         instruments = await client.search_instruments("gold")
        >>>         gold = instruments[0]
        >>>         print(f"Found: {gold.name} ({gold.symbol})")
        >>>
        >>> # Get historical data concurrently
        >>>         tasks = [
        >>>             client.get_bars("MGC", days=5, interval=5),  # 5-min bars
        >>>             client.get_bars("MNQ", days=1, interval=1),  # 1-min bars
        >>>         ]
        >>>         gold_data, nasdaq_data = await asyncio.gather(*tasks)
        >>>
        >>>         print(f"Gold bars: {len(gold_data)}")
        >>>         print(f"Nasdaq bars: {len(nasdaq_data)}")
        >>>
        >>> asyncio.run(main())

    For advanced async trading applications, combine with specialized managers:
        >>> from project_x_py import create_order_manager, create_realtime_client
        >>>
        >>> async def trading_app():
        >>>     async with ProjectX.from_env() as client:
        >>>         await client.authenticate()
        >>>
        >>> # Create specialized async managers
        >>>         jwt_token = client.get_session_token()
        >>>         account_id = client.get_account_info().id
        >>>
        >>>         realtime_client = create_realtime_client(jwt_token, str(account_id))
        >>>         order_manager = create_order_manager(client, realtime_client)
        >>>
        >>> # Now ready for real-time trading
        >>>         await realtime_client.connect()
        >>> # ... trading logic ...
    """


__all__ = ["ProjectX", "ProjectXBase", "RateLimiter"]
