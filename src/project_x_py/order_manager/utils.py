"""
Order management utility functions for ProjectX.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides async/sync helpers for price alignment to instrument tick size, contract
    resolution, and other utility operations used throughout the async OrderManager system.

Key Features:
    - Aligns prices to valid instrument tick size (async and sync)
    - Resolves contract IDs to instrument metadata
    - Precision rounding and validation helpers
    - Automatic tick size detection from instrument data
    - Decimal precision handling for accurate price alignment

Utility Functions:
    - align_price_to_tick: Synchronous price alignment to tick size
    - align_price_to_tick_size: Async price alignment with instrument lookup
    - resolve_contract_id: Contract ID resolution to instrument details

These utilities ensure that all order prices are properly aligned to instrument
tick sizes, preventing "Invalid price" errors from the exchange.

Example Usage:
    ```python
    # Aligning a price to tick size
    aligned = align_price_to_tick(2052.17, 0.25)
    # Resolving contract ID
    details = await resolve_contract_id("MNQ", project_x_client)
    # Async price alignment with automatic tick size detection
    aligned_price = await align_price_to_tick_size(2052.17, "MGC", client)
    ```

See Also:
    - `order_manager.core.OrderManager`
    - `order_manager.tracking`
    - `order_manager.position_orders`
"""

import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any

from project_x_py.exceptions import ProjectXOrderError

if TYPE_CHECKING:
    from project_x_py.client import ProjectXBase

logger = logging.getLogger(__name__)

# Cache for instrument tick sizes to improve performance
_tick_size_cache: dict[str, float] = {}


async def validate_price_tick_size(
    price: float | None,
    contract_id: str,
    project_x: "ProjectXBase",
    price_label: str = "price",
) -> None:
    """
    Validate that a price conforms to instrument tick size requirements BEFORE operations.

    This function checks if a price is already properly aligned to the instrument's tick size,
    raising a clear error if not. This prevents invalid prices from being submitted to the API.

    Args:
        price: The price to validate (can be None)
        contract_id: Contract ID to get tick size from (e.g., "MGC", "F.US.EP.U25")
        project_x: ProjectX client instance for instrument lookup
        price_label: Label for the price in error messages (e.g., "limit_price", "stop_price")

    Raises:
        ProjectXOrderError: If price doesn't align to tick size or other validation fails

    Example:
        >>> # This will raise an error if price is not tick-aligned
        >>> await validate_price_tick_size(2052.17, "MNQ", client, "limit_price")
        >>> # ProjectXOrderError: limit_price 2052.17 is not aligned to tick size 0.25 for MNQ.
        >>> # Valid prices near this value: 2052.00, 2052.25
    """
    if price is None:
        return

    try:
        # Get cached tick size or fetch it
        tick_size = await _get_cached_tick_size(contract_id, project_x)
        if tick_size is None or tick_size <= 0:
            logger.warning(
                f"No valid tick size available for contract {contract_id}, skipping validation for {price_label}: {price}"
            )
            return

        # Calculate what the aligned price should be
        aligned_price = align_price_to_tick(price, tick_size)

        # Check if price is already properly aligned using Decimal precision
        price_decimal = Decimal(str(price))
        aligned_decimal = Decimal(str(aligned_price))

        if price_decimal != aligned_decimal:
            # Calculate nearby valid prices for helpful error message
            lower_tick = align_price_to_tick(price - tick_size, tick_size)
            upper_tick = align_price_to_tick(price + tick_size, tick_size)

            raise ProjectXOrderError(
                f"{price_label} {price} is not aligned to tick size {tick_size} for {contract_id}. "
                f"Valid prices near this value: {lower_tick}, {aligned_price}"
                + (f", {upper_tick}" if upper_tick != aligned_price else "")
            )

        logger.debug(
            f"Price validation passed: {price_label} {price} is properly aligned to tick size {tick_size}"
        )

    except ProjectXOrderError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(f"Error validating {price_label} {price} for tick size: {e}")
        # Don't raise - allow trading to continue if validation fails due to system issues
        logger.warning(
            f"Skipping tick size validation for {price_label} {price} due to error"
        )


async def _get_cached_tick_size(
    contract_id: str, project_x: "ProjectXBase"
) -> float | None:
    """
    Get tick size from cache or fetch and cache it.

    Args:
        contract_id: Contract ID to get tick size from
        project_x: ProjectX client instance

    Returns:
        float: Tick size or None if not available
    """
    # Check cache first
    if contract_id in _tick_size_cache:
        return _tick_size_cache[contract_id]

    try:
        instrument_obj = None

        # Try to get instrument by simple symbol first (e.g., "MNQ")
        if "." not in contract_id:
            instrument_obj = await project_x.get_instrument(contract_id)
        else:
            # Extract symbol from contract ID (e.g., "CON.F.US.MGC.M25" -> "MGC")
            from project_x_py.utils import extract_symbol_from_contract_id

            symbol = extract_symbol_from_contract_id(contract_id)
            if symbol:
                instrument_obj = await project_x.get_instrument(symbol)

        if (
            instrument_obj
            and hasattr(instrument_obj, "tickSize")
            and instrument_obj.tickSize
        ):
            tick_size = float(instrument_obj.tickSize)
            # Cache the tick size for future use
            _tick_size_cache[contract_id] = tick_size
            return tick_size

        logger.warning(f"No tick size available for contract {contract_id}")
        return None

    except Exception as e:
        logger.error(f"Error getting tick size for {contract_id}: {e}")
        return None


