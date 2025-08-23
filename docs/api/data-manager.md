# Data Manager API

Real-time data processing and management with WebSocket streaming, multi-timeframe support, and efficient memory management.

## Overview

The RealtimeDataManager handles real-time market data streaming via WebSocket connections, processes OHLCV bar data across multiple timeframes, and provides efficient data access with automatic memory management.


## Quick Start

```python
from project_x_py import TradingSuite

async def basic_data_usage():
    # Create suite with real-time data
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["1min", "5min", "15min"]
    )

    # Access the integrated data manager
    data_manager = suite.data

    # Get current price
    current_price = await data_manager.get_current_price()
    print(f"Current MNQ Price: ${current_price:.2f}")

    # Get latest bars
    bars_1min = await data_manager.get_data("1min")
    bars_5min = await data_manager.get_data("5min")

    print(f"1min bars: {len(bars_1min)}")
    print(f"5min bars: {len(bars_5min)}")

    await suite.disconnect()

asyncio.run(basic_data_usage())
```

## Real-time Data Streaming

### WebSocket Connection

```python
from project_x_py import EventType

async def realtime_streaming():
    suite = await TradingSuite.create("MNQ", timeframes=["1min", "5min"])

    # Register event handlers for real-time data
    async def on_new_bar(event):
        print(f"New {event.timeframe} bar:")
        print(f"  Open: ${event.data['open']:.2f}")
        print(f"  High: ${event.data['high']:.2f}")
        print(f"  Low: ${event.data['low']:.2f}")
        print(f"  Close: ${event.data['close']:.2f}")
        print(f"  Volume: {event.data['volume']:,}")

    async def on_tick_data(event):
        print(f"Tick: ${event.data['price']:.2f} @ {event.data['time']}")

    # Subscribe to events
    await suite.on(EventType.NEW_BAR, on_new_bar)
    await suite.on(EventType.TICK_DATA, on_tick_data)

    # Stream data for 5 minutes
    await asyncio.sleep(300)
    await suite.disconnect()

asyncio.run(realtime_streaming())
```

### Data Subscriptions

```python
async def data_subscriptions():
    suite = await TradingSuite.create("MNQ")

    # Subscribe to additional data feeds
    await suite.data.subscribe_to_trades()      # Trade data
    await suite.data.subscribe_to_quotes()      # Quote data
    await suite.data.subscribe_to_level2()      # Order book data

    # Subscribe to multiple timeframes
    await suite.data.add_timeframe("30min")
    await suite.data.add_timeframe("1hour")

    # Unsubscribe when not needed
    await suite.data.remove_timeframe("30min")
    await suite.data.unsubscribe_from_trades()

    await suite.disconnect()

asyncio.run(data_subscriptions())
```

## Data Access

### Current Market Data

```python
async def current_market_data():
    suite = await TradingSuite.create("MNQ", timeframes=["1min"])

    # Get current price
    current_price = await suite.data.get_current_price()
    print(f"Current Price: ${current_price:.2f}")

    # Get current bid/ask
    quote = await suite.data.get_current_quote()
    print(f"Bid: ${quote.bid:.2f}")
    print(f"Ask: ${quote.ask:.2f}")
    print(f"Spread: ${quote.spread:.2f}")

    # Get latest tick
    latest_tick = await suite.data.get_latest_tick()
    print(f"Latest Tick: ${latest_tick.price:.2f} @ {latest_tick.timestamp}")

    # Get market snapshot
    snapshot = await suite.data.get_market_snapshot()
    print(f"Open: ${snapshot.open:.2f}")
    print(f"High: ${snapshot.high:.2f}")
    print(f"Low: ${snapshot.low:.2f}")
    print(f"Volume: {snapshot.volume:,}")

    await suite.disconnect()

asyncio.run(current_market_data())
```

### Historical Bar Data

```python
async def historical_bar_data():
    suite = await TradingSuite.create("MNQ", timeframes=["1min", "5min"])

    # Get recent bars for different timeframes
    bars_1min = await suite.data.get_data("1min", count=100)  # Last 100 1-min bars
    bars_5min = await suite.data.get_data("5min", count=50)   # Last 50 5-min bars

    print(f"1-min bars: {len(bars_1min)}")
    print(f"5-min bars: {len(bars_5min)}")

    # Get bars for specific time range
    from datetime import datetime, timedelta

    end_time = datetime.now()
    start_time = end_time - timedelta(hours=4)  # Last 4 hours

    recent_bars = await suite.data.get_data(
        timeframe="1min",
        start_time=start_time,
        end_time=end_time
    )
    print(f"Last 4 hours: {len(recent_bars)} bars")

    # Get all available data
    all_data = await suite.data.get_all_data("5min")
    print(f"Total 5-min bars in memory: {len(all_data)}")

    await suite.disconnect()

asyncio.run(historical_bar_data())
```

