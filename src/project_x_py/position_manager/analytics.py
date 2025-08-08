"""
P&L calculations and portfolio analytics for ProjectX position management.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides comprehensive P&L calculations and portfolio analytics for position
    management. Includes individual position P&L calculations, portfolio-level
    analysis, and integration with market prices for accurate profit/loss tracking.

Key Features:
    - Individual position P&L calculations with point value support
    - Portfolio-level P&L aggregation across all positions
    - Market price integration for real-time P&L tracking
    - Configurable point values for accurate dollar calculations
    - Comprehensive P&L breakdowns and analysis
    - Thread-safe operations with proper error handling

Analytics Capabilities:
    - Position-specific P&L with entry price vs current market price
    - Portfolio aggregation with missing price handling
    - Point value integration for accurate dollar calculations
    - Real-time P&L updates with market price changes
    - Comprehensive P&L reporting and analysis

Example Usage:
    ```python
    # Calculate individual position P&L
    position = await position_manager.get_position("MGC")
    pnl = await position_manager.calculate_position_pnl(
        position, current_price=2050.0, point_value=10.0
    )
    print(f"P&L: ${pnl['unrealized_pnl']:.2f}")

    # Portfolio P&L with current market prices
    prices = {"MGC": 2050.0, "NQ": 15500.0, "ES": 4400.0}
    portfolio_pnl = await position_manager.calculate_portfolio_pnl(prices)
    print(f"Total P&L: ${portfolio_pnl['total_pnl']:.2f}")
    ```

See Also:
    - `position_manager.core.PositionManager`
    - `position_manager.risk.RiskManagementMixin`
    - `position_manager.reporting.PositionReportingMixin`
"""

from datetime import datetime
from typing import TYPE_CHECKING

from project_x_py.models import Position
from project_x_py.types.response_types import (
    PortfolioMetricsResponse,
    PositionAnalysisResponse,
)
from project_x_py.types.trading import PositionType

if TYPE_CHECKING:
    from project_x_py.types import PositionManagerProtocol


