# Trading Sessions Guide

!!! warning "Experimental Feature"
    The ETH vs RTH Trading Sessions feature is experimental and has not been thoroughly tested with live market data. Use with caution in production environments. Session boundaries may need adjustment based on specific contract specifications.

## Overview

The Trading Sessions module enables you to filter and analyze market data based on different trading sessions:

- **RTH (Regular Trading Hours)**: Traditional market hours (typically 9:30 AM - 4:00 PM ET for equities)
- **ETH (Electronic Trading Hours)**: Extended/overnight trading hours
- **BOTH**: All available trading hours (default behavior)

This feature is particularly useful for:
- Separating overnight volatility from regular session price action
- Calculating session-specific technical indicators
- Analyzing volume profiles by session type
- Backtesting strategies with session-aware logic

## Quick Start

### Basic Session Filtering

```python
from project_x_py import TradingSuite
from project_x_py.sessions import SessionConfig, SessionType

# RTH-only trading (9:30 AM - 4:00 PM ET)
rth_suite = await TradingSuite.create(
    "MNQ",
    timeframes=["1min", "5min"],
    session_config=SessionConfig(session_type=SessionType.RTH)
)

# ETH-only analysis (overnight sessions, excludes maintenance)
eth_suite = await TradingSuite.create(
    "ES",
    session_config=SessionConfig(session_type=SessionType.ETH)
)

# Default behavior - includes all sessions
both_suite = await TradingSuite.create("CL")  # No session_config = BOTH
```

## Session Configuration

### SessionType Enum

```python
from project_x_py.sessions import SessionType

SessionType.RTH   # Regular Trading Hours only
SessionType.ETH   # Electronic Trading Hours only
SessionType.BOTH  # All trading hours (default)
```

### Product-Specific Sessions

Different futures products have different session schedules:

```python
# Equity Index Futures (ES, NQ, MNQ, MES)
equity_config = SessionConfig(
    session_type=SessionType.RTH,
    product="ES"  # RTH: 9:30 AM - 4:00 PM ET
)

# Energy Futures (CL)
energy_config = SessionConfig(
    session_type=SessionType.RTH,
    product="CL"  # RTH: 9:00 AM - 2:30 PM ET
)

# Treasury Futures (ZN, ZB)
treasury_config = SessionConfig(
    session_type=SessionType.RTH,
    product="ZN"  # RTH: 8:20 AM - 3:00 PM ET
)
```

### Maintenance Break Handling

The system automatically excludes daily maintenance windows:

```python
# ETH sessions automatically exclude 5:00 PM - 6:00 PM ET maintenance
eth_config = SessionConfig(session_type=SessionType.ETH)

# Data during maintenance periods is filtered out
# This prevents gaps and artifacts in technical indicators
```

## Session-Aware Indicators

### Calculating Indicators on Session Data

```python
from project_x_py.sessions import calculate_session_indicators

# Get RTH-only data
rth_data = await suite.data.get_session_bars(
    timeframe="5min",
    session_type=SessionType.RTH
)

# Calculate indicators on RTH data only
rth_with_indicators = await calculate_session_indicators(
    rth_data,
    indicators=["RSI", "MACD", "SMA"]
)

# Compare with ETH indicators
eth_data = await suite.data.get_session_bars(
    timeframe="5min",
    session_type=SessionType.ETH
)

eth_with_indicators = await calculate_session_indicators(
    eth_data,
    indicators=["RSI", "MACD", "SMA"]
)
```

### Session Volume Analysis

```python
# Analyze volume distribution by session
rth_volume = rth_data['volume'].sum()
eth_volume = eth_data['volume'].sum()

volume_ratio = rth_volume / (rth_volume + eth_volume)
print(f"RTH Volume: {volume_ratio:.1%} of total")

# Session-specific VWAP
rth_vwap = (rth_data['close'] * rth_data['volume']).sum() / rth_volume
eth_vwap = (eth_data['close'] * eth_data['volume']).sum() / eth_volume
```

## Session Statistics

### Performance Metrics by Session

