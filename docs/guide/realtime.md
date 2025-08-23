# Real-time Data Guide

This guide covers comprehensive real-time data streaming using ProjectX Python SDK v3.3.4+. All real-time operations are fully asynchronous and provide high-performance WebSocket connectivity with automatic reconnection and memory management.

## Overview

The RealtimeDataManager provides complete real-time market data streaming including OHLCV bars, tick data, price updates, and multi-timeframe synchronization. All operations are designed for high-frequency trading applications with minimal latency.

### Key Features

- **Multi-timeframe Streaming**: Simultaneous data across multiple timeframes
- **WebSocket Connectivity**: High-performance async WebSocket connections
- **Automatic Reconnection**: Built-in circuit breaker and reconnection logic
- **Memory Management**: Sliding windows with automatic cleanup
- **Event-Driven Architecture**: Real-time callbacks for all data updates
- **Data Synchronization**: Synchronized updates across timeframes
- **Performance Optimization**: Connection pooling and message batching

## Getting Started

### Basic Real-time Setup

```python
import asyncio
from project_x_py import TradingSuite, EventType

async def basic_realtime_setup():
    # Initialize with real-time capabilities
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["1sec", "1min", "5min"],  # Multiple timeframes
        initial_days=2  # Historical data for context
    )

    # Real-time data manager is automatically initialized and connected
    data_manager = suite.data

    print("Real-time connection established!")

    # Get current price
    current_price = await data_manager.get_current_price()
    print(f"Current MNQ price: ${current_price}")

    # Get recent data
    recent_1min = await data_manager.get_data("1min", bars=10)
    print(f"Last 10 1-minute bars: {len(recent_1min)} rows")
```

### Connection Management

The TradingSuite automatically manages WebSocket connections, but you can monitor and control them:

```python
async def connection_management():
    suite = await TradingSuite.create("MNQ")

    # Check connection status
    connection_status = await suite.data.get_connection_status()
    print(f"Connection Status: {connection_status}")

    # Connection health monitoring
    health = await suite.data.get_connection_health()
    print(f"Connection Health:")
    print(f"  Status: {health['status']}")
    print(f"  Uptime: {health['uptime']}")
    print(f"  Messages Received: {health['messages_received']}")
    print(f"  Last Message: {health['last_message_time']}")

    # Manual reconnection (rarely needed)
    if health['status'] != 'CONNECTED':
        print("Reconnecting...")
        await suite.data.reconnect()
```

## Real-time Data Types

### Price Ticks

Real-time price updates provide the most granular market data:

```python
async def handle_price_ticks():
    suite = await TradingSuite.create("MNQ")

    # Event-driven tick handling
    async def on_tick(event):
        tick_data = event.data

        print(f"Tick: ${tick_data['price']} (Size: {tick_data['size']})")
        print(f"  Time: {tick_data['timestamp']}")
        print(f"  Bid/Ask: ${tick_data['bid']}/${tick_data['ask']}")

        # Tick analysis
        if tick_data['size'] > 50:  # Large tick
            print(f"  =% Large tick detected!")

    # Register tick handler
    await suite.on(EventType.TICK_UPDATE, on_tick)

    # Alternative: Callback-based approach
    async def tick_callback(tick_data):
        print(f"Callback tick: ${tick_data['price']}")

    await suite.data.add_callback("tick", tick_callback)

    # Stream ticks for 30 seconds
    print("Streaming ticks...")
    await asyncio.sleep(30)
```

### OHLCV Bars

Real-time bar formation across multiple timeframes:

