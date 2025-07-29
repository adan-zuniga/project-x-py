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

__version__ = "1.1.3"
__author__ = "TexasCoding"

# Core client classes
from .client import ProjectX

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
from .order_manager import OrderManager
from .orderbook import OrderBook
from .position_manager import PositionManager
from .realtime import ProjectXRealtimeClient
from .realtime_data_manager import ProjectXRealtimeDataManager

# Utility functions
from .utils import (
    RateLimiter,
    # Market analysis utilities
    analyze_bid_ask_spread,
    # Risk and portfolio analysis
    calculate_correlation_matrix,
    calculate_max_drawdown,
    calculate_portfolio_metrics,
    calculate_position_sizing,
    calculate_position_value,
    calculate_risk_reward_ratio,
    calculate_sharpe_ratio,
    calculate_tick_value,
    calculate_volatility_metrics,
    calculate_volume_profile,
    convert_timeframe_to_seconds,
    create_data_snapshot,
    detect_candlestick_patterns,
    detect_chart_patterns,
    extract_symbol_from_contract_id,
    format_price,
    format_volume,
    get_env_var,
    get_market_session_info,
    get_polars_last_value as _get_polars_last_value,
    get_polars_rows as _get_polars_rows,
    is_market_hours,
    round_to_tick_size,
    setup_logging,
    validate_contract_id,
)

# Public API - these are the main classes users should import
__all__ = [
    "Account",
    "BracketOrderResponse",
    "ConfigManager",
    "Instrument",
    "Order",
    "OrderBook",
    "OrderManager",
    "OrderPlaceResponse",
    "Position",
    "PositionManager",
    "ProjectX",
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
    "ProjectXRealtimeDataManager",
    "ProjectXServerError",
    "RateLimiter",
    "Trade",
    # Enhanced technical analysis and trading utilities
    "analyze_bid_ask_spread",
    "calculate_adx",
    "calculate_atr",
    "calculate_bollinger_bands",
    "calculate_commodity_channel_index",
    "calculate_correlation_matrix",
    "calculate_ema",
    "calculate_macd",
    "calculate_max_drawdown",
    "calculate_portfolio_metrics",
    "calculate_position_sizing",
    "calculate_position_value",
    "calculate_risk_reward_ratio",
    "calculate_rsi",
    "calculate_sharpe_ratio",
    "calculate_sma",
    "calculate_stochastic",
    "calculate_tick_value",
    "calculate_volatility_metrics",
    "calculate_volume_profile",
    "calculate_williams_r",
    "convert_timeframe_to_seconds",
    "create_custom_config",
    "create_data_manager",
    "create_data_snapshot",
    "create_order_manager",
    "create_orderbook",
    "create_position_manager",
    "create_realtime_client",
    "create_trading_suite",
    "detect_candlestick_patterns",
    "detect_chart_patterns",
    "extract_symbol_from_contract_id",
    "format_price",
    "format_volume",
    "get_env_var",
    "get_market_session_info",
    "is_market_hours",
    "load_default_config",
    "load_topstepx_config",
    "round_to_tick_size",
    "setup_logging",
    "validate_contract_id",
]


def get_version() -> str:
    """Get the current version of the ProjectX package."""
    return __version__


def quick_start() -> dict:
    """
    Get quick start information for the ProjectX Python SDK.

    Returns:
        Dict with setup instructions and examples for building trading applications
    """
    return {
        "version": __version__,
        "setup_instructions": [
            "1. Set environment variables:",
            "   export PROJECT_X_USERNAME='your_username'",
            "   export PROJECT_X_API_KEY='your_api_key'",
            "   export PROJECT_X_ACCOUNT_ID='your_account_id'",
            "",
            "2. Basic SDK usage:",
            "   from project_x_py import ProjectX",
            "   client = ProjectX.from_env()",
            "   instruments = client.search_instruments('MGC')",
            "   data = client.get_data('MGC', days=5)",
        ],
        "examples": {
            "basic_client": "client = ProjectX.from_env()",
            "get_instruments": "instruments = client.search_instruments('MGC')",
            "get_data": "data = client.get_data('MGC', days=5, interval=15)",
            "place_order": "response = client.place_market_order('CONTRACT_ID', 0, 1)",
            "get_positions": "positions = client.search_open_positions()",
            "create_trading_suite": "suite = create_trading_suite('MGC', client, jwt_token, account_id)",
        },
        "documentation": "https://github.com/TexasCoding/project-x-py",
        "support": "Create an issue at https://github.com/TexasCoding/project-x-py/issues",
    }


