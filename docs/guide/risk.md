# Risk Management Guide

Risk management is crucial for successful trading. The ProjectX SDK provides comprehensive risk management tools through the RiskManager component and ManagedTrade class to help protect your capital and automate risk-based position sizing.

## Overview

The SDK's risk management system provides:

- **Position sizing** based on risk amount and stop distance
- **Account-level risk limits** (daily loss, drawdown, position size)
- **Real-time risk monitoring** with automatic alerts
- **ManagedTrade** for automated risk-controlled order execution
- **Risk metrics calculation** (VaR, Sharpe ratio, max drawdown)
- **Integration** with all trading components

## Getting Started

### Enable Risk Manager

```python
from project_x_py import TradingSuite, Features

async def basic_risk_setup():
    # Enable risk manager feature
    suite = await TradingSuite.create(
        "MNQ",
        features=[Features.RISK_MANAGER]
    )

    # Check if risk manager is available
    if suite.risk_manager:
        print("Risk Manager enabled")

        # Get current risk limits
        limits = await suite.risk_manager.get_limits()
        print(f"Max position size: {limits.max_position_size}")
        print(f"Max daily loss: ${limits.max_daily_loss:.2f}")

    await suite.disconnect()
```

### Basic Risk Configuration

```python
from project_x_py.risk_manager import RiskConfig

async def configure_risk():
    # Define risk parameters
    risk_config = RiskConfig(
        max_position_size=5,           # Max 5 contracts
        max_daily_loss=1000.0,         # Max $1000 daily loss
        max_drawdown_percent=10.0,     # Max 10% drawdown
        position_size_percent=2.0,     # 2% of account per trade
        stop_loss_percent=1.0,         # 1% stop loss
        risk_reward_ratio=2.0          # 1:2 risk/reward
    )

    suite = await TradingSuite.create(
        "MNQ",
        features=["risk_manager"],
        risk_config=risk_config
    )

    await suite.disconnect()
```

## Position Sizing

### Risk-Based Position Sizing

```python
async def risk_based_sizing():
    suite = await TradingSuite.create("MNQ", features=["risk_manager"])

    if suite.risk_manager:
        # Calculate position size based on risk amount
        position_size = await suite.risk_manager.calculate_position_size(
            risk_amount=200.0,      # Risk $200 per trade
            entry_price=21050.0,    # Entry price
            stop_price=21025.0,     # Stop loss price
            contract_size=20        # MNQ contract size ($20/point)
        )

        print(f"Recommended position size: {position_size} contracts")

        # Alternative: Calculate based on account percentage
        account_size = await suite.risk_manager.get_account_size()
        risk_amount_pct = account_size * 0.02  # 2% of account

        position_size_pct = await suite.risk_manager.calculate_position_size(
            risk_amount=risk_amount_pct,
            entry_price=21050.0,
            stop_price=21025.0,
            contract_size=20
        )

        print(f"Position size (2% risk): {position_size_pct} contracts")

    await suite.disconnect()
```

### ATR-Based Position Sizing

```python
from project_x_py.indicators import ATR

async def atr_based_sizing():
    suite = await TradingSuite.create("MNQ", features=["risk_manager"], timeframes=["5min"])

    # Get recent data and calculate ATR
    bars = await suite.data.get_data("5min", count=100)
    data_with_atr = bars.pipe(ATR, period=14)

    current_atr = data_with_atr.tail(1)["atr_14"].item()
    current_price = await suite.data.get_current_price()

    if suite.risk_manager:
        # Use 2x ATR as stop distance
        stop_distance = current_atr * 2
        stop_price = current_price - stop_distance  # For long position

        # Calculate position size
        position_size = await suite.risk_manager.calculate_position_size(
            risk_amount=250.0,
            entry_price=current_price,
            stop_price=stop_price,
            contract_size=20
        )

        print(f"Current ATR: {current_atr:.2f}")
        print(f"Stop distance: {stop_distance:.2f}")
        print(f"Position size: {position_size} contracts")

    await suite.disconnect()
```

## ManagedTrade

The ManagedTrade class provides automated risk-controlled trading with built-in position sizing and risk management.

### Basic ManagedTrade