```python
async def handle_bar_updates():
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["15sec", "1min", "5min", "15min"]
    )

    # Bar update handler
    async def on_new_bar(event):
        bar_data = event.data
        timeframe = bar_data['timeframe']
        bar = bar_data['data']

        print(f"New {timeframe} bar:")
        print(f"  O: ${bar['open']} H: ${bar['high']}")
        print(f"  L: ${bar['low']} C: ${bar['close']}")
        print(f"  Volume: {bar['volume']}")
        print(f"  Time: {bar['timestamp']}")

        # Bar analysis
        body_size = abs(bar['close'] - bar['open'])
        range_size = bar['high'] - bar['low']

        if body_size > range_size * 0.8:  # Strong directional bar
            direction = "Bullish" if bar['close'] > bar['open'] else "Bearish"
            print(f"  < Strong {direction} bar!")

    # Register bar handler
    await suite.on(EventType.NEW_BAR, on_new_bar)

    # Monitor bars for 5 minutes
    print("Monitoring bar formation...")
    await asyncio.sleep(300)
```

### Quote Updates

Real-time bid/ask quote changes:

```python
async def handle_quote_updates():
    suite = await TradingSuite.create("MNQ")

    async def on_quote_update(event):
        quote_data = event.data

        bid = quote_data['bid']
        ask = quote_data['ask']
        spread = ask - bid

        print(f"Quote: ${bid} x ${ask} (Spread: ${spread})")

        # Spread analysis
        if spread > 5.0:  # Wide spread for MNQ
            print("    Wide spread detected!")

        # Level 2 data (if available)
        if 'depth' in quote_data:
            depth = quote_data['depth']
            print(f"  Depth: {len(depth['bids'])} bids, {len(depth['asks'])} asks")

    await suite.on(EventType.QUOTE_UPDATE, on_quote_update)

    # Monitor quotes
    await asyncio.sleep(60)
```

## Multi-timeframe Analysis

### Synchronized Data Access

```python
async def multi_timeframe_analysis():
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["1min", "5min", "15min", "1hr"],
        initial_days=5
    )

    # Get synchronized data across timeframes
    timeframe_data = {}

    for tf in ["1min", "5min", "15min", "1hr"]:
        data = await suite.data.get_data(tf, bars=100)
        timeframe_data[tf] = data
        print(f"{tf}: {len(data)} bars")

    # Analysis across timeframes
    current_time = datetime.now()

    # Check trend alignment
    trends = {}
    for tf, data in timeframe_data.items():
        if len(data) >= 2:
            current_close = data[-1]['close']
            prev_close = data[-2]['close']
            trends[tf] = "Up" if current_close > prev_close else "Down"

    print(f"Trend Alignment: {trends}")

    # Look for confluence
    all_up = all(trend == "Up" for trend in trends.values())
    all_down = all(trend == "Down" for trend in trends.values())

    if all_up:
        print("= All timeframes bullish!")
    elif all_down:
        print("= All timeframes bearish!")
    else:
        print("= Mixed timeframe signals")
```

### Real-time Multi-timeframe Monitoring

```python
class MultiTimeframeMonitor:
    def __init__(self, suite):
        self.suite = suite
        self.timeframes = ["1min", "5min", "15min"]
        self.current_bars = {}
        self.signals = {}

    async def setup_monitoring(self):
        """Setup multi-timeframe monitoring."""

        # Initialize current bars for each timeframe
        for tf in self.timeframes:
            data = await self.suite.data.get_data(tf, bars=1)
            if len(data) > 0:
                self.current_bars[tf] = data[-1]

        # Register bar update handler
        await self.suite.on(EventType.NEW_BAR, self.on_bar_update)

        print("Multi-timeframe monitoring active")

    async def on_bar_update(self, event):
        """Handle new bar across all timeframes."""
        bar_data = event.data
        timeframe = bar_data['timeframe']
        bar = bar_data['data']

        if timeframe not in self.timeframes:
            return

        # Update current bar
        prev_bar = self.current_bars.get(timeframe)
        self.current_bars[timeframe] = bar

        # Generate signals
        signal = await self.generate_signal(timeframe, bar, prev_bar)
        if signal:
            self.signals[timeframe] = signal
            await self.check_confluence()

    async def generate_signal(self, timeframe, current_bar, prev_bar):
        """Generate signals based on bar patterns."""

        if not prev_bar:
            return None

        # Simple momentum signal
        if current_bar['close'] > prev_bar['close'] * 1.002:  # 0.2% up
            return {"type": "BULLISH", "strength": "STRONG"}
        elif current_bar['close'] < prev_bar['close'] * 0.998:  # 0.2% down
            return {"type": "BEARISH", "strength": "STRONG"}

        return None

    async def check_confluence(self):
        """Check for signal confluence across timeframes."""

        if len(self.signals) < 2:
            return

        # Check alignment
        signal_types = [sig["type"] for sig in self.signals.values()]

        if len(set(signal_types)) == 1:  # All same type
            signal_type = signal_types[0]
            timeframes = list(self.signals.keys())

            print(f"< CONFLUENCE SIGNAL: {signal_type}")
            print(f"   Timeframes: {', '.join(timeframes)}")

            # Clear signals after confluence
            self.signals.clear()

# Usage
async def run_multi_timeframe_monitoring():
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["1min", "5min", "15min"]
    )

    monitor = MultiTimeframeMonitor(suite)
    await monitor.setup_monitoring()

    # Keep monitoring for 10 minutes
    await asyncio.sleep(600)
```

