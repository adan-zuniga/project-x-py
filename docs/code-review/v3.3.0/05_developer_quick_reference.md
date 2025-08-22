# Developer Quick Reference - v3.3.0

**Review Date**: 2025-08-22  
**Target Audience**: Development Team  
**Purpose**: Quick actionable insights from code review

## Immediate Action Items

### 🚨 High Priority (Complete This Sprint)
1. **OrderBook Spoofing Detection** - `/src/project_x_py/orderbook/detection.py`
   ```python
   # TODO: Implement detect_spoofing_patterns method
   async def detect_spoofing_patterns(self) -> dict[str, Any]:
       # Track rapid order placement/cancellation
       # Identify phantom liquidity patterns
       # Generate confidence scores
   ```

### 📋 Medium Priority (Next 2-4 Weeks)
1. **Add Test Coverage** - Create tests for:
   - OrderBook iceberg detection edge cases
   - Indicators calculation accuracy vs TA-Lib
   - TradingSuite initialization failure scenarios
   - EventBus concurrency and memory management

2. **Performance Benchmarks** - Establish baselines for:
   - OrderBook depth updates (target: 10K+/sec)
   - Indicator calculations (target: <10ms for 10K bars)
   - EventBus throughput (target: 1K+ events/sec)

## Code Quality Guidelines

### ✅ What's Working Well (Keep Doing)
1. **Async/Await Patterns**: All modules properly use async throughout
2. **Polars DataFrames**: Excellent performance with vectorized operations
3. **Component Architecture**: Clean separation of concerns
4. **Memory Management**: Sliding windows and weak references work well
5. **Event System**: Unified EventBus provides excellent inter-component communication

### ⚠️ Common Patterns to Watch
1. **Thread Safety**: Always use async locks for shared data structures
   ```python
   async def update_data(self):
       async with self.data_lock:  # ✅ Good
           # Modify shared data
   ```

2. **Error Handling**: Use decorators and proper exception isolation
   ```python
   @handle_errors("operation name", reraise=False, default_return=None)
   async def risky_operation(self):
       # Implementation
   ```

3. **Configuration**: Use typed configs with defaults
   ```python
   def get_config(self) -> ComponentConfig:
       if self.custom_config:
           return self.custom_config
       return default_config()  # ✅ Good - always return valid config
   ```

## Performance Best Practices

### 🚀 OrderBook Optimization
```python
# ✅ Good - Efficient Polars chaining
result = (
    self.orderbook_bids.lazy()
    .filter(pl.col("volume") > 0)
    .sort("price", descending=True)
    .head(levels)
    .collect()
)

# ❌ Avoid - Multiple DataFrame operations
filtered = self.orderbook_bids.filter(pl.col("volume") > 0)
sorted_data = filtered.sort("price", descending=True)
result = sorted_data.head(levels)
```

### 📊 Indicators Optimization
```python
# ✅ Good - Single chain with intermediate column cleanup
result = (
    data.with_columns([...])
    .with_columns([...])
    .drop(["temp_col1", "temp_col2"])  # Clean up intermediate columns
)

# ✅ Good - Use safe_division utility
safe_division(pl.col("numerator"), pl.col("denominator"))
```

### ⚡ EventBus Best Practices
```python
# ✅ Good - Async handlers
@suite.events.on(EventType.ORDER_FILLED)
async def handle_order_fill(event):
    # Async processing
    pass

# ❌ Avoid - Sync handlers (will raise exception)
def sync_handler(event):  # This will fail validation
    pass
```

## Testing Guidelines

### 🧪 Test Structure
```python
@pytest.mark.asyncio
async def test_orderbook_depth_accuracy():
    """Test orderbook depth calculations are mathematically correct."""
    # Arrange - Create test data
    # Act - Perform operation
    # Assert - Verify results
    
@pytest.mark.parametrize("period", [14, 21, 50])
async def test_rsi_calculation_accuracy(period):
    """Test RSI calculation matches TA-Lib reference."""
    # Compare with known-good reference implementation
```

### 📈 Performance Tests
```python
@pytest.mark.performance
async def test_indicator_calculation_speed():
    """Verify indicator calculations meet performance targets."""
    data = create_large_dataset(rows=10000)
    
    start_time = time.perf_counter()
    result = RSI(data, period=14)
    elapsed = time.perf_counter() - start_time
    
    assert elapsed < 0.010  # 10ms target
```

## Memory Management Guidelines