```python
from project_x_py.sessions import SessionStatistics

# Initialize session statistics tracker
stats = SessionStatistics(suite)

# Calculate session-specific metrics
rth_stats = await stats.calculate_session_stats(SessionType.RTH)
eth_stats = await stats.calculate_session_stats(SessionType.ETH)

print(f"RTH Volatility: {rth_stats['volatility']:.2%}")
print(f"ETH Volatility: {eth_stats['volatility']:.2%}")
print(f"RTH Average Range: ${rth_stats['avg_range']:.2f}")
print(f"ETH Average Range: ${eth_stats['avg_range']:.2f}")
```

### Session Transition Analysis

```python
# Analyze overnight gaps (ETH close to RTH open)
gaps = await stats.calculate_overnight_gaps()

for gap in gaps:
    print(f"Date: {gap['date']}")
    print(f"ETH Close: ${gap['eth_close']:.2f}")
    print(f"RTH Open: ${gap['rth_open']:.2f}")
    print(f"Gap: ${gap['gap_size']:.2f} ({gap['gap_percent']:.2%})")
```

## Advanced Usage

### Custom Session Boundaries

```python
from project_x_py.sessions import SessionTimes
import pytz

# Define custom session times
custom_times = SessionTimes(
    rth_start=time(9, 0),   # 9:00 AM
    rth_end=time(15, 30),    # 3:30 PM
    eth_start=time(18, 0),   # 6:00 PM
    eth_end=time(17, 0),     # 5:00 PM next day
    timezone=pytz.timezone("US/Eastern")
)

custom_config = SessionConfig(
    session_type=SessionType.RTH,
    custom_times=custom_times
)
```

### Session Filtering with DataFrames

```python
# Manual session filtering on Polars DataFrames
import polars as pl

# Get raw data
data = await suite.data.get_data("1min")

# Apply session filter
from project_x_py.sessions import SessionFilterMixin

filter_mixin = SessionFilterMixin(
    session_config=SessionConfig(session_type=SessionType.RTH)
)

rth_filtered = filter_mixin.filter_session_data(data)
```

### Backtesting with Sessions

```python
# Backtest strategy on RTH data only
async def backtest_rth_strategy():
    # Historical data with RTH filter
    historical = await suite.client.get_bars(
        "MNQ",
        days=30,
        interval=300  # 5-minute bars
    )

    # Apply RTH filter
    rth_historical = filter_mixin.filter_session_data(historical)

    # Run strategy on RTH data
    signals = generate_signals(rth_historical)
    results = calculate_returns(signals, rth_historical)

    return results
```

## Performance Considerations

### Caching and Optimization

The session filtering system includes several optimizations:

1. **Boundary Caching**: Session boundaries are cached to avoid recalculation
2. **Lazy Evaluation**: Filters are only applied when data is accessed
3. **Efficient Filtering**: Uses Polars' vectorized operations for speed

```python
# Performance tips
# 1. Reuse SessionConfig objects
config = SessionConfig(session_type=SessionType.RTH)
suite1 = await TradingSuite.create("MNQ", session_config=config)
suite2 = await TradingSuite.create("ES", session_config=config)

# 2. Filter once, use multiple times
rth_data = await suite.data.get_session_bars("5min", SessionType.RTH)
# Use rth_data for multiple calculations without re-filtering
```

### Memory Management

```python
# For large datasets, consider chunking
async def process_large_dataset():
    for day in range(30):
        daily_data = await suite.client.get_bars("MNQ", days=1)
        rth_daily = filter_mixin.filter_session_data(daily_data)

        # Process daily chunk
        process_day(rth_daily)

        # Clear memory
        del daily_data, rth_daily
```

## Examples

### Complete Example: Session Comparison

