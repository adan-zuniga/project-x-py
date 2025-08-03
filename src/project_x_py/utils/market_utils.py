"""
Market hours, session information, and contract validation utilities.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides market hours checking, session information, and contract validation
    utilities for trading applications. Includes CME futures market hours,
    contract ID validation, and symbol extraction for ProjectX trading.

Key Features:
    - CME futures market hours checking
    - Detailed market session information
    - Contract ID validation and parsing
    - Symbol extraction from contract IDs
    - Timeframe conversion utilities
    - Timezone-aware market operations

Market Utilities:
    - Market hours validation for CME futures
    - Session timing and next session calculations
    - Contract ID format validation
    - Symbol extraction and parsing
    - Timeframe string conversion to seconds
    - Timezone-aware market operations

Example Usage:
    ```python
    from project_x_py.utils import (
        is_market_hours,
        get_market_session_info,
        validate_contract_id,
        extract_symbol_from_contract_id,
        convert_timeframe_to_seconds,
    )

    # Check if market is open
    if is_market_hours():
        print("Market is open")
    else:
        print("Market is closed")

    # Get detailed session information
    session_info = get_market_session_info()
    print(f"Market open: {session_info['is_open']}")
    print(f"Next session: {session_info['next_session_start']}")

    # Validate contract IDs
    if validate_contract_id("CON.F.US.MGC.M25"):
        print("Valid contract ID")

    # Extract symbol from contract ID
    symbol = extract_symbol_from_contract_id("CON.F.US.MGC.M25")
    # Returns: "MGC"

    # Convert timeframe to seconds
    seconds = convert_timeframe_to_seconds("5min")
    # Returns: 300
    ```

Market Hours (CME Futures):
    - Sunday 5 PM CT to Friday 4 PM CT
    - Daily maintenance break: 4 PM - 5 PM CT
    - Saturday: Closed
    - Friday after 4 PM CT: Closed until Sunday 5 PM CT
    - Sunday before 5 PM CT: Closed until 5 PM CT

Contract ID Formats:
    - Full format: "CON.F.US.MGC.M25" (CON.F.US.SYMBOL.MONTHYEAR)
    - Simple format: "MGC" (base symbol)
    - Validation for both formats
    - Symbol extraction from full contract IDs

Timeframe Conversion:
    - Second-based: "1sec", "5sec", "10sec", "15sec", "30sec"
    - Minute-based: "1min", "5min", "15min", "30min"
    - Hour-based: "1hr", "4hr"
    - Day-based: "1day"
    - Week-based: "1week"
    - Month-based: "1month"

Performance Characteristics:
    - Fast market hours checking
    - Efficient contract ID validation
    - Memory-efficient string operations
    - Timezone-aware calculations
    - Optimized for high-frequency trading scenarios

See Also:
    - `utils.trading_calculations`: Trading calculations and math
    - `utils.data_utils`: Data processing and analysis
"""

import re
from datetime import datetime, timedelta
from typing import Any

import pytz


def is_market_hours(timezone: str = "America/Chicago") -> bool:
    """
    Check if it's currently market hours (CME futures).

    Args:
        timezone: Timezone to check (default: CME time)

    Returns:
        bool: True if market is open
    """
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)

    # CME futures markets are generally open Sunday 5 PM to Friday 4 PM CT
    # with a daily maintenance break from 4 PM to 5 PM CT
    weekday = now.weekday()  # Monday = 0, Sunday = 6
    hour = now.hour

    # Friday after 4 PM CT
    if weekday == 4 and hour >= 16:
        return False

    # Saturday (closed)
    if weekday == 5:
        return False

    # Sunday before 5 PM CT
    if weekday == 6 and hour < 17:
        return False

    # Daily maintenance break (4 PM - 5 PM CT)
    return hour != 16