```python
from project_x_py.risk_manager import ManagedTrade

async def basic_managed_trade():
    suite = await TradingSuite.create("MNQ", features=["risk_manager"])

    # Create a managed trade with risk parameters
    managed_trade = ManagedTrade(
        suite=suite,
        max_risk_per_trade=200.0,    # Risk $200 per trade
        risk_reward_ratio=2.0,       # 1:2 risk/reward
        max_position_size=3          # Max 3 contracts
    )

    # Execute trade with automatic risk management
    result = await managed_trade.execute_trade(
        side=0,  # Buy
        entry_signal="RSI oversold + support bounce",
        stop_loss_type="atr",        # ATR-based stop
        take_profit_type="fixed"     # Fixed profit target
    )

    if result.success:
        print(f"Trade executed successfully:")
        print(f"  Entry Order: {result.main_order_id}")
        print(f"  Stop Loss: {result.stop_order_id}")
        print(f"  Take Profit: {result.target_order_id}")
        print(f"  Position Size: {result.position_size}")
        print(f"  Risk Amount: ${result.risk_amount:.2f}")
    else:
        print(f"Trade rejected: {result.error}")

    await suite.disconnect()
```

### Advanced ManagedTrade

```python
async def advanced_managed_trade():
    suite = await TradingSuite.create("MNQ", features=["risk_manager"], timeframes=["5min"])

    # Advanced managed trade configuration
    managed_trade = ManagedTrade(
        suite=suite,
        max_risk_per_trade=300.0,
        risk_reward_ratio=2.5,
        max_position_size=5,
        use_trailing_stop=True,      # Enable trailing stop
        trailing_stop_distance=1.5,  # 1.5x ATR trailing distance
        partial_profit_levels=[      # Take partial profits
            {"percentage": 0.5, "at_reward_ratio": 1.0},  # 50% at 1:1
            {"percentage": 0.3, "at_reward_ratio": 1.5}   # 30% at 1.5:1
        ]
    )

    # Execute with custom parameters
    result = await managed_trade.execute_trade(
        side=0,  # Buy
        entry_signal="Breakout above resistance",
        entry_type="limit",          # Use limit order for entry
        entry_price=21075.0,         # Specific entry price
        stop_loss_type="percentage", # Percentage-based stop
        stop_loss_percentage=1.2,    # 1.2% stop loss
        take_profit_type="multiple", # Multiple profit targets
        profit_targets=[21150.0, 21200.0, 21250.0],
        time_in_force="DAY"         # Day order
    )

    if result.success:
        print(f"Advanced trade executed:")
        print(f"  Position Size: {result.position_size} contracts")
        print(f"  Entry Price: ${result.entry_price:.2f}")
        print(f"  Stop Loss: ${result.stop_loss_price:.2f}")
        print(f"  Profit Targets: {[f'${p:.2f}' for p in result.profit_targets]}")

    await suite.disconnect()
```

## Risk Limits and Monitoring

### Setting Risk Limits

```python
async def set_risk_limits():
    suite = await TradingSuite.create("MNQ", features=["risk_manager"])

    if suite.risk_manager:
        # Set account-level risk limits
        await suite.risk_manager.set_limits(
            max_position_size=10,        # Max position size
            max_daily_loss=2000.0,       # Max daily loss
            max_drawdown_percent=15.0,   # Max drawdown percentage
            max_correlation=0.7,         # Max position correlation
            max_sector_exposure=50.0,    # Max sector exposure %
            risk_per_trade_percent=2.0   # Max risk per trade
        )

        # Set instrument-specific limits
        await suite.risk_manager.set_instrument_limits(
            instrument="MNQ",
            max_position=5,              # Max MNQ position
            max_daily_trades=20,         # Max trades per day
            max_trade_size=3             # Max single trade size
        )

        print("Risk limits updated")

    await suite.disconnect()
```

### Real-time Risk Monitoring