### Tick Data Access

```python
async def tick_data_access():
    suite = await TradingSuite.create("MNQ")

    # Subscribe to tick data first
    await suite.data.subscribe_to_trades()

    # Wait for some tick data to accumulate
    await asyncio.sleep(30)

    # Get recent ticks
    recent_ticks = await suite.data.get_recent_ticks(count=50)
    print(f"Recent ticks: {len(recent_ticks)}")

    for tick in recent_ticks[-5:]:  # Last 5 ticks
        print(f"  ${tick.price:.2f} x {tick.size} @ {tick.timestamp}")

    # Get tick statistics
    tick_stats = await suite.data.get_tick_statistics()
    print(f"Ticks per minute: {tick_stats.ticks_per_minute:.1f}")
    print(f"Average tick size: {tick_stats.avg_tick_size:.0f}")
    print(f"Price range: ${tick_stats.min_price:.2f} - ${tick_stats.max_price:.2f}")

    await suite.disconnect()

asyncio.run(tick_data_access())
```

## Multi-Timeframe Management

### Timeframe Configuration

```python
async def timeframe_management():
    # Initialize with multiple timeframes
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["30sec", "1min", "5min", "15min", "1hour"]
    )

    # Get available timeframes
    timeframes = suite.data.get_timeframes()
    print(f"Available timeframes: {timeframes}")

    # Add new timeframe dynamically
    await suite.data.add_timeframe("30min")
    await suite.data.add_timeframe("4hour")

    # Remove timeframe
    await suite.data.remove_timeframe("30sec")

    # Check if timeframe exists
    has_5min = suite.data.has_timeframe("5min")
    print(f"Has 5min data: {has_5min}")

    await suite.disconnect()

asyncio.run(timeframe_management())
```

### Cross-Timeframe Analysis

```python
async def cross_timeframe_analysis():
    suite = await TradingSuite.create("MNQ", timeframes=["1min", "5min", "15min"])

    # Wait for data to accumulate
    await asyncio.sleep(60)

    # Get data from multiple timeframes
    data_1min = await suite.data.get_data("1min")
    data_5min = await suite.data.get_data("5min")
    data_15min = await suite.data.get_data("15min")

    # Compare current price across timeframes
    current_1min = data_1min.tail(1)["close"].item() if len(data_1min) > 0 else 0
    current_5min = data_5min.tail(1)["close"].item() if len(data_5min) > 0 else 0
    current_15min = data_15min.tail(1)["close"].item() if len(data_15min) > 0 else 0

    print(f"Current prices:")
    print(f"  1min: ${current_1min:.2f}")
    print(f"  5min: ${current_5min:.2f}")
    print(f"  15min: ${current_15min:.2f}")

    # Analyze timeframe alignment
    alignment = await suite.data.analyze_timeframe_alignment()
    print(f"Timeframe alignment score: {alignment.score:.2f}")
    print(f"Trend direction: {alignment.trend_direction}")

    await suite.disconnect()

asyncio.run(cross_timeframe_analysis())
```

## Data Processing

### Bar Construction


```python
async def bar_construction():
    suite = await TradingSuite.create("MNQ", timeframes=["1min"])

    # Configure bar construction
    await suite.data.configure_bar_processing(
        use_tick_data=True,        # Use tick data for bar construction
        fill_gaps=True,            # Fill gaps in data
        validate_bars=True,        # Validate bar integrity
        remove_outliers=True       # Remove price outliers
    )

    # Monitor bar construction
    async def on_bar_constructed(event):
        bar = event.data
        print(f"Bar constructed for {event.timeframe}:")
        print(f"  OHLC: {bar.open:.2f}/{bar.high:.2f}/{bar.low:.2f}/{bar.close:.2f}")
        print(f"  Volume: {bar.volume:,}")
        print(f"  Tick Count: {bar.tick_count}")

    await suite.on(EventType.BAR_CONSTRUCTED, on_bar_constructed)

    await asyncio.sleep(120)  # Monitor for 2 minutes
    await suite.disconnect()

asyncio.run(bar_construction())
```

### Data Validation

