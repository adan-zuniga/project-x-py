"""
ProjectX Python SDK for Trading Applications

Author: @TexasCoding
Date: 2025-08-02

Overview:
    A comprehensive Python SDK for the ProjectX Trading Platform Gateway API, providing
    developers with tools to build sophisticated trading strategies and applications.
    This library offers comprehensive access to real-time market data, order management,
    position tracking, and advanced analytics for algorithmic trading.

Key Features:
    - Real-time market data streaming and historical data access
    - Comprehensive order management (market, limit, stop, bracket orders)
    - Position tracking and portfolio analytics
    - Level 2 orderbook depth and market microstructure analysis
    - Advanced technical indicators and pattern recognition
    - Risk management and position sizing tools
    - Multi-timeframe data management and analysis
    - WebSocket-based real-time updates and event handling

Core Components:
    - ProjectX: Main client for API interactions and authentication
    - OrderManager: Order placement, modification, and tracking
    - PositionManager: Position monitoring, analytics, and risk management
    - OrderBook: Level 2 market depth analysis and order flow
    - RealtimeDataManager: Multi-timeframe real-time data processing
    - ProjectXRealtimeClient: WebSocket-based real-time connections

Trading Capabilities:
    - Market data retrieval and real-time streaming
    - Account management and authentication
    - Order placement, modification, and cancellation
    - Position management and portfolio analytics
    - Trade history and execution analysis
    - Advanced technical indicators and market analysis
    - Level 2 orderbook depth and market microstructure
    - Risk management and position sizing

Example Usage:
    ```python
    from project_x_py import ProjectX, OrderManager, PositionManager

    # Basic client setup
    async with ProjectX.from_env() as client:
        await client.authenticate()

        # Get market data
        bars = await client.get_bars("MGC", days=5)
        instrument = await client.get_instrument("MGC")

        # Place orders
        order_manager = OrderManager(client)
        response = await order_manager.place_market_order(
            contract_id=instrument.id,
            side=0,  # Buy
            size=1,
        )

        # Track positions
        position_manager = PositionManager(client)
        positions = await position_manager.get_all_positions()

        # Create complete trading suite
        suite = await create_trading_suite(
            instrument="MGC", project_x=client, timeframes=["1min", "5min", "15min"]
        )
    ```

Architecture Benefits:
    - Async-first design for high-performance trading applications
    - Comprehensive error handling and retry logic
    - Rate limiting and connection management
    - Real-time data processing with WebSocket integration
    - Modular design for flexible trading system development
    - Type-safe operations with comprehensive validation

**Important**: This is a development toolkit/SDK, not a trading strategy itself.
It provides the infrastructure to help developers create their own trading applications
that integrate with the ProjectX platform.

Version: 2.0.5
Author: TexasCoding

See Also:
    - `client`: Main client for API interactions
    - `order_manager`: Order management and tracking
    - `position_manager`: Position monitoring and analytics
    - `orderbook`: Level 2 market depth analysis
    - `realtime_data_manager`: Real-time data processing
    - `indicators`: Technical analysis and indicators
    - `utils`: Utility functions and calculations
"""

from typing import Any

from project_x_py.client.base import ProjectXBase

__version__ = "2.0.8"
__author__ = "TexasCoding"

# Core client classes - renamed from Async* to standard names
from project_x_py.client import ProjectX

# Configuration management
from project_x_py.config import (
    ConfigManager,
    create_custom_config,
    load_default_config,
    load_topstepx_config,
)

# Exceptions
from project_x_py.exceptions import (
    ProjectXAuthenticationError,
    ProjectXConnectionError,
    ProjectXDataError,
    ProjectXError,
    ProjectXInstrumentError,
    ProjectXOrderError,
    ProjectXPositionError,
    ProjectXRateLimitError,
    ProjectXServerError,
)

