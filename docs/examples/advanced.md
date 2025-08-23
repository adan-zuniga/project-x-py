# Advanced Trading Examples

This page demonstrates sophisticated trading strategies and advanced features of the ProjectX Python SDK v3.3.4. These examples include order placement, risk management, and complex event-driven trading systems.

!!! warning "Live Trading Alert"
    **These examples place REAL ORDERS on the market!**

    - Only use with demo/simulated accounts for testing
    - All examples use MNQ (micro contracts) to minimize risk
    - Always monitor positions and orders closely
    - Include proper risk management and stop losses

## 1. Advanced Bracket Order Strategy

Bracket orders combine entry, stop loss, and take profit in a single operation:

```python
#!/usr/bin/env python
"""
Advanced bracket order strategy with dynamic stops based on ATR
"""
import asyncio
from decimal import Decimal
from project_x_py import TradingSuite, EventType
from project_x_py.indicators import ATR, RSI, SMA

class ATRBracketStrategy:
    def __init__(self, suite: TradingSuite):
        self.suite = suite
        self.atr_period = 14
        self.rsi_period = 14
        self.sma_period = 20
        self.position_size = 1
        self.active_orders = []

    async def calculate_dynamic_levels(self):
        """Calculate stop and target levels based on ATR."""
        bars = await self.suite.data.get_data("5min")

        # Calculate ATR for volatility-based stops
        atr_values = bars.pipe(ATR, period=self.atr_period)
        current_atr = float(atr_values[-1])

        # Dynamic stop loss: 2x ATR
        stop_offset = Decimal(str(current_atr * 2))

        # Dynamic take profit: 3x ATR (1.5:1 reward:risk)
        target_offset = Decimal(str(current_atr * 3))

        return stop_offset, target_offset

    async def check_entry_conditions(self):
        """Check if conditions are met for entry."""
        bars = await self.suite.data.get_data("5min")

        if len(bars) < max(self.rsi_period, self.sma_period, self.atr_period):
            return None, None

        # Calculate indicators
        rsi = bars.pipe(RSI, period=self.rsi_period)
        sma = bars.pipe(SMA, period=self.sma_period)
        current_price = bars['close'][-1]
        current_rsi = rsi[-1]
        current_sma = sma[-1]

        # Long signal: Price above SMA and RSI oversold recovery
        if current_price > current_sma and 30 < current_rsi < 50:
            return "long", current_price

        # Short signal: Price below SMA and RSI overbought decline
        elif current_price < current_sma and 50 < current_rsi < 70:
            return "short", current_price

        return None, None

    async def place_bracket_order(self, direction: str):
        """Place a bracket order based on strategy conditions."""
        try:
            # Calculate dynamic stop and target levels
            stop_offset, target_offset = await self.calculate_dynamic_levels()

            # Determine side (0=Buy, 1=Sell)
            side = 0 if direction == "long" else 1

            print(f"Placing {direction.upper()} bracket order:")
            print(f"  Size: {self.position_size} contracts")
            print(f"  Stop Loss: {stop_offset} points")
            print(f"  Take Profit: {target_offset} points")

            # Place bracket order
            result = await self.suite.orders.place_bracket_order(
                contract_id=self.suite.instrument_info.id,
                side=side,
                size=self.position_size,
                stop_offset=stop_offset,
                target_offset=target_offset
            )

            print(f"Bracket order placed successfully:")
            print(f"  Main Order ID: {result.main_order_id}")
            print(f"  Stop Order ID: {result.stop_order_id}")
            print(f"  Target Order ID: {result.target_order_id}")

            self.active_orders.append(result)
            return result

        except Exception as e:
            print(f"Failed to place bracket order: {e}")
            return None

    async def monitor_orders(self):
        """Monitor active orders and handle fills/cancellations."""
        for bracket in self.active_orders[:]:  # Copy list to modify during iteration
            try:
                # Check main order status
                main_status = await self.suite.orders.get_order_status(bracket.main_order_id)

                if main_status.status == "Filled":
                    print(f"Main order {bracket.main_order_id} filled at ${main_status.fill_price}")

                elif main_status.status in ["Cancelled", "Rejected"]:
                    print(f"Main order {bracket.main_order_id} {main_status.status}")
                    self.active_orders.remove(bracket)

            except Exception as e:
                print(f"Error monitoring order {bracket.main_order_id}: {e}")

async def main():
    # Create trading suite with required timeframes
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["1min", "5min"],
        initial_days=10,  # Need historical data for indicators
        features=["risk_manager"]
    )

    # Initialize strategy
    strategy = ATRBracketStrategy(suite)

    # Set up event handlers for real-time monitoring
    async def on_new_bar(event):
        if event.data.get('timeframe') == '5min':
            print(f"New 5min bar: ${event.data['close']:.2f}")

            # Check for entry signals
            direction, price = await strategy.check_entry_conditions()
            if direction and len(strategy.active_orders) == 0:  # No active positions
                print(f"Entry signal detected: {direction.upper()} at ${price:.2f}")

                # Confirm with user before placing order
                response = input(f"Place {direction.upper()} bracket order? (y/N): ")
                if response.lower().startswith('y'):
                    await strategy.place_bracket_order(direction)

    async def on_order_filled(event):
        order_data = event.data
        print(f"ORDER FILLED: {order_data.get('order_id')} at ${order_data.get('fill_price', 0):.2f}")

    # Register event handlers
    await suite.on(EventType.NEW_BAR, on_new_bar)
    await suite.on(EventType.ORDER_FILLED, on_order_filled)

    print("Advanced Bracket Order Strategy Active")
    print("Monitoring for entry signals on 5-minute bars...")
    print("Press Ctrl+C to exit")

    try:
        while True:
            await asyncio.sleep(5)

            # Monitor active orders
            await strategy.monitor_orders()

            # Display current market info
            current_price = await suite.data.get_current_price()
            active_count = len(strategy.active_orders)
            print(f"Price: ${current_price:.2f} | Active Orders: {active_count}")

    except KeyboardInterrupt:
        print("\nShutting down strategy...")

        # Cancel any remaining orders
        for bracket in strategy.active_orders:
            try:
                await suite.orders.cancel_order(bracket.main_order_id)
                print(f"Cancelled order {bracket.main_order_id}")
            except Exception as e:
                print(f"Error cancelling order: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 2. Multi-Timeframe Momentum Strategy

Advanced strategy using multiple timeframes for confirmation:

```python
#!/usr/bin/env python
"""
Multi-timeframe momentum strategy with confluence analysis
"""
import asyncio
from decimal import Decimal
from project_x_py import TradingSuite, EventType
from project_x_py.indicators import RSI, MACD, EMA, ATR