```python
async def data_validation():
    suite = await TradingSuite.create("MNQ", timeframes=["1min", "5min"])

    # Enable data validation
    await suite.data.enable_validation(
        check_price_consistency=True,
        check_volume_sanity=True,
        check_timestamp_order=True,
        max_price_deviation=0.05  # 5% max price deviation
    )

    # Get validation statistics
    validation_stats = await suite.data.get_validation_stats()
    print(f"Validation Statistics:")
    print(f"  Bars validated: {validation_stats.bars_validated:,}")
    print(f"  Errors detected: {validation_stats.errors_detected}")
    print(f"  Corrections made: {validation_stats.corrections_made}")
    print(f"  Success rate: {validation_stats.success_rate:.1%}")

    # Get validation errors
    errors = await suite.data.get_validation_errors(limit=10)
    for error in errors:
        print(f"Error: {error.type} - {error.description}")

    await suite.disconnect()

asyncio.run(data_validation())
```

## Memory Management

### Data Storage Configuration

```python
async def memory_management():
    suite = await TradingSuite.create("MNQ", timeframes=["1min", "5min"])

    # Configure memory limits
    await suite.data.configure_memory_management(
        max_bars_per_timeframe=1000,  # Max bars in memory
        enable_disk_overflow=True,    # Use disk for overflow
        cleanup_frequency=300,        # Cleanup every 5 minutes
        compression_enabled=True      # Compress older data
    )

    # Get memory usage statistics
    memory_stats = await suite.data.get_memory_stats()
    print(f"Memory Usage:")
    print(f"  Total bars in memory: {memory_stats.total_bars:,}")
    print(f"  Memory usage: {memory_stats.memory_usage_mb:.1f} MB")
    print(f"  Disk usage: {memory_stats.disk_usage_mb:.1f} MB")
    print(f"  Compression ratio: {memory_stats.compression_ratio:.2f}x")

    # Manual cleanup
    await suite.data.cleanup_old_data(days=7)  # Remove data older than 7 days
    await suite.data.compress_data()           # Compress all data

    await suite.disconnect()

asyncio.run(memory_management())
```

### Performance Optimization

```python
async def performance_optimization():
    suite = await TradingSuite.create("MNQ", timeframes=["1min", "5min"])

    # Configure performance settings
    await suite.data.configure_performance(
        use_memory_mapping=True,      # Use memory-mapped files
        batch_size=100,               # Process in batches
        parallel_processing=True,     # Use multiple threads
        cache_frequently_accessed=True # Cache hot data
    )

    # Get performance metrics
    perf_metrics = await suite.data.get_performance_metrics()
    print(f"Performance Metrics:")
    print(f"  Data processing rate: {perf_metrics.bars_per_second:.1f} bars/sec")
    print(f"  Memory access time: {perf_metrics.avg_access_time_ms:.2f}ms")
    print(f"  Cache hit rate: {perf_metrics.cache_hit_rate:.1%}")
    print(f"  CPU usage: {perf_metrics.cpu_usage_percent:.1f}%")

    await suite.disconnect()

asyncio.run(performance_optimization())
```

## Data Export & Import

### Data Export

```python
async def data_export():
    suite = await TradingSuite.create("MNQ", timeframes=["1min", "5min"])

    # Wait for data accumulation
    await asyncio.sleep(120)

    # Export to different formats

    # CSV export
    csv_data = await suite.data.export_to_csv(
        timeframe="1min",
        include_volume=True,
        date_format="%Y-%m-%d %H:%M:%S"
    )
    with open("mnq_1min_data.csv", "w") as f:
        f.write(csv_data)

    # JSON export
    json_data = await suite.data.export_to_json(
        timeframe="5min",
        pretty_format=True
    )
    with open("mnq_5min_data.json", "w") as f:
        f.write(json_data)

    # Parquet export (efficient binary format)
    await suite.data.export_to_parquet(
        timeframe="1min",
        filename="mnq_1min_data.parquet",
        compression="snappy"
    )

    await suite.disconnect()

asyncio.run(data_export())
```

### Data Import

```python
async def data_import():
    suite = await TradingSuite.create("MNQ", timeframes=["1min"])

    # Import historical data

    # From CSV
    await suite.data.import_from_csv(
        filename="historical_data.csv",
        timeframe="1min",
        date_column="timestamp",
        price_columns=["open", "high", "low", "close"],
        volume_column="volume"
    )

    # From JSON
    await suite.data.import_from_json(
        filename="historical_data.json",
        timeframe="1min"
    )

    # From Parquet
    await suite.data.import_from_parquet(
        filename="historical_data.parquet",
        timeframe="1min"
    )

    # Validate imported data
    validation_result = await suite.data.validate_imported_data("1min")
    print(f"Imported data validation: {validation_result.success}")
    if not validation_result.success:
        for error in validation_result.errors:
            print(f"  Error: {error}")

    await suite.disconnect()

asyncio.run(data_import())
```

## Event Handling

### Data Events