## Data Processing and Aggregation

### Custom Bar Aggregation

```python
async def custom_bar_aggregation():
    suite = await TradingSuite.create("MNQ")

    # Custom aggregation periods
    custom_aggregator = CustomBarAggregator(period_seconds=45)  # 45-second bars

    async def on_tick(event):
        tick_data = event.data

        # Feed ticks to custom aggregator
        bar = await custom_aggregator.process_tick(tick_data)

        if bar:  # New bar completed
            print(f"Custom 45s bar:")
            print(f"  OHLC: {bar['open']:.2f}, {bar['high']:.2f}, {bar['low']:.2f}, {bar['close']:.2f}")
            print(f"  Volume: {bar['volume']}")

            # Your custom analysis here
            await analyze_custom_bar(bar)

    await suite.on(EventType.TICK_UPDATE, on_tick)

    # Stream for custom aggregation
    await asyncio.sleep(300)

class CustomBarAggregator:
    def __init__(self, period_seconds: int):
        self.period = timedelta(seconds=period_seconds)
        self.current_bar = None
        self.bar_start_time = None

    async def process_tick(self, tick_data):
        """Process tick and return completed bar if ready."""

        tick_time = datetime.fromisoformat(tick_data['timestamp'])
        price = tick_data['price']
        size = tick_data['size']

        # Initialize new bar
        if not self.current_bar:
            self.start_new_bar(tick_time, price)
            return None

        # Check if bar period elapsed
        if tick_time >= self.bar_start_time + self.period:
            completed_bar = self.current_bar.copy()
            self.start_new_bar(tick_time, price)
            return completed_bar

        # Update current bar
        self.current_bar['high'] = max(self.current_bar['high'], price)
        self.current_bar['low'] = min(self.current_bar['low'], price)
        self.current_bar['close'] = price
        self.current_bar['volume'] += size

        return None

    def start_new_bar(self, start_time, open_price):
        """Start a new bar."""
        self.bar_start_time = start_time
        self.current_bar = {
            'timestamp': start_time,
            'open': open_price,
            'high': open_price,
            'low': open_price,
            'close': open_price,
            'volume': 0
        }

async def analyze_custom_bar(bar):
    """Analyze custom aggregated bar."""

    body_size = abs(bar['close'] - bar['open'])
    range_size = bar['high'] - bar['low']

    if body_size > range_size * 0.7:
        direction = "bullish" if bar['close'] > bar['open'] else "bearish"
        print(f"  = Strong {direction} bar (body {body_size:.2f})")
```

### Volume Analysis