class MultiTimeframeMomentumStrategy:
    def __init__(self, suite: TradingSuite):
        self.suite = suite
        self.position_size = 1
        self.risk_per_trade = Decimal("0.02")  # 2% risk per trade
        self.active_position = None

    async def analyze_timeframe(self, timeframe: str):
        """Analyze a specific timeframe for momentum signals."""
        bars = await self.suite.data.get_data(timeframe)

        if len(bars) < 50:  # Need sufficient data
            return None

        # Calculate indicators
        rsi = bars.pipe(RSI, period=14)
        macd_result = bars.pipe(MACD, fast_period=12, slow_period=26, signal_period=9)
        ema_20 = bars.pipe(EMA, period=20)
        ema_50 = bars.pipe(EMA, period=50)

        current_price = bars['close'][-1]
        current_rsi = rsi[-1]
        current_macd = macd_result['macd'][-1]
        macd_signal = macd_result['signal'][-1]
        current_ema_20 = ema_20[-1]
        current_ema_50 = ema_50[-1]

        # Determine trend and momentum
        trend = "bullish" if current_ema_20 > current_ema_50 else "bearish"
        momentum = "positive" if current_macd > macd_signal else "negative"
        rsi_level = "oversold" if current_rsi < 30 else "overbought" if current_rsi > 70 else "neutral"

        return {
            "timeframe": timeframe,
            "price": current_price,
            "trend": trend,
            "momentum": momentum,
            "rsi_level": rsi_level,
            "rsi": current_rsi,
            "macd": current_macd,
            "macd_signal": macd_signal,
            "ema_20": current_ema_20,
            "ema_50": current_ema_50
        }

    async def check_confluence(self):
        """Check for confluence across multiple timeframes."""
        # Analyze all timeframes
        tf_5min = await self.analyze_timeframe("5min")
        tf_15min = await self.analyze_timeframe("15min")  # Add 15min if available
        tf_1hr = await self.analyze_timeframe("1hr")      # Add 1hr if available

        analyses = [tf for tf in [tf_5min, tf_15min, tf_1hr] if tf is not None]

        if len(analyses) < 2:
            return None, None

        # Count bullish/bearish signals
        bullish_signals = sum(1 for tf in analyses if tf['trend'] == 'bullish' and tf['momentum'] == 'positive')
        bearish_signals = sum(1 for tf in analyses if tf['trend'] == 'bearish' and tf['momentum'] == 'negative')

        # Require confluence (majority agreement)
        if bullish_signals >= 2 and tf_5min['rsi'] < 70:  # Not overbought on entry timeframe
            return "long", analyses
        elif bearish_signals >= 2 and tf_5min['rsi'] > 30:  # Not oversold on entry timeframe
            return "short", analyses

        return None, analyses

    async def calculate_position_size(self, entry_price: float, stop_loss: float):
        """Calculate position size based on risk management."""
        account_info = await self.suite.client.get_account_info()
        account_balance = float(account_info.balance)

        # Calculate risk amount
        risk_amount = account_balance * float(self.risk_per_trade)

        # Calculate risk per contract
        price_diff = abs(entry_price - stop_loss)
        risk_per_contract = price_diff * 20  # MNQ multiplier

        # Calculate position size
        calculated_size = int(risk_amount / risk_per_contract)
        return max(1, min(calculated_size, 5))  # Between 1-5 contracts

    async def place_momentum_trade(self, direction: str, analyses: list):
        """Place a trade based on momentum confluence."""
        try:
            current_price = analyses[0]['price']  # Use 5min price

            # Calculate ATR-based stop loss
            bars_5min = await self.suite.data.get_data("5min")
            atr = bars_5min.pipe(ATR, period=14)
            current_atr = float(atr[-1])

            # Dynamic stops based on volatility
            if direction == "long":
                stop_loss = current_price - (current_atr * 2)
                take_profit = current_price + (current_atr * 3)
                side = 0  # Buy
            else:
                stop_loss = current_price + (current_atr * 2)
                take_profit = current_price - (current_atr * 3)
                side = 1  # Sell

            # Calculate position size
            position_size = await self.calculate_position_size(current_price, stop_loss)

            print(f"\n{direction.upper()} Momentum Trade Setup:")
            print(f"  Entry Price: ${current_price:.2f}")
            print(f"  Stop Loss: ${stop_loss:.2f}")
            print(f"  Take Profit: ${take_profit:.2f}")
            print(f"  Position Size: {position_size} contracts")
            print(f"  Risk/Reward: {abs(take_profit - current_price) / abs(current_price - stop_loss):.2f}:1")

            # Display confluence analysis
            print("\nConfluence Analysis:")
            for analysis in analyses:
                print(f"  {analysis['timeframe']}: {analysis['trend']} trend, {analysis['momentum']} momentum, RSI: {analysis['rsi']:.1f}")

            # Confirm trade
            response = input(f"\nPlace {direction.upper()} momentum trade? (y/N): ")
            if not response.lower().startswith('y'):
                return None

            # Place bracket order
            result = await self.suite.orders.place_bracket_order(
                contract_id=self.suite.instrument_info.id,
                side=side,
                size=position_size,
                stop_offset=Decimal(str(abs(current_price - stop_loss))),
                target_offset=Decimal(str(abs(take_profit - current_price)))
            )

            self.active_position = {
                "direction": direction,
                "entry_price": current_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "size": position_size,
                "bracket": result
            }

            print(f"Momentum trade placed successfully!")
            return result

        except Exception as e:
            print(f"Failed to place momentum trade: {e}")
            return None

