# ETH vs RTH Trading Sessions - Complete Usage Guide

*Last Updated: 2025-08-28*
*Version: 3.4.0*
*Feature Status: ✅ Implemented & Tested*

## Overview

The ETH vs RTH Trading Sessions feature provides comprehensive session-aware trading capabilities throughout the ProjectX SDK. This allows you to filter all market data, indicators, and trading operations based on Electronic Trading Hours (ETH) vs Regular Trading Hours (RTH).

### Key Benefits
- **Accurate backtesting** with proper session boundaries
- **Session-specific analytics** (RTH vs ETH volume, VWAP, etc.)
- **Indicator calculations** that respect market sessions
- **Real-time session filtering** for live trading
- **Product-specific configurations** for all major futures

---

## Quick Start

### Basic Setup
```python
from project_x_py import TradingSuite, SessionConfig, SessionType

# Option 1: RTH-only trading (recommended for most strategies)
session_config = SessionConfig(session_type=SessionType.RTH)
suite = await TradingSuite.create("ES", session_config=session_config)

# Option 2: ETH (24-hour) - default behavior
suite = await TradingSuite.create("ES")  # Uses ETH by default

# Option 3: Custom session configuration
custom_config = SessionConfig(
    session_type=SessionType.RTH,
    market_timezone="America/New_York",
    product_sessions={"ES": custom_session_times}
)
suite = await TradingSuite.create("ES", session_config=custom_config)
```

### Immediate Usage
```python
# Get session-filtered data
rth_data = await suite.get_session_data("5min", SessionType.RTH)
eth_data = await suite.get_session_data("5min", SessionType.ETH)

# Switch sessions dynamically
await suite.set_session_type(SessionType.RTH)

# Get session statistics
stats = await suite.get_session_statistics()
print(f"RTH Volume: {stats['rth_volume']:,}")
```

---

## Session Configuration

### SessionType Enum
```python
from project_x_py.sessions import SessionType

SessionType.ETH     # Electronic Trading Hours (24-hour)
SessionType.RTH     # Regular Trading Hours (market-specific)
SessionType.CUSTOM  # Custom session definition
```

### SessionConfig Options
```python
from project_x_py.sessions import SessionConfig

# Basic configuration
config = SessionConfig(
    session_type=SessionType.RTH,           # ETH, RTH, or CUSTOM
    market_timezone="America/New_York",     # Market timezone
    use_exchange_timezone=True              # Use exchange timezone
)

# Advanced configuration with product overrides
config = SessionConfig(
    session_type=SessionType.RTH,
    product_sessions={
        "ES": SessionTimes(
            rth_start=time(9, 30),   # 9:30 AM ET
            rth_end=time(16, 0),     # 4:00 PM ET
            eth_start=time(18, 0),   # 6:00 PM ET (prev day)
            eth_end=time(17, 0)      # 5:00 PM ET
        ),
        "CL": SessionTimes(
            rth_start=time(9, 0),    # 9:00 AM ET
            rth_end=time(14, 30),    # 2:30 PM ET
            eth_start=time(18, 0),   # 6:00 PM ET (prev day)
            eth_end=time(17, 0)      # 5:00 PM ET
        )
    }
)
```

### Built-in Product Sessions
The SDK includes pre-configured session times for major futures:

| Product | RTH Hours (ET) | Description |
|---------|----------------|-------------|
| ES, NQ, YM, RTY, MNQ, MES | 9:30 AM - 4:00 PM | Equity index futures |
| CL | 9:00 AM - 2:30 PM | Crude oil |
| GC, SI | 8:20 AM - 1:30 PM | Precious metals |
| ZN | 8:20 AM - 3:00 PM | Treasury futures |

---

## TradingSuite Integration

### Creating Session-Aware TradingSuite
```python
# Method 1: With session config
session_config = SessionConfig(session_type=SessionType.RTH)
suite = await TradingSuite.create(
    "ES",
    timeframes=["1min", "5min", "15min"],
    session_config=session_config,
    features=["orderbook", "risk_manager"]
)

# Method 2: Default (ETH) then switch
suite = await TradingSuite.create("ES")
await suite.set_session_type(SessionType.RTH)
```