```python
async def volume_analysis():
    suite = await TradingSuite.create("MNQ", timeframes=["1min"])

    volume_analyzer = VolumeAnalyzer()

    async def on_bar_update(event):
        bar_data = event.data

        if bar_data['timeframe'] == '1min':
            bar = bar_data['data']
            analysis = await volume_analyzer.analyze_bar(bar)

            if analysis['volume_spike']:
                print(f"=% Volume spike detected!")
                print(f"   Volume: {bar['volume']} (Avg: {analysis['avg_volume']:.0f})")
                print(f"   Multiple: {analysis['volume_multiple']:.1f}x")

            if analysis['exhaustion']:
                print(f"=4 Volume exhaustion - potential reversal")

    await suite.on(EventType.NEW_BAR, on_bar_update)

    await asyncio.sleep(300)

class VolumeAnalyzer:
    def __init__(self, lookback_periods: int = 20):
        self.lookback_periods = lookback_periods
        self.volume_history = []

    async def analyze_bar(self, bar):
        """Analyze volume characteristics of a bar."""

        current_volume = bar['volume']
        self.volume_history.append(current_volume)

        # Keep only recent history
        if len(self.volume_history) > self.lookback_periods:
            self.volume_history.pop(0)

        if len(self.volume_history) < 5:
            return {"volume_spike": False, "exhaustion": False}

        # Calculate volume statistics
        avg_volume = sum(self.volume_history[:-1]) / len(self.volume_history[:-1])
        volume_multiple = current_volume / avg_volume if avg_volume > 0 else 1

        # Volume spike detection
        volume_spike = volume_multiple > 2.0  # 2x average volume

        # Volume exhaustion detection
        recent_avg = sum(self.volume_history[-3:]) / 3
        older_avg = sum(self.volume_history[-8:-5]) / 3
        exhaustion = recent_avg < older_avg * 0.6  # 40% drop in volume

        return {
            "volume_spike": volume_spike,
            "exhaustion": exhaustion,
            "avg_volume": avg_volume,
            "volume_multiple": volume_multiple,
            "recent_avg": recent_avg
        }
```

## Memory Management and Performance

### Automatic Memory Management

The RealtimeDataManager includes sophisticated memory management:

```python
async def memory_management_demo():
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["1sec", "15sec", "1min", "5min"]  # Multiple high-frequency timeframes
    )

    # Check memory usage
    memory_stats = await suite.data.get_memory_stats()

    print("Memory Usage:")
    for timeframe, stats in memory_stats['by_timeframe'].items():
        print(f"  {timeframe}: {stats['bar_count']} bars, {stats['memory_mb']:.1f} MB")

    print(f"Total Memory: {memory_stats['total_memory_mb']:.1f} MB")
    print(f"Tick Buffer: {memory_stats['tick_buffer_size']} ticks")

    # Memory limits (automatically managed)
    limits = await suite.data.get_memory_limits()
    print(f"\nMemory Limits:")
    print(f"  Max bars per timeframe: {limits['max_bars_per_timeframe']}")
    print(f"  Tick buffer size: {limits['tick_buffer_size']}")
    print(f"  Total memory limit: {limits['max_memory_mb']} MB")

    # Manual cleanup (rarely needed)
    await suite.data.cleanup_old_data(keep_hours=1)  # Keep only last hour
```

### Performance Optimization

```python
async def optimize_performance():
    suite = await TradingSuite.create("MNQ")

    # Performance monitoring
    perf_stats = await suite.data.get_performance_stats()

    print("Performance Statistics:")
    print(f"  Message Rate: {perf_stats['messages_per_second']:.1f}/sec")
    print(f"  Processing Latency: {perf_stats['avg_processing_latency_ms']:.2f}ms")
    print(f"  Memory Growth Rate: {perf_stats['memory_growth_mb_per_hour']:.2f} MB/hr")

    # Optimize settings based on usage
    if perf_stats['messages_per_second'] > 100:
        print("High message rate - enabling batching")
        await suite.data.enable_message_batching(batch_size=50, batch_timeout_ms=100)

    # Connection optimization
    connection_stats = await suite.data.get_connection_stats()

    print(f"\nConnection Statistics:")
    print(f"  Reconnections: {connection_stats['reconnection_count']}")
    print(f"  Average Latency: {connection_stats['avg_latency_ms']:.2f}ms")
    print(f"  Message Loss Rate: {connection_stats['message_loss_rate']:.4%}")

    if connection_stats['avg_latency_ms'] > 100:
        print("High latency detected - checking connection quality")
```

