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

if TYPE_CHECKING:
    from project_x_py.client import ProjectXBase

logger = logging.getLogger(__name__)


def align_price_to_tick(price: float, tick_size: float) -> float:
    """Align price to the nearest valid tick."""
    if tick_size <= 0:
        return price

    decimal_price = Decimal(str(price))
    decimal_tick = Decimal(str(tick_size))

    # Round to nearest tick
    aligned = (decimal_price / decimal_tick).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    ) * decimal_tick

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
        >>> # Align a price for MGC (tick size 0.1)
        >>> aligned = await align_price_to_tick_size(2052.17, "MGC", client)
        >>> print(aligned)  # 2052.2

        >>> # Align a price for ES (tick size 0.25)
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

        # Convert to Decimal for precise calculation
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

        # Create the quantization pattern
        if decimal_places == 0:
            quantize_pattern = Decimal("1")
        else:
            quantize_pattern = Decimal("0." + "0" * (decimal_places - 1) + "1")

        result = float(aligned_decimal.quantize(quantize_pattern))

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
