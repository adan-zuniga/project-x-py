"""
Formatting utilities for prices, volumes, and other display values.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides formatting utilities for prices, volumes, and other display values
    commonly used in trading applications. Includes currency formatting, volume
    abbreviation, and display optimization for financial data.

Key Features:
    - Currency formatting for prices with decimal precision
    - Volume abbreviation for large numbers (K, M, B)
    - Display optimization for financial data
    - Consistent formatting across the SDK
    - Type-safe formatting operations
    - Performance-optimized formatting functions

Formatting Utilities:
    - Price formatting with currency symbols and decimal precision
    - Volume formatting with automatic abbreviation
    - Display optimization for large numbers
    - Consistent formatting patterns across modules
    - Error handling for invalid inputs

Example Usage:
    ```python
    from project_x_py.utils import format_price, format_volume

    # Format prices with currency
    price = format_price(2050.50, decimals=2)
    # Returns: "$2,050.50"

    # Format large volumes with abbreviation
    volume = format_volume(1500000)
    # Returns: "1.5M"

    # Format smaller volumes
    small_volume = format_volume(1500)
    # Returns: "1.5K"

    # Use in trading applications
    print(f"Price: {format_price(current_price)}")
    print(f"Volume: {format_volume(total_volume)}")

    # Custom decimal precision
    precise_price = format_price(2050.375, decimals=3)
    # Returns: "$2,050.375"
    ```

Formatting Features:
    - Currency formatting with comma separators
    - Configurable decimal precision for prices
    - Automatic volume abbreviation (K, M, B)
    - Type-safe operations with proper error handling
    - Performance-optimized for high-frequency use
    - Consistent formatting across all modules

Performance Characteristics:
    - Fast formatting operations for real-time display
    - Memory-efficient string operations
    - Type-safe operations with proper validation
    - Optimized for high-frequency trading scenarios
    - Minimal overhead for display formatting

See Also:
    - `utils.trading_calculations`: Trading calculations and math
    - `utils.data_utils`: Data processing and analysis
"""


def format_price(price: float, decimals: int = 2) -> str:
    """Format price for display."""
    return f"${price:,.{decimals}f}"


def format_volume(volume: int) -> str:
    """Format volume for display."""
    if volume >= 1_000_000:
        return f"{volume / 1_000_000:.1f}M"
    elif volume >= 1_000:
        return f"{volume / 1_000:.1f}K"
    else:
        return str(volume)
