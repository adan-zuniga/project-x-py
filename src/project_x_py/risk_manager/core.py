"""Core risk management functionality."""

import asyncio
import logging
import statistics
from collections import deque
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from project_x_py.exceptions import InvalidOrderParameters
from project_x_py.types import (
    OrderSide,
    OrderType,
    PositionSizingResponse,
    RiskAnalysisResponse,
    RiskValidationResponse,
)
from project_x_py.types.protocols import (
    OrderManagerProtocol,
    PositionManagerProtocol,
    ProjectXClientProtocol,
)

from .config import RiskConfig

if TYPE_CHECKING:
    from project_x_py.event_bus import EventBus
    from project_x_py.models import Account, Instrument, Order, Position

logger = logging.getLogger(__name__)


class RiskManager:
    """Comprehensive risk management system for trading.

    Handles position sizing, risk validation, stop-loss management,
    and portfolio risk monitoring.
    """

    def __init__(
        self,
        project_x: ProjectXClientProtocol,
        order_manager: OrderManagerProtocol,
        position_manager: PositionManagerProtocol,
        event_bus: "EventBus",
        config: RiskConfig | None = None,
    ):
        """Initialize risk manager.

        Args:
            project_x: ProjectX client instance
            order_manager: Order manager instance
            position_manager: Position manager instance
            event_bus: Event bus for risk events
            config: Risk configuration (uses defaults if not provided)
        """
        self.client = project_x
        self.orders = order_manager
        self.positions = position_manager
        self.event_bus = event_bus
        self.config = config or RiskConfig()

        # Track daily losses and trades
        self._daily_loss = Decimal("0")
        self._daily_trades = 0
        self._last_reset_date = datetime.now().date()

        # Track trade history for Kelly criterion
        self._trade_history: deque[dict[str, Any]] = deque(maxlen=100)
        self._win_rate = 0.0
        self._avg_win = Decimal("0")
        self._avg_loss = Decimal("0")

        # Track current risk exposure
        self._current_risk = Decimal("0")
        self._max_drawdown = Decimal("0")

    async def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        risk_amount: float | None = None,
        risk_percent: float | None = None,
        instrument: Optional["Instrument"] = None,
        use_kelly: bool | None = None,
    ) -> PositionSizingResponse:
        """Calculate optimal position size based on risk parameters.

        Args:
            entry_price: Planned entry price
            stop_loss: Stop loss price
            risk_amount: Fixed dollar amount to risk (overrides percentage)
            risk_percent: Percentage of account to risk (default from config)
            instrument: Instrument for tick size calculation
            use_kelly: Override config to use/not use Kelly criterion

        Returns:
            PositionSizingResponse with calculated size and risk metrics
        """
        try:
            # Get account info
            account = await self._get_account_info()
            account_balance = float(account.balance)

            # Reset daily counters if needed
            self._check_daily_reset()

            # Determine risk amount
            if risk_amount is None:
                risk_percent = risk_percent or self.config.max_risk_per_trade
                risk_amount = account_balance * risk_percent

            # Apply maximum risk limits
            if self.config.max_risk_per_trade_amount:
                risk_amount = min(risk_amount, self.config.max_risk_per_trade_amount)

            # Calculate price difference and position size
            price_diff = abs(entry_price - stop_loss)
            if price_diff == 0:
                raise InvalidOrderParameters(
                    "Entry and stop loss prices cannot be equal"
                )

            # Basic position size calculation
            position_size = int(risk_amount / price_diff)

            # Apply Kelly criterion if enabled
            if (
                use_kelly or (use_kelly is None and self.config.use_kelly_criterion)
            ) and len(self._trade_history) >= self.config.min_trades_for_kelly:
                kelly_size = self._calculate_kelly_size(
                    position_size, account_balance, entry_price
                )
                position_size = min(position_size, kelly_size)

            # Apply position size limits
            position_size = min(position_size, self.config.max_position_size)

            # Calculate actual risk
            actual_risk = position_size * price_diff
            actual_risk_percent = actual_risk / account_balance

            # Get tick size for the instrument
            tick_size = 0.25  # Default
            if instrument:
                tick_size = float(instrument.tickSize)

            return PositionSizingResponse(
                position_size=position_size,
                risk_amount=actual_risk,
                risk_percent=actual_risk_percent,
                entry_price=entry_price,
                stop_loss=stop_loss,
                tick_size=tick_size,
                account_balance=account_balance,
                kelly_fraction=self._calculate_kelly_fraction()
                if self.config.use_kelly_criterion
                else None,
                max_position_size=self.config.max_position_size,
                sizing_method="kelly" if use_kelly else "fixed_risk",
            )

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            raise

    async def validate_trade(
        self,
        order: "Order",
        current_positions: list["Position"] | None = None,
    ) -> RiskValidationResponse:
        """Validate a trade against risk rules.

        Args:
            order: Order to validate
            current_positions: Current positions (fetched if not provided)

        Returns:
            RiskValidationResponse with validation result and reasons
        """
        try:
            reasons = []
            warnings = []
            is_valid = True

            # Get current positions if not provided
            if current_positions is None:
                current_positions = await self.positions.get_all_positions()

            # Check daily trade limit
            if self._daily_trades >= self.config.max_daily_trades:
                is_valid = False
                reasons.append(
                    f"Daily trade limit reached ({self.config.max_daily_trades})"
                )

            # Check maximum positions
            if len(current_positions) >= self.config.max_positions:
                is_valid = False
                reasons.append(
                    f"Maximum positions limit reached ({self.config.max_positions})"
                )

            # Check position size limit
            if order.size > self.config.max_position_size:
                is_valid = False
                reasons.append(
                    f"Position size exceeds limit ({self.config.max_position_size})"
                )

            # Check daily loss limit
            account = await self._get_account_info()
            account_balance = float(account.balance)

            if self.config.max_daily_loss_amount:
                if float(self._daily_loss) >= self.config.max_daily_loss_amount:
                    is_valid = False
                    reasons.append(
                        f"Daily loss limit reached (${self.config.max_daily_loss_amount})"
                    )
            else:
                daily_loss_percent = float(self._daily_loss) / account_balance
                if daily_loss_percent >= self.config.max_daily_loss:
                    is_valid = False
                    reasons.append(
                        f"Daily loss limit reached ({self.config.max_daily_loss * 100}%)"
                    )

            # Check portfolio risk
            total_risk = await self._calculate_portfolio_risk(current_positions)
            if total_risk > self.config.max_portfolio_risk:
                warnings.append(
                    f"Portfolio risk high ({total_risk * 100:.1f}% vs "
                    f"{self.config.max_portfolio_risk * 100}% limit)"
                )

            # Check trading hours if restricted
            if (
                self.config.restrict_trading_hours
                and not self._is_within_trading_hours()
            ):
                is_valid = False
                reasons.append("Outside allowed trading hours")

            # Check for correlated positions
            correlated_count = await self._count_correlated_positions(
                order.contractId, current_positions
            )
            if correlated_count >= self.config.max_correlated_positions:
                warnings.append(
                    f"Multiple correlated positions ({correlated_count} positions)"
                )

            return RiskValidationResponse(
                is_valid=is_valid,
                reasons=reasons,
                warnings=warnings,
                current_risk=float(self._current_risk),
                daily_loss=float(self._daily_loss),
                daily_trades=self._daily_trades,
                position_count=len(current_positions),
                portfolio_risk=total_risk,
            )

        except Exception as e:
            logger.error(f"Error validating trade: {e}")
            return RiskValidationResponse(
                is_valid=False,
                reasons=[f"Validation error: {e!s}"],
                warnings=[],
                current_risk=0.0,
                daily_loss=0.0,
                daily_trades=0,
                position_count=0,
                portfolio_risk=0.0,
            )

    async def attach_risk_orders(
        self,
        position: "Position",
        stop_loss: float | None = None,
        take_profit: float | None = None,
        use_trailing: bool | None = None,
    ) -> dict[str, Any]:
        """Automatically attach stop-loss and take-profit orders to a position.

        Args:
            position: Position to protect
            stop_loss: Override stop loss price
            take_profit: Override take profit price
            use_trailing: Override trailing stop configuration

        Returns:
            Dictionary with attached order details
        """
        try:
            instrument = await self.client.get_instrument(position.contractId)
            tick_size = float(instrument.tickSize)

            # Determine position direction
            is_long = position.is_long
            position_size = position.size
            entry_price = float(position.averagePrice)

            # Calculate stop loss if not provided
            if stop_loss is None and self.config.use_stop_loss:
                if self.config.stop_loss_type == "fixed":
                    stop_distance = self.config.default_stop_distance * tick_size
                elif self.config.stop_loss_type == "atr":
                    # TODO: Get ATR from data manager
                    stop_distance = self.config.default_stop_distance * tick_size
                else:  # percentage
                    stop_distance = entry_price * (
                        self.config.default_stop_distance / 100
                    )

                stop_loss = (
                    entry_price - stop_distance
                    if is_long
                    else entry_price + stop_distance
                )

            # Calculate take profit if not provided
            if take_profit is None and self.config.use_take_profit and stop_loss:
                risk = abs(entry_price - stop_loss)
                reward = risk * self.config.default_risk_reward_ratio
                take_profit = entry_price + reward if is_long else entry_price - reward

            # Place bracket order
            # For an existing position, we need to place exit orders
            # These are opposite side to the position
            exit_side = OrderSide.SELL if is_long else OrderSide.BUY

            # Place stop loss order
            stop_response = None
            if stop_loss:
                stop_response = await self.orders.place_stop_order(
                    contract_id=position.contractId,
                    side=exit_side,
                    size=position_size,
                    stop_price=stop_loss,
                )

            # Place take profit order
            target_response = None
            if take_profit:
                target_response = await self.orders.place_limit_order(
                    contract_id=position.contractId,
                    side=exit_side,
                    size=position_size,
                    limit_price=take_profit,
                )

            # Create bracket response structure
            from project_x_py.models import BracketOrderResponse

            bracket_response = BracketOrderResponse(
                success=bool(stop_response or target_response),
                entry_order_id=None,  # No entry for existing position
                stop_order_id=stop_response.orderId
                if stop_response and stop_response.success
                else None,
                target_order_id=target_response.orderId
                if target_response and target_response.success
                else None,
                entry_price=entry_price,
                stop_loss_price=stop_loss or 0.0,
                take_profit_price=take_profit or 0.0,
                entry_response=None,
                stop_response=stop_response,
                target_response=target_response,
                error_message=None,
            )

            # Setup trailing stop if configured
            use_trailing = (
                use_trailing
                if use_trailing is not None
                else self.config.use_trailing_stops
            )
            if use_trailing and self.config.trailing_stop_distance > 0:
                # Monitor position for trailing stop activation
                _trailing_task = asyncio.create_task(  # noqa: RUF006
                    self._monitor_trailing_stop(
                        position,
                        {
                            "stop_order_id": bracket_response.stop_order_id,
                            "target_order_id": bracket_response.target_order_id,
                        },
                    )
                )

            # Emit risk order placed event
            await self.event_bus.emit(
                "risk_orders_placed",
                {
                    "position": position,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "bracket_order": bracket_response,
                    "use_trailing": use_trailing,
                },
            )

            return {
                "position_id": position.id,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "bracket_order": bracket_response,
                "use_trailing": use_trailing,
                "risk_reward_ratio": self.config.default_risk_reward_ratio,
            }

        except Exception as e:
            logger.error(f"Error attaching risk orders: {e}")
            raise

    async def adjust_stops(
        self,
        position: "Position",
        new_stop: float,
        order_id: str | None = None,
    ) -> bool:
        """Adjust stop-loss order for a position.

        Args:
            position: Position to adjust
            new_stop: New stop loss price
            order_id: Specific order ID to modify (finds it if not provided)

        Returns:
            True if adjustment successful
        """
        try:
            # Find stop order if not provided
            if order_id is None:
                orders = await self.orders.search_open_orders()
                stop_orders = [
                    o
                    for o in orders
                    if o.contractId == position.contractId
                    and o.type in [4, 3]  # STOP=4, STOP_LIMIT=3
                    and o.side
                    != (OrderSide.BUY if position.is_long else OrderSide.SELL)
                ]

                if not stop_orders:
                    logger.warning(f"No stop order found for position {position.id}")
                    return False

                order_id = str(stop_orders[0].id)

            # Modify the order
            success = await self.orders.modify_order(
                order_id=int(order_id),
                stop_price=new_stop,
            )

            if success:
                await self.event_bus.emit(
                    "stop_adjusted",
                    {
                        "position": position,
                        "new_stop": new_stop,
                        "order_id": order_id,
                    },
                )

            return success

        except Exception as e:
            logger.error(f"Error adjusting stop: {e}")
            return False

    async def get_risk_metrics(self) -> RiskAnalysisResponse:
        """Get current risk metrics and analysis.

        Returns:
            Comprehensive risk analysis
        """
        try:
            account = await self._get_account_info()
            positions = await self.positions.get_all_positions()

            # Calculate metrics
            _total_risk = await self._calculate_portfolio_risk(positions)
            position_risks = []

            for pos in positions:
                risk = await self._calculate_position_risk(pos)
                position_risks.append(
                    {
                        "position_id": pos.id,
                        "symbol": self._extract_symbol(pos.contractId),
                        "risk_amount": float(risk["amount"]),
                        "risk_percent": float(risk["percent"]),
                    }
                )

            return RiskAnalysisResponse(
                current_risk=float(self._current_risk),
                max_risk=self.config.max_portfolio_risk,
                daily_loss=float(self._daily_loss),
                daily_loss_limit=self.config.max_daily_loss,
                position_count=len(positions),
                position_limit=self.config.max_positions,
                daily_trades=self._daily_trades,
                daily_trade_limit=self.config.max_daily_trades,
                win_rate=self._win_rate,
                profit_factor=self._calculate_profit_factor(),
                sharpe_ratio=self._calculate_sharpe_ratio(),
                max_drawdown=float(self._max_drawdown),
                position_risks=position_risks,
                risk_per_trade=self.config.max_risk_per_trade,
                account_balance=float(account.balance),
                margin_used=0.0,  # Not available in Account model
                margin_available=float(account.balance),  # Simplified
            )

        except Exception as e:
            logger.error(f"Error getting risk metrics: {e}")
            raise

    # Helper methods

    async def _get_account_info(self) -> "Account":
        """Get current account information."""
        accounts = await self.client.list_accounts()
        if accounts:
            return accounts[0]
        # Create a default account if none found
        from project_x_py.models import Account

        return Account(
            id=0,
            name="Default",
            balance=10000.0,
            canTrade=True,
            isVisible=True,
            simulated=True,
        )

    def _check_daily_reset(self) -> None:
        """Reset daily counters if new day."""
        current_date = datetime.now().date()
        if current_date > self._last_reset_date:
            self._daily_loss = Decimal("0")
            self._daily_trades = 0
            self._last_reset_date = current_date

    def _calculate_kelly_fraction(self) -> float:
        """Calculate Kelly criterion fraction."""
        if self._win_rate == 0 or self._avg_loss == 0:
            return 0.0

        # Kelly formula: f = (p * b - q) / b
        # where p = win rate, q = loss rate, b = avg win / avg loss
        p = self._win_rate
        q = 1 - p
        b = float(self._avg_win / self._avg_loss) if self._avg_loss > 0 else 0

        if b == 0:
            return 0.0

        kelly = (p * b - q) / b

        # Apply Kelly fraction from config (partial Kelly)
        return max(0, min(kelly * self.config.kelly_fraction, 0.25))

    def _calculate_kelly_size(
        self,
        base_size: int,
        account_balance: float,
        entry_price: float,
    ) -> int:
        """Calculate position size using Kelly criterion."""
        kelly_fraction = self._calculate_kelly_fraction()
        if kelly_fraction <= 0:
            return base_size

        # Calculate Kelly-adjusted position value
        kelly_value = account_balance * kelly_fraction
        kelly_size = int(kelly_value / entry_price)

        return min(base_size, kelly_size)

    async def _calculate_portfolio_risk(self, positions: list["Position"]) -> float:
        """Calculate total portfolio risk."""
        if not positions:
            return 0.0

        account = await self._get_account_info()
        account_balance = float(account.balance)

        total_risk = Decimal("0")
        for pos in positions:
            risk = await self._calculate_position_risk(pos)
            total_risk += risk["amount"]

        return float(total_risk / Decimal(str(account_balance)))

    async def _calculate_position_risk(
        self, position: "Position"
    ) -> dict[str, Decimal]:
        """Calculate risk for a single position."""
        # Find stop loss order
        orders: list[Order] = await self.orders.search_open_orders()
        stop_orders = [
            o
            for o in orders
            if o.contractId == position.contractId
            and o.type in [OrderType.STOP, OrderType.STOP_LIMIT]
        ]

        if stop_orders:
            stop_price_value = stop_orders[0].stopPrice or stop_orders[0].limitPrice
            if stop_price_value is not None:
                stop_price = float(stop_price_value)
                risk = abs(float(position.averagePrice) - stop_price) * position.size
            else:
                # Use default stop distance if no valid stop price
                risk = self.config.default_stop_distance * position.size
        else:
            # Use default stop distance if no stop order
            risk = self.config.default_stop_distance * position.size

        account = await self._get_account_info()
        risk_percent = risk / float(account.balance)

        return {
            "amount": Decimal(str(risk)),
            "percent": Decimal(str(risk_percent)),
        }

    def _is_within_trading_hours(self) -> bool:
        """Check if current time is within allowed trading hours."""
        if not self.config.restrict_trading_hours:
            return True

        now = datetime.now().time()
        for start_str, end_str in self.config.allowed_trading_hours:
            start = datetime.strptime(start_str, "%H:%M").time()
            end = datetime.strptime(end_str, "%H:%M").time()

            if start <= now <= end:
                return True

        return False

    async def _count_correlated_positions(
        self,
        contract_id: str,
        positions: list["Position"],
    ) -> int:
        """Count positions in correlated instruments."""
        # For now, simple implementation - count positions in same base symbol
        base_symbol = self._extract_symbol(contract_id)

        count = 0
        for pos in positions:
            if self._extract_symbol(pos.contractId) == base_symbol:
                count += 1

        return count

    def _extract_symbol(self, contract_id: str) -> str:
        """Extract base symbol from contract ID."""
        # Example: "CON.F.US.MNQ.U24" -> "MNQ"
        parts = contract_id.split(".")
        return parts[3] if len(parts) > 3 else contract_id

    async def _monitor_trailing_stop(
        self,
        position: "Position",
        bracket_order: dict[str, Any],
    ) -> None:
        """Monitor position for trailing stop activation."""
        try:
            is_long = position.is_long
            entry_price = float(position.averagePrice)

            while True:
                # Get current price
                current_positions = await self.positions.get_all_positions()
                current_pos = next(
                    (p for p in current_positions if p.id == position.id), None
                )

                if not current_pos:
                    # Position closed
                    break

                # Check if trailing should activate
                current_price = float(current_pos.averagePrice)
                profit = (
                    (current_price - entry_price)
                    if is_long
                    else (entry_price - current_price)
                )

                if profit >= self.config.trailing_stop_trigger:
                    # Adjust stop to trail
                    new_stop = (
                        current_price - self.config.trailing_stop_distance
                        if is_long
                        else current_price + self.config.trailing_stop_distance
                    )

                    await self.adjust_stops(current_pos, new_stop)

                await asyncio.sleep(5)  # Check every 5 seconds

        except Exception as e:
            logger.error(f"Error monitoring trailing stop: {e}")

    def _calculate_profit_factor(self) -> float:
        """Calculate profit factor from trade history."""
        if not self._trade_history:
            return 0.0

        gross_profit = sum(t["pnl"] for t in self._trade_history if t["pnl"] > 0)
        gross_loss = abs(sum(t["pnl"] for t in self._trade_history if t["pnl"] < 0))

        return gross_profit / gross_loss if gross_loss > 0 else 0.0

    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio from trade history."""
        if len(self._trade_history) < 2:
            return 0.0

        returns = [t["pnl"] for t in self._trade_history]
        if not returns:
            return 0.0

        avg_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)

        if std_return == 0:
            return 0.0

        # Annualized Sharpe (assuming daily returns and 252 trading days)
        sharpe_ratio: float = (avg_return / std_return) * (252**0.5)
        return sharpe_ratio

    async def record_trade_result(
        self,
        position_id: str,
        pnl: float,
        duration_seconds: int,
    ) -> None:
        """Record trade result for risk analysis.

        Args:
            position_id: Position identifier
            pnl: Profit/loss amount
            duration_seconds: Trade duration
        """
        self._trade_history.append(
            {
                "position_id": position_id,
                "pnl": pnl,
                "duration": duration_seconds,
                "timestamp": datetime.now(),
            }
        )

        # Update statistics
        self._update_trade_statistics()

        # Update daily loss
        if pnl < 0:
            self._daily_loss += Decimal(str(abs(pnl)))

        # Increment daily trades
        self._daily_trades += 1

        # Emit event
        await self.event_bus.emit(
            "trade_recorded",
            {
                "position_id": position_id,
                "pnl": pnl,
                "duration": duration_seconds,
                "daily_loss": float(self._daily_loss),
                "daily_trades": self._daily_trades,
            },
        )

    def _update_trade_statistics(self) -> None:
        """Update win rate and average win/loss statistics."""
        if not self._trade_history:
            return

        wins = [t for t in self._trade_history if t["pnl"] > 0]
        losses = [t for t in self._trade_history if t["pnl"] < 0]

        self._win_rate = (
            len(wins) / len(self._trade_history) if self._trade_history else 0
        )
        self._avg_win = (
            Decimal(str(statistics.mean([t["pnl"] for t in wins])))
            if wins
            else Decimal("0")
        )
        self._avg_loss = (
            Decimal(str(abs(statistics.mean([t["pnl"] for t in losses]))))
            if losses
            else Decimal("0")
        )