```python
from project_x_py import EventType

async def real_time_risk_monitoring():
    suite = await TradingSuite.create("MNQ", features=["risk_manager"])

    # Risk event handlers
    async def on_risk_limit_exceeded(event):
        print(f"= RISK LIMIT EXCEEDED: {event.limit_type}")
        print(f"   Current: {event.current_value}")
        print(f"   Limit: {event.limit_value}")

        # Take action - close positions, cancel orders, etc.
        if event.limit_type == "daily_loss":
            await suite.orders.cancel_all_orders()
            await suite.positions.close_all_positions(method="market")

    async def on_risk_warning(event):
        print(f" Risk Warning: {event.warning_type}")
        print(f"   Message: {event.message}")

    # Register risk event handlers
    await suite.on(EventType.RISK_LIMIT_EXCEEDED, on_risk_limit_exceeded)
    await suite.on(EventType.RISK_WARNING, on_risk_warning)

    # Monitor risk continuously
    while True:
        if suite.risk_manager:
            # Get current risk metrics
            risk_metrics = await suite.risk_manager.get_risk_metrics()

            print(f"Risk Metrics:")
            print(f"  Current Risk: ${risk_metrics.current_risk:.2f}")
            print(f"  Daily P&L: ${risk_metrics.daily_pnl:.2f}")
            print(f"  Drawdown: {risk_metrics.drawdown_percent:.1f}%")
            print(f"  Risk Utilization: {risk_metrics.risk_utilization:.1f}%")

            # Check if approaching limits
            if risk_metrics.risk_utilization > 80:
                print(" High risk utilization - reduce position size")

            if risk_metrics.drawdown_percent > 8:
                print(" High drawdown - consider reducing exposure")

        await asyncio.sleep(60)  # Check every minute
```

### Risk Alerts and Actions

```python
async def risk_alerts_and_actions():
    suite = await TradingSuite.create("MNQ", features=["risk_manager"])

    if suite.risk_manager:
        # Configure risk alerts
        await suite.risk_manager.configure_alerts(
            daily_loss_alert=500.0,      # Alert at $500 daily loss
            drawdown_alert=5.0,          # Alert at 5% drawdown
            position_size_alert=80.0,    # Alert at 80% of max position
            correlation_alert=0.6        # Alert at 60% correlation
        )

        # Set automatic risk actions
        await suite.risk_manager.configure_auto_actions(
            daily_loss_limit_action="close_all",     # Close all positions
            max_drawdown_action="reduce_positions",  # Reduce position sizes
            correlation_limit_action="warn_only"     # Warning only
        )

        # Check if trade would exceed limits
        trade_allowed = await suite.risk_manager.check_trade_allowed(
            instrument="MNQ",
            side=0,  # Buy
            size=2,
            price=21050.0
        )

        if not trade_allowed.allowed:
            print(f"Trade not allowed: {trade_allowed.reason}")
        else:
            print("Trade pre-approved by risk manager")

    await suite.disconnect()
```

## Risk Metrics and Analytics

### Portfolio Risk Analysis

```python
async def portfolio_risk_analysis():
    suite = await TradingSuite.create("MNQ", features=["risk_manager"])

    if suite.risk_manager:
        # Get comprehensive risk analysis
        risk_analysis = await suite.risk_manager.get_risk_analysis()

        print(f"Portfolio Risk Analysis:")
        print(f"  Value at Risk (95%): ${risk_analysis.var_95:.2f}")
        print(f"  Expected Shortfall: ${risk_analysis.expected_shortfall:.2f}")
        print(f"  Beta: {risk_analysis.beta:.2f}")
        print(f"  Sharpe Ratio: {risk_analysis.sharpe_ratio:.2f}")
        print(f"  Sortino Ratio: {risk_analysis.sortino_ratio:.2f}")
        print(f"  Max Drawdown: {risk_analysis.max_drawdown:.2f}%")
        print(f"  Calmar Ratio: {risk_analysis.calmar_ratio:.2f}")

        # Position concentration analysis
        concentration = risk_analysis.concentration_analysis
        print(f"\nPosition Concentration:")
        for instrument, percentage in concentration.items():
            print(f"  {instrument}: {percentage:.1f}%")

        # Correlation analysis
        correlations = await suite.risk_manager.get_correlation_matrix()
        print(f"\nCorrelation Matrix:")
        print(correlations)

    await suite.disconnect()
```

### Historical Performance Analysis