## Error Handling and Circuit Breaker

### Connection Error Handling

```python
async def robust_connection_handling():
    suite = await TradingSuite.create("MNQ")

    # Connection event handlers
    async def on_connected(event):
        print(" Connected to real-time data")

    async def on_disconnected(event):
        reason = event.data.get('reason', 'Unknown')
        print(f"L Disconnected: {reason}")

    async def on_reconnecting(event):
        attempt = event.data.get('attempt', 0)
        print(f"= Reconnecting (attempt {attempt})...")

    async def on_error(event):
        error = event.data.get('error', 'Unknown error')
        print(f"= Connection error: {error}")

    # Register connection event handlers
    await suite.on(EventType.REALTIME_CONNECTED, on_connected)
    await suite.on(EventType.REALTIME_DISCONNECTED, on_disconnected)
    await suite.on(EventType.REALTIME_RECONNECTING, on_reconnecting)
    await suite.on(EventType.REALTIME_ERROR, on_error)

    # Monitor connection health
    async def health_monitor():
        while True:
            try:
                health = await suite.data.get_connection_health()

                if health['status'] != 'CONNECTED':
                    print(f"  Connection issues: {health['status']}")

                    # Check if manual intervention needed
                    if health.get('consecutive_failures', 0) > 5:
                        print("Multiple failures - manual intervention may be needed")

            except Exception as e:
                print(f"Health check error: {e}")

            await asyncio.sleep(30)  # Check every 30 seconds

    # Run health monitoring
    health_task = asyncio.create_task(health_monitor())

    # Your trading logic here...
    await asyncio.sleep(300)

    # Cleanup
    health_task.cancel()
```

### Circuit Breaker Pattern

```python
class RealtimeCircuitBreaker:
    def __init__(self, suite, failure_threshold: int = 5, reset_timeout: int = 60):
        self.suite = suite
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def call_with_breaker(self, operation, *args, **kwargs):
        """Execute operation with circuit breaker protection."""

        if self.state == "OPEN":
            if self.should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")

        try:
            result = await operation(*args, **kwargs)
            await self.on_success()
            return result

        except Exception as e:
            await self.on_failure()
            raise e

    async def on_success(self):
        """Handle successful operation."""
        self.failure_count = 0
        self.state = "CLOSED"

    async def on_failure(self):
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            print(f"=% Circuit breaker OPEN after {self.failure_count} failures")

    def should_attempt_reset(self) -> bool:
        """Check if should attempt reset."""
        if self.last_failure_time:
            time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
            return time_since_failure >= self.reset_timeout
        return False

# Usage
async def use_circuit_breaker():
    suite = await TradingSuite.create("MNQ")
    breaker = RealtimeCircuitBreaker(suite)

    # Protected operations
    try:
        current_price = await breaker.call_with_breaker(
            suite.data.get_current_price
        )
        print(f"Price: ${current_price}")

    except Exception as e:
        print(f"Operation failed: {e}")
```

## Advanced Real-time Features

### Data Validation and Integrity