def check_setup() -> dict:
    """
    Check if the ProjectX Python SDK is properly configured for development.

    Validates environment variables, configuration files, and dependencies
    needed to build trading applications with the SDK.

    Returns:
        Dict with setup status and recommendations for SDK configuration
    """
    try:
        from .config import check_environment

        env_status = check_environment()

        status = {
            "environment_configured": env_status["auth_configured"],
            "config_file_exists": env_status["config_file_exists"],
            "issues": [],
            "recommendations": [],
        }

        if not env_status["auth_configured"]:
            status["issues"].append("Missing required environment variables")
            status["recommendations"].extend(
                [
                    "Set PROJECT_X_API_KEY environment variable",
                    "Set PROJECT_X_USERNAME environment variable",
                ]
            )

        if env_status["missing_required"]:
            status["missing_variables"] = env_status["missing_required"]

        if env_status["environment_overrides"]:
            status["environment_overrides"] = env_status["environment_overrides"]

        if not status["issues"]:
            status["status"] = "Ready to use"
        else:
            status["status"] = "Setup required"

        return status

    except Exception as e:
        return {
            "status": "Error checking setup",
            "error": str(e),
            "recommendations": [
                "Ensure all dependencies are installed",
                "Check package installation",
            ],
        }


def diagnose_issues() -> dict:
    """
    Diagnose common SDK setup issues and provide troubleshooting recommendations.

    Performs comprehensive checks of dependencies, network connectivity, configuration,
    and environment setup to help developers resolve common issues when building
    trading applications with the ProjectX Python SDK.

    Returns:
        Dict with diagnostics results and specific fixes for identified issues
    """
    diagnostics = check_setup()
    diagnostics["issues"] = []
    diagnostics["recommendations"] = []

    # Check dependencies
    try:
        import polars
        import pytz
        import requests
    except ImportError as e:
        diagnostics["issues"].append(f"Missing dependency: {e.name}")
        diagnostics["recommendations"].append(f"Install with: pip install {e.name}")

    # Check network connectivity
    try:
        requests.get("https://www.google.com", timeout=5)
    except requests.RequestException:
        diagnostics["issues"].append("Network connectivity issue")
        diagnostics["recommendations"].append("Check internet connection")

    # Check config validity
    try:
        config = load_default_config()
        ConfigManager().validate_config(config)
    except ValueError as e:
        diagnostics["issues"].append(f"Invalid configuration: {e!s}")
        diagnostics["recommendations"].append("Fix config file or env vars")

    if not diagnostics["issues"]:
        diagnostics["status"] = "All systems operational"
    else:
        diagnostics["status"] = "Issues detected"

    return diagnostics


# Package-level convenience functions
def create_client(
    username: str | None = None,
    api_key: str | None = None,
    config: ProjectXConfig | None = None,
    account_name: str | None = None,
) -> ProjectX:
    """
    Create a ProjectX client with flexible initialization options.

    This convenience function provides multiple ways to initialize a ProjectX client:
    - Using environment variables (recommended for security)
    - Using explicit credentials
    - Using custom configuration
    - Selecting specific account by name

    Args:
        username: ProjectX username (uses PROJECT_X_USERNAME env var if None)
        api_key: ProjectX API key (uses PROJECT_X_API_KEY env var if None)
        config: Configuration object with endpoints and settings (uses defaults if None)
        account_name: Optional account name to select specific account

    Returns:
        ProjectX: Configured client instance ready for API operations

    Example:
        >>> # Using environment variables (recommended)
        >>> client = create_client()
        >>> # Using explicit credentials
        >>> client = create_client("username", "api_key")
        >>> # Using specific account
        >>> client = create_client(account_name="Main Trading Account")
        >>> # Using custom configuration
        >>> config = create_custom_config(api_url="https://custom.api.com")
        >>> client = create_client(config=config)
    """
    if username is None or api_key is None:
        return ProjectX.from_env(config=config, account_name=account_name)
    else:
        return ProjectX(
            username=username, api_key=api_key, config=config, account_name=account_name
        )


