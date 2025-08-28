# Trading Suite API

Unified trading interface combining all managers into a single, easy-to-use entry point for complete trading operations.

## Overview

The TradingSuite is the primary interface for trading operations, combining all managers into a unified interface. It provides automatic component initialization, dependency injection, and configuration management.

::: project_x_py.trading_suite.TradingSuite

## Quick Start

### Basic Setup

```python
from project_x_py import TradingSuite

async def main():
    # Simple one-liner with defaults
    suite = await TradingSuite.create("MNQ")

    # Everything is ready - client authenticated, realtime connected
    await suite.disconnect()

asyncio.run(main())
```

### Advanced Configuration

```python
async def advanced_setup():
    # With specific configuration
    suite = await TradingSuite.create(
        instrument="MNQ",
        timeframes=["1min", "5min", "15min"],
        features=["orderbook", "risk_manager"],
        initial_days=10,
        timezone="America/Chicago"
    )

    # Access integrated components
    print(f"Client: {suite.client}")
    print(f"Orders: {suite.orders}")
    print(f"Positions: {suite.positions}")
    print(f"Data: {suite.data}")
    print(f"OrderBook: {suite.orderbook}")  # if enabled
    print(f"RiskManager: {suite.risk_manager}")  # if enabled

    await suite.disconnect()
```

### Session Configuration (v3.4.0+)

!!! warning "Experimental Feature"
    Session filtering is experimental and not thoroughly tested with live data. Use with caution in production.

```python
from project_x_py.sessions import SessionConfig, SessionType

async def session_setup():
    # RTH-only trading (9:30 AM - 4:00 PM ET)
    rth_suite = await TradingSuite.create(
        instrument="MNQ",
        timeframes=["1min", "5min"],
        session_config=SessionConfig(session_type=SessionType.RTH)
    )

    # ETH-only analysis (overnight sessions)
    eth_suite = await TradingSuite.create(
        instrument="ES",
        session_config=SessionConfig(session_type=SessionType.ETH)
    )

    # Custom session times
    from datetime import time
    import pytz

    custom_config = SessionConfig(
        session_type=SessionType.RTH,
        custom_times=SessionTimes(
            rth_start=time(9, 0),
            rth_end=time(15, 30),
            timezone=pytz.timezone("US/Eastern")
        )
    )

    custom_suite = await TradingSuite.create(
        instrument="CL",
        session_config=custom_config
    )

    await rth_suite.disconnect()
    await eth_suite.disconnect()
    await custom_suite.disconnect()
```

### Configuration File Setup

```python
async def config_file_setup():
    # From configuration file
    suite = await TradingSuite.from_config("config/trading.yaml")

    # Or from dictionary
    config = {
        "instrument": "MNQ",
        "timeframes": ["1min", "5min"],
        "features": ["orderbook"],
        "initial_days": 5
    }
    suite = await TradingSuite.from_dict(config)

    await suite.disconnect()
```

## Features

### Available Features

::: project_x_py.trading_suite.Features

### Feature Configuration

```python
from project_x_py import Features

# Enable specific features
features = [
    Features.ORDERBOOK,        # Level 2 market depth
    Features.RISK_MANAGER,     # Risk management and position sizing
    Features.AUTO_RECONNECT,   # Automatic reconnection (future)
]

suite = await TradingSuite.create(
    "MNQ",
    features=features
)
```

## Configuration

### TradingSuiteConfig

::: project_x_py.trading_suite.TradingSuiteConfig

### Component Configuration