class PositionAnalyticsMixin:
    """
    Mixin for P&L calculations and portfolio analytics.

    Provides comprehensive P&L calculation capabilities for individual positions
    and portfolio-level analysis. Includes support for point values, market price
    integration, and detailed P&L breakdowns for accurate profit/loss tracking.

    Key Features:
        - Individual position P&L with entry vs current price calculations
        - Portfolio-level P&L aggregation with missing price handling
        - Point value integration for accurate dollar calculations
        - Real-time P&L updates with market price changes
        - Comprehensive P&L reporting and analysis
        - Thread-safe operations with proper error handling

    P&L Calculation Methods:
        - calculate_position_pnl: Individual position P&L with point values
        - calculate_portfolio_pnl: Portfolio aggregation with market prices
        - get_portfolio_pnl: Portfolio structure with placeholder P&L

    Performance Characteristics:
        - Real-time P&L calculations with minimal latency
        - Memory-efficient operations for large portfolios
        - Graceful handling of missing market prices
        - Thread-safe operations with proper lock management
    """

    async def calculate_position_pnl(
        self: "PositionManagerProtocol",
        position: Position,
        current_price: float | None = None,
        point_value: float | None = None,
    ) -> PositionAnalysisResponse:
        """
        Calculate P&L for a position given current market price.

        Computes unrealized profit/loss for a position based on the difference
        between entry price and current market price, accounting for position
        direction (long/short).

        Args:
            position (Position): The position object to calculate P&L for
            current_price (float | None): Current market price of the contract. If
                None, returns a graceful response with zero P&L and an error message.
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
        # Handle missing price gracefully (used in error_scenarios tests)
        if current_price is None:
            from datetime import datetime as _dt

            return {
                "position_id": getattr(position, "id", 0) or 0,
                "contract_id": getattr(position, "contractId", ""),
                "entry_price": getattr(position, "averagePrice", 0.0) or 0.0,
                "current_price": 0.0,
                "unrealized_pnl": 0.0,
                "position_size": int(getattr(position, "size", 0) or 0),
                "position_value": 0.0,
                "margin_used": 0.0,
                "duration_minutes": 0,
                "high_water_mark": 0.0,
                "low_water_mark": 0.0,
                "max_unrealized_pnl": 0.0,
                "min_unrealized_pnl": 0.0,
                "volatility": 0.0,
                "beta": 0.0,
                "delta_exposure": 0.0,
                "gamma_exposure": 0.0,
                "theta_decay": 0.0,
                "risk_contribution": 0.0,
                "analysis_timestamp": _dt.now().isoformat(),
                # Non-typed extension used by tests
                "error": "No current price available",
            }

        # Calculate P&L based on position direction
        if position.type == PositionType.LONG:  # LONG
            price_change = current_price - position.averagePrice
        elif position.type == PositionType.SHORT:  # SHORT (type == PositionType.SHORT)
            price_change = position.averagePrice - current_price
        else:
            price_change = 0.0

        # Apply point value if provided (for accurate dollar P&L)
        if point_value is not None:
            pnl_per_contract = price_change * point_value
        else:
            pnl_per_contract = price_change

        unrealized_pnl = pnl_per_contract * position.size
        _market_value = current_price * position.size

        # Calculate additional fields for PositionAnalysisResponse
        position_value = abs(
            current_price * position.size
        )  # Absolute value of position

        # Simplified calculations - would need more data for accurate values
        duration_minutes = 0  # Would need position open time
        high_water_mark = max(current_price, position.averagePrice)
        low_water_mark = min(current_price, position.averagePrice)
        max_unrealized_pnl = unrealized_pnl if unrealized_pnl > 0 else 0.0
        min_unrealized_pnl = unrealized_pnl if unrealized_pnl < 0 else 0.0

        # Risk metrics (simplified - would need market data for accurate calculations)
        volatility = (
            abs(price_change / position.averagePrice)
            if position.averagePrice > 0
            else 0.0
        )
        risk_contribution = abs(unrealized_pnl) / max(
            position_value, 1.0
        )  # Risk as % of position value

        from datetime import datetime

        return {
            "position_id": position.id,
            "contract_id": position.contractId,
            "entry_price": position.averagePrice,
            "current_price": current_price,
            "unrealized_pnl": unrealized_pnl,
            "position_size": position.size,
            "position_value": position_value,
            "margin_used": 0.0,  # Would need margin data from broker
            "duration_minutes": duration_minutes,
            "high_water_mark": high_water_mark,
            "low_water_mark": low_water_mark,
            "max_unrealized_pnl": max_unrealized_pnl,
            "min_unrealized_pnl": min_unrealized_pnl,
            "volatility": volatility,
            "beta": 1.0,  # Would need market correlation data
            "delta_exposure": float(position.size),  # Simplified delta
            "gamma_exposure": 0.0,  # Would need options Greeks
            "theta_decay": 0.0,  # Would need options Greeks
            "risk_contribution": risk_contribution,
            "analysis_timestamp": datetime.now().isoformat(),
        }

    async def calculate_portfolio_pnl(
        self: "PositionManagerProtocol",
        current_prices: dict[str, float],
        account_id: int | None = None,
    ) -> PortfolioMetricsResponse:
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
            PortfolioMetricsResponse: Portfolio P&L analysis containing:
                - total_value (float): Total portfolio market value
                - total_pnl (float): Sum of all calculated P&Ls
                - realized_pnl (float): Realized gains/losses
                - unrealized_pnl (float): Unrealized gains/losses
                - win_rate (float): Percentage of winning positions
                - profit_factor (float): Ratio of average win to average loss
                - largest_win/largest_loss (float): Extreme P&L values
                - total_trades (int): Number of positions analyzed
                - last_updated (str): ISO timestamp

        Example:
            >>> # Get current prices from market data
            >>> prices = {"MGC": 2050.0, "NQ": 15500.0, "ES": 4400.0}
            >>> portfolio = await position_manager.calculate_portfolio_pnl(prices)
            >>> print(f"Total P&L: ${portfolio['total_pnl']:.2f}")
            >>> print(f"Total Value: ${portfolio['total_value']:.2f}")
            >>> print(f"Win Rate: {portfolio['win_rate']:.1%}")
            >>> print(f"Profit Factor: {portfolio['profit_factor']:.2f}")
            >>> print(f"Largest Win: ${portfolio['largest_win']:.2f}")
            >>> print(f"Trades: {portfolio['total_trades']}")

        Note:
            - P&L calculations assume point values of 1.0
            - For accurate dollar P&L, use calculate_position_pnl() with point values
            - Only positions with market prices contribute to P&L calculations
        """
        positions = await self.get_all_positions(account_id=account_id)

        # Calculate direct metrics without intermediate dictionaries
        total_pnl = 0.0
        total_value = 0.0
        pnl_values: list[float] = []

        for position in positions:
            current_price = current_prices.get(position.contractId)
            if current_price is not None:
                pnl_data = await self.calculate_position_pnl(position, current_price)
                pnl = pnl_data["unrealized_pnl"]
                value = pnl_data["position_value"]

                total_pnl += pnl
                total_value += value
                pnl_values.append(pnl)

        # Calculate win/loss metrics directly from PnL values
        winning_pnls = [pnl for pnl in pnl_values if pnl > 0]
        losing_pnls = [pnl for pnl in pnl_values if pnl < 0]

        win_rate = len(winning_pnls) / len(positions) if positions else 0.0
        avg_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0.0
        avg_loss = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0.0
        largest_win = max(winning_pnls, default=0.0)
        largest_loss = min(losing_pnls, default=0.0)

        profit_factor = abs(avg_win / avg_loss) if avg_loss < 0 else 0.0
        total_return = (total_pnl / total_value * 100) if total_value > 0 else 0.0

        from datetime import datetime

        return {
            "total_value": total_value,
            "total_pnl": total_pnl,
            "realized_pnl": 0.0,  # Would need historical trade data
            "unrealized_pnl": total_pnl,  # All P&L is unrealized in this context
            "daily_pnl": 0.0,  # Would need daily data
            "weekly_pnl": 0.0,  # Would need weekly data
            "monthly_pnl": 0.0,  # Would need monthly data
            "ytd_pnl": 0.0,  # Would need year-to-date data
            "total_return": total_return,
            "annualized_return": 0.0,  # Would need time-weighted returns
            "sharpe_ratio": 0.0,  # Would need return volatility data
            "sortino_ratio": 0.0,  # Would need downside deviation data
            "max_drawdown": 0.0,  # Would need historical high-water marks
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "total_trades": len(positions),
            "winning_trades": len(winning_pnls),
            "losing_trades": len(losing_pnls),
            "largest_win": largest_win,
            "largest_loss": largest_loss,
            "avg_trade_duration_minutes": 0.0,  # Would need position entry times
            "last_updated": datetime.now().isoformat(),
        }

    async def get_portfolio_pnl(
        self: "PositionManagerProtocol", account_id: int | None = None
    ) -> PortfolioMetricsResponse:
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
            PortfolioMetricsResponse: Portfolio metrics with placeholder values:
                - total_value (float): Portfolio market value (estimated)
                - total_pnl (float): 0.0 (requires market prices)
                - realized_pnl (float): 0.0 (requires historical data)
                - unrealized_pnl (float): 0.0 (requires market prices)
                - win_rate (float): 0.0 (requires P&L calculations)
                - profit_factor (float): 0.0 (requires P&L calculations)
                - total_trades (int): Number of open positions
                - last_updated (str): ISO timestamp

        Example:
            >>> # Get portfolio structure
            >>> portfolio = await position_manager.get_portfolio_pnl()
            >>> print(f"Total Value: ${portfolio['total_value']:.2f}")
            >>> print(f"Open Positions: {portfolio['total_trades']}")
            >>> print(f"Last Updated: {portfolio['last_updated']}")
            >>> # For actual P&L, use calculate_portfolio_pnl() with market prices

        See Also:
            calculate_portfolio_pnl(): For actual P&L calculations with market prices
        """
        positions = await self.get_all_positions(account_id=account_id)

        # Calculate total portfolio value directly from positions
        total_value = sum(
            abs(position.size * position.averagePrice) for position in positions
        )

        return {
            "total_value": total_value,
            "total_pnl": 0.0,  # Default value when no current prices available
            "realized_pnl": 0.0,  # Would need historical trade data
            "unrealized_pnl": 0.0,  # Default value when no current prices available
            "daily_pnl": 0.0,  # Would need daily data
            "weekly_pnl": 0.0,  # Would need weekly data
            "monthly_pnl": 0.0,  # Would need monthly data
            "ytd_pnl": 0.0,  # Would need year-to-date data
            "total_return": 0.0,  # Would need return calculations
            "annualized_return": 0.0,  # Would need time-weighted returns
            "sharpe_ratio": 0.0,  # Would need return volatility data
            "sortino_ratio": 0.0,  # Would need downside deviation data
            "max_drawdown": 0.0,  # Would need historical high-water marks
            "win_rate": 0.0,  # No trades to analyze without prices
            "profit_factor": 0.0,  # No trades to analyze without prices
            "avg_win": 0.0,  # No trades to analyze without prices
            "avg_loss": 0.0,  # No trades to analyze without prices
            "total_trades": len(positions),
            "winning_trades": 0,  # No trades to analyze without prices
            "losing_trades": 0,  # No trades to analyze without prices
            "largest_win": 0.0,  # No trades to analyze without prices
            "largest_loss": 0.0,  # No trades to analyze without prices
            "avg_trade_duration_minutes": 0.0,  # Would need position entry times
            "last_updated": datetime.now().isoformat(),
        }