def create_realtime_client(
    jwt_token: str, account_id: str, config: ProjectXConfig | None = None
) -> ProjectXRealtimeClient:
    """
    Create a ProjectX real-time client for WebSocket connections.

    This function creates a real-time client that connects to ProjectX WebSocket hubs
    for live market data, order updates, and position changes. The client handles
    both user-specific data (orders, positions, accounts) and market data (quotes, trades, depth).

    Args:
        jwt_token: JWT authentication token from ProjectX client session
        account_id: Account ID for user-specific subscriptions
        config: Configuration object with hub URLs (uses default TopStepX if None)

    Returns:
        ProjectXRealtimeClient: Configured real-time client ready for WebSocket connections

    Example:
        >>> # Get JWT token from main client
        >>> client = ProjectX.from_env()
        >>> jwt_token = client.get_session_token()
        >>> account = client.get_account_info()
        >>> # Create real-time client
        >>> realtime_client = create_realtime_client(jwt_token, account.id)
        >>> # Connect and subscribe
        >>> realtime_client.connect()
        >>> realtime_client.subscribe_user_updates()
        >>> realtime_client.subscribe_market_data("MGC")
    """
    if config is None:
        config = load_default_config()

    return ProjectXRealtimeClient(
        jwt_token=jwt_token,
        account_id=account_id,
        user_hub_url=config.user_hub_url,
        market_hub_url=config.market_hub_url,
    )


def create_data_manager(
    instrument: str,
    project_x: ProjectX,
    realtime_client: ProjectXRealtimeClient,
    timeframes: list[str] | None = None,
    config: ProjectXConfig | None = None,
) -> ProjectXRealtimeDataManager:
    """
    Create a ProjectX real-time OHLCV data manager with dependency injection.

    This function creates a data manager that combines historical OHLCV data from the API
    with real-time updates via WebSocket to maintain live, multi-timeframe candlestick data.
    Perfect for building trading algorithms that need both historical context and real-time updates.

    Args:
        instrument: Trading instrument symbol (e.g., "MGC", "MNQ", "ES")
        project_x: ProjectX client instance for historical data and API access
        realtime_client: ProjectXRealtimeClient instance for real-time market data feeds
        timeframes: List of timeframes to track (default: ["5min"]).
                   Common: ["5sec", "1min", "5min", "15min", "1hour", "1day"]
        config: Configuration object with timezone settings (uses defaults if None)

    Returns:
        ProjectXRealtimeDataManager: Configured data manager ready for initialization

    Example:
        >>> # Setup clients
        >>> client = ProjectX.from_env()
        >>> realtime_client = create_realtime_client(jwt_token, account_id)
        >>> # Create data manager for multiple timeframes
        >>> data_manager = create_data_manager(
        ...     instrument="MGC",
        ...     project_x=client,
        ...     realtime_client=realtime_client,
        ...     timeframes=["5sec", "1min", "5min", "15min"],
        ... )
        >>> # Initialize with historical data and start real-time feed
        >>> data_manager.initialize(initial_days=30)
        >>> data_manager.start_realtime_feed()
        >>> # Access multi-timeframe data
        >>> current_5min = data_manager.get_data("5min")
        >>> current_1min = data_manager.get_data("1min")
    """
    if timeframes is None:
        timeframes = ["5min"]

    if config is None:
        config = load_default_config()

    return ProjectXRealtimeDataManager(
        instrument=instrument,
        project_x=project_x,
        realtime_client=realtime_client,
        timeframes=timeframes,
        timezone=config.timezone,
    )