```python
class DataIntegrityChecker:
    def __init__(self, suite):
        self.suite = suite
        self.last_timestamps = {}
        self.price_validators = {}

    async def setup_validation(self):
        """Setup data validation."""

        await self.suite.on(EventType.TICK_UPDATE, self.validate_tick)
        await self.suite.on(EventType.NEW_BAR, self.validate_bar)

    async def validate_tick(self, event):
        """Validate incoming tick data."""
        tick_data = event.data

        # Timestamp validation
        timestamp = datetime.fromisoformat(tick_data['timestamp'])

        if 'tick' not in self.last_timestamps:
            self.last_timestamps['tick'] = timestamp
            return

        # Check for time regression
        if timestamp < self.last_timestamps['tick']:
            print(f"  Tick timestamp regression detected")
            return

        # Check for unrealistic time gaps
        time_gap = (timestamp - self.last_timestamps['tick']).total_seconds()
        if time_gap > 60:  # More than 1 minute gap
            print(f"  Large time gap in ticks: {time_gap:.1f} seconds")

        self.last_timestamps['tick'] = timestamp

        # Price validation
        price = tick_data['price']
        if not self.is_valid_price(price):
            print(f"  Invalid tick price: ${price}")

    async def validate_bar(self, event):
        """Validate bar data."""
        bar_data = event.data
        bar = bar_data['data']
        timeframe = bar_data['timeframe']

        # OHLC consistency
        if not (bar['low'] <= bar['open'] <= bar['high'] and
                bar['low'] <= bar['close'] <= bar['high']):
            print(f"  Invalid OHLC relationship in {timeframe} bar")

        # Volume validation
        if bar['volume'] < 0:
            print(f"  Negative volume in {timeframe} bar")

        # Timestamp sequence validation
        timestamp = datetime.fromisoformat(bar['timestamp'])
        last_key = f"bar_{timeframe}"

        if last_key in self.last_timestamps:
            if timestamp <= self.last_timestamps[last_key]:
                print(f"  Bar timestamp issue in {timeframe}")

        self.last_timestamps[last_key] = timestamp

    def is_valid_price(self, price: float) -> bool:
        """Validate price reasonableness."""
        # Basic sanity checks for MNQ
        return 1000 <= price <= 50000  # Reasonable range for MNQ

# Usage
async def run_data_validation():
    suite = await TradingSuite.create("MNQ", timeframes=["1min", "5min"])

    validator = DataIntegrityChecker(suite)
    await validator.setup_validation()

    # Data will be validated automatically
    await asyncio.sleep(300)
```

### Market Session Tracking

```python
class MarketSessionTracker:
    def __init__(self, suite):
        self.suite = suite
        self.session_start = None
        self.session_volume = 0
        self.session_high = None
        self.session_low = None
        self.pre_market_data = []

    async def setup_session_tracking(self):
        """Setup market session tracking."""

        await self.suite.on(EventType.TICK_UPDATE, self.track_session_data)
        await self.suite.on(EventType.NEW_BAR, self.update_session_stats)

        # Check current session status
        await self.initialize_session()

    async def initialize_session(self):
        """Initialize session tracking."""
        current_time = datetime.now()

        # Market hours for ES/NQ (CT): 5:00 PM - 4:00 PM next day
        if current_time.hour >= 17 or current_time.hour < 16:
            self.session_start = current_time
            print(f"= Market session active since {self.session_start}")
        else:
            print("= Market closed")

    async def track_session_data(self, event):
        """Track session-level data."""
        tick_data = event.data
        price = tick_data['price']
        size = tick_data['size']

        # Update session statistics
        self.session_volume += size

        if self.session_high is None or price > self.session_high:
            self.session_high = price
            print(f"=% New session high: ${price}")

        if self.session_low is None or price < self.session_low:
            self.session_low = price
            print(f"D  New session low: ${price}")

        # Track pre-market activity
        current_time = datetime.now()
        if current_time.hour < 9:  # Before 9 AM
            self.pre_market_data.append({
                'time': current_time,
                'price': price,
                'size': size
            })

    async def update_session_stats(self, event):
        """Update session statistics on bar completion."""
        bar_data = event.data

        if bar_data['timeframe'] == '1min':
            bar = bar_data['data']

            # Check for session milestones
            if self.session_volume % 100000 == 0:  # Every 100k contracts
                print(f"= Session volume milestone: {self.session_volume:,}")

            # Range expansion alerts
            if self.session_high and self.session_low:
                session_range = self.session_high - self.session_low

                if session_range > 200:  # Large range for MNQ
                    print(f"= Wide session range: ${session_range:.2f}")

    async def get_session_summary(self):
        """Get current session summary."""

        if not self.session_start:
            return "Market session not active"

        session_duration = datetime.now() - self.session_start

        return {
            'session_start': self.session_start,
            'duration': session_duration,
            'volume': self.session_volume,
            'high': self.session_high,
            'low': self.session_low,
            'range': self.session_high - self.session_low if self.session_high and self.session_low else 0,
            'pre_market_ticks': len(self.pre_market_data)
        }

# Usage
async def track_market_session():
    suite = await TradingSuite.create("MNQ", timeframes=["1min"])

    tracker = MarketSessionTracker(suite)
    await tracker.setup_session_tracking()

    # Periodic session summary
    async def print_session_summary():
        while True:
            summary = await tracker.get_session_summary()
            if isinstance(summary, dict):
                print(f"\n= Session Summary:")
                print(f"   Duration: {summary['duration']}")
                print(f"   Volume: {summary['volume']:,}")
                print(f"   Range: ${summary['range']:.2f}")
                print(f"   High/Low: ${summary['high']:.2f}/${summary['low']:.2f}")

            await asyncio.sleep(300)  # Every 5 minutes

    summary_task = asyncio.create_task(print_session_summary())

    # Keep running
    await asyncio.sleep(3600)  # 1 hour

    summary_task.cancel()
```