### Session Methods
```python
# Get current session configuration
current_session = suite.get_current_session_type()

# Change session type dynamically
await suite.set_session_type(SessionType.RTH)
await suite.set_session_type(SessionType.ETH)

# Get session-filtered data
rth_1min = await suite.get_session_data("1min", SessionType.RTH)
eth_5min = await suite.get_session_data("5min", SessionType.ETH)

# Get session statistics
stats = await suite.get_session_statistics()
```

### Session Statistics
```python
stats = await suite.get_session_statistics()

# Available statistics:
print(f"RTH Volume: {stats['rth_volume']:,}")
print(f"ETH Volume: {stats['eth_volume']:,}")
print(f"RTH VWAP: ${stats['rth_vwap']:.2f}")
print(f"ETH VWAP: ${stats['eth_vwap']:.2f}")
print(f"RTH Range: ${stats['rth_range']:.2f}")
print(f"ETH Range: ${stats['eth_range']:.2f}")
print(f"RTH Trades: {stats['rth_trade_count']:,}")
print(f"ETH Trades: {stats['eth_trade_count']:,}")
```

---

## Client API Methods

### Session-Aware Market Data
```python
async with ProjectX.from_env() as client:
    await client.authenticate()

    # Get session-filtered bars
    rth_bars = await client.get_session_bars(
        symbol="ES",
        timeframe="5min",
        session_type=SessionType.RTH,
        days=5
    )

    # Get session-filtered trades
    rth_trades = await client.get_session_trades(
        symbol="ES",
        session_type=SessionType.RTH,
        limit=1000
    )

    # Get session statistics from API
    session_stats = await client.get_session_statistics(
        symbol="ES",
        session_type=SessionType.RTH
    )
```

### Batch Operations
```python
# Get multiple timeframes for RTH only
data = {}
for timeframe in ["1min", "5min", "15min"]:
    data[timeframe] = await client.get_session_bars(
        symbol="ES",
        timeframe=timeframe,
        session_type=SessionType.RTH,
        days=10
    )
```

---

## Session-Aware Indicators

### Basic Usage
```python
from project_x_py.indicators import SMA, EMA, RSI, MACD, VWAP

# Get RTH-only data
rth_data = await suite.get_session_data("1min", SessionType.RTH)

# Apply indicators to session-filtered data
with_indicators = (rth_data
    .pipe(SMA, period=20)
    .pipe(EMA, period=12)
    .pipe(RSI, period=14)
    .pipe(VWAP)
)

# All indicators calculated only on RTH data
print(with_indicators.columns)
# ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'sma_20', 'ema_12', 'rsi_14', 'vwap']
```

### Session-Specific Indicators
```python
from project_x_py.sessions.indicators import (
    calculate_session_vwap,
    calculate_session_levels,
    calculate_anchored_vwap
)

# Session VWAP (resets at session boundaries)
session_vwap_data = await calculate_session_vwap(
    data=rth_data,
    session_type=SessionType.RTH,
    product="ES"
)

# Session high/low levels
session_levels = await calculate_session_levels(rth_data)

# Anchored VWAP from session open
anchored_vwap = await calculate_anchored_vwap(
    data=rth_data,
    anchor_point="session_open"
)
```

### Multi-Session Comparison
```python
# Compare RTH vs ETH indicators
rth_data = await suite.get_session_data("5min", SessionType.RTH)
eth_data = await suite.get_session_data("5min", SessionType.ETH)

rth_sma = rth_data.pipe(SMA, period=20)
eth_sma = eth_data.pipe(SMA, period=20)

# Analyze differences
rth_mean = float(rth_sma["sma_20"].mean())
eth_mean = float(eth_sma["sma_20"].mean())
print(f"RTH SMA(20) Average: ${rth_mean:.2f}")
print(f"ETH SMA(20) Average: ${eth_mean:.2f}")
print(f"Difference: ${abs(rth_mean - eth_mean):.2f}")
```