```python
import asyncio
from project_x_py import TradingSuite
from project_x_py.sessions import SessionConfig, SessionType
from project_x_py.indicators import RSI, ATR

async def compare_sessions():
    # Create suites for each session type
    rth_suite = await TradingSuite.create(
        "MNQ",
        timeframes=["5min"],
        session_config=SessionConfig(session_type=SessionType.RTH)
    )

    eth_suite = await TradingSuite.create(
        "MNQ",
        timeframes=["5min"],
        session_config=SessionConfig(session_type=SessionType.ETH)
    )

    # Get session-specific data
    rth_bars = await rth_suite.data.get_data("5min")
    eth_bars = await eth_suite.data.get_data("5min")

    # Calculate indicators
    rth_with_rsi = RSI(rth_bars, period=14)
    eth_with_rsi = RSI(eth_bars, period=14)

    rth_with_atr = ATR(rth_with_rsi, period=14)
    eth_with_atr = ATR(eth_with_rsi, period=14)

    # Compare metrics
    rth_avg_atr = rth_with_atr['atr'].mean()
    eth_avg_atr = eth_with_atr['atr'].mean()

    print(f"RTH Average ATR: ${rth_avg_atr:.2f}")
    print(f"ETH Average ATR: ${eth_avg_atr:.2f}")
    print(f"Volatility Ratio: {eth_avg_atr/rth_avg_atr:.2f}x")

    # Cleanup
    await rth_suite.disconnect()
    await eth_suite.disconnect()

asyncio.run(compare_sessions())
```

### Example: Overnight Gap Trading

```python
async def overnight_gap_strategy():
    suite = await TradingSuite.create("ES", timeframes=["1min"])

    # Get overnight gap
    eth_close = await suite.data.get_session_close(SessionType.ETH)
    rth_open = await suite.data.get_session_open(SessionType.RTH)

    gap_size = rth_open - eth_close
    gap_percent = gap_size / eth_close

    # Trading logic based on gap
    if gap_percent > 0.005:  # 0.5% gap up
        # Fade the gap
        order = await suite.orders.place_limit_order(
            contract_id=suite.instrument_id,
            side=1,  # Sell
            size=1,
            limit_price=rth_open - 2.0
        )
    elif gap_percent < -0.005:  # 0.5% gap down
        # Buy the dip
        order = await suite.orders.place_limit_order(
            contract_id=suite.instrument_id,
            side=0,  # Buy
            size=1,
            limit_price=rth_open + 2.0
        )

    await suite.disconnect()
```

## Best Practices

### 1. Choose Appropriate Session Type

- **RTH**: Best for strategies focused on liquid, regular hours
- **ETH**: Useful for overnight positions and gap analysis
- **BOTH**: Default for continuous market analysis

### 2. Handle Session Transitions

```python
# Monitor session changes
async def on_session_change(event):
    if event.new_session == SessionType.RTH:
        print("RTH session started")
        # Adjust position sizing, activate day trading logic
    elif event.new_session == SessionType.ETH:
        print("ETH session started")
        # Reduce position size, switch to overnight logic

suite.on("session_change", on_session_change)
```

### 3. Validate Data Availability

```python
# Check data availability by session
rth_data = await suite.data.get_session_bars("1min", SessionType.RTH)

if rth_data.is_empty():
    print("No RTH data available")
    # Handle weekend/holiday/pre-market scenarios
```

### 4. Consider Time Zones

```python
# Always work in Eastern Time for US futures
from pytz import timezone

et = timezone("US/Eastern")
current_et = datetime.now(et)

# Session times are automatically handled in ET
```

## Troubleshooting

### Common Issues

1. **No data returned for session**
   - Check if market is open for that session
   - Verify product-specific session times
   - Ensure data subscription includes desired sessions

2. **Incorrect session boundaries**
   - Verify product configuration
   - Check for holidays/early closes
   - Consider using custom session times

3. **Performance degradation**
   - Use caching for repeated calculations
   - Filter data once and reuse
   - Consider chunking large datasets

### Debug Logging

```python
import logging

# Enable session filtering debug logs
logging.getLogger("project_x_py.sessions").setLevel(logging.DEBUG)

# This will show:
# - Session boundary calculations
# - Filter application details
# - Cache hit/miss information
```

## See Also

- [TradingSuite API](../api/trading-suite.md) - Main trading interface
- [Data Manager Guide](realtime.md) - Real-time data management
- [Indicators Guide](indicators.md) - Technical indicator calculations
- [Example Script](https://github.com/TexasCoding/project-x-py/blob/main/examples/sessions/16_eth_vs_rth_sessions_demo.py) - Complete demonstration