```python
from project_x_py.types import (
    OrderManagerConfig,
    PositionManagerConfig,
    DataManagerConfig,
    OrderbookConfig
)
from project_x_py.risk_manager import RiskConfig
from project_x_py.sessions import SessionConfig, SessionType

async def custom_configuration():
    # Custom component configurations
    order_config = OrderManagerConfig(
        max_concurrent_orders=10,
        default_timeout=30.0,
        retry_attempts=3
    )

    position_config = PositionManagerConfig(
        track_unrealized=True,
        calculate_metrics=True,
        update_frequency=1.0
    )

    risk_config = RiskConfig(
        max_position_size=5,
        max_daily_loss=1000.0,
        max_drawdown_percent=10.0
    )

    # Session configuration (v3.4.0+)
    session_config = SessionConfig(
        session_type=SessionType.RTH,
        product="MNQ"  # Product-specific session times
    )

    suite = await TradingSuite.create(
        "MNQ",
        order_manager_config=order_config,
        position_manager_config=position_config,
        risk_config=risk_config,
        session_config=session_config  # New in v3.4.0
    )

    await suite.disconnect()
```

## Component Access

### Core Components

```python
async def component_access():
    suite = await TradingSuite.create("MNQ", features=["orderbook", "risk_manager"])

    # Always available components
    client = suite.client              # ProjectX API client
    orders = suite.orders             # OrderManager
    positions = suite.positions       # PositionManager
    data = suite.data                 # RealtimeDataManager
    realtime = suite.realtime         # ProjectXRealtimeClient

    # Optional components (based on features)
    if suite.orderbook:
        orderbook = suite.orderbook   # OrderBook (Level 2)

    if suite.risk_manager:
        risk_mgr = suite.risk_manager # RiskManager

    # Instrument information
    instrument_info = suite.instrument_info
    instrument_id = suite.instrument_id

    await suite.disconnect()
```

## Trading Operations

### Order Management

```python
async def order_operations():
    suite = await TradingSuite.create("MNQ")

    # Place market order
    market_order = await suite.orders.place_market_order(
        contract_id=suite.instrument_id,
        side=0,  # Buy
        size=1
    )

    # Place limit order
    limit_order = await suite.orders.place_limit_order(
        contract_id=suite.instrument_id,
        side=0,  # Buy
        size=1,
        limit_price=21050.0
    )

    # Place bracket order
    bracket_result = await suite.orders.place_bracket_order(
        contract_id=suite.instrument_id,
        side=0,  # Buy
        size=1,
        entry_price=21050.0,
        stop_offset=25.0,
        target_offset=50.0
    )

    await suite.disconnect()
```

### Position Management

```python
async def position_operations():
    suite = await TradingSuite.create("MNQ")

    # Get current position
    position = await suite.positions.get_position("MNQ")
    if position:
        print(f"Size: {position.size}")
        print(f"Avg Price: {position.avg_price}")
        print(f"Unrealized PnL: {position.unrealized_pnl}")

    # Get all positions
    all_positions = await suite.positions.get_all_positions()

    # Get position metrics
    metrics = await suite.positions.get_metrics()
    print(f"Total PnL: {metrics.get('total_pnl', 0)}")
    print(f"Win Rate: {metrics.get('win_rate', 0):.1%}")

    await suite.disconnect()
```

### Market Data Access

```python
async def data_access():
    suite = await TradingSuite.create("MNQ", timeframes=["1min", "5min"])

    # Get historical data via client
    historical = await suite.client.get_bars("MNQ", days=5, interval=60)

    # Get real-time data
    current_price = await suite.data.get_current_price()
    latest_bars_1min = await suite.data.get_data("1min")
    latest_bars_5min = await suite.data.get_data("5min")

    # OrderBook data (if enabled)
    if suite.orderbook:
        depth = await suite.orderbook.get_depth()
        trades = await suite.orderbook.get_recent_trades()

    await suite.disconnect()
```

### Session-Aware Data Access (v3.4.0+)

```python
from project_x_py.sessions import SessionType

async def session_data_access():
    # Create suite with session configuration
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["1min", "5min"],
        session_config=SessionConfig(session_type=SessionType.RTH)
    )

    # Get session-specific data
    rth_data = await suite.data.get_session_bars("5min", SessionType.RTH)
    eth_data = await suite.data.get_session_bars("5min", SessionType.ETH)

    # Session trades
    rth_trades = await suite.data.get_session_trades(SessionType.RTH)

    # Session statistics
    from project_x_py.sessions import SessionStatistics
    stats = SessionStatistics(suite)
    rth_stats = await stats.calculate_session_stats(SessionType.RTH)

    print(f"RTH Volatility: {rth_stats['volatility']:.2%}")
    print(f"RTH Volume: {rth_stats['total_volume']:,}")

    await suite.disconnect()
```

