# Position Manager API

Comprehensive async position tracking, portfolio management, and performance analytics with real-time monitoring.

## Overview

The PositionManager provides complete position tracking capabilities including real-time updates, performance analytics, risk monitoring, and portfolio management with full async support.

::: project_x_py.position_manager.PositionManager

## Quick Start

```python
from project_x_py import TradingSuite

async def basic_position_management():
    suite = await TradingSuite.create("MNQ")

    # Access the integrated position manager
    positions = suite.positions

    # Get current position
    position = await positions.get_position("MNQ")
    if position:
        print(f"Size: {position.size}")
        print(f"Avg Price: ${position.avg_price:.2f}")
        print(f"Unrealized PnL: ${position.unrealized_pnl:.2f}")

    await suite.disconnect()
```

## Position Tracking

### Current Positions

```python
async def current_positions():
    suite = await TradingSuite.create("MNQ")

    # Get specific position
    mnq_position = await suite.positions.get_position("MNQ")
    if mnq_position:
        print(f"MNQ Position:")
        print(f"  Size: {mnq_position.size}")
        print(f"  Side: {'Long' if mnq_position.size > 0 else 'Short'}")
        print(f"  Average Price: ${mnq_position.avg_price:.2f}")
        print(f"  Market Value: ${mnq_position.market_value:.2f}")
        print(f"  Unrealized PnL: ${mnq_position.unrealized_pnl:.2f}")
        print(f"  Realized PnL: ${mnq_position.realized_pnl:.2f}")

    # Get all positions
    all_positions = await suite.positions.get_all_positions()
    for instrument, position in all_positions.items():
        print(f"{instrument}: {position.size} @ ${position.avg_price:.2f}")

    await suite.disconnect()
```

### Position Details

```python
async def position_details():
    suite = await TradingSuite.create("MNQ")

    position = await suite.positions.get_position("MNQ")
    if position:
        # Basic information
        print(f"Instrument: {position.instrument}")
        print(f"Size: {position.size}")
        print(f"Average Price: ${position.avg_price:.2f}")

        # P&L information
        print(f"Unrealized PnL: ${position.unrealized_pnl:.2f}")
        print(f"Realized PnL: ${position.realized_pnl:.2f}")
        print(f"Total PnL: ${position.total_pnl:.2f}")

        # Market information
        print(f"Current Price: ${position.current_price:.2f}")
        print(f"Market Value: ${position.market_value:.2f}")

        # Risk metrics
        print(f"Position Value: ${position.position_value:.2f}")
        print(f"Max Drawdown: ${position.max_drawdown:.2f}")

        # Timestamps
        print(f"Opened: {position.open_time}")
        print(f"Last Updated: {position.last_update}")

    await suite.disconnect()
```

## Portfolio Management

### Portfolio Overview

```python
async def portfolio_overview():
    suite = await TradingSuite.create("MNQ")

    # Get comprehensive portfolio metrics
    portfolio_metrics = await suite.positions.get_portfolio_metrics()

    print("Portfolio Overview:")
    print(f"  Total Value: ${portfolio_metrics['total_portfolio_value']:,.2f}")
    print(f"  Total PnL: ${portfolio_metrics['total_pnl']:,.2f}")
    print(f"  Unrealized PnL: ${portfolio_metrics['unrealized_pnl']:,.2f}")
    print(f"  Realized PnL: ${portfolio_metrics['realized_pnl']:,.2f}")
    print(f"  Number of Positions: {portfolio_metrics['position_count']}")

    # Performance metrics
    performance = portfolio_metrics.get('performance', {})
    print("\nPerformance Metrics:")
    print(f"  Return: {performance.get('return_percentage', 0):.2f}%")
    print(f"  Sharpe Ratio: {performance.get('sharpe_ratio', 0):.2f}")
    print(f"  Max Drawdown: {performance.get('max_drawdown_percentage', 0):.2f}%")
    print(f"  Win Rate: {performance.get('win_rate', 0):.1f}%")

    await suite.disconnect()
```

### Risk Metrics

```python
async def risk_metrics():
    suite = await TradingSuite.create("MNQ")

    # Get risk analysis
    risk_analysis = await suite.positions.get_risk_analysis()

    print("Risk Analysis:")
    print(f"  Portfolio Beta: {risk_analysis.get('beta', 0):.2f}")
    print(f"  Value at Risk (95%): ${risk_analysis.get('var_95', 0):,.2f}")
    print(f"  Expected Shortfall: ${risk_analysis.get('expected_shortfall', 0):,.2f}")
    print(f"  Maximum Position Size: {risk_analysis.get('max_position_size', 0)}")

    # Position concentration
    concentration = risk_analysis.get('concentration', {})
    print("\nPosition Concentration:")
    for instrument, percentage in concentration.items():
        print(f"  {instrument}: {percentage:.1f}%")

    await suite.disconnect()
```

## Performance Analytics

### Trade Analytics