async def main():
    # Create suite with multiple timeframes
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["5min", "15min", "1hr"],
        initial_days=15,  # More historical data for higher timeframes
        features=["risk_manager"]
    )

    strategy = MultiTimeframeMomentumStrategy(suite)

    # Event handlers
    async def on_new_bar(event):
        if event.data.get('timeframe') == '5min':  # Only act on 5min bars
            # Check for confluence signals
            direction, analyses = await strategy.check_confluence()

            if direction and not strategy.active_position:
                print(f"\n=== MOMENTUM CONFLUENCE DETECTED: {direction.upper()} ===")
                await strategy.place_momentum_trade(direction, analyses)
            elif analyses:
                # Display current analysis
                print(f"\nCurrent Analysis (no confluence):")
                for analysis in analyses:
                    if analysis:
                        print(f"  {analysis['timeframe']}: {analysis['trend']}/{analysis['momentum']} (RSI: {analysis['rsi']:.1f})")

    async def on_order_filled(event):
        if strategy.active_position:
            order_id = event.data.get('order_id')
            fill_price = event.data.get('fill_price', 0)

            # Check if it's our stop or target
            bracket = strategy.active_position['bracket']
            if order_id in [bracket.stop_order_id, bracket.target_order_id]:
                result = "STOP LOSS" if order_id == bracket.stop_order_id else "TAKE PROFIT"
                print(f"\n{result} HIT: Order {order_id} filled at ${fill_price:.2f}")
                strategy.active_position = None  # Clear position

    # Register events
    await suite.on(EventType.NEW_BAR, on_new_bar)
    await suite.on(EventType.ORDER_FILLED, on_order_filled)

    print("Multi-Timeframe Momentum Strategy Active")
    print("Analyzing 5min, 15min, and 1hr timeframes for confluence...")
    print("Press Ctrl+C to exit")

    try:
        while True:
            await asyncio.sleep(10)

            # Display status
            current_price = await suite.data.get_current_price()
            position_status = "ACTIVE" if strategy.active_position else "FLAT"
            print(f"Price: ${current_price:.2f} | Position: {position_status}")

    except KeyboardInterrupt:
        print("\nShutting down strategy...")

        # Cancel active orders if any
        if strategy.active_position:
            bracket = strategy.active_position['bracket']
            try:
                await suite.orders.cancel_order(bracket.main_order_id)
                print("Cancelled active orders")
            except Exception as e:
                print(f"Error cancelling orders: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 3. Advanced Risk Management System

Comprehensive risk management with position sizing and portfolio limits:

```python
#!/usr/bin/env python
"""
Advanced risk management system with portfolio-level controls
"""
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from project_x_py import TradingSuite, EventType

class AdvancedRiskManager:
    def __init__(self, suite: TradingSuite):
        self.suite = suite

        # Risk parameters
        self.max_risk_per_trade = Decimal("0.02")  # 2% per trade
        self.max_daily_risk = Decimal("0.06")      # 6% per day
        self.max_portfolio_risk = Decimal("0.20")  # 20% total portfolio
        self.max_positions = 3                     # Maximum open positions

        # Tracking
        self.daily_pnl = Decimal("0")
        self.active_trades = []
        self.daily_reset_time = datetime.now().date()

    async def get_account_balance(self):
        """Get current account balance."""
        account_info = await self.suite.client.get_account_info()
        return Decimal(str(account_info.balance))

    async def calculate_current_portfolio_risk(self):
        """Calculate current portfolio risk exposure."""
        positions = await self.suite.positions.get_all_positions()
        total_risk = Decimal("0")

        for position in positions:
            if position.size != 0:
                # Estimate risk based on position size and current unrealized P&L
                position_value = abs(Decimal(str(position.size * position.average_price * 20)))  # MNQ multiplier
                total_risk += position_value

        account_balance = await self.get_account_balance()
        portfolio_risk_pct = total_risk / account_balance if account_balance > 0 else Decimal("0")

        return portfolio_risk_pct, total_risk

    async def calculate_position_size(self, entry_price: float, stop_loss: float, risk_amount: Decimal = None):
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
            errors.append(f"Portfolio risk limit reached ({self.max_portfolio_risk * 100}%)")

        # Check proposed trade risk
        trade_risk = Decimal(str(proposed_trade['risk_amount']))
        if trade_risk > (account_balance * self.max_risk_per_trade):
            errors.append(f"Trade risk too high ({self.max_risk_per_trade * 100}% max)")

        return len(errors) == 0, errors

    async def monitor_daily_pnl(self):
        """Monitor and update daily P&L."""
        current_date = datetime.now().date()

        # Reset daily P&L if new day
        if current_date > self.daily_reset_time:
            self.daily_pnl = Decimal("0")
            self.daily_reset_time = current_date
            print(f"Daily P&L reset for {current_date}")

        # Calculate current daily P&L
        positions = await self.suite.positions.get_all_positions()
        total_unrealized = sum(Decimal(str(p.unrealized_pnl)) for p in positions)
        total_realized = sum(Decimal(str(p.realized_pnl)) for p in positions)

        self.daily_pnl = total_realized + total_unrealized

        return self.daily_pnl

    async def place_risk_managed_trade(self, direction: str, entry_price: float, stop_loss: float, take_profit: float):
        """Place a trade with full risk management."""
        try:
            # Calculate position size
            position_size = await self.calculate_position_size(entry_price, stop_loss)

            if position_size == 0:
                print("Position size calculated as 0 - trade rejected")
                return None

            # Calculate trade risk
            risk_per_contract = abs(Decimal(str(entry_price)) - Decimal(str(stop_loss))) * 20
            total_risk = risk_per_contract * position_size

            # Prepare trade proposal
            proposed_trade = {
                "direction": direction,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "size": position_size,
                "risk_amount": total_risk
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

            print(f"\nRisk-Managed Trade Setup:")
            print(f"  Direction: {direction.upper()}")
            print(f"  Entry: ${entry_price:.2f}")
            print(f"  Stop: ${stop_loss:.2f}")
            print(f"  Target: ${take_profit:.2f}")
            print(f"  Size: {position_size} contracts")
            print(f"  Risk: ${total_risk:.2f} ({risk_pct:.2f}% of account)")
            print(f"  R:R Ratio: {abs(take_profit - entry_price) / abs(entry_price - stop_loss):.2f}:1")

            # Show current risk status
            portfolio_risk_pct, _ = await self.calculate_current_portfolio_risk()
            daily_pnl = await self.monitor_daily_pnl()

            print(f"\nCurrent Risk Status:")
            print(f"  Daily P&L: ${daily_pnl:.2f}")
            print(f"  Portfolio Risk: {portfolio_risk_pct * 100:.2f}%")
            print(f"  Active Positions: {len(self.active_trades)}")

            # Confirm trade
            response = input(f"\nProceed with risk-managed {direction.upper()} trade? (y/N): ")
            if not response.lower().startswith('y'):
                return None

            # Place bracket order
            side = 0 if direction == "long" else 1
            stop_offset = Decimal(str(abs(entry_price - stop_loss)))
            target_offset = Decimal(str(abs(take_profit - entry_price)))

            result = await self.suite.orders.place_bracket_order(
                contract_id=self.suite.instrument_info.id,
                side=side,
                size=position_size,
                stop_offset=stop_offset,
                target_offset=target_offset
            )

            # Track the trade
            trade_record = {
                **proposed_trade,
                "bracket": result,
                "timestamp": datetime.now(),
                "status": "active"
            }

            self.active_trades.append(trade_record)

            print(f"Risk-managed trade placed successfully!")
            print(f"  Main Order: {result.main_order_id}")
            print(f"  Stop Order: {result.stop_order_id}")
            print(f"  Target Order: {result.target_order_id}")

            return result

        except Exception as e:
            print(f"Failed to place risk-managed trade: {e}")
            return None

    async def generate_risk_report(self):
        """Generate comprehensive risk report."""
        print("\n" + "="*50)
        print("RISK MANAGEMENT REPORT")
        print("="*50)

        account_balance = await self.get_account_balance()
        daily_pnl = await self.monitor_daily_pnl()
        portfolio_risk_pct, total_risk = await self.calculate_current_portfolio_risk()

        print(f"Account Balance: ${account_balance:,.2f}")
        print(f"Daily P&L: ${daily_pnl:.2f} ({(daily_pnl/account_balance)*100:.2f}%)")
        print(f"Portfolio Risk: ${total_risk:,.2f} ({portfolio_risk_pct*100:.2f}%)")
        print(f"Active Trades: {len(self.active_trades)}")

        print(f"\nRisk Limits:")
        print(f"  Per Trade: {self.max_risk_per_trade*100:.1f}% (${account_balance * self.max_risk_per_trade:.2f})")
        print(f"  Daily: {self.max_daily_risk*100:.1f}% (${account_balance * self.max_daily_risk:.2f})")
        print(f"  Portfolio: {self.max_portfolio_risk*100:.1f}% (${account_balance * self.max_portfolio_risk:.2f})")
        print(f"  Max Positions: {self.max_positions}")

        if self.active_trades:
            print(f"\nActive Trades:")
            for i, trade in enumerate(self.active_trades, 1):
                print(f"  {i}. {trade['direction'].upper()} - ${trade['entry_price']:.2f} (Risk: ${trade['risk_amount']:.2f})")

        print("="*50)

async def main():
    suite = await TradingSuite.create("MNQ", timeframes=["5min"], features=["risk_manager"])
    risk_manager = AdvancedRiskManager(suite)

    # Event handlers
    async def on_order_filled(event):
        order_data = event.data
        print(f"Order filled: {order_data.get('order_id')} at ${order_data.get('fill_price', 0):.2f}")

        # Update trade records
        for trade in risk_manager.active_trades:
            bracket = trade['bracket']
            if order_data.get('order_id') in [bracket.stop_order_id, bracket.target_order_id]:
                trade['status'] = 'completed'
                print(f"Trade completed: {trade['direction']} from ${trade['entry_price']:.2f}")

    await suite.on(EventType.ORDER_FILLED, on_order_filled)

    print("Advanced Risk Management System Active")
    print("Commands:")
    print("  'long' - Test long trade")
    print("  'short' - Test short trade")
    print("  'report' - Generate risk report")
    print("  'quit' - Exit")

    try:
        while True:
            command = input("\nEnter command: ").strip().lower()

            if command == 'quit':
                break
            elif command == 'report':
                await risk_manager.generate_risk_report()
            elif command in ['long', 'short']:
                # Get current price and simulate trade levels
                current_price = await suite.data.get_current_price()

                if command == 'long':
                    entry_price = float(current_price)
                    stop_loss = entry_price * 0.998  # 0.2% stop
                    take_profit = entry_price * 1.004  # 0.4% target
                else:
                    entry_price = float(current_price)
                    stop_loss = entry_price * 1.002  # 0.2% stop
                    take_profit = entry_price * 0.996  # 0.4% target

                await risk_manager.place_risk_managed_trade(command, entry_price, stop_loss, take_profit)

            # Update daily P&L monitoring
            await risk_manager.monitor_daily_pnl()

    except KeyboardInterrupt:
        print("\nShutting down risk management system...")

if __name__ == "__main__":
    asyncio.run(main())
```

## 4. Order Book Analysis and Scalping Strategy

Advanced market microstructure analysis for scalping:

```python
#!/usr/bin/env python
"""
Advanced order book analysis and scalping strategy
"""
import asyncio
from collections import deque
from decimal import Decimal
from project_x_py import TradingSuite, EventType

class OrderBookScalpingStrategy:
    def __init__(self, suite: TradingSuite):
        self.suite = suite
        self.orderbook = None
        self.tick_history = deque(maxlen=100)
        self.imbalance_threshold = 0.70  # 70% imbalance threshold
        self.min_size_edge = 50  # Minimum size difference for edge
        self.active_orders = []
        self.scalp_profit_ticks = 2  # Target 2 ticks profit

    async def initialize_orderbook(self):
        """Initialize order book for analysis."""
        try:
            # Access orderbook if available
            if hasattr(self.suite, 'orderbook') and self.suite.orderbook:
                self.orderbook = self.suite.orderbook
                print("Order book initialized successfully")
                return True
            else:
                print("Order book not available - create suite with 'orderbook' feature")
                return False
        except Exception as e:
            print(f"Failed to initialize order book: {e}")
            return False

    async def analyze_order_book_imbalance(self):
        """Analyze order book for size imbalances."""
        if not self.orderbook:
            return None

        try:
            # Get current bid/ask levels
            book_data = await self.orderbook.get_book_snapshot()

            if not book_data or 'bids' not in book_data or 'asks' not in book_data:
                return None

            bids = book_data['bids'][:5]  # Top 5 levels
            asks = book_data['asks'][:5]

            # Calculate size at each level
            total_bid_size = sum(level['size'] for level in bids)
            total_ask_size = sum(level['size'] for level in asks)

            if total_bid_size + total_ask_size == 0:
                return None

            # Calculate imbalance ratio
            bid_ratio = total_bid_size / (total_bid_size + total_ask_size)
            ask_ratio = total_ask_size / (total_bid_size + total_ask_size)

            # Determine imbalance direction
            if bid_ratio >= self.imbalance_threshold:
                return {
                    "direction": "bullish",
                    "strength": bid_ratio,
                    "bid_size": total_bid_size,
                    "ask_size": total_ask_size,
                    "spread": asks[0]['price'] - bids[0]['price'] if bids and asks else 0
                }
            elif ask_ratio >= self.imbalance_threshold:
                return {
                    "direction": "bearish",
                    "strength": ask_ratio,
                    "bid_size": total_bid_size,
                    "ask_size": total_ask_size,
                    "spread": asks[0]['price'] - bids[0]['price'] if bids and asks else 0
                }

            return None

        except Exception as e:
            print(f"Error analyzing order book: {e}")
            return None

    async def analyze_tape_reading(self):
        """Analyze recent trades for momentum."""
        if len(self.tick_history) < 10:
            return None

        recent_ticks = list(self.tick_history)[-10:]

        # Analyze trade aggressiveness
        buy_volume = sum(tick['size'] for tick in recent_ticks if tick.get('aggressor') == 'buy')
        sell_volume = sum(tick['size'] for tick in recent_ticks if tick.get('aggressor') == 'sell')

        total_volume = buy_volume + sell_volume
        if total_volume == 0:
            return None

        buy_ratio = buy_volume / total_volume

        # Strong buying/selling pressure
        if buy_ratio >= 0.70:
            return {"direction": "bullish", "strength": buy_ratio, "volume": total_volume}
        elif buy_ratio <= 0.30:
            return {"direction": "bearish", "strength": 1 - buy_ratio, "volume": total_volume}

        return None

    async def place_scalp_order(self, direction: str, analysis_data: dict):
        """Place a scalping order with tight stops."""
        try:
            current_price = await self.suite.data.get_current_price()
            tick_size = 0.25  # MNQ tick size

            if direction == "long":
                entry_price = float(current_price)
                stop_loss = entry_price - (tick_size * 3)  # 3 tick stop
                take_profit = entry_price + (tick_size * self.scalp_profit_ticks)
                side = 0
            else:
                entry_price = float(current_price)
                stop_loss = entry_price + (tick_size * 3)  # 3 tick stop
                take_profit = entry_price - (tick_size * self.scalp_profit_ticks)
                side = 1

            print(f"\nScalp Setup ({direction.upper()}):")
            print(f"  Entry: ${entry_price:.2f}")
            print(f"  Stop: ${stop_loss:.2f} ({abs(entry_price - stop_loss) / tick_size:.0f} ticks)")
            print(f"  Target: ${take_profit:.2f} ({abs(take_profit - entry_price) / tick_size:.0f} ticks)")
            print(f"  Analysis: {analysis_data}")

            # Quick confirmation for scalping
            response = input(f"Execute {direction.upper()} scalp? (y/N): ")
            if not response.lower().startswith('y'):
                return None

            # Place bracket order with tight parameters
            result = await self.suite.orders.place_bracket_order(
                contract_id=self.suite.instrument_info.id,
                side=side,
                size=1,  # Small size for scalping
                stop_offset=Decimal(str(abs(entry_price - stop_loss))),
                target_offset=Decimal(str(abs(take_profit - entry_price)))
            )

            scalp_record = {
                "direction": direction,
                "entry_price": entry_price,
                "bracket": result,
                "analysis": analysis_data,
                "timestamp": asyncio.get_event_loop().time()
            }

            self.active_orders.append(scalp_record)
            print(f"Scalp order placed: {result.main_order_id}")
            return result

        except Exception as e:
            print(f"Failed to place scalp order: {e}")
            return None

    async def monitor_scalps(self):
        """Monitor active scalping positions."""
        for scalp in self.active_orders[:]:
            try:
                # Check if orders are still active
                main_status = await self.suite.orders.get_order_status(scalp['bracket'].main_order_id)

                if main_status.status in ["Filled", "Cancelled", "Rejected"]:
                    print(f"Scalp completed: {scalp['direction']} - {main_status.status}")
                    self.active_orders.remove(scalp)

                # Time-based cancellation (scalps should be quick)
                elif (asyncio.get_event_loop().time() - scalp['timestamp']) > 300:  # 5 minutes
                    print(f"Cancelling stale scalp order: {scalp['bracket'].main_order_id}")
                    await self.suite.orders.cancel_order(scalp['bracket'].main_order_id)
                    self.active_orders.remove(scalp)

            except Exception as e:
                print(f"Error monitoring scalp: {e}")

async def main():
    # Create suite with order book feature
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["15sec", "1min"],
        features=["orderbook"],  # Essential for order book analysis
        initial_days=1
    )

    strategy = OrderBookScalpingStrategy(suite)

    # Initialize order book
    if not await strategy.initialize_orderbook():
        print("Cannot proceed without order book data")
        return

    # Event handlers
    async def on_tick(event):
        tick_data = event.data

        # Store tick for analysis
        strategy.tick_history.append({
            'price': tick_data.get('price', 0),
            'size': tick_data.get('size', 0),
            'aggressor': tick_data.get('aggressor', 'unknown'),
            'timestamp': asyncio.get_event_loop().time()
        })

        # Analyze every 10th tick to avoid over-trading
        if len(strategy.tick_history) % 10 == 0:
            # Check for order book imbalances
            ob_analysis = await strategy.analyze_order_book_imbalance()
            tape_analysis = await strategy.analyze_tape_reading()

            # Look for confluence between order book and tape
            if ob_analysis and tape_analysis:
                if (ob_analysis['direction'] == tape_analysis['direction'] and
                    len(strategy.active_orders) == 0):  # No active scalps

                    print(f"\nScalping signal detected:")
                    print(f"  Order Book: {ob_analysis['direction']} ({ob_analysis['strength']:.2f})")
                    print(f"  Tape: {tape_analysis['direction']} ({tape_analysis['strength']:.2f})")

                    await strategy.place_scalp_order(ob_analysis['direction'], {
                        'orderbook': ob_analysis,
                        'tape': tape_analysis
                    })

    async def on_order_filled(event):
        order_data = event.data
        print(f"SCALP FILL: {order_data.get('order_id')} at ${order_data.get('fill_price', 0):.2f}")

    # Register events
    await suite.on(EventType.TICK, on_tick)
    await suite.on(EventType.ORDER_FILLED, on_order_filled)

    print("Order Book Scalping Strategy Active")
    print("Analyzing market microstructure for scalping opportunities...")
    print("Press Ctrl+C to exit")

    try:
        while True:
            await asyncio.sleep(5)

            # Monitor active scalps
            await strategy.monitor_scalps()

            # Display status
            current_price = await suite.data.get_current_price()
            active_scalps = len(strategy.active_orders)
            recent_ticks = len(strategy.tick_history)

            print(f"Price: ${current_price:.2f} | Active Scalps: {active_scalps} | Ticks: {recent_ticks}")

    except KeyboardInterrupt:
        print("\nShutting down scalping strategy...")

        # Cancel any active orders
        for scalp in strategy.active_orders:
            try:
                await suite.orders.cancel_order(scalp['bracket'].main_order_id)
                print(f"Cancelled scalp order: {scalp['bracket'].main_order_id}")
            except Exception as e:
                print(f"Error cancelling order: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Safety Guidelines for Advanced Trading

!!! danger "Critical Safety Reminders"

    1. **Demo Accounts Only**: Always test with simulated accounts first
    2. **Position Sizing**: Never risk more than 2% per trade
    3. **Stop Losses**: Always use stop losses - never trade without them
    4. **Market Hours**: Be aware of futures market hours and rollover dates
    5. **Margin Requirements**: Ensure sufficient margin for all positions
    6. **Monitoring**: Never leave positions unmonitored
    7. **Risk Management**: Implement portfolio-level risk controls
    8. **Paper Trading**: Thoroughly test all strategies before live trading

## Common Pitfalls to Avoid

- **Over-leveraging**: Using too much leverage relative to account size
- **Over-trading**: Placing too many trades based on marginal signals
- **Ignoring Risk Management**: Not implementing proper stop losses and position sizing
- **Chasing Markets**: Entering trades after big moves have already occurred
- **Emotional Trading**: Making decisions based on fear or greed
- **Inadequate Testing**: Not thoroughly backtesting strategies before live trading
- **Poor Timing**: Trading during low liquidity periods or major news events

## Next Steps

After mastering these advanced examples:

1. **Develop Your Own Strategies**: Combine different techniques to create unique approaches
2. **Implement Backtesting**: Test strategies on historical data before live trading
3. **Build Risk Management Systems**: Create comprehensive risk controls
4. **Optimize Performance**: Fine-tune parameters based on market conditions
5. **Scale Gradually**: Start small and gradually increase position sizes as you gain confidence

For more examples, see:
- [Real-time Data Processing](realtime.md)
- [Backtesting Strategies](backtesting.md)
- [Basic Usage Examples](basic.md)
