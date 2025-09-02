#!/usr/bin/env python
"""
Advanced risk management system with portfolio-level controls
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

from project_x_py import EventType, TradingSuite
from project_x_py.models import BracketOrderResponse


class AdvancedRiskManager:
    def __init__(self, suite: TradingSuite):
        self.suite = suite

        # Risk parameters
        self.max_risk_per_trade = Decimal("0.02")  # 2% per trade
        self.max_daily_risk = Decimal("0.06")  # 6% per day
        self.max_portfolio_risk = Decimal("0.20")  # 20% total portfolio
        self.max_positions = 3  # Maximum open positions

        # Tracking
        self.daily_pnl = Decimal("0")
        self.active_trades = []
        self.daily_reset_time = datetime.now().date()

    async def get_account_balance(self):
        """Get current account balance."""
        account_info = self.suite.client.get_account_info()
        return Decimal(str(account_info.balance))

    async def calculate_current_portfolio_risk(self):
        """Calculate current portfolio risk exposure."""
        positions = await self.suite["MNQ"].positions.get_all_positions()
        total_risk = Decimal("0")

        for position in positions:
            if position.size != 0:
                # Estimate risk based on position size and current unrealized P&L
                position_value = abs(
                    Decimal(str(position.size * position.averagePrice * 20))
                )  # MNQ multiplier
                total_risk += position_value

        account_balance = await self.get_account_balance()
        portfolio_risk_pct = (
            total_risk / account_balance if account_balance > 0 else Decimal("0")
        )

        return portfolio_risk_pct, total_risk

    async def calculate_position_size(
        self, entry_price: float, stop_loss: float, risk_amount: Decimal | None = None
    ):
        """Calculate optimal position size based on risk parameters."""
        if risk_amount is None:
            account_balance = await self.get_account_balance()
            risk_amount = account_balance * self.max_risk_per_trade

        # Calculate risk per contract
        price_diff = abs(Decimal(str(entry_price)) - Decimal(str(stop_loss)))
        risk_per_contract = price_diff * 20  # MNQ multiplier

        if risk_per_contract <= 0:
            return 0

        # Calculate position size
        calculated_size = int(risk_amount / risk_per_contract)

        # Apply position limits
        max_size = 10  # Hard limit
        return max(1, min(calculated_size, max_size))

    async def check_risk_limits(self, proposed_trade: dict):
        """Check if proposed trade violates risk limits."""
        errors = []

        # Check maximum positions
        if len(self.active_trades) >= self.max_positions:
            errors.append(f"Maximum positions reached ({self.max_positions})")

        # Check daily risk limit
        account_balance = await self.get_account_balance()
        if abs(self.daily_pnl) >= (account_balance * self.max_daily_risk):
            errors.append(f"Daily risk limit reached ({self.max_daily_risk * 100}%)")

        # Check portfolio risk
        portfolio_risk_pct, _ = await self.calculate_current_portfolio_risk()
        if portfolio_risk_pct >= self.max_portfolio_risk:
            errors.append(
                f"Portfolio risk limit reached ({self.max_portfolio_risk * 100}%)"
            )

        # Check proposed trade risk
        trade_risk = Decimal(str(proposed_trade["risk_amount"]))
        if trade_risk > (account_balance * self.max_risk_per_trade):
            errors.append(f"Trade risk too high ({self.max_risk_per_trade * 100}% max)")

        return len(errors) == 0, errors

    async def monitor_daily_pnl(self):
        """Monitor and update daily P&L."""
        current_price = await self.suite["MNQ"].data.get_current_price()
        account_balance = await self.get_account_balance()
        if current_price is None:
            return Decimal("0")

        current_date = datetime.now().date()

        # Reset daily P&L if new day
        if current_date > self.daily_reset_time:
            self.daily_pnl = Decimal("0")
            self.daily_reset_time = current_date
            print(f"Daily P&L reset for {current_date}")

        # Calculate current daily P&L
        positions = await self.suite["MNQ"].positions.get_all_positions()
        total_unrealized = sum(
            Decimal(str(p.unrealized_pnl(current_price)))
            for p in positions
            if p.size != 0
        )

        self.daily_pnl = account_balance + total_unrealized

        return self.daily_pnl

    async def place_risk_managed_trade(
        self, direction: str, entry_price: float, stop_loss: float, take_profit: float
    ):
        """Place a trade with full risk management."""
        try:
            # Calculate position size
            position_size = await self.calculate_position_size(entry_price, stop_loss)

            if position_size == 0:
                print("Position size calculated as 0 - trade rejected")
                return None

            # Calculate trade risk
            risk_per_contract = (
                abs(Decimal(str(entry_price)) - Decimal(str(stop_loss))) * 20
            )
            total_risk = risk_per_contract * position_size

            # Prepare trade proposal
            proposed_trade = {
                "direction": direction,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "size": position_size,
                "risk_amount": total_risk,
            }

            # Check risk limits
            risk_ok, risk_errors = await self.check_risk_limits(proposed_trade)

            if not risk_ok:
                print("Trade rejected due to risk limits:")
                for error in risk_errors:
                    print(f"  - {error}")
                return None

            # Display trade details
            account_balance = await self.get_account_balance()
            risk_pct = (total_risk / account_balance) * 100

            print("\nRisk-Managed Trade Setup:")
            print(f"  Direction: {direction.upper()}")
            print(f"  Entry: ${entry_price:.2f}")
            print(f"  Stop: ${stop_loss:.2f}")
            print(f"  Target: ${take_profit:.2f}")
            print(f"  Size: {position_size} contracts")
            print(f"  Risk: ${total_risk:.2f} ({risk_pct:.2f}% of account)")
            print(
                f"  R:R Ratio: {abs(take_profit - entry_price) / abs(entry_price - stop_loss):.2f}:1"
            )

            # Show current risk status
            portfolio_risk_pct, _ = await self.calculate_current_portfolio_risk()
            daily_pnl = await self.monitor_daily_pnl()

            print("\nCurrent Risk Status:")
            print(f"  Daily P&L: ${daily_pnl:.2f}")
            print(f"  Portfolio Risk: {portfolio_risk_pct * 100:.2f}%")
            print(f"  Active Positions: {len(self.active_trades)}")

            # Confirm trade
            response = input(
                f"\nProceed with risk-managed {direction.upper()} trade? (y/N): "
            )
            if not response.lower().startswith("y"):
                return None

            # Place bracket order
            side = 0 if direction == "long" else 1

            result = await self.suite["MNQ"].orders.place_bracket_order(
                contract_id=self.suite["MNQ"].instrument_info.id,
                side=side,
                size=position_size,
                entry_price=None,
                entry_type="market",
                stop_loss_price=float(stop_loss),
                take_profit_price=float(take_profit),
            )

            # Track the trade
            trade_record = {
                **proposed_trade,
                "bracket": result,
                "timestamp": datetime.now(),
                "status": "active",
            }

            self.active_trades.append(trade_record)

            print("Risk-managed trade placed successfully!")
            print(f"  Main Order: {result.entry_order_id}")
            print(f"  Stop Order: {result.stop_order_id}")
            print(f"  Target Order: {result.target_order_id}")

            return result

        except Exception as e:
            print(f"Failed to place risk-managed trade: {e}")
            return None

    async def generate_risk_report(self):
        """Generate comprehensive risk report."""
        print("\n" + "=" * 50)
        print("RISK MANAGEMENT REPORT")
        print("=" * 50)

        account_balance = await self.get_account_balance()
        daily_pnl = await self.monitor_daily_pnl()
        portfolio_risk_pct, total_risk = await self.calculate_current_portfolio_risk()

        print(f"Account Balance: ${account_balance:,.2f}")
        print(
            f"Daily P&L: ${daily_pnl:.2f} ({(daily_pnl / account_balance) * 100:.2f}%)"
        )
        print(f"Portfolio Risk: ${total_risk:,.2f} ({portfolio_risk_pct * 100:.2f}%)")
        print(f"Active Trades: {len(self.active_trades)}")

        print("\nRisk Limits:")
        print(
            f"  Per Trade: {self.max_risk_per_trade * 100:.1f}% (${account_balance * self.max_risk_per_trade:.2f})"
        )
        print(
            f"  Daily: {self.max_daily_risk * 100:.1f}% (${account_balance * self.max_daily_risk:.2f})"
        )
        print(
            f"  Portfolio: {self.max_portfolio_risk * 100:.1f}% (${account_balance * self.max_portfolio_risk:.2f})"
        )
        print(f"  Max Positions: {self.max_positions}")

        if self.active_trades:
            print("\nActive Trades:")
            for i, trade in enumerate(self.active_trades, 1):
                print(
                    f"  {i}. {trade['direction'].upper()} - ${trade['entry_price']:.2f} (Risk: ${trade['risk_amount']:.2f})"
                )

        print("=" * 50)


async def main():
    suite = await TradingSuite.create(
        ["MNQ"], timeframes=["5min"], features=["risk_manager"]
    )
    risk_manager = AdvancedRiskManager(suite)
    mnq_context = suite["MNQ"]

    # Event handlers
    async def on_order_filled(event):
        order_data = event.data
        print(
            f"Order filled: {order_data.get('order_id')} at ${order_data.get('fill_price', 0):.2f}"
        )

        # Update trade records
        for trade in risk_manager.active_trades:
            bracket: BracketOrderResponse = trade["bracket"]
            if bracket is None:
                return

            if order_data.get("order_id") in [
                bracket.stop_order_id,
                bracket.target_order_id,
            ]:
                trade["status"] = "completed"
                print(
                    f"Trade completed: {trade['direction']} from ${trade['entry_price']:.2f}"
                )

    await mnq_context.on(EventType.ORDER_FILLED, on_order_filled)

    print("Advanced Risk Management System Active")
    print("Commands:")
    print("  'long' - Test long trade")
    print("  'short' - Test short trade")
    print("  'report' - Generate risk report")
    print("  'quit' - Exit")

    try:
        while True:
            command = input("\nEnter command: ").strip().lower()

            if command == "quit":
                break
            elif command == "report":
                await risk_manager.generate_risk_report()
            elif command in ["long", "short"]:
                # Get current price and simulate trade levels
                current_price = await mnq_context.data.get_current_price()

                if command == "long":
                    entry_price = float(current_price) if current_price else 0
                    stop_loss = entry_price * 0.998  # 0.2% stop
                    take_profit = entry_price * 1.004  # 0.4% target
                else:
                    entry_price = float(current_price) if current_price else 0
                    stop_loss = entry_price * 1.002  # 0.2% stop
                    take_profit = entry_price * 0.996  # 0.4% target

                await risk_manager.place_risk_managed_trade(
                    command, entry_price, stop_loss, take_profit
                )

            # Update daily P&L monitoring
            await risk_manager.monitor_daily_pnl()

    except KeyboardInterrupt:
        print("\nShutting down risk management system...")


if __name__ == "__main__":
    asyncio.run(main())