## Best Practices

### 1. Efficient Event Handling

```python
# Good: Lightweight event handlers
async def efficient_tick_handler(event):
    """Efficient tick processing."""
    tick_data = event.data

    # Quick analysis only
    if tick_data['size'] > 100:  # Large size threshold
        # Queue for detailed analysis
        await analysis_queue.put(tick_data)

# Avoid: Heavy processing in event handlers
async def inefficient_handler(event):
    """Avoid this - too much processing in handler."""
    tick_data = event.data

    # Don't do heavy calculations here
    complex_analysis = await heavy_calculation(tick_data)  # L Bad
    database_write = await save_to_database(tick_data)     # L Bad
```

### 2. Memory-Conscious Data Handling

```python
async def memory_conscious_streaming():
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["1min", "5min"],  # Limit timeframes to what you need
        initial_days=1  # Don't load excessive historical data
    )

    # Periodic cleanup
    async def periodic_cleanup():
        while True:
            await asyncio.sleep(3600)  # Every hour
            await suite.data.cleanup_old_data(keep_hours=2)  # Keep only 2 hours

    cleanup_task = asyncio.create_task(periodic_cleanup())

    # Your streaming logic...

    cleanup_task.cancel()
```

### 3. Connection Resilience

```python
async def resilient_streaming():
    suite = await TradingSuite.create("MNQ")

    # Connection monitoring
    async def monitor_connection():
        consecutive_failures = 0

        while True:
            try:
                health = await suite.data.get_connection_health()

                if health['status'] == 'CONNECTED':
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    print(f"Connection issue #{consecutive_failures}")

                    if consecutive_failures > 3:
                        print("Multiple connection failures - taking defensive action")
                        # Stop placing new orders, close positions, etc.

            except Exception as e:
                print(f"Health check failed: {e}")
                consecutive_failures += 1

            await asyncio.sleep(15)

    monitor_task = asyncio.create_task(monitor_connection())

    # Your trading logic...

    monitor_task.cancel()
```

## Summary

The ProjectX RealtimeDataManager provides comprehensive real-time data streaming capabilities:

- **High-performance WebSocket connectivity** with automatic reconnection
- **Multi-timeframe synchronization** across any number of timeframes
- **Event-driven architecture** for responsive real-time applications
- **Memory management** with sliding windows and automatic cleanup
- **Data validation** ensuring integrity of streaming data
- **Circuit breaker patterns** for robust error handling
- **Performance optimization** with message batching and connection pooling

All real-time operations are designed for production trading environments with minimal latency, comprehensive error handling, and automatic resource management.

---

**Next**: [Technical Indicators Guide](indicators.md) | **Previous**: [Position Management Guide](positions.md)