# Technical Analysis - Import from indicators module for backward compatibility
from project_x_py.indicators import (
    calculate_adx,
    calculate_atr,
    calculate_bollinger_bands,
    calculate_commodity_channel_index,
    calculate_ema,
    calculate_macd,
    calculate_obv,
    calculate_rsi,
    # TA-Lib style functions
    calculate_sma,
    calculate_stochastic,
    calculate_vwap,
    calculate_williams_r,
)

# Data models
from project_x_py.models import (
    Account,
    BracketOrderResponse,
    # Trading entities
    Instrument,
    Order,
    OrderPlaceResponse,
    Position,
    # Configuration
    ProjectXConfig,
    Trade,
)
from project_x_py.order_manager import OrderManager
from project_x_py.orderbook import (
    OrderBook,
    create_orderbook,
)
from project_x_py.position_manager import PositionManager
from project_x_py.realtime import ProjectXRealtimeClient as ProjectXRealtimeClient
from project_x_py.realtime_data_manager import RealtimeDataManager

# Utility functions
from project_x_py.utils import (
    RateLimiter,
    # Risk and portfolio analysis
    calculate_max_drawdown,
    calculate_portfolio_metrics,
    calculate_sharpe_ratio,
    # Utilities
    get_env_var,
    round_to_tick_size,
    setup_logging,
)

__all__ = [
    # Data Models
    "Account",
    "BracketOrderResponse",
    # Configuration
    "ConfigManager",
    "Instrument",
    "Order",
    # Core classes (now async-only but with original names)
    "OrderBook",
    "OrderManager",
    "OrderPlaceResponse",
    "Position",
    "PositionManager",
    "ProjectX",
    # Exceptions
    "ProjectXAuthenticationError",
    "ProjectXConfig",
    "ProjectXConnectionError",
    "ProjectXDataError",
    "ProjectXError",
    "ProjectXInstrumentError",
    "ProjectXOrderError",
    "ProjectXPositionError",
    "ProjectXRateLimitError",
    "ProjectXRealtimeClient",
    "ProjectXServerError",
    # Utilities
    "RateLimiter",
    "RealtimeDataManager",
    "Trade",
    # Version info
    "__author__",
    "__version__",
    # Technical Analysis
    "calculate_adx",
    "calculate_atr",
    "calculate_bollinger_bands",
    "calculate_commodity_channel_index",
    "calculate_ema",
    "calculate_macd",
    "calculate_max_drawdown",
    "calculate_obv",
    "calculate_portfolio_metrics",
    "calculate_rsi",
    "calculate_sharpe_ratio",
    "calculate_sma",
    "calculate_stochastic",
    "calculate_vwap",
    "calculate_williams_r",
    "create_custom_config",
    # Factory functions (async-only)
    "create_data_manager",
    "create_initialized_trading_suite",
    "create_order_manager",
    "create_orderbook",
    "create_position_manager",
    "create_realtime_client",
    "create_trading_suite",
    "get_env_var",
    "load_default_config",
    "load_topstepx_config",
    "round_to_tick_size",
    "setup_logging",
]