```python
async def historical_performance_analysis():
    suite = await TradingSuite.create("MNQ", features=["risk_manager"])

    if suite.risk_manager:
        # Get historical risk metrics
        historical_metrics = await suite.risk_manager.get_historical_metrics(
            days=30  # Last 30 days
        )

        print(f"30-Day Performance Analysis:")
        print(f"  Total Return: {historical_metrics.total_return:.2f}%")
        print(f"  Annualized Return: {historical_metrics.annualized_return:.2f}%")
        print(f"  Volatility: {historical_metrics.volatility:.2f}%")
        print(f"  Win Rate: {historical_metrics.win_rate:.1f}%")
        print(f"  Profit Factor: {historical_metrics.profit_factor:.2f}")
        print(f"  Recovery Factor: {historical_metrics.recovery_factor:.2f}")

        # Risk-adjusted metrics
        print(f"\nRisk-Adjusted Metrics:")
        print(f"  Sharpe Ratio: {historical_metrics.sharpe_ratio:.2f}")
        print(f"  Sortino Ratio: {historical_metrics.sortino_ratio:.2f}")
        print(f"  Calmar Ratio: {historical_metrics.calmar_ratio:.2f}")
        print(f"  Information Ratio: {historical_metrics.information_ratio:.2f}")

        # Drawdown analysis
        drawdown_stats = historical_metrics.drawdown_analysis
        print(f"\nDrawdown Analysis:")
        print(f"  Max Drawdown: {drawdown_stats.max_drawdown:.2f}%")
        print(f"  Average Drawdown: {drawdown_stats.avg_drawdown:.2f}%")
        print(f"  Recovery Time: {drawdown_stats.avg_recovery_days:.1f} days")

    await suite.disconnect()
```

## Integration with Trading Components

### Risk-Aware Order Management

```python
async def risk_aware_orders():
    suite = await TradingSuite.create("MNQ", features=["risk_manager"])

    # Orders automatically check risk limits
    try:
        # This order will be checked against risk limits
        order = await suite.orders.place_limit_order(
            contract_id=suite.instrument_id,
            side=0,  # Buy
            size=3,  # Might exceed risk limits
            limit_price=21050.0
        )
        print(f"Order placed: {order.order_id}")

    except RiskLimitExceededError as e:
        print(f"Order rejected by risk manager: {e}")

        # Get recommended position size
        if suite.risk_manager:
            recommended_size = await suite.risk_manager.get_recommended_size(
                instrument="MNQ",
                side=0,
                price=21050.0
            )
            print(f"Recommended size: {recommended_size}")

            # Place order with recommended size
            order = await suite.orders.place_limit_order(
                contract_id=suite.instrument_id,
                side=0,
                size=recommended_size,
                limit_price=21050.0
            )

    await suite.disconnect()
```

### Risk-Based Position Management

```python
async def risk_based_position_management():
    suite = await TradingSuite.create("MNQ", features=["risk_manager"])

    # Get current position
    position = await suite.positions.get_position("MNQ")

    if position and suite.risk_manager:
        # Analyze position risk
        position_risk = await suite.risk_manager.analyze_position_risk(position)

        print(f"Position Risk Analysis:")
        print(f"  Position Value: ${position_risk.position_value:.2f}")
        print(f"  Risk Amount: ${position_risk.risk_amount:.2f}")
        print(f"  Risk Percentage: {position_risk.risk_percentage:.2f}%")
        print(f"  Beta: {position_risk.beta:.2f}")

        # Check if position should be reduced
        if position_risk.risk_percentage > 3.0:  # Above 3% risk
            print("Position risk too high - reducing size")

            # Calculate new target size
            target_size = await suite.risk_manager.calculate_target_size(
                current_position=position,
                target_risk_percent=2.0  # Target 2% risk
            )

            # Reduce position
            await suite.positions.reduce_position(
                instrument="MNQ",
                target_size=target_size,
                method="market"
            )

    await suite.disconnect()
```

## Advanced Risk Strategies

### Portfolio Hedging

```python
async def portfolio_hedging():
    suite = await TradingSuite.create("MNQ", features=["risk_manager"])

    if suite.risk_manager:
        # Get portfolio exposure
        exposure = await suite.risk_manager.get_portfolio_exposure()

        if exposure.net_delta > 1000:  # Too much long exposure
            print("Portfolio too long - implementing hedge")

            # Calculate hedge size
            hedge_size = await suite.risk_manager.calculate_hedge_size(
                target_delta=0,      # Delta neutral
                hedge_instrument="ES" # Use ES to hedge MNQ
            )

            # Place hedge order
            hedge_order = await suite.orders.place_market_order(
                contract_id="CON.F.US.ES.U25",  # ES contract
                side=1,  # Sell for hedge
                size=hedge_size
            )

            print(f"Hedge order placed: {hedge_order.order_id}")

    await suite.disconnect()
```