def create_orderbook(
    instrument: str,
    config: ProjectXConfig | None = None,
    realtime_client: ProjectXRealtimeClient | None = None,
    project_x: "ProjectX | None" = None,
) -> "OrderBook":
    """
    Create a ProjectX OrderBook for advanced market depth analysis.

    This function creates an orderbook instance for Level 2 market depth analysis,
    iceberg order detection, and advanced market microstructure analytics. The orderbook
    processes real-time market depth data to provide insights into market structure,
    liquidity, and hidden order activity.

    Args:
        instrument: Trading instrument symbol (e.g., "MGC", "MNQ", "ES")
        config: Configuration object with timezone settings (uses defaults if None)
        realtime_client: Optional realtime client for automatic market data integration
        project_x: Optional ProjectX client for instrument metadata (enables dynamic tick size)

    Returns:
        OrderBook: Configured orderbook instance ready for market depth processing

    Example:
        >>> # Create orderbook with automatic real-time integration
        >>> orderbook = create_orderbook("MGC", realtime_client=realtime_client)
        >>> # OrderBook will automatically receive market depth updates
        >>> snapshot = orderbook.get_orderbook_snapshot()
        >>> spread = orderbook.get_bid_ask_spread()
        >>> imbalance = orderbook.get_order_imbalance()
        >>> iceberg_signals = orderbook.detect_iceberg_orders()
        >>> # Volume analysis
        >>> volume_profile = orderbook.get_volume_profile()
        >>> liquidity_analysis = orderbook.analyze_liquidity_distribution()
        >>>
        >>> # Alternative: Manual mode without real-time client
        >>> orderbook = create_orderbook("MGC")
        >>> # Manually process market data
        >>> orderbook.process_market_depth(depth_data)
    """
    if config is None:
        config = load_default_config()

    orderbook = OrderBook(
        instrument=instrument,
        timezone=config.timezone,
        client=project_x,
    )

    # Initialize with real-time capabilities if provided
    if realtime_client is not None:
        orderbook.initialize(realtime_client)

    return orderbook


def create_order_manager(
    project_x: ProjectX,
    realtime_client: ProjectXRealtimeClient | None = None,
) -> OrderManager:
    """
    Create a ProjectX OrderManager for comprehensive order operations.

    Args:
        project_x: ProjectX client instance
        realtime_client: Optional ProjectXRealtimeClient for real-time order tracking

    Returns:
        OrderManager instance

    Example:
        >>> order_manager = create_order_manager(project_x, realtime_client)
        >>> order_manager.initialize()
        >>> # Place orders
        >>> response = order_manager.place_market_order("MGC", 0, 1)
        >>> bracket = order_manager.place_bracket_order(
        ...     "MGC", 0, 1, 2045.0, 2040.0, 2055.0
        ... )
        >>> # Manage orders
        >>> orders = order_manager.search_open_orders()
        >>> order_manager.cancel_order(order_id)
    """
    order_manager = OrderManager(project_x)
    order_manager.initialize(realtime_client=realtime_client)
    return order_manager


def create_position_manager(
    project_x: ProjectX,
    realtime_client: ProjectXRealtimeClient | None = None,
) -> PositionManager:
    """
    Create a ProjectX PositionManager for comprehensive position operations.

    Args:
        project_x: ProjectX client instance
        realtime_client: Optional ProjectXRealtimeClient for real-time position tracking

    Returns:
        PositionManager instance

    Example:
        >>> position_manager = create_position_manager(project_x, realtime_client)
        >>> position_manager.initialize()
        >>> # Get positions
        >>> positions = position_manager.get_all_positions()
        >>> mgc_position = position_manager.get_position("MGC")
        >>> # Portfolio analytics
        >>> pnl = position_manager.get_portfolio_pnl()
        >>> risk = position_manager.get_risk_metrics()
        >>> # Position monitoring
        >>> position_manager.add_position_alert("MGC", max_loss=-500.0)
        >>> position_manager.start_monitoring()
    """
    position_manager = PositionManager(project_x)
    position_manager.initialize(realtime_client=realtime_client)
    return position_manager