# Factory functions - Updated to be async-only
async def create_trading_suite(
    instrument: str,
    project_x: ProjectXBase,
    jwt_token: str | None = None,
    account_id: str | None = None,
    timeframes: list[str] | None = None,
    enable_orderbook: bool = True,
    config: ProjectXConfig | None = None,
    auto_connect: bool = True,
    auto_subscribe: bool = True,
    initial_days: int = 5,
) -> dict[str, Any]:
    """
    Create a complete async trading suite with all components initialized.

    This is the recommended way to set up a trading environment as it ensures
    all components are properly configured and connected.

    Args:
        instrument: Trading instrument symbol (e.g., "MGC", "MNQ")
        project_x: Authenticated ProjectX client instance
        jwt_token: JWT token for real-time connections (optional, will get from client)
        account_id: Account ID for trading (optional, will get from client)
        timeframes: List of timeframes for real-time data (default: ["5min"])
        enable_orderbook: Whether to include OrderBook in suite
        config: Optional custom configuration
        auto_connect: Automatically connect realtime client and subscribe to user updates (default: True)
        auto_subscribe: Automatically subscribe to market data and start realtime feed (default: True)
        initial_days: Days of historical data to load when auto_subscribe is True (default: 5)

    Returns:
        Dictionary containing initialized trading components:
        - realtime_client: Real-time WebSocket client
        - data_manager: Real-time data manager
        - order_manager: Order management system
        - position_manager: Position tracking system
        - orderbook: Level 2 order book (if enabled)
        - instrument_info: Instrument contract information (if auto_subscribe is True)

    Example:
        # Fully automated setup (recommended)
        async with ProjectX.from_env() as client:
            await client.authenticate()

            suite = await create_trading_suite(
                instrument="MGC",
                project_x=client,
                timeframes=["1min", "5min", "15min"]
            )
            # Ready to use - all connections and subscriptions are active!

        # Manual setup (for more control)
        suite = await create_trading_suite(
            instrument="MGC",
            project_x=client,
            auto_connect=False,
            auto_subscribe=False
        )
        # Manually connect and subscribe as needed
    """
    # Use provided config or get from project_x client
    if config is None:
        config = project_x.config

    # Get JWT token if not provided
    if jwt_token is None:
        jwt_token = project_x.session_token
        if not jwt_token:
            raise ValueError("JWT token is required but not available from client")

    # Get account ID if not provided
    if account_id is None and project_x.account_info:
        account_id = str(project_x.account_info.id)

    if not account_id:
        raise ValueError("Account ID is required but not available")

    # Default timeframes
    if timeframes is None:
        timeframes = ["5min"]

    # Create real-time client
    realtime_client = ProjectXRealtimeClient(
        jwt_token=jwt_token,
        account_id=account_id,
        config=config,
    )

    # Create data manager
    data_manager = RealtimeDataManager(
        instrument=instrument,
        project_x=project_x,
        realtime_client=realtime_client,
        timeframes=timeframes,
    )

    # Create orderbook if enabled
    orderbook = None
    if enable_orderbook:
        orderbook = OrderBook(
            instrument=instrument,
            timezone_str=config.timezone,
            project_x=project_x,
        )

    # Create order manager
    order_manager = OrderManager(project_x)

    # Create position manager
    position_manager = PositionManager(project_x)

    # Build suite dictionary
    suite = {
        "realtime_client": realtime_client,
        "data_manager": data_manager,
        "order_manager": order_manager,
        "position_manager": position_manager,
    }

    if orderbook:
        suite["orderbook"] = orderbook

    # Auto-connect if requested
    if auto_connect:
        await realtime_client.connect()
        await realtime_client.subscribe_user_updates()

    # Auto-subscribe and initialize if requested
    if auto_subscribe:
        # Search for instrument
        instruments = await project_x.search_instruments(instrument)
        if not instruments:
            raise ValueError(f"Instrument {instrument} not found")

        instrument_info: Instrument = instruments[0]
        suite["instrument_info"] = instrument_info

        # Initialize data manager with historical data
        await data_manager.initialize(initial_days=initial_days)

        # Subscribe to market data
        await realtime_client.subscribe_market_data([instrument_info.id])

        # Start realtime feed
        await data_manager.start_realtime_feed()

        # Initialize orderbook if enabled
        if orderbook:
            await orderbook.initialize(
                realtime_client=realtime_client,
                subscribe_to_depth=True,
                subscribe_to_quotes=True,
            )

    return suite


async def create_initialized_trading_suite(
    instrument: str,
    project_x: ProjectXBase,
    timeframes: list[str] | None = None,
    enable_orderbook: bool = True,
    initial_days: int = 5,
) -> dict[str, Any]:
    """
    Create and fully initialize a trading suite with all connections active.

    This is a convenience wrapper around create_trading_suite that always
    auto-connects and auto-subscribes, perfect for most trading strategies.

    Args:
        instrument: Trading instrument symbol (e.g., "MGC", "MNQ")
        project_x: Authenticated ProjectX client instance
        timeframes: List of timeframes for real-time data (default: ["5min"])
        enable_orderbook: Whether to include OrderBook in suite
        initial_days: Days of historical data to load (default: 5)

    Returns:
        Fully initialized trading suite ready for use

    Example:
        async with ProjectX.from_env() as client:
            await client.authenticate()

            # One line to get a fully ready trading suite!
            suite = await create_initialized_trading_suite("MNQ", client)

            # Everything is connected and subscribed - start trading!
            strategy = MyStrategy(suite)
            await strategy.run()
    """
    return await create_trading_suite(
        instrument=instrument,
        project_x=project_x,
        timeframes=timeframes,
        enable_orderbook=enable_orderbook,
        auto_connect=True,
        auto_subscribe=True,
        initial_days=initial_days,
    )