### Dynamic Risk Scaling

```python
async def dynamic_risk_scaling():
    suite = await TradingSuite.create("MNQ", features=["risk_manager"], timeframes=["5min"])

    # Monitor volatility and adjust risk accordingly
    async def adjust_risk_for_volatility():
        # Calculate current market volatility
        bars = await suite.data.get_data("5min", count=100)
        data_with_atr = bars.pipe(ATR, period=14)
        current_atr = data_with_atr.tail(1)["atr_14"].item()

        # Get historical ATR for comparison
        avg_atr = data_with_atr["atr_14"].mean()
        volatility_ratio = current_atr / avg_atr

        if suite.risk_manager:
            # Adjust risk based on volatility
            base_risk = 200.0  # Base risk amount

            if volatility_ratio > 1.5:  # High volatility
                adjusted_risk = base_risk * 0.7  # Reduce risk
                print(f"High volatility detected - reducing risk to ${adjusted_risk:.2f}")
            elif volatility_ratio < 0.7:  # Low volatility
                adjusted_risk = base_risk * 1.3  # Increase risk
                print(f"Low volatility detected - increasing risk to ${adjusted_risk:.2f}")
            else:
                adjusted_risk = base_risk

            # Update risk manager settings
            await suite.risk_manager.set_dynamic_risk_amount(adjusted_risk)

    # Run volatility-based risk adjustment
    await adjust_risk_for_volatility()
    await suite.disconnect()
```

## Risk Management Best Practices

### 1. Always Define Your Risk

```python
#  Good: Define risk before entering trade
max_risk = 250.0  # $250 per trade
entry_price = 21050.0
stop_distance = 25.0  # $25 stop
position_size = max_risk / stop_distance  # Risk-based sizing

# L Bad: Arbitrary position sizing
# position_size = 5  # Why 5? No risk consideration
```

### 2. Use Stop Losses

```python
#  Good: Always use stop losses
await suite.orders.place_bracket_order(
    contract_id=suite.instrument_id,
    side=0,
    size=1,
    entry_price=21050.0,
    stop_offset=25.0,    # Stop loss defined
    target_offset=50.0   # Profit target defined
)

# L Bad: No stop loss
# await suite.orders.place_market_order(...)  # No protection
```

### 3. Monitor Risk Continuously

```python
#  Good: Continuous risk monitoring
async def monitor_risk():
    while True:
        risk_metrics = await suite.risk_manager.get_risk_metrics()
        if risk_metrics.daily_pnl < -500:  # Daily loss limit
            await suite.positions.close_all_positions(method="market")
            break
        await asyncio.sleep(60)

# L Bad: No risk monitoring
# Place trades and forget about risk
```

### 4. Diversify Risk

```python
#  Good: Spread risk across instruments
instruments = ["MNQ", "MES", "RTY"]  # Different indices
for instrument in instruments:
    # Place trades with risk limits per instrument
    pass

# L Bad: All risk in one instrument
# All trades in MNQ only - concentrated risk
```

### 5. Use ManagedTrade for Automation

```python
#  Good: Use ManagedTrade for consistent risk management
managed_trade = ManagedTrade(
    suite=suite,
    max_risk_per_trade=200.0,
    risk_reward_ratio=2.0
)
await managed_trade.execute_trade(side=0, entry_signal="RSI oversold")

# L Manual risk calculations every time (error-prone)
```

## Conclusion

Risk management is the foundation of successful trading. The ProjectX SDK provides comprehensive tools to:

- **Automate position sizing** based on risk amount
- **Monitor risk in real-time** with alerts and automatic actions
- **Enforce account-level limits** to protect capital
- **Analyze portfolio risk** with advanced metrics
- **Integrate risk management** with all trading components

Start with basic risk limits and position sizing, then gradually implement more advanced features like dynamic risk scaling and portfolio hedging as you become comfortable with the system.

**Remember**: The goal is not to eliminate risk (impossible in trading) but to manage and control it systematically.

## See Also


- [Position Management](positions.md) - Portfolio risk monitoring
- [Order Management](orders.md) - Risk-aware order placement
- [Statistics](../api/statistics.md) - Risk metrics and analytics