def clear_tick_size_cache() -> None:
    """Clear the tick size cache. Useful for testing or when instruments change."""
    global _tick_size_cache
    _tick_size_cache.clear()
    logger.debug("Tick size cache cleared")


def align_price_to_tick(price: float, tick_size: float) -> float:
    """
    Align price to the nearest valid tick using Decimal precision.

    Args:
        price: The price to align
        tick_size: The instrument's tick size

    Returns:
        float: Price aligned to nearest tick with preserved precision
    """
    if tick_size <= 0:
        return price

    # Convert to Decimal for precision
    decimal_price = Decimal(str(price))
    decimal_tick = Decimal(str(tick_size))

    # Round to nearest tick using precise Decimal arithmetic
    aligned = (decimal_price / decimal_tick).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    ) * decimal_tick

    # Determine appropriate precision for result
    tick_str = str(tick_size)
    if "." in tick_str:
        decimal_places = len(tick_str.split(".")[1])
        if decimal_places > 0:
            quantize_pattern = Decimal("0." + "0" * (decimal_places - 1) + "1")
            aligned = aligned.quantize(quantize_pattern)

    return float(aligned)


async def align_price_to_tick_size(
    price: float | None, contract_id: str, project_x: "ProjectXBase"
) -> float | None:
    """
    Align a price to the instrument's tick size.

    This function automatically retrieves the instrument's tick size and aligns the
    provided price to the nearest valid tick. This prevents "Invalid price" errors
    from the exchange by ensuring all prices conform to the instrument's pricing
    requirements.

    The function performs the following operations:
    1. Retrieves instrument data to determine tick size
    2. Uses precise decimal arithmetic for accurate alignment
    3. Handles various contract ID formats (simple symbols and full contract IDs)
    4. Returns the original price if alignment fails (graceful degradation)

    Args:
        price: The price to align (can be None)
        contract_id: Contract ID to get tick size from (e.g., "MGC", "F.US.EP.U25")
        project_x: ProjectX client instance for instrument lookup

    Returns:
        float: Price aligned to tick size, or None if input price is None

    Example:
        >>> # V3.1: Align a price for MNQ (tick size 0.25)
        >>> aligned = await align_price_to_tick_size(20052.17, "MNQ", client)
        >>> print(aligned)  # 20052.25

        >>> # V3.1: Align a price for ES (tick size 0.25)
        >>> aligned = await align_price_to_tick_size(5000.17, "ES", client)
        >>> print(aligned)  # 5000.25
    """
    try:
        if price is None:
            return None

        instrument_obj = None

        # Try to get instrument by simple symbol first (e.g., "MNQ")
        if "." not in contract_id:
            instrument_obj = await project_x.get_instrument(contract_id)
        else:
            # Extract symbol from contract ID (e.g., "CON.F.US.MGC.M25" -> "MGC")
            from project_x_py.utils import extract_symbol_from_contract_id

            symbol = extract_symbol_from_contract_id(contract_id)
            if symbol:
                instrument_obj = await project_x.get_instrument(symbol)

        if not instrument_obj or not hasattr(instrument_obj, "tickSize"):
            logger.warning(
                f"No tick size available for contract {contract_id}, using original price: {price}"
            )
            return price

        tick_size = instrument_obj.tickSize
        if tick_size is None or tick_size <= 0:
            logger.warning(
                f"Invalid tick size {tick_size} for {contract_id}, using original price: {price}"
            )
            return price

        logger.debug(
            f"Aligning price {price} with tick size {tick_size} for {contract_id}"
        )

        # Convert to Decimal for precise calculation with high precision context
        price_decimal = Decimal(str(price))
        tick_decimal = Decimal(str(tick_size))

        # Round to nearest tick using precise decimal arithmetic
        ticks = (price_decimal / tick_decimal).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        aligned_decimal = ticks * tick_decimal

        # Determine the number of decimal places needed for the tick size
        tick_str = str(tick_size)
        decimal_places = len(tick_str.split(".")[1]) if "." in tick_str else 0

        # Create the quantization pattern with appropriate precision
        if decimal_places == 0:
            quantize_pattern = Decimal("1")
        else:
            quantize_pattern = Decimal("0." + "0" * (decimal_places - 1) + "1")

        # Quantize to appropriate precision and convert back to float
        result = float(
            aligned_decimal.quantize(quantize_pattern, rounding=ROUND_HALF_UP)
        )

        if result != price:
            logger.info(
                f"Price alignment: {price} -> {result} (tick size: {tick_size})"
            )

        return result

    except Exception as e:
        logger.error(f"Error aligning price {price} to tick size: {e}")
        return price  # Return original price if alignment fails


async def resolve_contract_id(
    contract_id: str, project_x: "ProjectXBase"
) -> dict[str, Any] | None:
    """Resolve a contract ID to its full contract details."""
    try:
        # Try to get from instrument cache first
        instrument = await project_x.get_instrument(contract_id)
        if instrument:
            # Return dict representation of instrument
            return {
                "id": instrument.id,
                "name": instrument.name,
                "tickSize": instrument.tickSize,
                "tickValue": instrument.tickValue,
                "activeContract": instrument.activeContract,
            }
        return None
    except Exception:
        return None
