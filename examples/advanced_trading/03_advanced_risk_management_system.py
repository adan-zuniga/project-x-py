#!/usr/bin/env python
"""
Advanced risk management system with portfolio-level controls.

This example demonstrates:
- Position sizing based on risk parameters
- Portfolio risk monitoring
- Bracket orders with automatic stop-loss and take-profit
- Real-time P&L tracking
- Risk limit enforcement
"""

import asyncio
from datetime import datetime
from decimal import Decimal

from project_x_py import EventType, TradingSuite
from project_x_py.event_bus import Event


class AdvancedRiskManager:
    """Advanced risk management system for trading."""

    def __init__(self, suite: TradingSuite):
        self.suite = suite

        # Risk parameters
        self.max_risk_per_trade = Decimal("0.02")  # 2% per trade
        self.max_daily_risk = Decimal("0.06")  # 6% per day
        self.max_portfolio_risk = Decimal("0.20")  # 20% total portfolio
        self.max_positions = 3  # Maximum open positions

        # Tracking
        self.account_balance = Decimal("50000")  # Default demo balance
        self.daily_pnl = Decimal("0")
        self.active_trades = []
        self.daily_reset_time = datetime.now().date()

    async def update_account_info(self):
        """Update account information."""
        try:
            # Try to get positions to calculate P&L
            positions = await self.suite["MNQ"].positions.get_all_positions()

            # Calculate total P&L from positions
            total_pnl = Decimal("0")
            # Note: Actual P&L calculation would depend on position attributes
            # This is a placeholder for demonstration

            # Update daily P&L
            current_date = datetime.now().date()
            if current_date > self.daily_reset_time:
                self.daily_pnl = Decimal("0")
                self.daily_reset_time = current_date
                print(f"Daily P&L reset for {current_date}")

            self.daily_pnl += total_pnl

        except Exception as e:
            print(f"Could not update account info: {e}")

    async def calculate_position_size(
        self, entry_price: float, stop_loss: float
    ) -> int:
        """Calculate optimal position size based on risk parameters."""
        # Calculate risk amount
        risk_amount = self.account_balance * self.max_risk_per_trade

        # Calculate risk per contract (MNQ = $20 per point)
        price_diff = abs(Decimal(str(entry_price)) - Decimal(str(stop_loss)))
        risk_per_contract = price_diff * 20

        if risk_per_contract <= 0:
            return 0

        # Calculate position size
        calculated_size = int(risk_amount / risk_per_contract)

        # Apply position limits
        max_size = 10  # Hard limit
        return max(1, min(calculated_size, max_size))

    async def check_risk_limits(self, proposed_size: int) -> tuple[bool, list[str]]:
        """Check if proposed trade violates risk limits."""
        errors = []

        # Check maximum positions
        positions = await self.suite["MNQ"].positions.get_all_positions()
        active_positions = [p for p in positions if p.size != 0]

        if len(active_positions) >= self.max_positions:
            errors.append(f"Maximum positions reached ({self.max_positions})")

        # Check daily risk limit
        if abs(self.daily_pnl) >= (self.account_balance * self.max_daily_risk):
            errors.append(f"Daily risk limit reached ({self.max_daily_risk * 100}%)")

        # Check portfolio risk
        total_position_size = sum(abs(p.size) for p in active_positions)
        if total_position_size + proposed_size > 20:  # Max 20 contracts total
            errors.append("Portfolio size limit reached (20 contracts max)")

        return len(errors) == 0, errors

    async def place_risk_managed_trade(
        self, direction: str, stop_offset: float = 50, target_offset: float = 100
    ):
        """Place a trade with full risk management."""
        try:
            # Get current price
            current_price = await self.suite["MNQ"].data.get_current_price()
            if not current_price:
                print("Could not get current price")
                return None

            # Calculate entry, stop, and target prices
            if direction == "long":
                entry_price = current_price
                stop_loss = current_price - stop_offset
                take_profit = current_price + target_offset
                side = 0  # Buy
            else:
                entry_price = current_price
                stop_loss = current_price + stop_offset
                take_profit = current_price - target_offset
                side = 1  # Sell

            # Calculate position size
            position_size = await self.calculate_position_size(entry_price, stop_loss)

            if position_size == 0:
                print("Position size calculated as 0 - trade rejected")
                return None

            # Check risk limits
            risk_ok, risk_errors = await self.check_risk_limits(position_size)

            if not risk_ok:
                print("Trade rejected due to risk limits:")
                for error in risk_errors:
                    print(f"  - {error}")
                return None

            # Calculate trade risk
            risk_per_contract = abs(entry_price - stop_loss) * 20  # MNQ multiplier
            total_risk = risk_per_contract * position_size
            risk_pct = float((total_risk / float(self.account_balance)) * 100)

            # Display trade details
            print("\n" + "=" * 50)
            print("RISK-MANAGED TRADE SETUP")
            print("=" * 50)
            print(f"Direction: {direction.upper()}")
            print(f"Current Price: ${entry_price:.2f}")
            print(f"Stop Loss: ${stop_loss:.2f} ({stop_offset} points)")
            print(f"Take Profit: ${take_profit:.2f} ({target_offset} points)")
            print(f"Position Size: {position_size} contracts")
            print(f"Risk Amount: ${total_risk:.2f} ({risk_pct:.2f}% of account)")
            print(f"R:R Ratio: {target_offset / stop_offset:.1f}:1")

            # Show current status
            positions = await self.suite["MNQ"].positions.get_all_positions()
            active_positions = [p for p in positions if p.size != 0]
            print("\nCurrent Status:")
            print(f"  Active Positions: {len(active_positions)}")
            print(f"  Daily P&L: ${self.daily_pnl:.2f}")
            print("=" * 50)

            # Confirm trade
            response = input(f"\nProceed with {direction.upper()} trade? (y/N): ")
            if not response.lower().startswith("y"):
                print("Trade cancelled")
                return None

            # Place bracket order
            print("\nPlacing bracket order...")

            # Get the instrument contract ID
            instrument = self.suite["MNQ"].instrument_info
            contract_id = instrument.id if hasattr(instrument, "id") else "MNQ"

            result = await self.suite["MNQ"].orders.place_bracket_order(
                contract_id=contract_id,
                side=side,
                size=position_size,
                entry_price=None,  # Market entry
                entry_type="market",
                stop_loss_price=stop_loss,
                take_profit_price=take_profit,
            )

            if result and result.success:
                # Track the trade
                trade_record = {
                    "direction": direction,
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "size": position_size,
                    "risk_amount": total_risk,
                    "bracket_result": result,
                    "timestamp": datetime.now(),
                    "status": "active",
                }
                self.active_trades.append(trade_record)

                print("\n✅ Risk-managed trade placed successfully!")
                print(f"  Entry Order: {result.entry_order_id}")
                print(f"  Stop Order: {result.stop_order_id}")
                print(f"  Target Order: {result.target_order_id}")
            else:
                error_msg = result.error_message if result else "Unknown error"
                print(f"\n❌ Failed to place trade: {error_msg}")

            return result

        except Exception as e:
            print(f"Failed to place risk-managed trade: {e}")
            import traceback

            traceback.print_exc()
            return None

    async def generate_risk_report(self):
        """Generate comprehensive risk report."""
        await self.update_account_info()

        print("\n" + "=" * 60)
        print("RISK MANAGEMENT REPORT")
        print("=" * 60)

        print(f"Account Balance: ${self.account_balance:,.2f}")
        print(
            f"Daily P&L: ${self.daily_pnl:.2f} ({(self.daily_pnl / self.account_balance) * 100:.2f}%)"
        )

        # Get current positions
        positions = await self.suite["MNQ"].positions.get_all_positions()
        active_positions = [p for p in positions if p.size != 0]

        print(f"\nActive Positions: {len(active_positions)}")
        for i, pos in enumerate(active_positions, 1):
            side = "LONG" if pos.size > 0 else "SHORT"
            print(f"  {i}. {side} {abs(pos.size)} contracts")

        print("\nRisk Limits:")
        print(
            f"  Per Trade: {self.max_risk_per_trade * 100:.1f}% (${self.account_balance * self.max_risk_per_trade:.2f})"
        )
        print(
            f"  Daily: {self.max_daily_risk * 100:.1f}% (${self.account_balance * self.max_daily_risk:.2f})"
        )
        print(f"  Portfolio: {self.max_portfolio_risk * 100:.1f}%")
        print(f"  Max Positions: {self.max_positions}")

        if self.active_trades:
            print("\nRecent Trades:")
            for i, trade in enumerate(self.active_trades[-5:], 1):  # Show last 5
                print(
                    f"  {i}. {trade['direction'].upper()} - "
                    f"${trade['entry_price']:.2f} "
                    f"(Risk: ${trade['risk_amount']:.2f}) - "
                    f"{trade['status'].upper()}"
                )

        print("=" * 60)


