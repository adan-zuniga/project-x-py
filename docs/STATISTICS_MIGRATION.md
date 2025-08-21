# Statistics System Migration Guide (v3.2.1 → v3.3.0)

## Overview

The v3.3.0 release introduces a completely redesigned statistics system that is 100% async internally. This guide helps you migrate from the old mixed sync/async patterns to the new unified async architecture.

## Key Changes

### 1. All New Statistics Methods are Async

**Old Pattern (v3.2.1):**
```python
# Mixed sync/async methods caused deadlocks
stats = component.get_memory_stats()  # Synchronous
await component.track_operation("test")  # Async
```

**New Pattern (v3.3.0):**
```python
# All new methods are async
stats = await component.get_stats()  # Async
health = await component.get_health_score()  # Async
await component.track_error(error, "context")  # Async
```

### 2. Backward Compatibility

For backward compatibility, `get_memory_stats()` remains synchronous:

```python
# Still works for existing code
memory_stats = component.get_memory_stats()  # Synchronous - DEPRECATED
```

This method is deprecated and will be removed in v4.0.0. New code should use:

```python
# New async approach
stats = await component.get_stats()
memory_usage = await component.get_memory_usage()
```

## Migration Strategy

### Phase 1: Immediate Changes (Required)

1. **Remove old imports:**
```python
# Remove these
from project_x_py.utils import EnhancedStatsTrackingMixin
from project_x_py.utils import StatsTrackingMixin
from project_x_py.utils import StatisticsAggregator

# Use these instead
from project_x_py.statistics import (
    BaseStatisticsTracker,
    StatisticsAggregator,
    HealthMonitor,
    StatsExporter
)
```

2. **Update statistics calls to async:**
```python
# Old
stats = manager.get_order_statistics()

# New
stats = await manager.get_order_statistics_async()
# Or for new unified interface:
stats = await manager.get_stats()
```

### Phase 2: Recommended Updates

1. **Use new health monitoring:**
```python
# Get component health score (0-100)
health = await component.get_health_score()

# Get detailed health breakdown
monitor = HealthMonitor()
breakdown = await monitor.get_health_breakdown(stats)
```

2. **Use new export capabilities:**
```python
from project_x_py.statistics import StatsExporter

exporter = StatsExporter()
json_stats = await exporter.to_json(stats, pretty=True)
prometheus_metrics = await exporter.to_prometheus(stats)
```

3. **Use new error tracking:**
```python
# Track errors with context
await component.track_error(
    error=exception,
    context="order_placement",
    details={"order_id": "12345", "size": 10}
)

# Get error statistics
error_count = await component.get_error_count()
recent_errors = await component.get_recent_errors(limit=10)
```

## Component-Specific Notes

### OrderManager
- `get_order_statistics()` → `await get_order_statistics_async()` (new method)
- Internal statistics automatically tracked on order events

### PositionManager
- `get_position_stats()` → `await get_position_stats()` (new async method)
- P&L tracking now automatic with event system

### RealtimeDataManager
- Uses composition pattern with BaseStatisticsTracker
- All statistics methods delegated to internal tracker

### OrderBook
- Now inherits from BaseStatisticsTracker
- `get_memory_stats()` is now async internally but wrapped for compatibility

### RiskManager
- Comprehensive risk statistics tracking added
- New metrics: violations, checks, position sizing

## Performance Considerations

### TTL Caching
The new system includes 5-second TTL caching by default:

```python
# Cached automatically for 5 seconds
stats1 = await component.get_stats()
stats2 = await component.get_stats()  # Returns cached value if < 5 seconds
```

### Parallel Collection
Statistics are collected in parallel from all components:

```python
aggregator = StatisticsAggregator()
# Collects from all components simultaneously
stats = await aggregator.get_comprehensive_stats()
```

### Memory Management
Automatic cleanup with bounded collections:
- Error history: Max 100 entries
- Operation timings: Max 1000 per operation
- Circular buffers prevent memory leaks

## Common Migration Issues

### Issue 1: Import Errors
```python
ImportError: cannot import name 'EnhancedStatsTrackingMixin'
```
**Solution:** Update imports to use new statistics module.

### Issue 2: Sync/Async Mismatch
```python
TypeError: object dict can't be used in 'await' expression
```
**Solution:** Remove `await` for `get_memory_stats()`, add `await` for new methods.

### Issue 3: Missing Methods
```python
AttributeError: 'OrderManager' object has no attribute 'get_stats'
```
**Solution:** Ensure you're using v3.3.0+ of the SDK.

## Testing Your Migration

Run this test to verify your migration:

```python
import asyncio
from project_x_py import TradingSuite

async def test_statistics():
    suite = await TradingSuite.create("MNQ")
    
    # Test new async methods
    stats = await suite.orders.get_stats()
    assert "name" in stats
    assert stats["name"] == "order_manager"
    
    # Test health scoring
    health = await suite.orders.get_health_score()
    assert 0 <= health <= 100
    
    # Test backward compatibility
    memory_stats = suite.orders.get_memory_stats()
    assert isinstance(memory_stats, dict)
    
    print("✅ Migration successful!")

asyncio.run(test_statistics())
```

## Support

For migration assistance:
1. Check the [CHANGELOG](../CHANGELOG.md) for detailed changes
2. Review the [test files](../tests/statistics/) for usage examples
3. Open an issue on GitHub for specific problems

## Timeline

- **v3.3.0** (Current): New async statistics system introduced
- **v3.4.0** (Future): Deprecation warnings for sync methods
- **v4.0.0** (Future): Removal of deprecated sync methods

Plan your migration accordingly to avoid breaking changes in v4.0.0.