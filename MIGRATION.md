# Migration Guide

## v3.1.14 - Order Tracking Consolidation

### Overview
The `order_tracker.py` module has been deprecated in favor of using the integrated methods in `TradingSuite`. This change simplifies the API and reduces code duplication.

### Deprecated Components
- `OrderTracker` class from `project_x_py.order_tracker`
- `OrderChainBuilder` class from `project_x_py.order_tracker`
- `track_order()` function from `project_x_py.order_tracker`

These will be removed in v4.0.0 (expected Q2 2025).

### Migration Path

#### OrderTracker
**Old way:**
```python
from project_x_py.order_tracker import OrderTracker

async with OrderTracker(suite) as tracker:
    order = await suite.orders.place_limit_order(...)
    tracker.track(order)
    filled = await tracker.wait_for_fill()
```

**New way (no import needed):**
```python
# OrderTracker is accessed directly from TradingSuite
async with suite.track_order() as tracker:
    order = await suite.orders.place_limit_order(...)
    tracker.track(order)
    filled = await tracker.wait_for_fill()
```

#### OrderChainBuilder
**Old way:**
```python
from project_x_py.order_tracker import OrderChainBuilder

chain = OrderChainBuilder(suite)
chain.market_order(size=2).with_stop_loss(offset=50)
result = await chain.execute()
```

**New way (no import needed):**
```python
# OrderChainBuilder is accessed directly from TradingSuite
chain = suite.order_chain()
chain.market_order(size=2).with_stop_loss(offset=50)
result = await chain.execute()
```

### Benefits of Migration
1. **Simpler API**: No need to import separate classes
2. **Better integration**: Direct access through TradingSuite
3. **Reduced confusion**: Single source of truth for order tracking
4. **Type safety**: Better IDE support with integrated methods

### Backward Compatibility
The deprecated classes are still available and will continue to work until v4.0.0. However, they will emit deprecation warnings when used.

### Timeline
- **v3.1.14** (Current): Deprecation warnings added
- **v3.2.0**: Documentation will be updated to use new patterns
- **v4.0.0**: Deprecated classes will be removed

### Questions?
If you have any questions about this migration, please open an issue on GitHub.