async def main():
    """Main function to run the risk management system."""
    print("Initializing Advanced Risk Management System...")

    # Create TradingSuite with risk management features
    suite = await TradingSuite.create(
        ["MNQ"],
        timeframes=["1min", "5min"],
        initial_days=1,
        features=["risk_manager"],  # Enable risk manager feature
    )

    # Create risk manager
    risk_manager = AdvancedRiskManager(suite)
    mnq_context = suite["MNQ"]

    # Set up event handlers
    async def on_new_bar(_event: Event):
        """Handle new bar events to update P&L."""
        # Update account info on each new bar
        await risk_manager.update_account_info()

    async def on_quote(_event: Event):
        """Handle quote updates."""
        # Could use this for real-time P&L updates
        # Placeholder for future real-time updates

    # Register event handlers
    await mnq_context.on(EventType.NEW_BAR, on_new_bar)
    await mnq_context.on(EventType.QUOTE_UPDATE, on_quote)

    print("\n" + "=" * 60)
    print("ADVANCED RISK MANAGEMENT SYSTEM ACTIVE")
    print("=" * 60)
    print("\nCommands:")
    print("  'long'  - Place risk-managed LONG trade")
    print("  'short' - Place risk-managed SHORT trade")
    print("  'report' - Generate risk report")
    print("  'quit'  - Exit system")
    print("=" * 60)

    try:
        while True:
            # Get user input
            command = input("\nEnter command: ").strip().lower()

            if command == "quit":
                break
            elif command == "report":
                await risk_manager.generate_risk_report()
            elif command == "long":
                await risk_manager.place_risk_managed_trade("long")
            elif command == "short":
                await risk_manager.place_risk_managed_trade("short")
            elif command:
                print(f"Unknown command: {command}")

            # Brief pause to allow async operations
            await asyncio.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\nShutting down risk management system...")
    finally:
        # Disconnect from real-time feeds
        await suite.disconnect()
        print("System disconnected. Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