## Event Handling

### Real-time Events

```python
from project_x_py import EventType

async def event_handling():
    suite = await TradingSuite.create("MNQ", timeframes=["1min"])

    # Register event handlers
    async def on_new_bar(event):
        print(f"New {event.timeframe} bar: {event.data}")

    async def on_order_filled(event):
        print(f"Order filled: {event.order_id}")

    async def on_position_changed(event):
        print(f"Position changed: {event.data}")

    # Register handlers
    await suite.on(EventType.NEW_BAR, on_new_bar)
    await suite.on(EventType.ORDER_FILLED, on_order_filled)
    await suite.on(EventType.POSITION_CHANGED, on_position_changed)

    # Keep running to receive events
    await asyncio.sleep(60)
    await suite.disconnect()
```

## Statistics & Health Monitoring

### Comprehensive Statistics

```python
async def statistics_monitoring():
    suite = await TradingSuite.create("MNQ", features=["orderbook", "risk_manager"])

    # Get system statistics (async-first API)
    stats = await suite.get_stats()
    print(f"System Health: {stats['health_score']:.1f}/100")
    print(f"API Success Rate: {stats['api_success_rate']:.1%}")
    print(f"Memory Usage: {stats['memory_usage_mb']:.1f} MB")

    # Component-specific statistics
    order_stats = await suite.orders.get_stats()
    position_stats = await suite.positions.get_stats()
    data_stats = await suite.data.get_stats()

    if suite.orderbook:
        orderbook_stats = await suite.orderbook.get_stats()

    # Export statistics
    prometheus_metrics = await suite.export_stats("prometheus")
    csv_data = await suite.export_stats("csv")

    await suite.disconnect()
```

### Health Monitoring

```python
async def health_monitoring():
    suite = await TradingSuite.create("MNQ")

    # Real-time health monitoring
    health_score = await suite.get_health_score()
    if health_score < 70:
        print(f" System health degraded: {health_score:.1f}/100")

        # Get component health breakdown
        component_health = await suite.get_component_health()
        for name, health in component_health.items():
            if health['error_count'] > 0:
                print(f"  {name}: {health['error_count']} errors")

    await suite.disconnect()
```

## Risk Management

### ManagedTrade Integration

```python
from project_x_py.risk_manager import ManagedTrade

async def risk_managed_trading():
    suite = await TradingSuite.create("MNQ", features=["risk_manager"])

    # Create a managed trade with risk controls
    managed_trade = ManagedTrade(
        suite=suite,
        max_risk_per_trade=100.0,  # $100 max risk
        risk_reward_ratio=2.0,     # 1:2 risk/reward
        max_position_size=3        # Max 3 contracts
    )

    # Execute the trade with automatic risk management
    result = await managed_trade.execute_trade(
        side=0,  # Buy
        entry_signal="RSI oversold + support level",
        stop_loss_type="atr",      # ATR-based stop
        take_profit_type="fixed"   # Fixed target
    )

    if result.success:
        print(f"Trade executed: {result.main_order_id}")
        print(f"Stop Loss: {result.stop_order_id}")
        print(f"Take Profit: {result.target_order_id}")

    await suite.disconnect()
```

## Order Tracking & Lifecycle

### Order Chain Management

```python
async def order_lifecycle():
    suite = await TradingSuite.create("MNQ")

    # Track order lifecycle
    tracker = suite.track_order()

    # Create order chain
    chain = suite.order_chain()

    # Build complex order sequence
    entry_order = await chain.add_market_order(
        contract_id=suite.instrument_id,
        side=0,
        size=1
    )

    # Add conditional orders
    await chain.add_stop_order(
        contract_id=suite.instrument_id,
        side=1,  # Sell to close
        size=1,
        stop_price=21000.0,
        condition=f"when {entry_order.id} filled"
    )

    # Execute the chain
    await chain.execute()

    await suite.disconnect()
```