```python
async def trade_analytics():
    suite = await TradingSuite.create("MNQ")

    # Get detailed analytics
    analytics = await suite.positions.get_analytics()

    print("Trade Analytics:")
    print(f"  Total Trades: {analytics['total_trades']}")
    print(f"  Winning Trades: {analytics['winning_trades']}")
    print(f"  Losing Trades: {analytics['losing_trades']}")
    print(f"  Win Rate: {analytics['win_rate']:.1f}%")

    print(f"\nProfit/Loss:")
    print(f"  Average Win: ${analytics['avg_winning_trade']:,.2f}")
    print(f"  Average Loss: ${analytics['avg_losing_trade']:,.2f}")
    print(f"  Largest Win: ${analytics['largest_winning_trade']:,.2f}")
    print(f"  Largest Loss: ${analytics['largest_losing_trade']:,.2f}")
    print(f"  Profit Factor: {analytics['profit_factor']:.2f}")

    print(f"\nTrade Duration:")
    print(f"  Average Hold Time: {analytics['avg_hold_time_hours']:.1f} hours")
    print(f"  Shortest Trade: {analytics['shortest_trade_minutes']:.0f} minutes")
    print(f"  Longest Trade: {analytics['longest_trade_hours']:.1f} hours")

    await suite.disconnect()
```

### Performance Tracking

```python
async def performance_tracking():
    suite = await TradingSuite.create("MNQ")

    # Track performance over time
    performance_history = await suite.positions.get_performance_history(
        days=30  # Last 30 days
    )

    for date, metrics in performance_history.items():
        print(f"{date}: PnL ${metrics['daily_pnl']:,.2f}, "
              f"Return {metrics['daily_return']:.2f}%")

    # Monthly performance summary
    monthly_performance = await suite.positions.get_monthly_performance()
    for month, stats in monthly_performance.items():
        print(f"{month}: ${stats['total_pnl']:,.2f} "
              f"({stats['return_percentage']:+.1f}%)")

    await suite.disconnect()
```

## Real-time Monitoring

### Position Updates

```python
from project_x_py import EventType

async def position_monitoring():
    suite = await TradingSuite.create("MNQ", timeframes=["1min"])

    # Real-time position update handler
    async def on_position_changed(event):
        position = event.data
        print(f"Position Update - {position.instrument}:")
        print(f"  Size: {position.size}")
        print(f"  Unrealized PnL: ${position.unrealized_pnl:.2f}")
        print(f"  Current Price: ${position.current_price:.2f}")

    # Register for position events
    await suite.on(EventType.POSITION_CHANGED, on_position_changed)

    # Keep monitoring
    await asyncio.sleep(300)  # Monitor for 5 minutes
    await suite.disconnect()
```

### P&L Alerts

```python
async def pnl_alerts():
    suite = await TradingSuite.create("MNQ")

    # Set up P&L monitoring
    async def monitor_pnl():
        while True:
            portfolio_metrics = await suite.positions.get_portfolio_metrics()
            unrealized_pnl = portfolio_metrics.get('unrealized_pnl', 0)

            # Alert thresholds
            if unrealized_pnl < -500:  # $500 loss
                print(f"= LOSS ALERT: ${unrealized_pnl:.2f}")
            elif unrealized_pnl > 1000:  # $1000 profit
                print(f"< PROFIT ALERT: ${unrealized_pnl:.2f}")

            await asyncio.sleep(30)  # Check every 30 seconds

    # Run monitoring
    await monitor_pnl()
```

## Position Operations

### Position Modifications

```python
async def position_modifications():
    suite = await TradingSuite.create("MNQ")

    # Scale into position
    await suite.positions.scale_into_position(
        instrument="MNQ",
        target_size=5,       # Target 5 contracts
        scale_levels=3,      # Scale in over 3 levels
        price_increment=5.0  # $5 between levels
    )

    # Scale out of position
    await suite.positions.scale_out_position(
        instrument="MNQ",
        scale_levels=3,      # Scale out over 3 levels
        price_increment=10.0 # $10 between levels
    )

    # Hedge position
    hedge_result = await suite.positions.hedge_position(
        instrument="MNQ",
        hedge_ratio=0.5,     # 50% hedge
        hedge_instrument="ES" # Hedge with ES
    )

    await suite.disconnect()
```

### Position Closing

```python
async def position_closing():
    suite = await TradingSuite.create("MNQ")

    # Close specific position
    close_result = await suite.positions.close_position(
        instrument="MNQ",
        method="market",     # Market order
        partial_size=None    # Close entire position
    )

    # Partial close
    partial_close = await suite.positions.close_position(
        instrument="MNQ",
        method="limit",
        limit_price=21100.0,
        partial_size=2       # Close 2 contracts only
    )

    # Close all positions
    close_all = await suite.positions.close_all_positions(
        method="market",
        emergency=False      # False = normal close, True = emergency
    )

    await suite.disconnect()
```

## Reporting

### Position Reports

