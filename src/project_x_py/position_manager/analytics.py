"""P&L calculations and portfolio analytics."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from project_x_py.models import Position

if TYPE_CHECKING:
    from project_x_py.position_manager.types import PositionManagerProtocol


class PositionAnalyticsMixin:
    """Mixin for P&L calculations and portfolio analytics."""

    async def calculate_position_pnl(
        self: "PositionManagerProtocol",
        position: Position,
        current_price: float,
        point_value: float | None = None,
    ) -> dict[str, Any]:
        """
        Calculate P&L for a position given current market price.

        Computes unrealized profit/loss for a position based on the difference
        between entry price and current market price, accounting for position
        direction (long/short).

        Args:
            position (Position): The position object to calculate P&L for
            current_price (float): Current market price of the contract
            point_value (float, optional): Dollar value per point movement.
                For futures, this is the contract multiplier (e.g., 10 for MGC).
                If None, P&L is returned in points rather than dollars.
                Defaults to None.

        Returns:
            dict[str, Any]: Comprehensive P&L calculations containing:
                - unrealized_pnl (float): Total unrealized P&L (dollars or points)
                - market_value (float): Current market value of position
                - pnl_per_contract (float): P&L per contract (dollars or points)
                - current_price (float): The provided current price
                - entry_price (float): Average entry price (position.averagePrice)
                - size (int): Position size in contracts
                - direction (str): "LONG" or "SHORT"
                - price_change (float): Favorable price movement amount

        Example:
            >>> # Calculate P&L in points
            >>> position = await position_manager.get_position("MGC")
            >>> pnl = await position_manager.calculate_position_pnl(position, 2050.0)
            >>> print(f"Unrealized P&L: {pnl['unrealized_pnl']:.2f} points")
            >>> # Calculate P&L in dollars with contract multiplier
            >>> pnl = await position_manager.calculate_position_pnl(
            ...     position,
            ...     2050.0,
            ...     point_value=10.0,  # MGC = $10/point
            ... )
            >>> print(f"Unrealized P&L: ${pnl['unrealized_pnl']:.2f}")
            >>> print(f"Per contract: ${pnl['pnl_per_contract']:.2f}")

        Note:
            - Long positions profit when price increases
            - Short positions profit when price decreases
            - Use instrument.contractMultiplier for accurate point_value
        """
        # Calculate P&L based on position direction
        if position.type == 1:  # LONG
            price_change = current_price - position.averagePrice
        else:  # SHORT (type == 2)
            price_change = position.averagePrice - current_price

        # Apply point value if provided (for accurate dollar P&L)
        if point_value is not None:
            pnl_per_contract = price_change * point_value
        else:
            pnl_per_contract = price_change

        unrealized_pnl = pnl_per_contract * position.size
        market_value = current_price * position.size

        return {
            "unrealized_pnl": unrealized_pnl,
            "market_value": market_value,
            "pnl_per_contract": pnl_per_contract,
            "current_price": current_price,
            "entry_price": position.averagePrice,
            "size": position.size,
            "direction": "LONG" if position.type == 1 else "SHORT",
            "price_change": price_change,
        }

    async def calculate_portfolio_pnl(
        self: "PositionManagerProtocol",
        current_prices: dict[str, float],
        account_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Calculate portfolio P&L given current market prices.

        Computes aggregate P&L across all positions using provided market prices.
        Handles missing prices gracefully and provides detailed breakdown by position.

        Args:
            current_prices (dict[str, float]): Dictionary mapping contract IDs to
                their current market prices. Example: {"MGC": 2050.0, "NQ": 15500.0}
            account_id (int, optional): The account ID to calculate P&L for.
                If None, uses the default account from authentication.
                Defaults to None.

        Returns:
            dict[str, Any]: Portfolio P&L analysis containing:
                - total_pnl (float): Sum of all calculated P&Ls
                - positions_count (int): Total number of positions
                - positions_with_prices (int): Positions with price data
                - positions_without_prices (int): Positions missing price data
                - position_breakdown (list[dict]): Detailed P&L per position:
                    * contract_id (str): Contract identifier
                    * size (int): Position size
                    * entry_price (float): Average entry price
                    * current_price (float | None): Current market price
                    * unrealized_pnl (float | None): Position P&L
                    * market_value (float | None): Current market value
                    * direction (str): "LONG" or "SHORT"
                - timestamp (datetime): Calculation timestamp

        Example:
            >>> # Get current prices from market data
            >>> prices = {"MGC": 2050.0, "NQ": 15500.0, "ES": 4400.0}
            >>> portfolio_pnl = await position_manager.calculate_portfolio_pnl(prices)
            >>> print(f"Total P&L: ${portfolio_pnl['total_pnl']:.2f}")
            >>> print(
            ...     f"Positions analyzed: {portfolio_pnl['positions_with_prices']}/"
            ...     f"{portfolio_pnl['positions_count']}"
            ... )
            >>> # Check individual positions
            >>> for pos in portfolio_pnl["position_breakdown"]:
            ...     if pos["unrealized_pnl"] is not None:
            ...         print(f"{pos['contract_id']}: ${pos['unrealized_pnl']:.2f}")

        Note:
            - P&L calculations assume point values of 1.0
            - For accurate dollar P&L, use calculate_position_pnl() with point values
            - Positions without prices in current_prices dict will have None P&L
        """
        positions = await self.get_all_positions(account_id=account_id)

        total_pnl = 0.0
        position_breakdown = []
        positions_with_prices = 0

        for position in positions:
            current_price = current_prices.get(position.contractId)

            if current_price is not None:
                pnl_data = await self.calculate_position_pnl(position, current_price)
                total_pnl += pnl_data["unrealized_pnl"]
                positions_with_prices += 1

                position_breakdown.append(
                    {
                        "contract_id": position.contractId,
                        "size": position.size,
                        "entry_price": position.averagePrice,
                        "current_price": current_price,
                        "unrealized_pnl": pnl_data["unrealized_pnl"],
                        "market_value": pnl_data["market_value"],
                        "direction": pnl_data["direction"],
                    }
                )
            else:
                # No price data available
                position_breakdown.append(
                    {
                        "contract_id": position.contractId,
                        "size": position.size,
                        "entry_price": position.averagePrice,
                        "current_price": None,
                        "unrealized_pnl": None,
                        "market_value": None,
                        "direction": "LONG" if position.type == 1 else "SHORT",
                    }
                )

        return {
            "total_pnl": total_pnl,
            "positions_count": len(positions),
            "positions_with_prices": positions_with_prices,
            "positions_without_prices": len(positions) - positions_with_prices,
            "position_breakdown": position_breakdown,
            "timestamp": datetime.now(),
        }

    async def get_portfolio_pnl(
        self: "PositionManagerProtocol", account_id: int | None = None
    ) -> dict[str, Any]:
        """
        Get portfolio P&L placeholder data (requires market prices for actual P&L).

        Retrieves current positions and provides a structure for P&L analysis.
        Since ProjectX API doesn't provide P&L data directly, actual P&L calculation
        requires current market prices via calculate_portfolio_pnl().

        Args:
            account_id (int, optional): The account ID to analyze.
                If None, uses the default account from authentication.
                Defaults to None.

        Returns:
            dict[str, Any]: Portfolio structure containing:
                - position_count (int): Number of open positions
                - positions (list[dict]): Position details with placeholders:
                    * contract_id (str): Contract identifier
                    * size (int): Position size
                    * avg_price (float): Average entry price
                    * market_value (float): Size x average price estimate
                    * direction (str): "LONG" or "SHORT"
                    * note (str): Reminder about P&L calculation
                - total_pnl (float): 0.0 (placeholder)
                - total_unrealized_pnl (float): 0.0 (placeholder)
                - total_realized_pnl (float): 0.0 (placeholder)
                - net_pnl (float): 0.0 (placeholder)
                - last_updated (datetime): Timestamp
                - note (str): Instructions for actual P&L calculation

        Example:
            >>> # Get portfolio structure
            >>> portfolio = await position_manager.get_portfolio_pnl()
            >>> print(f"Open positions: {portfolio['position_count']}")
            >>> for pos in portfolio["positions"]:
            ...     print(f"{pos['contract_id']}: {pos['size']} @ ${pos['avg_price']}")
            >>> # For actual P&L, use calculate_portfolio_pnl() with prices
            >>> print(portfolio["note"])

        See Also:
            calculate_portfolio_pnl(): For actual P&L calculations with market prices
        """
        positions = await self.get_all_positions(account_id=account_id)

        position_breakdown = []

        for position in positions:
            # Note: ProjectX doesn't provide P&L data, would need current market prices to calculate
            position_breakdown.append(
                {
                    "contract_id": position.contractId,
                    "size": position.size,
                    "avg_price": position.averagePrice,
                    "market_value": position.size * position.averagePrice,
                    "direction": "LONG" if position.type == 1 else "SHORT",
                    "note": "P&L requires current market price - use calculate_position_pnl() method",
                }
            )

        return {
            "position_count": len(positions),
            "positions": position_breakdown,
            "total_pnl": 0.0,  # Default value when no current prices available
            "total_unrealized_pnl": 0.0,
            "total_realized_pnl": 0.0,
            "net_pnl": 0.0,
            "last_updated": datetime.now(),
            "note": "For P&L calculations, use calculate_portfolio_pnl() with current market prices",
        }
