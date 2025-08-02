"""
ProjectX Utility Functions

Author: TexasCoding
Date: June 2025

This module contains utility functions used throughout the ProjectX client.
Note: Technical indicators have been moved to the indicators module.
"""

# Data utilities
from .data_utils import create_data_snapshot, get_polars_last_value, get_polars_rows

# Environment utilities
from .environment import get_env_var

# Formatting utilities
from .formatting import format_price, format_volume

# Logging utilities
from .logging_utils import setup_logging

# Market microstructure utilities
from .market_microstructure import analyze_bid_ask_spread, calculate_volume_profile

# Market utilities
from .market_utils import (
    convert_timeframe_to_seconds,
    extract_symbol_from_contract_id,
    get_market_session_info,
    is_market_hours,
    validate_contract_id,
)

# Pattern detection utilities
from .pattern_detection import detect_candlestick_patterns, detect_chart_patterns

# Portfolio analytics utilities
from .portfolio_analytics import (
    calculate_correlation_matrix,
    calculate_max_drawdown,
    calculate_portfolio_metrics,
    calculate_sharpe_ratio,
    calculate_volatility_metrics,
)

# Rate limiting
from .rate_limiter import RateLimiter

# Trading calculations
from .trading_calculations import (
    calculate_position_sizing,
    calculate_position_value,
    calculate_risk_reward_ratio,
    calculate_tick_value,
    round_to_tick_size,
)

__all__ = [
    # Rate limiting
    "RateLimiter",
    # Market microstructure
    "analyze_bid_ask_spread",
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
    "calculate_volume_profile",
    "convert_timeframe_to_seconds",
    "create_data_snapshot",
    # Pattern detection
    "detect_candlestick_patterns",
    "detect_chart_patterns",
    "extract_symbol_from_contract_id",
    # Formatting utilities
    "format_price",
    "format_volume",
    # Environment utilities
    "get_env_var",
    "get_market_session_info",
    "get_polars_last_value",
    # Data utilities
    "get_polars_rows",
    # Market utilities
    "is_market_hours",
    "round_to_tick_size",
    # Logging utilities
    "setup_logging",
    "validate_contract_id",
]