## Connection Management

### Lifecycle Management

```python
async def connection_lifecycle():
    # Context manager (recommended)
    async with TradingSuite.create("MNQ") as suite:
        # Suite automatically connects on entry
        await suite.orders.place_market_order(
            contract_id=suite.instrument_id,
            side=0,
            size=1
        )
        # Suite automatically disconnects on exit

    # Manual management
    suite = await TradingSuite.create("MNQ")
    try:
        # Trading operations
        pass
    finally:
        await suite.disconnect()
```

### Reconnection Handling

```python
async def reconnection_handling():
    suite = await TradingSuite.create("MNQ", features=["auto_reconnect"])

    # Check connection status
    client_connected = await suite.client.is_connected()
    realtime_connected = await suite.realtime.is_connected()

    if not client_connected:
        await suite.client.reconnect()

    if not realtime_connected:
        await suite.realtime.reconnect()

    await suite.disconnect()
```

## Configuration Examples

### YAML Configuration

```yaml
# config/trading.yaml
instrument: "MNQ"
timeframes:
  - "1min"
  - "5min"
  - "15min"
features:
  - "orderbook"
  - "risk_manager"
initial_days: 10
timezone: "America/Chicago"

order_manager:
  max_concurrent_orders: 10
  default_timeout: 30.0
  retry_attempts: 3

position_manager:
  track_unrealized: true
  calculate_metrics: true
  update_frequency: 1.0

risk_config:
  max_position_size: 5
  max_daily_loss: 1000.0
  max_drawdown_percent: 10.0

orderbook:
  max_depth_levels: 10
  enable_order_flow: true
  track_volume_profile: true
```

### JSON Configuration

```json
{
  "instrument": "MNQ",
  "timeframes": ["1min", "5min"],
  "features": ["orderbook", "risk_manager"],
  "initial_days": 5,
  "order_manager": {
    "max_concurrent_orders": 5,
    "default_timeout": 30.0
  },
  "risk_config": {
    "max_position_size": 3,
    "max_daily_loss": 500.0
  }
}
```

## Best Practices

### Initialization

```python
#  Recommended: Use TradingSuite.create()
suite = await TradingSuite.create("MNQ", features=["orderbook"])

#  Good: Use context manager for automatic cleanup
async with TradingSuite.create("MNQ") as suite:
    # Trading operations
    pass

# L Not recommended: Manual component initialization
# client = ProjectX.from_env()
# orders = OrderManager(client)  # Too complex
```

### Error Handling

```python
from project_x_py.exceptions import ProjectXError

async def robust_trading():
    try:
        suite = await TradingSuite.create("MNQ")

        # Trading operations with error handling
        try:
            order = await suite.orders.place_market_order(
                contract_id=suite.instrument_id,
                side=0,
                size=1
            )
        except ProjectXError as e:
            print(f"Order failed: {e}")

    except Exception as e:
        print(f"Suite creation failed: {e}")
    finally:
        if 'suite' in locals():
            await suite.disconnect()
```

### Resource Management

```python
async def resource_management():
    # Monitor resource usage
    suite = await TradingSuite.create("MNQ", features=["orderbook"])

    # Periodic health checks
    while True:
        stats = await suite.get_stats()
        memory_mb = stats.get('memory_usage_mb', 0)

        if memory_mb > 100:  # MB threshold
            print(f"High memory usage: {memory_mb:.1f} MB")

        await asyncio.sleep(60)  # Check every minute
```

## See Also

- [Order Manager API](order-manager.md) - Detailed order management
- [Position Manager API](position-manager.md) - Position tracking
- [Statistics API](statistics.md) - Health monitoring and analytics
- [Client API](client.md) - Core client functionality
- [Risk Management Guide](../guide/risk.md) - Risk management concepts