---

## Real-Time Session Filtering

### RealtimeDataManager with Sessions
```python
from project_x_py import create_realtime_client, RealtimeDataManager

# Create session-aware data manager
jwt_token = await client.get_session_token()
realtime_client = create_realtime_client(jwt_token, str(account.id))

data_manager = RealtimeDataManager(
    instrument="ES",
    client=client,
    realtime_client=realtime_client,
    timeframes=["1min", "5min"],
    session_config=SessionConfig(session_type=SessionType.RTH)
)

# Initialize and start
await data_manager.initialize(initial_days=5)
if realtime_client.connect():
    await data_manager.start_realtime_feed()
```

### Session Event Callbacks
```python
# Register session-aware callbacks
async def on_rth_bar(event):
    """Called only for RTH bars."""
    data = event.data
    print(f"RTH Bar: ${data['close']:.2f} Volume: {data['volume']:,}")

async def on_session_transition(event):
    """Called when session changes (RTH -> ETH or ETH -> RTH)."""
    session_info = event.data
    print(f"Session changed to: {session_info['session_type']}")

# Register callbacks
await data_manager.add_callback('new_bar', on_rth_bar)
await data_manager.add_callback('session_transition', on_session_transition)
```

### Memory Management with Sessions
```python
# Configure session-aware memory limits
memory_config = {
    "max_bars_per_timeframe": 1000,
    "enable_session_cleanup": True,
    "rth_retention_hours": 48,    # Keep 2 days of RTH data
    "eth_retention_hours": 24     # Keep 1 day of ETH data
}

data_manager = RealtimeDataManager(
    instrument="ES",
    client=client,
    realtime_client=realtime_client,
    timeframes=["1min"],
    session_config=SessionConfig(session_type=SessionType.RTH),
    memory_config=memory_config
)
```

---

## Advanced Usage Patterns

### Strategy Development
```python
class RTHOnlyStrategy:
    def __init__(self):
        self.session_config = SessionConfig(session_type=SessionType.RTH)

    async def setup(self):
        self.suite = await TradingSuite.create(
            "ES",
            timeframes=["1min", "5min"],
            session_config=self.session_config,
            features=["orderbook", "risk_manager"]
        )

    async def analyze_market(self):
        # Get RTH-only data for analysis
        data_1min = await self.suite.get_session_data("1min", SessionType.RTH)
        data_5min = await self.suite.get_session_data("5min", SessionType.RTH)

        # Apply indicators to RTH data only
        signals_1min = data_1min.pipe(RSI, period=14).pipe(MACD)
        signals_5min = data_5min.pipe(SMA, period=20).pipe(EMA, period=50)

        return signals_1min, signals_5min

    async def get_session_context(self):
        """Get session-specific market context."""
        stats = await self.suite.get_session_statistics()

        return {
            "rth_volume": stats['rth_volume'],
            "volume_profile": "high" if stats['rth_volume'] > stats['eth_volume'] else "low",
            "session_range": stats['rth_range'],
            "vwap": stats['rth_vwap']
        }
```

### Multi-Product Session Analysis
```python
async def analyze_multiple_products():
    """Compare session characteristics across products."""
    products = ["ES", "NQ", "CL", "GC"]
    results = {}

    for product in products:
        suite = await TradingSuite.create(
            product,
            session_config=SessionConfig(session_type=SessionType.RTH)
        )

        # Get RTH statistics
        stats = await suite.get_session_statistics()

        results[product] = {
            "rth_volume": stats['rth_volume'],
            "rth_range": stats['rth_range'],
            "rth_vwap": stats['rth_vwap'],
            "volume_ratio": stats['rth_volume'] / stats['eth_volume']
        }

        await suite.disconnect()

    return results
```