def create_order_manager(
    project_x: ProjectXBase,
    realtime_client: ProjectXRealtimeClient | None = None,
) -> OrderManager:
    """
    Create an async order manager instance.

    Args:
        project_x: Authenticated ProjectX client
        realtime_client: Optional real-time client for order updates

    Returns:
        Configured OrderManager instance

    Example:
        order_manager = create_order_manager(project_x, realtime_client)
        response = await order_manager.place_market_order(
            contract_id=instrument.id,
            side=0,  # Buy
            size=1
        )
    """
    order_manager = OrderManager(project_x)
    if realtime_client:
        # This would need to be done in an async context
        # For now, just store the client
        order_manager.realtime_client = realtime_client
    return order_manager


def create_position_manager(
    project_x: ProjectXBase,
    realtime_client: ProjectXRealtimeClient | None = None,
    order_manager: OrderManager | None = None,
) -> PositionManager:
    """
    Create an async position manager instance.

    Args:
        project_x: Authenticated ProjectX client
        realtime_client: Optional real-time client for position updates
        order_manager: Optional order manager for integrated order cleanup

    Returns:
        Configured PositionManager instance

    Example:
        position_manager = create_position_manager(
            project_x,
            realtime_client,
            order_manager
        )
        positions = await position_manager.get_all_positions()
    """
    position_manager = PositionManager(project_x)
    if realtime_client:
        # This would need to be done in an async context
        # For now, just store the client
        position_manager.realtime_client = realtime_client
    if order_manager:
        position_manager.order_manager = order_manager
    return position_manager


def create_realtime_client(
    jwt_token: str,
    account_id: str,
    config: ProjectXConfig | None = None,
) -> ProjectXRealtimeClient:
    """
    Create a real-time WebSocket client instance.

    Args:
        jwt_token: JWT authentication token
        account_id: Account ID for real-time subscriptions
        config: Optional configuration (uses defaults if not provided)

    Returns:
        Configured ProjectXRealtimeClient instance

    Example:
        realtime_client = create_realtime_client(
            jwt_token=client.session_token,
            account_id=str(client.account_info.id)
        )
        await realtime_client.connect()
        await realtime_client.subscribe_user_updates()
    """
    return ProjectXRealtimeClient(
        jwt_token=jwt_token,
        account_id=account_id,
        config=config,
    )


def create_data_manager(
    instrument: str,
    project_x: ProjectXBase,
    realtime_client: ProjectXRealtimeClient,
    timeframes: list[str] | None = None,
) -> RealtimeDataManager:
    """
    Create a real-time data manager instance.

    Args:
        instrument: Trading instrument symbol (e.g., "MGC", "MNQ")
        project_x: Authenticated ProjectX client
        realtime_client: Real-time client for WebSocket data
        timeframes: List of timeframes to track (default: ["5min"])

    Returns:
        Configured RealtimeDataManager instance

    Example:
        data_manager = create_data_manager(
            instrument="MGC",
            project_x=client,
            realtime_client=realtime_client,
            timeframes=["1min", "5min", "15min"]
        )
        await data_manager.initialize()
        await data_manager.start_realtime_feed()
    """
    if timeframes is None:
        timeframes = ["5min"]

    return RealtimeDataManager(
        instrument=instrument,
        project_x=project_x,
        realtime_client=realtime_client,
        timeframes=timeframes,
    )