```python
from project_x_py import EventType

async def data_event_handling():
    suite = await TradingSuite.create("MNQ", timeframes=["1min", "5min"])

    # Register comprehensive event handlers

    async def on_new_bar(event):
        print(f"New {event.timeframe} bar: ${event.data.close:.2f}")

    async def on_data_gap(event):
        print(f"Data gap detected: {event.gap_duration} seconds")

    async def on_data_quality_alert(event):
        print(f"Data quality alert: {event.alert_type} - {event.description}")

    async def on_connection_status(event):
        print(f"Connection status: {event.status}")

    # Register event handlers
    await suite.on(EventType.NEW_BAR, on_new_bar)
    await suite.on(EventType.DATA_GAP, on_data_gap)
    await suite.on(EventType.DATA_QUALITY_ALERT, on_data_quality_alert)
    await suite.on(EventType.CONNECTION_STATUS_CHANGED, on_connection_status)

    # Monitor events
    await asyncio.sleep(300)
    await suite.disconnect()

asyncio.run(data_event_handling())
```

## Data Statistics

```python
async def data_statistics():
    suite = await TradingSuite.create("MNQ", timeframes=["1min", "5min"])

    # Let data accumulate
    await asyncio.sleep(120)

    # Get comprehensive data statistics
    stats = await suite.data.get_stats()

    print("Data Manager Statistics:")
    print(f"  Total bars received: {stats['total_bars_received']:,}")
    print(f"  Bars per minute: {stats['bars_per_minute']:.1f}")
    print(f"  Data quality score: {stats['data_quality_score']:.1f}/100")
    print(f"  Connection uptime: {stats['connection_uptime']:.1f}%")
    print(f"  Average latency: {stats['avg_latency_ms']:.1f}ms")

    # Timeframe-specific statistics
    for timeframe in ["1min", "5min"]:
        tf_stats = await suite.data.get_timeframe_stats(timeframe)
        print(f"\n{timeframe} Statistics:")
        print(f"  Bars in memory: {tf_stats['bars_in_memory']:,}")
        print(f"  Last update: {tf_stats['last_update']}")
        print(f"  Data completeness: {tf_stats['completeness']:.1f}%")
        print(f"  Memory usage: {tf_stats['memory_usage_mb']:.1f} MB")

    await suite.disconnect()

asyncio.run(data_statistics())
```

## Configuration

### DataManagerConfig


```python
from project_x_py.types import DataManagerConfig

async def configure_data_manager():
    # Custom data manager configuration
    data_config = DataManagerConfig(
        max_bars_per_timeframe=2000,      # Increase memory limit
        enable_tick_data=True,            # Enable tick data collection
        enable_level2_data=False,         # Disable Level 2 (if not needed)
        data_validation=True,             # Enable validation
        auto_cleanup=True,                # Enable automatic cleanup
        cleanup_interval_minutes=10,      # Cleanup every 10 minutes
        compression_enabled=True,         # Enable compression
        disk_cache_enabled=True,          # Enable disk caching
        max_disk_cache_gb=1.0            # 1GB disk cache limit
    )

    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["1min", "5min"],
        data_manager_config=data_config
    )

    await suite.disconnect()

asyncio.run(configure_data_manager())
```

## Best Practices

### Efficient Data Access

```python
#  Good: Access data efficiently
data = await suite.data.get_data("1min", count=100)  # Specific count
recent_data = data.tail(20)  # Get last 20 bars

# L Less efficient: Getting all data when only need recent
# all_data = await suite.data.get_all_data("1min")  # Large dataset
# recent_data = all_data.tail(20)

#  Good: Use appropriate timeframes
await TradingSuite.create("MNQ", timeframes=["5min", "15min"])  # What you need

# L Wasteful: Too many timeframes
# await TradingSuite.create("MNQ", timeframes=["15sec", "30sec", "1min", "2min", "5min", "15min", "30min"])
```

### Memory Management

```python
#  Good: Configure memory limits
await suite.data.configure_memory_management(
    max_bars_per_timeframe=1000,
    cleanup_frequency=300
)

#  Good: Monitor memory usage
stats = await suite.data.get_memory_stats()
if stats.memory_usage_mb > 100:  # 100MB threshold
    await suite.data.cleanup_old_data(hours=4)  # Keep last 4 hours
```

### Event Handling

```python
#  Good: Use specific event handlers
async def on_new_bar(event):
    if event.timeframe == "5min":  # Only process 5min bars
        # Process bar data
        pass

#  Good: Handle connection issues
async def on_connection_status(event):
    if event.status == "disconnected":
        print("Connection lost - data may be incomplete")
    elif event.status == "reconnected":
        print("Connection restored")
```

## See Also

- [Trading Suite API](trading-suite.md) - Main trading interface
- [Real-time Guide](../guide/realtime.md) - Real-time data concepts