### 💾 Efficient Memory Usage
```python
# ✅ Good - Bounded data structures
self.trade_history: deque = deque(maxlen=1000)
self.depth_levels: dict = {}  # With periodic cleanup

# ✅ Good - Weak references for event tracking
self._active_tasks: WeakSet[asyncio.Task] = WeakSet()

# ✅ Good - Lazy evaluation
return self.data.lazy().filter(...).collect()
```

### 🧹 Resource Cleanup
```python
# ✅ Good - Context manager pattern
async with TradingSuite.create("MNQ") as suite:
    # Use suite
    pass  # Automatic cleanup

# ✅ Good - Manual cleanup in finally blocks
try:
    await component.initialize()
    # Use component
finally:
    await component.cleanup()
```

## Configuration Best Practices

### ⚙️ Typed Configurations
```python
# ✅ Good - Use typed configurations
@dataclass
class OrderManagerConfig:
    enable_bracket_orders: bool = True
    enable_trailing_stops: bool = True
    max_position_size: int = 1000

# ✅ Good - Feature-based configuration generation
def get_config(features: list[Features]) -> OrderManagerConfig:
    return OrderManagerConfig(
        enable_bracket_orders=Features.RISK_MANAGER in features,
        # ... other settings based on features
    )
```

### 📁 Configuration Files
```yaml
# trading_config.yaml
instrument: MNQ
timeframes:
  - 1min
  - 5min
features:
  - orderbook
  - risk_manager
initial_days: 5
```

## Integration Patterns

### 🔗 Component Communication
```python
# ✅ Good - Use EventBus for component communication
await self.event_bus.emit(
    EventType.ORDER_FILLED,
    {"order_id": order.id, "fill_price": fill_price},
    source="OrderManager"
)

# ✅ Good - Listen for events from other components
@suite.events.on(EventType.NEW_BAR)
async def on_new_bar(event):
    bar_data = event.data
    # Process new bar
```

### 🏗️ Dependency Injection
```python
# ✅ Good - Pass dependencies through constructor
class OrderManager:
    def __init__(self, client: ProjectXBase, event_bus: EventBus):
        self.client = client
        self.event_bus = event_bus
        
# ✅ Good - Use factory pattern for complex initialization  
suite = await TradingSuite.create("MNQ", features=["orderbook"])
```

## Debugging and Monitoring

### 🐛 Debug Utilities
```python
# Enable event history for debugging
suite.events.enable_history(max_size=1000)

# Get event history
recent_events = suite.events.get_history()

# Get component statistics
stats = await suite.get_comprehensive_stats()
memory_stats = component.get_memory_stats()
```

### 📊 Health Monitoring
```python
# Check component health
health = await client.get_health_status()
performance_stats = await client.get_performance_stats()

# Monitor memory usage
memory_mb = await component.get_memory_usage()
if memory_mb > threshold:
    logger.warning(f"High memory usage: {memory_mb}MB")
```

## Common Pitfalls to Avoid

### ❌ Don't Do This
```python
# ❌ Sync operations in async context
def sync_calculation():  # Wrong in async module
    return heavy_computation()

# ❌ Direct DataFrame copying 
df_copy = original_df.clone()  # Memory inefficient

# ❌ Missing error handling
async def risky_operation():
    result = await api_call()  # Could fail
    return result  # No error handling

# ❌ Unbounded data growth
self.data_list.append(new_data)  # Grows forever
```

### ✅ Do This Instead
```python
# ✅ Async operations throughout
async def async_calculation():
    return await heavy_async_computation()

# ✅ Efficient DataFrame operations
result = original_df.lazy().select([...]).collect()

# ✅ Comprehensive error handling
@handle_errors("operation name")
async def safe_operation():
    result = await api_call()
    return result

# ✅ Bounded data structures
self.data_deque = deque(maxlen=1000)
self.data_deque.append(new_data)
```

## Quick Reference Links

- **OrderBook Analytics**: `src/project_x_py/orderbook/analytics.py`
- **Indicator Calculations**: `src/project_x_py/indicators/momentum.py`  
- **TradingSuite Factory**: `src/project_x_py/trading_suite.py:312`
- **EventBus API**: `src/project_x_py/event_bus.py:127`
- **Configuration Types**: `src/project_x_py/types/config_types.py`
- **Statistics System**: `src/project_x_py/statistics/`

---
*Keep this reference handy during development. Focus on completing the spoofing detection implementation and adding comprehensive test coverage.*