### Session Transition Monitoring
```python
async def monitor_session_transitions():
    """Monitor and react to session transitions."""

    # Create ETH suite to catch all transitions
    suite = await TradingSuite.create(
        "ES",
        session_config=SessionConfig(session_type=SessionType.ETH)
    )

    transition_count = 0

    async def on_transition(event):
        nonlocal transition_count
        transition_count += 1

        session_info = event.data
        current_session = session_info['session_type']

        print(f"[{datetime.now()}] Transition #{transition_count}")
        print(f"Now in: {current_session}")

        if current_session == "RTH":
            print("🔔 Regular trading hours started")
            # Switch to RTH-only analysis
            await suite.set_session_type(SessionType.RTH)
        elif current_session == "ETH":
            print("🌙 Extended hours trading")
            # Switch back to full ETH
            await suite.set_session_type(SessionType.ETH)

    # Register transition callback
    await suite.on(EventType.SESSION_TRANSITION, on_transition)

    # Keep monitoring
    await asyncio.sleep(3600)  # Monitor for 1 hour
    await suite.disconnect()
```

---

## Performance Optimizations

### Efficient Data Retrieval
```python
# ✅ GOOD: Get session data once, apply multiple indicators
rth_data = await suite.get_session_data("1min", SessionType.RTH)
with_all_indicators = (rth_data
    .pipe(SMA, period=20)
    .pipe(EMA, period=12)
    .pipe(RSI, period=14)
    .pipe(VWAP)
)

# ❌ BAD: Multiple session data calls
sma_data = (await suite.get_session_data("1min", SessionType.RTH)).pipe(SMA, period=20)
ema_data = (await suite.get_session_data("1min", SessionType.RTH)).pipe(EMA, period=12)
```

### Memory Management
```python
# Configure appropriate retention for your use case
memory_config = {
    "max_bars_per_timeframe": 2000,      # Increase for longer analysis
    "enable_session_cleanup": True,      # Clean up old session data
    "cleanup_interval_minutes": 30       # Clean up every 30 minutes
}
```

### Caching Session Calculations
```python
from functools import lru_cache
import polars as pl

class SessionAnalyzer:
    def __init__(self, suite):
        self.suite = suite

    @lru_cache(maxsize=10)
    async def get_cached_session_data(self, timeframe: str, session_type: SessionType) -> pl.DataFrame:
        """Cache session data to avoid repeated API calls."""
        return await self.suite.get_session_data(timeframe, session_type)

    async def analyze_with_cache(self):
        # This will use cached data on subsequent calls
        data = await self.get_cached_session_data("5min", SessionType.RTH)
        return data.pipe(SMA, period=20)
```

---

## Testing and Validation

### Basic Validation
```python
async def validate_session_setup():
    """Validate your session configuration works correctly."""

    suite = await TradingSuite.create(
        "ES",
        session_config=SessionConfig(session_type=SessionType.RTH)
    )

    # Test session data retrieval
    rth_data = await suite.get_session_data("5min", SessionType.RTH)
    eth_data = await suite.get_session_data("5min", SessionType.ETH)

    print(f"RTH bars: {len(rth_data)}")
    print(f"ETH bars: {len(eth_data)}")
    print(f"ETH should have more bars: {len(eth_data) > len(rth_data)}")

    # Test session switching
    await suite.set_session_type(SessionType.RTH)
    assert suite.get_current_session_type() == SessionType.RTH

    await suite.set_session_type(SessionType.ETH)
    assert suite.get_current_session_type() == SessionType.ETH

    print("✅ All validations passed")
    await suite.disconnect()
```

### Session Boundary Testing
```python
async def test_session_boundaries():
    """Test that session boundaries are correctly identified."""
    from project_x_py.sessions.indicators import find_session_boundaries

    # Get mixed session data
    suite = await TradingSuite.create("ES")
    eth_data = await suite.get_session_data("1min", SessionType.ETH)

    # Find session boundaries
    boundaries = find_session_boundaries(eth_data)
    print(f"Found {len(boundaries)} session boundaries")

    # Validate boundaries align with expected RTH start times
    for boundary in boundaries[:3]:  # Check first 3 boundaries
        boundary_time = eth_data["timestamp"][boundary]
        print(f"Session boundary at: {boundary_time}")
        # Should be around 9:30 AM ET

    await suite.disconnect()
```