def get_market_session_info(timezone: str = "America/Chicago") -> dict[str, Any]:
    """
    Get detailed market session information.

    Args:
        timezone: Market timezone

    Returns:
        dict: Market session details

    Example:
        >>> info = get_market_session_info()
        >>> print(f"Market open: {info['is_open']}")
        >>> print(f"Next session: {info['next_session_start']}")
    """
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    weekday = now.weekday()
    hour = now.hour

    # Initialize variables
    next_open = None
    next_close = None

    # Calculate next session times
    if weekday == 4 and hour >= 16:  # Friday after close
        # Next open is Sunday 5 PM
        days_until_sunday = (6 - weekday) % 7
        next_open = now.replace(hour=17, minute=0, second=0, microsecond=0)
        next_open += timedelta(days=days_until_sunday)
    elif weekday == 5:  # Saturday
        # Next open is Sunday 5 PM
        next_open = now.replace(hour=17, minute=0, second=0, microsecond=0)
        next_open += timedelta(days=1)
    elif weekday == 6 and hour < 17:  # Sunday before open
        # Opens today at 5 PM
        next_open = now.replace(hour=17, minute=0, second=0, microsecond=0)
    elif hour == 16:  # Daily maintenance
        # Reopens in 1 hour
        next_open = now.replace(hour=17, minute=0, second=0, microsecond=0)
    else:
        # Market is open, next close varies
        if weekday == 4:  # Friday
            next_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        else:  # Other days
            next_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
            if now.hour >= 16:
                next_close += timedelta(days=1)

    is_open = is_market_hours(timezone)

    session_info = {
        "is_open": is_open,
        "current_time": now,
        "timezone": timezone,
        "weekday": now.strftime("%A"),
    }

    if not is_open and next_open:
        session_info["next_session_start"] = next_open
        session_info["time_until_open"] = next_open - now
    elif is_open and next_close:
        session_info["next_session_end"] = next_close
        session_info["time_until_close"] = next_close - now

    return session_info


def validate_contract_id(contract_id: str) -> bool:
    """
    Validate ProjectX contract ID format.

    Args:
        contract_id: Contract ID to validate

    Returns:
        bool: True if valid format

    Example:
        >>> validate_contract_id("CON.F.US.MGC.M25")
        True
        >>> validate_contract_id("MGC")
        True
        >>> validate_contract_id("invalid.contract")
        False
    """
    # Full contract ID format: CON.F.US.MGC.M25
    full_pattern = r"^CON\.F\.US\.[A-Z]{2,4}\.[FGHJKMNQUVXZ]\d{2}$"

    # Simple symbol format: MGC, NQ, etc.
    simple_pattern = r"^[A-Z]{2,4}$"

    return bool(
        re.match(full_pattern, contract_id) or re.match(simple_pattern, contract_id)
    )


def extract_symbol_from_contract_id(contract_id: str) -> str | None:
    """
    Extract the base symbol from a full contract ID.

    Args:
        contract_id: Full contract ID or symbol

    Returns:
        str: Base symbol (e.g., "MGC" from "CON.F.US.MGC.M25")
        None: If extraction fails

    Example:
        >>> extract_symbol_from_contract_id("CON.F.US.MGC.M25")
        'MGC'
        >>> extract_symbol_from_contract_id("MGC")
        'MGC'
    """
    if not contract_id:
        return None

    # If it's already a simple symbol, return it
    if re.match(r"^[A-Z]{2,4}$", contract_id):
        return contract_id

    # Extract from full contract ID
    match = re.match(r"^CON\.F\.US\.([A-Z]{2,4})\.[FGHJKMNQUVXZ]\d{2}$", contract_id)
    return match.group(1) if match else None


def convert_timeframe_to_seconds(timeframe: str) -> int:
    """
    Convert timeframe string to seconds.

    Args:
        timeframe: Timeframe (e.g., "1min", "5min", "1hr", "1day")

    Returns:
        int: Timeframe in seconds

    Example:
        >>> convert_timeframe_to_seconds("5min")
        300
        >>> convert_timeframe_to_seconds("1hr")
        3600
    """
    timeframe = timeframe.lower()

    # Parse number and unit
    match = re.match(r"(\d+)(.*)", timeframe)
    if not match:
        return 0

    number = int(match.group(1))
    unit = match.group(2)

    # Convert to seconds
    multipliers = {
        "s": 1,
        "sec": 1,
        "second": 1,
        "seconds": 1,
        "m": 60,
        "min": 60,
        "minute": 60,
        "minutes": 60,
        "h": 3600,
        "hr": 3600,
        "hour": 3600,
        "hours": 3600,
        "d": 86400,
        "day": 86400,
        "days": 86400,
        "w": 604800,
        "week": 604800,
        "weeks": 604800,
    }

    return number * multipliers.get(unit, 0)
