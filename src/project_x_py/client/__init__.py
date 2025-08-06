"""V3
Async ProjectX Python SDK - Core Async Client Module

Author: @TexasCoding
Date: 2025-08-02

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
from project_x_py.utils.async_rate_limiter import RateLimiter


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
        >>> # V3: Basic async SDK usage with environment variables (recommended)
        >>> import asyncio
        >>> from project_x_py import ProjectX
        >>>
        >>> async def main():
        >>> # V3: Create and authenticate client with context manager
        >>>     async with ProjectX.from_env() as client:
        >>>         await client.authenticate()
        >>>
        >>> # V3: Get account info with typed models
        >>>         account = client.get_account_info()
        >>>         print(f"Account: {account.name}")
        >>>         print(f"ID: {account.id}")
        >>>         print(f"Balance: ${account.balance:,.2f}")
        >>>
        >>> # V3: Search for instruments with smart contract selection
        >>>         instruments = await client.search_instruments("gold")
        >>>         gold = instruments[0] if instruments else None
        >>>         if gold:
        >>>             print(f"Found: {gold.name} ({gold.symbol})")
        >>>             print(f"Contract ID: {gold.id}")
        >>>
        >>> # V3: Get historical data concurrently (returns Polars DataFrames)
        >>>         tasks = [
        >>>             client.get_bars("MGC", days=5, interval=5),  # 5-min bars
        >>>             client.get_bars("MNQ", days=1, interval=1),  # 1-min bars
        >>>         ]
        >>>         gold_data, nasdaq_data = await asyncio.gather(*tasks)
        >>>
        >>>         print(f"Gold bars: {len(gold_data)} (Polars DataFrame)")
        >>>         print(f"Nasdaq bars: {len(nasdaq_data)} (Polars DataFrame)")
        >>>         print(f"Columns: {gold_data.columns}")
        >>>
        >>> asyncio.run(main())

    For advanced async trading applications, combine with specialized managers:
        >>> # V3: Advanced trading with specialized managers
        >>> from project_x_py import (
        ...     ProjectX,
        ...     create_realtime_client,
        ...     create_order_manager,
        ...     create_position_manager,
        ...     create_realtime_data_manager,
        ... )
        >>>
        >>> async def trading_app():
        >>>     async with ProjectX.from_env() as client:
        >>>         await client.authenticate()
        >>>
        >>> # V3: Create specialized async managers with dependency injection
        >>>         jwt_token = client.get_session_token()
        >>>         account_id = str(client.get_account_info().id)
        >>>
        >>> # V3: Real-time WebSocket client for all managers
        >>>         realtime_client = await create_realtime_client(jwt_token, account_id)
        >>> # V3: Create managers with shared realtime client
        >>>         order_manager = create_order_manager(client, realtime_client)
        >>>         position_manager = create_position_manager(client, realtime_client)
        >>>         data_manager = create_realtime_data_manager(
        ...             "MNQ", client, realtime_client, timeframes=["1min", "5min"]
        ...         )
        >>>
        >>> # V3: Connect and start real-time trading
        >>>         await realtime_client.connect()
        >>>         await data_manager.start_realtime_feed()
        >>> # V3: Now ready for real-time trading with all managers
        >>> # ... your trading logic here ...
    """


__all__ = ["ProjectX", "ProjectXBase", "RateLimiter"]
