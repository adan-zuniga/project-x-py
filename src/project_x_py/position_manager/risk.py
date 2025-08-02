"""Risk metrics and position sizing functionality."""

from typing import TYPE_CHECKING, Any

from project_x_py.models import Position

if TYPE_CHECKING:
    from project_x_py.position_manager.types import PositionManagerProtocol


class RiskManagementMixin:
    """Mixin for risk metrics and position sizing."""

    async def get_risk_metrics(
        self: "PositionManagerProtocol", account_id: int | None = None
    ) -> dict[str, Any]:
        """
        Calculate portfolio risk metrics and concentration analysis.

        Analyzes portfolio composition, exposure concentration, and generates risk
        warnings based on configured thresholds. Provides insights for risk management
        and position sizing decisions.

        Args:
            account_id (int, optional): The account ID to analyze.
                If None, uses the default account from authentication.
                Defaults to None.

        Returns:
            dict[str, Any]: Comprehensive risk analysis containing:
                - portfolio_risk (float): Overall portfolio risk score (0.0-1.0)
                - largest_position_risk (float): Concentration in largest position
                - total_exposure (float): Sum of all position values
                - position_count (int): Number of open positions
                - diversification_score (float): Portfolio diversification (0.0-1.0)
                - risk_warnings (list[str]): Generated warnings based on thresholds

        Risk thresholds (configurable via self.risk_settings):
            - max_portfolio_risk: 2% default
            - max_position_risk: 1% default
            - max_correlation: 0.7 default
            - alert_threshold: 0.5% default

        Example:
            >>> # Analyze portfolio risk
            >>> risk_metrics = await position_manager.get_risk_metrics()
            >>> print(f"Portfolio risk: {risk_metrics['portfolio_risk']:.2%}")
            >>> print(f"Largest position: {risk_metrics['largest_position_risk']:.2%}")
            >>> print(f"Diversification: {risk_metrics['diversification_score']:.2f}")
            >>> # Check for warnings
            >>> if risk_metrics["risk_warnings"]:
            ...     print("\nRisk Warnings:")
            ...     for warning in risk_metrics["risk_warnings"]:
            ...         print(f"  ⚠️  {warning}")

        Note:
            - P&L-based risk metrics require current market prices
            - Diversification score: 1.0 = well diversified, 0.0 = concentrated
            - Empty portfolio returns zero risk with perfect diversification
        """
        positions = await self.get_all_positions(account_id=account_id)

        if not positions:
            return {
                "portfolio_risk": 0.0,
                "largest_position_risk": 0.0,
                "total_exposure": 0.0,
                "position_count": 0,
                "diversification_score": 1.0,
            }

        total_exposure = sum(abs(pos.size * pos.averagePrice) for pos in positions)
        largest_exposure = (
            max(abs(pos.size * pos.averagePrice) for pos in positions)
            if positions
            else 0.0
        )

        # Calculate basic risk metrics (note: P&L-based risk requires market prices)
        portfolio_risk = (
            0.0  # Would need current market prices to calculate P&L-based risk
        )
        largest_position_risk = (
            largest_exposure / total_exposure if total_exposure > 0 else 0.0
        )

        # Simple diversification score (inverse of concentration)
        diversification_score = (
            1.0 - largest_position_risk if largest_position_risk < 1.0 else 0.0
        )

        return {
            "portfolio_risk": portfolio_risk,
            "largest_position_risk": largest_position_risk,
            "total_exposure": total_exposure,
            "position_count": len(positions),
            "diversification_score": diversification_score,
            "risk_warnings": self._generate_risk_warnings(
                positions, portfolio_risk, largest_position_risk
            ),
        }

    def _generate_risk_warnings(
        self: "PositionManagerProtocol",
        positions: list[Position],
        portfolio_risk: float,
        largest_position_risk: float,
    ) -> list[str]:
        """
        Generate risk warnings based on current portfolio state.

        Analyzes portfolio metrics against configured risk thresholds and generates
        actionable warnings for risk management.

        Args:
            positions (list[Position]): Current open positions
            portfolio_risk (float): Calculated portfolio risk (0.0-1.0)
            largest_position_risk (float): Largest position concentration (0.0-1.0)

        Returns:
            list[str]: List of warning messages, empty if no issues detected

        Warning conditions:
            - Portfolio risk exceeds max_portfolio_risk setting
            - Largest position exceeds max_position_risk setting
            - Single position portfolio (no diversification)
        """
        warnings = []

        if portfolio_risk > self.risk_settings["max_portfolio_risk"]:
            warnings.append(
                f"Portfolio risk ({portfolio_risk:.2%}) exceeds maximum ({self.risk_settings['max_portfolio_risk']:.2%})"
            )

        if largest_position_risk > self.risk_settings["max_position_risk"]:
            warnings.append(
                f"Largest position risk ({largest_position_risk:.2%}) exceeds maximum ({self.risk_settings['max_position_risk']:.2%})"
            )

        if len(positions) == 1:
            warnings.append("Portfolio lacks diversification (single position)")

        return warnings

    async def calculate_position_size(
        self: "PositionManagerProtocol",
        contract_id: str,
        risk_amount: float,
        entry_price: float,
        stop_price: float,
        account_balance: float | None = None,
    ) -> dict[str, Any]:
        """
        Calculate optimal position size based on risk parameters.

        Implements fixed-risk position sizing by calculating the maximum number
        of contracts that can be traded while limiting loss to the specified
        risk amount if the stop loss is hit.

        Args:
            contract_id (str): Contract to size position for (e.g., "MGC")
            risk_amount (float): Maximum dollar amount to risk on the trade
            entry_price (float): Planned entry price for the position
            stop_price (float): Stop loss price for risk management
            account_balance (float, optional): Account balance for risk percentage
                calculation. If None, retrieved from account info or defaults
                to $10,000. Defaults to None.

        Returns:
            dict[str, Any]: Position sizing analysis containing:
                - suggested_size (int): Recommended number of contracts
                - risk_per_contract (float): Dollar risk per contract
                - total_risk (float): Actual total risk with suggested size
                - risk_percentage (float): Risk as percentage of account
                - entry_price (float): Provided entry price
                - stop_price (float): Provided stop price
                - price_diff (float): Absolute price difference (risk in points)
                - contract_multiplier (float): Contract point value
                - account_balance (float): Account balance used
                - risk_warnings (list[str]): Risk management warnings
                - error (str): Error message if calculation fails

        Example:
            >>> # Size position for $500 risk on Gold
            >>> sizing = await position_manager.calculate_position_size(
            ...     "MGC", risk_amount=500.0, entry_price=2050.0, stop_price=2040.0
            ... )
            >>> print(f"Trade {sizing['suggested_size']} contracts")
            >>> print(
            ...     f"Risk: ${sizing['total_risk']:.2f} "
            ...     f"({sizing['risk_percentage']:.1f}% of account)"
            ... )
            >>> # With specific account balance
            >>> sizing = await position_manager.calculate_position_size(
            ...     "NQ",
            ...     risk_amount=1000.0,
            ...     entry_price=15500.0,
            ...     stop_price=15450.0,
            ...     account_balance=50000.0,
            ... )

        Formula:
            position_size = risk_amount / (price_diff x contract_multiplier)

        Warnings generated when:
            - Risk percentage exceeds max_position_risk setting
            - Calculated size is 0 (risk amount too small)
            - Size is unusually large (>10 contracts)
        """
        try:
            # Get account balance if not provided
            if account_balance is None:
                if self.project_x.account_info:
                    account_balance = self.project_x.account_info.balance
                else:
                    account_balance = 10000.0  # Default fallback

            # Calculate risk per contract
            price_diff = abs(entry_price - stop_price)
            if price_diff == 0:
                return {"error": "Entry price and stop price cannot be the same"}

            # Get instrument details for contract multiplier
            instrument = await self.project_x.get_instrument(contract_id)
            contract_multiplier = (
                getattr(instrument, "contractMultiplier", 1.0) if instrument else 1.0
            )

            risk_per_contract = price_diff * contract_multiplier
            suggested_size = (
                int(risk_amount / risk_per_contract) if risk_per_contract > 0 else 0
            )

            # Calculate risk metrics
            total_risk = suggested_size * risk_per_contract
            risk_percentage = (
                (total_risk / account_balance) * 100 if account_balance > 0 else 0.0
            )

            return {
                "suggested_size": suggested_size,
                "risk_per_contract": risk_per_contract,
                "total_risk": total_risk,
                "risk_percentage": risk_percentage,
                "entry_price": entry_price,
                "stop_price": stop_price,
                "price_diff": price_diff,
                "contract_multiplier": contract_multiplier,
                "account_balance": account_balance,
                "risk_warnings": self._generate_sizing_warnings(
                    risk_percentage, suggested_size
                ),
            }

        except Exception as e:
            self.logger.error(f"❌ Position sizing calculation failed: {e}")
            return {"error": str(e)}

    def _generate_sizing_warnings(
        self: "PositionManagerProtocol", risk_percentage: float, size: int
    ) -> list[str]:
        """
        Generate warnings for position sizing calculations.

        Evaluates calculated position size and risk percentage against thresholds
        to provide risk management guidance.

        Args:
            risk_percentage (float): Position risk as percentage of account (0-100)
            size (int): Calculated position size in contracts

        Returns:
            list[str]: Risk warnings, empty if sizing is appropriate

        Warning thresholds:
            - Risk percentage > max_position_risk setting
            - Size = 0 (risk amount insufficient)
            - Size > 10 contracts (arbitrary large position threshold)
        """
        warnings = []

        if risk_percentage > self.risk_settings["max_position_risk"] * 100:
            warnings.append(
                f"Risk percentage ({risk_percentage:.2f}%) exceeds recommended maximum"
            )

        if size == 0:
            warnings.append(
                "Calculated position size is 0 - risk amount may be too small"
            )

        if size > 10:  # Arbitrary large size threshold
            warnings.append(
                f"Large position size ({size} contracts) - consider reducing risk"
            )

        return warnings
