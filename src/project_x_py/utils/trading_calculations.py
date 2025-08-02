"""Trading-related calculations for position sizing, risk management, and price calculations."""

from typing import Any


def calculate_tick_value(
    price_change: float, tick_size: float, tick_value: float
) -> float:
    """
    Calculate dollar value of a price change.

    Args:
        price_change: Price difference
        tick_size: Minimum price movement
        tick_value: Dollar value per tick

    Returns:
        float: Dollar value of the price change

    Example:
        >>> # MGC moves 5 ticks
        >>> calculate_tick_value(0.5, 0.1, 1.0)
        5.0
    """
    if tick_size <= 0:
        return 0.0

    num_ticks = abs(price_change) / tick_size
    return num_ticks * tick_value


def calculate_position_value(
    size: int, price: float, tick_value: float, tick_size: float
) -> float:
    """
    Calculate total dollar value of a position.

    Args:
        size: Number of contracts
        price: Current price
        tick_value: Dollar value per tick
        tick_size: Minimum price movement

    Returns:
        float: Total position value in dollars

    Example:
        >>> # 5 MGC contracts at $2050
        >>> calculate_position_value(5, 2050.0, 1.0, 0.1)
        102500.0
    """
    if tick_size <= 0:
        return 0.0

    ticks_per_point = 1.0 / tick_size
    value_per_point = ticks_per_point * tick_value
    return abs(size) * price * value_per_point


def round_to_tick_size(price: float, tick_size: float) -> float:
    """
    Round price to nearest valid tick.

    Args:
        price: Price to round
        tick_size: Minimum price movement

    Returns:
        float: Price rounded to nearest tick

    Example:
        >>> round_to_tick_size(2050.37, 0.1)
        2050.4
    """
    if tick_size <= 0:
        return price

    return round(price / tick_size) * tick_size


def calculate_risk_reward_ratio(
    entry_price: float, stop_price: float, target_price: float
) -> float:
    """
    Calculate risk/reward ratio for a trade setup.

    Args:
        entry_price: Entry price
        stop_price: Stop loss price
        target_price: Profit target price

    Returns:
        float: Risk/reward ratio (reward / risk)

    Raises:
        ValueError: If prices are invalid (e.g., stop/target inversion)

    Example:
        >>> # Long trade: entry=2050, stop=2045, target=2065
        >>> calculate_risk_reward_ratio(2050, 2045, 2065)
        3.0
    """
    if entry_price == stop_price:
        raise ValueError("Entry price and stop price cannot be equal")

    risk = abs(entry_price - stop_price)
    reward = abs(target_price - entry_price)

    is_long = stop_price < entry_price
    if is_long and target_price <= entry_price:
        raise ValueError("For long positions, target must be above entry")
    elif not is_long and target_price >= entry_price:
        raise ValueError("For short positions, target must be below entry")

    if risk <= 0:
        return 0.0

    return reward / risk


def calculate_position_sizing(
    account_balance: float,
    risk_per_trade: float,
    entry_price: float,
    stop_loss_price: float,
    tick_value: float = 1.0,
) -> dict[str, Any]:
    """
    Calculate optimal position size based on risk management.

    Args:
        account_balance: Current account balance
        risk_per_trade: Risk per trade as decimal (e.g., 0.02 for 2%)
        entry_price: Entry price for the trade
        stop_loss_price: Stop loss price
        tick_value: Dollar value per tick

    Returns:
        Dict with position sizing information

    Example:
        >>> sizing = calculate_position_sizing(50000, 0.02, 2050, 2040, 1.0)
        >>> print(f"Position size: {sizing['position_size']} contracts")
    """
    try:
        # Calculate risk per share/contract
        price_risk = abs(entry_price - stop_loss_price)

        if price_risk == 0:
            return {"error": "No price risk (entry equals stop loss)"}

        # Calculate dollar risk
        dollar_risk_per_contract = price_risk * tick_value

        # Calculate maximum dollar risk for this trade
        max_dollar_risk = account_balance * risk_per_trade

        # Calculate position size
        position_size = max_dollar_risk / dollar_risk_per_contract

        # Round down to whole contracts
        position_size = int(position_size)

        # Calculate actual risk
        actual_dollar_risk = position_size * dollar_risk_per_contract
        actual_risk_percent = actual_dollar_risk / account_balance

        return {
            "position_size": position_size,
            "price_risk": price_risk,
            "dollar_risk_per_contract": dollar_risk_per_contract,
            "max_dollar_risk": max_dollar_risk,
            "actual_dollar_risk": actual_dollar_risk,
            "actual_risk_percent": actual_risk_percent,
            "risk_reward_ratio": None,  # Can be calculated if target provided
        }

    except Exception as e:
        return {"error": str(e)}