---

## Troubleshooting

### Common Issues

#### Issue: No RTH data returned
```python
# Problem: Wrong product or session times
rth_data = await suite.get_session_data("1min", SessionType.RTH)
if rth_data.is_empty():
    print("No RTH data found!")

# Solution: Check product session configuration
session_times = suite.session_config.get_session_times("ES")
print(f"RTH hours: {session_times.rth_start} - {session_times.rth_end}")
```

#### Issue: Session statistics are zeros
```python
stats = await suite.get_session_statistics()
if stats['rth_volume'] == 0:
    print("No RTH volume data")

    # Check if data manager has sufficient data
    memory_stats = await suite.data.get_memory_stats()
    print(f"Total bars: {memory_stats.get('total_bars', 0)}")

    # Ensure sufficient initialization
    await suite.data.initialize(initial_days=5)
```

#### Issue: Indicators not respecting sessions
```python
# Problem: Using wrong data source
full_data = await suite.data.get_data("1min")  # Contains ETH + RTH
wrong_sma = full_data.pipe(SMA, period=20)     # Uses all data

# Solution: Use session-filtered data
rth_data = await suite.get_session_data("1min", SessionType.RTH)
correct_sma = rth_data.pipe(SMA, period=20)    # Uses only RTH data
```

### Debug Mode
```python
import logging

# Enable session debugging
logging.getLogger("project_x_py.sessions").setLevel(logging.DEBUG)

# This will show:
# - Session boundary detection
# - Data filtering operations
# - Memory cleanup activities
# - Session transition events
```

---

## Best Practices

### 1. Choose the Right Session Type
- **RTH**: Most day trading strategies, backtesting with realistic volume
- **ETH**: 24-hour strategies, overnight positions, global markets
- **CUSTOM**: Specific trading windows, exotic products

### 2. Memory Management
```python
# For long-running strategies
memory_config = {
    "max_bars_per_timeframe": 1000,
    "enable_session_cleanup": True,
    "cleanup_interval_minutes": 15
}

# For analysis/backtesting
memory_config = {
    "max_bars_per_timeframe": 10000,
    "enable_session_cleanup": False
}
```

### 3. Error Handling
```python
try:
    rth_data = await suite.get_session_data("1min", SessionType.RTH)
    if rth_data.is_empty():
        # Fallback to ETH data or handle gracefully
        print("No RTH data available, using ETH")
        rth_data = await suite.get_session_data("1min", SessionType.ETH)
except Exception as e:
    print(f"Session data error: {e}")
    # Implement fallback strategy
```

### 4. Testing Your Strategy
```python
# Always test with both session types
for session_type in [SessionType.RTH, SessionType.ETH]:
    await suite.set_session_type(session_type)
    results = await run_strategy_analysis()
    print(f"{session_type.value} Results: {results}")
```

---

## Migration Guide

### From Non-Session Code
```python
# OLD: No session awareness
suite = await TradingSuite.create("ES")
data = await suite.data.get_data("1min")

# NEW: Session-aware
session_config = SessionConfig(session_type=SessionType.RTH)
suite = await TradingSuite.create("ES", session_config=session_config)
data = await suite.get_session_data("1min", SessionType.RTH)
```

### Backward Compatibility
All existing code continues to work without changes. The session system is additive:

```python
# This still works exactly as before
suite = await TradingSuite.create("ES")  # Uses ETH (24-hour) by default
data = await suite.data.get_data("1min") # Returns all data (ETH)

# New session features are opt-in
rth_only = await suite.get_session_data("1min", SessionType.RTH)
```

---

## References

- **Core Module**: `project_x_py.sessions`
- **Configuration**: `project_x_py.sessions.config`
- **Indicators**: `project_x_py.sessions.indicators`
- **Statistics**: `project_x_py.sessions.statistics`
- **Pull Request**: [#59 - ETH vs RTH Trading Sessions](https://github.com/TexasCoding/project-x-py/pull/59)

---

*This document covers version 3.4.0 of the session features. For updates and additional examples, see the project repository and test files.*