```python
async def position_reports():
    suite = await TradingSuite.create("MNQ")

    # Generate position report
    report = await suite.positions.generate_report(
        format="detailed",   # "summary", "detailed", "csv"
        include_closed=True, # Include closed positions
        date_range=30        # Last 30 days
    )

    # Save report
    with open("position_report.txt", "w") as f:
        f.write(report)

    # CSV export
    csv_data = await suite.positions.export_to_csv(
        include_metrics=True,
        date_range=30
    )

    with open("positions.csv", "w") as f:
        f.write(csv_data)

    await suite.disconnect()
```

### Trade Journal Integration

```python
async def trade_journal():
    suite = await TradingSuite.create("MNQ")

    # Add trade notes
    await suite.positions.add_trade_note(
        position_id="some_position_id",
        note="Entered on RSI oversold + support bounce",
        tags=["RSI", "support", "scalp"]
    )

    # Get trade history with notes
    trade_history = await suite.positions.get_trade_history(
        include_notes=True,
        days=7  # Last 7 days
    )

    for trade in trade_history:
        print(f"Trade: {trade['instrument']} {trade['side']}")
        print(f"  Entry: ${trade['entry_price']:.2f}")
        print(f"  Exit: ${trade['exit_price']:.2f}")
        print(f"  PnL: ${trade['pnl']:.2f}")
        if trade.get('notes'):
            print(f"  Notes: {trade['notes']}")

    await suite.disconnect()
```

## Position Statistics

```python
async def position_statistics():
    suite = await TradingSuite.create("MNQ")

    # Get position manager statistics
    stats = await suite.positions.get_stats()

    print("Position Manager Statistics:")
    print(f"  Active Positions: {stats['active_positions']}")
    print(f"  Total Trades Today: {stats['trades_today']}")
    print(f"  P&L Today: ${stats['pnl_today']:,.2f}")
    print(f"  Win Rate (30d): {stats['win_rate_30d']:.1f}%")
    print(f"  Average Trade Size: {stats['avg_trade_size']:.1f}")

    # Performance metrics
    performance = stats.get('performance_metrics', {})
    print("\nPerformance Metrics:")
    print(f"  Sharpe Ratio: {performance.get('sharpe_ratio', 0):.2f}")
    print(f"  Sortino Ratio: {performance.get('sortino_ratio', 0):.2f}")
    print(f"  Calmar Ratio: {performance.get('calmar_ratio', 0):.2f}")
    print(f"  Max Drawdown: {performance.get('max_drawdown', 0):.2f}%")

    await suite.disconnect()
```

## Configuration

### PositionManagerConfig

```python
from project_x_py.types import PositionManagerConfig

async def configure_position_manager():
    # Custom position manager configuration
    position_config = PositionManagerConfig(
        track_unrealized=True,         # Track unrealized P&L
        calculate_metrics=True,        # Calculate performance metrics
        update_frequency=1.0,          # Update frequency in seconds
        enable_trade_journal=True,     # Enable trade notes
        auto_calculate_risk=True,      # Auto-calculate risk metrics
        max_position_history=1000      # Max historical positions
    )

    suite = await TradingSuite.create(
        "MNQ",
        position_manager_config=position_config
    )

    await suite.disconnect()
```

## Best Practices

### Position Management

```python
#  Good: Monitor positions regularly
async def monitor_positions(suite):
    while True:
        positions = await suite.positions.get_all_positions()
        for instrument, position in positions.items():
            # Check for risk limits
            if abs(position.unrealized_pnl) > 500:  # $500 risk limit
                print(f"Risk limit exceeded for {instrument}")
                # Take action (close, hedge, etc.)

        await asyncio.sleep(60)  # Check every minute

#  Good: Use proper error handling
try:
    position = await suite.positions.get_position("MNQ")
    if position.size > 10:  # Position too large
        await suite.positions.reduce_position("MNQ", percentage=0.5)
except PositionNotFoundError:
    print("No position found")

#  Good: Track performance metrics
metrics = await suite.positions.get_analytics()
if metrics['win_rate'] < 0.4:  # Win rate below 40%
    print("Strategy performance declining")
```

### Risk Management

```python
#  Good: Set position limits
MAX_POSITION_SIZE = 5
MAX_PORTFOLIO_RISK = 1000.0

async def check_risk_limits(suite):
    portfolio_metrics = await suite.positions.get_portfolio_metrics()

    # Check portfolio risk
    if abs(portfolio_metrics['unrealized_pnl']) > MAX_PORTFOLIO_RISK:
        print("Portfolio risk limit exceeded")
        await suite.positions.close_all_positions(method="market")

    # Check individual position sizes
    positions = await suite.positions.get_all_positions()
    for instrument, position in positions.items():
        if abs(position.size) > MAX_POSITION_SIZE:
            print(f"Position size limit exceeded for {instrument}")
            await suite.positions.reduce_position(
                instrument,
                target_size=MAX_POSITION_SIZE
            )
```

## See Also

- [Trading Suite API](trading-suite.md) - Main trading interface
- [Order Manager API](order-manager.md) - Order management
- [Risk Management Guide](../guide/risk.md) - Risk management concepts
- [Statistics API](statistics.md) - Performance monitoring
