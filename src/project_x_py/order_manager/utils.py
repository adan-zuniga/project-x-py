"""Utility functions for order management."""

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

    Args:
        price: The price to align
        contract_id: Contract ID to get tick size from
        project_x: ProjectX client instance

    Returns:
        float: Price aligned to tick size
        None: If price is None
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