def create_trading_suite(
    instrument: str,
    project_x: ProjectX,
    jwt_token: str,
    account_id: str,
    timeframes: list[str] | None = None,
    config: ProjectXConfig | None = None,
) -> dict[str, Any]:
    """
    Create a complete trading application toolkit with optimized architecture.

    This factory function provides developers with a comprehensive suite of connected
    components for building sophisticated trading applications. It sets up:

    - Single ProjectXRealtimeClient for efficient WebSocket connections
    - ProjectXRealtimeDataManager for multi-timeframe OHLCV data management
    - OrderBook for advanced market depth analysis and microstructure insights
    - OrderManager for comprehensive order lifecycle management
    - PositionManager for position tracking, risk management, and portfolio analytics
    - Proper dependency injection and optimized connection sharing

    Perfect for developers building algorithmic trading systems, market analysis tools,
    or automated trading strategies that need real-time data and order management.

    Args:
        instrument: Trading instrument symbol (e.g., "MGC", "MNQ", "ES")
        project_x: ProjectX client instance for API access
        jwt_token: JWT token for WebSocket authentication
        account_id: Account ID for real-time subscriptions and trading operations
        timeframes: List of timeframes to track (default: ["5min"])
        config: Configuration object with endpoints and settings (uses defaults if None)

    Returns:
        dict: Complete trading toolkit with keys:
              - "realtime_client": ProjectXRealtimeClient for WebSocket connections
              - "data_manager": ProjectXRealtimeDataManager for OHLCV data
              - "orderbook": OrderBook for market depth analysis
              - "order_manager": OrderManager for order operations
              - "position_manager": PositionManager for position tracking
              - "config": ProjectXConfig used for initialization

    Example:
        >>> suite = create_trading_suite(
        ...     "MGC", project_x, jwt_token, account_id, ["5sec", "1min", "5min"]
        ... )
        >>> # Connect once
        >>> suite["realtime_client"].connect()
        >>> # Initialize components
        >>> suite["data_manager"].initialize(initial_days=30)
        >>> suite["data_manager"].start_realtime_feed()
        >>> # OrderBook automatically receives market depth updates (no manual setup needed)
        >>> # Place orders
        >>> bracket = suite["order_manager"].place_bracket_order(
        ...     "MGC", 0, 1, 2045.0, 2040.0, 2055.0
        ... )
        >>> # Monitor positions
        >>> suite["position_manager"].add_position_alert("MGC", max_loss=-500.0)
        >>> suite["position_manager"].start_monitoring()
        >>> # Access data
        >>> ohlcv_data = suite["data_manager"].get_data("5min")
        >>> orderbook_snapshot = suite["orderbook"].get_orderbook_snapshot()
        >>> portfolio_pnl = suite["position_manager"].get_portfolio_pnl()
    """
    if timeframes is None:
        timeframes = ["5min"]

    if config is None:
        config = load_default_config()

    # Create single realtime client (shared connection)
    realtime_client = ProjectXRealtimeClient(
        jwt_token=jwt_token,
        account_id=account_id,
        config=config,
    )

    # Create OHLCV data manager with dependency injection
    data_manager = ProjectXRealtimeDataManager(
        instrument=instrument,
        project_x=project_x,
        realtime_client=realtime_client,
        timeframes=timeframes,
        timezone=config.timezone,
    )

    # Create orderbook for market depth analysis with automatic real-time integration
    orderbook = OrderBook(
        instrument=instrument,
        timezone=config.timezone,
        client=project_x,
    )
    orderbook.initialize(realtime_client=realtime_client)

    # Create order manager for comprehensive order operations
    order_manager = OrderManager(project_x)
    order_manager.initialize(realtime_client=realtime_client)

    # Create position manager for position tracking and risk management
    position_manager = PositionManager(project_x)
    position_manager.initialize(
        realtime_client=realtime_client, order_manager=order_manager
    )

    return {
        "realtime_client": realtime_client,
        "data_manager": data_manager,
        "orderbook": orderbook,
        "order_manager": order_manager,
        "position_manager": position_manager,
        "config": config,
    }
