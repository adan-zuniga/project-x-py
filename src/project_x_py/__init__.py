"""
ProjectX Python SDK for Trading Applications

A comprehensive Python SDK for the ProjectX Trading Platform Gateway API, providing developers
with tools to build sophisticated trading strategies and applications. This library offers
comprehensive access to:

- Market data retrieval and real-time streaming
- Account management and authentication
- Order placement, modification, and cancellation
- Position management and portfolio analytics
- Trade history and execution analysis
- Advanced technical indicators and market analysis
- Level 2 orderbook depth and market microstructure

**Important**: This is a development toolkit/SDK, not a trading strategy itself.
It provides the infrastructure to help developers create their own trading applications
that integrate with the ProjectX platform.

Author: TexasCoding
Date: January 2025
"""

from typing import Any, Optional

__version__ = "2.0.0"
__author__ = "TexasCoding"

# Core client classes - renamed from Async* to standard names
from .async_client import AsyncProjectX as ProjectX
from .async_order_manager import AsyncOrderManager as OrderManager
from .async_orderbook import (
    AsyncOrderBook as OrderBook,
    create_async_orderbook as create_orderbook,
)
from .async_position_manager import AsyncPositionManager as PositionManager
from .async_realtime import AsyncProjectXRealtimeClient as ProjectXRealtimeClient
from .async_realtime_data_manager import AsyncRealtimeDataManager as RealtimeDataManager

# Configuration management
from .config import (
    ConfigManager,
    create_custom_config,
    load_default_config,
    load_topstepx_config,
)

# Exceptions
from .exceptions import (
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
from .indicators import (
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
from .models import (
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

# Utility functions
from .utils import (
    RateLimiter,
    # Market analysis utilities
    analyze_bid_ask_spread,
    # Risk and portfolio analysis
    calculate_max_drawdown,
    calculate_portfolio_metrics,
    calculate_sharpe_ratio,
    # Decimal and numeric utilities
    decimal_to_str,
    # Time and date utilities
    format_duration,
    format_timestamp,
    get_env_var,
    round_to_tick_size,
    setup_logging,
    # Trade execution utilities
    validate_price_precision,
)

__all__ = [
    # Version info
    "__version__",
    "__author__",
    # Core classes (now async-only but with original names)
    "ProjectX",
    "OrderManager",
    "PositionManager",
    "RealtimeDataManager",
    "ProjectXRealtimeClient",
    "OrderBook",
    "create_orderbook",
    # Configuration
    "ProjectXConfig",
    "ConfigManager",
    "load_default_config",
    "load_topstepx_config",
    "create_custom_config",
    # Data Models
    "Account",
    "Instrument",
    "Position",
    "Order",
    "Trade",
    "OrderPlaceResponse",
    "BracketOrderResponse",
    # Exceptions
    "ProjectXError",
    "ProjectXAuthenticationError",
    "ProjectXConnectionError",
    "ProjectXRateLimitError",
    "ProjectXServerError",
    "ProjectXDataError",
    "ProjectXOrderError",
    "ProjectXPositionError",
    "ProjectXInstrumentError",
    # Utilities
    "setup_logging",
    "get_env_var",
    "round_to_tick_size",
    "decimal_to_str",
    "validate_price_precision",
    "calculate_portfolio_metrics",
    "calculate_sharpe_ratio",
    "calculate_max_drawdown",
    "analyze_bid_ask_spread",
    "format_timestamp",
    "format_duration",
    "RateLimiter",
    # Technical Analysis
    "calculate_sma",
    "calculate_ema",
    "calculate_rsi",
    "calculate_macd",
    "calculate_bollinger_bands",
    "calculate_atr",
    "calculate_adx",
    "calculate_stochastic",
    "calculate_williams_r",
    "calculate_commodity_channel_index",
    "calculate_obv",
    "calculate_vwap",
    # Factory functions (async-only)
    "create_trading_suite",
    "create_order_manager",
    "create_position_manager",
]


# Factory functions - Updated to be async-only
async def create_trading_suite(
    instrument: str,
    project_x: ProjectX,
    jwt_token: str | None = None,
    account_id: str | None = None,
    timeframes: list[str] | None = None,
    enable_orderbook: bool = True,
    config: ProjectXConfig | None = None,
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

    Returns:
        Dictionary containing initialized trading components:
        - realtime_client: Real-time WebSocket client
        - data_manager: Real-time data manager
        - order_manager: Order management system
        - position_manager: Position tracking system
        - orderbook: Level 2 order book (if enabled)

    Example:
        async with ProjectX.from_env() as client:
            await client.authenticate()

            suite = await create_trading_suite(
                instrument="MGC",
                project_x=client,
                timeframes=["1min", "5min", "15min"]
            )

            # Connect real-time services
            await suite["realtime_client"].connect()
            await suite["data_manager"].initialize()
    """
    # Use provided config or get from project_x client
    if config is None:
        config = project_x.config

    # Get JWT token if not provided
    if jwt_token is None:
        jwt_token = project_x.session_token

    # Get account ID if not provided
    if account_id is None and project_x.account_info:
        account_id = str(project_x.account_info.id)

    # Default timeframes
    if timeframes is None:
        timeframes = ["5min"]

    # Create real-time client
    realtime_client = ProjectXRealtimeClient(
        jwt_token=jwt_token,
        account_id=account_id or "",
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
    order_manager = OrderManager(
        project_x=project_x,
        realtime_client=realtime_client,
    )

    # Create position manager with order manager integration
    position_manager = PositionManager(
        project_x=project_x,
        realtime_client=realtime_client,
        order_manager=order_manager,
    )

    # Build suite dictionary
    suite = {
        "realtime_client": realtime_client,
        "data_manager": data_manager,
        "order_manager": order_manager,
        "position_manager": position_manager,
    }

    if orderbook:
        suite["orderbook"] = orderbook

    return suite


def create_order_manager(
    project_x: ProjectX,
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
    return OrderManager(
        project_x=project_x,
        realtime_client=realtime_client,
    )


def create_position_manager(
    project_x: ProjectX,
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
    return PositionManager(
        project_x=project_x,
        realtime_client=realtime_client,
        order_manager=order_manager,
    )
