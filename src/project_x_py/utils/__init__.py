"""
ProjectX Utility Functions

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Contains utility functions used throughout the ProjectX client. Provides
    generic, reusable functionality for data processing, error handling,
    logging, market analysis, and trading calculations. All utilities are
    stateless, pure functions designed for cross-module compatibility.

Key Features:
    - Generic utility functions for data processing and manipulation
    - Comprehensive error handling and logging utilities
    - Market analysis and pattern detection tools
    - Trading calculations and risk management utilities
    - Environment configuration and validation helpers
    - Rate limiting and performance optimization tools

Utility Categories:
    - Core Utilities: Rate limiting, data manipulation, environment handling
    - Error Handling: Decorators, context managers, standardized error messages
    - Logging: Structured logging, performance monitoring, API call tracking
    - Market Analysis: Session info, contract validation, pattern detection
    - Portfolio Analytics: Performance metrics, correlation analysis, drawdown calculation
    - Trading Calculations: Position sizing, risk management, tick value calculations

Example Usage:
    ```python
    from project_x_py.utils import (
        # Error handling
        handle_errors,
        retry_on_network_error,
        ErrorContext,
        # Trading calculations
        calculate_tick_value,
        calculate_position_sizing,
        round_to_tick_size,
        # Market utilities
        is_market_hours,
        get_market_session_info,
        validate_contract_id,
        # Portfolio analytics
        calculate_sharpe_ratio,
        calculate_max_drawdown,
        calculate_portfolio_metrics,
        # Pattern detection
        detect_candlestick_patterns,
        detect_chart_patterns,
        # Data utilities
        create_data_snapshot,
        get_polars_last_value,
    )


    # Use error handling decorators
    @handle_errors("fetch market data")
    async def get_market_data():
        # Implementation
        pass


    # Use trading calculations
    tick_value = calculate_tick_value(0.5, 0.1, 1.0)  # 5 ticks
    position_size = calculate_position_sizing(50000, 0.02, 2050, 2040)

    # Use market utilities
    if is_market_hours():
        print("Market is open")

    # Use portfolio analytics
    sharpe = calculate_sharpe_ratio(returns_data)
    drawdown = calculate_max_drawdown(price_data)
    ```

Architecture Principles:
    - Generic and reusable across different contexts
    - Work with standard data types (DataFrames, numbers, strings)
    - No domain-specific knowledge or dependencies
    - Stateless and pure functions
    - Comprehensive error handling and logging

Note: Technical indicators have been moved to the indicators module for better organization.

See Also:
    - `utils.async_rate_limiter`: Rate limiting for API calls
    - `utils.error_handler`: Error handling decorators and context managers
    - `utils.trading_calculations`: Trading math and risk management
    - `utils.portfolio_analytics`: Performance metrics and analysis
    - `utils.market_utils`: Market session and contract utilities
    - `utils.pattern_detection`: Technical pattern detection
"""

# Data utilities
# Rate limiting
from project_x_py.utils.async_rate_limiter import RateLimiter
from project_x_py.utils.data_utils import (
    create_data_snapshot,
    get_polars_last_value,
    get_polars_rows,
)

# Enhanced statistics tracking moved to project_x_py.statistics in v3.3.0
# Environment utilities
from project_x_py.utils.environment import get_env_var

# Error handling utilities
from project_x_py.utils.error_handler import (
    ErrorContext,
    handle_errors,
    handle_rate_limit,
    retry_on_network_error,
    validate_response,
)
from project_x_py.utils.error_messages import (
    ErrorCode,
    ErrorMessages,
    format_error_message,
)

# Formatting utilities
from project_x_py.utils.formatting import format_price, format_volume
from project_x_py.utils.logging_config import (
    LogContext,
    LogMessages,
    ProjectXLogger,
    configure_sdk_logging,
    log_api_call,
)

# Logging utilities
from project_x_py.utils.logging_utils import setup_logging

# Market utilities
from project_x_py.utils.market_utils import (
    convert_timeframe_to_seconds,
    extract_symbol_from_contract_id,
    get_market_session_info,
    is_market_hours,
    validate_contract_id,
)

# Pattern detection utilities
from project_x_py.utils.pattern_detection import (
    detect_candlestick_patterns,
    detect_chart_patterns,
)

# Portfolio analytics utilities
from project_x_py.utils.portfolio_analytics import (
    calculate_correlation_matrix,
    calculate_max_drawdown,
    calculate_portfolio_metrics,
    calculate_sharpe_ratio,
    calculate_volatility_metrics,
)

# StatisticsAggregator moved to project_x_py.statistics in v3.3.0
# Trading calculations
from project_x_py.utils.trading_calculations import (
    calculate_position_sizing,
    calculate_position_value,
    calculate_risk_reward_ratio,
    calculate_tick_value,
    round_to_tick_size,
)

__all__ = [
    # Error handling
    "ErrorCode",
    "ErrorContext",
    "ErrorMessages",
    # Enhanced statistics moved to project_x_py.statistics in v3.3.0
    # Rate limiting
    "LogContext",
    "LogMessages",
    "ProjectXLogger",
    "RateLimiter",
    # Portfolio analytics
    "calculate_correlation_matrix",
    "calculate_max_drawdown",
    "calculate_portfolio_metrics",
    "calculate_position_sizing",
    "calculate_position_value",
    "calculate_risk_reward_ratio",
    "calculate_sharpe_ratio",
    # Trading calculations
    "calculate_tick_value",
    "calculate_volatility_metrics",
    "configure_sdk_logging",
    "convert_timeframe_to_seconds",
    "create_data_snapshot",
    # Pattern detection
    "detect_candlestick_patterns",
    "detect_chart_patterns",
    "extract_symbol_from_contract_id",
    "format_error_message",
    # Formatting utilities
    "format_price",
    "format_volume",
    # Environment utilities
    "get_env_var",
    "get_market_session_info",
    "get_polars_last_value",
    # Data utilities
    "get_polars_rows",
    "handle_errors",
    "handle_rate_limit",
    # Market utilities
    "is_market_hours",
    "log_api_call",
    "retry_on_network_error",
    "round_to_tick_size",
    # Logging utilities
    "setup_logging",
    "validate_contract_id",
    "validate_response",
]
