# Factory Functions Removal Plan

## Overview
The new TradingSuite class (v3.0.0) completely replaces all factory functions, providing a cleaner, more intuitive API. This document tracks the removal of obsolete factory functions.

## Obsolete Factory Functions to Remove

### 1. `create_trading_suite()` (340 lines!)
**Replaced by:** `TradingSuite.create()`
- Old: Complex 340-line function with many parameters
- New: Simple class method with sensible defaults
- **Action:** DELETE after examples updated

### 2. `create_initialized_trading_suite()`
**Replaced by:** `TradingSuite.create()` (auto-initializes by default)
- Old: Wrapper around create_trading_suite
- New: Built into TradingSuite.create()
- **Action:** DELETE after examples updated

### 3. `create_order_manager()`
**Replaced by:** `suite.orders` (automatically created)
- Old: Manual instantiation required
- New: Automatically wired in TradingSuite
- **Action:** DELETE immediately (no direct usage in examples)

### 4. `create_position_manager()`
**Replaced by:** `suite.positions` (automatically created)
- Old: Manual instantiation with optional params
- New: Automatically wired with proper dependencies
- **Action:** DELETE immediately (no direct usage in examples)

### 5. `create_realtime_client()`
**Replaced by:** Internal to TradingSuite
- Old: Manual WebSocket client creation
- New: Automatically created and managed
- **Action:** DELETE after checking internal usage

### 6. `create_data_manager()`
**Replaced by:** `suite.data` (automatically created)
- Old: Manual instantiation with timeframes
- New: Automatically created with config
- **Action:** DELETE immediately (no direct usage in examples)

## Comparison

### Old Way (v2.x)
```python
# 50+ lines of setup
async with ProjectX.from_env() as client:
    await client.authenticate()
    
    # Manual component creation
    realtime_client = create_realtime_client(
        jwt_token=client.session_token,
        account_id=str(client.account_info.id)
    )
    
    # More manual creation
    data_manager = create_data_manager(
        instrument="MNQ",
        project_x=client,
        realtime_client=realtime_client,
        timeframes=["1min", "5min"]
    )
    
    order_manager = create_order_manager(client, realtime_client)
    position_manager = create_position_manager(client, realtime_client, order_manager)
    
    # Manual connections
    await realtime_client.connect()
    await realtime_client.subscribe_user_updates()
    await position_manager.initialize(realtime_client, order_manager)
    await data_manager.initialize()
    
    # Manual subscriptions
    instrument_info = await client.get_instrument("MNQ")
    await realtime_client.subscribe_market_data([instrument_info.id])
    await data_manager.start_realtime_feed()
    
    # Now ready to use...
```

### New Way (v3.0)
```python
# 1 line!
suite = await TradingSuite.create("MNQ")
# Everything is ready to use!
```

## Files to Update

### Examples Using Factory Functions
1. `examples/integrated_trading_suite.py` - Uses `create_trading_suite`
2. `examples/factory_functions_demo.py` - Demonstrates all factory functions
3. `examples/12_simplified_strategy.py` - Uses `create_initialized_trading_suite`
4. `examples/13_factory_comparison.py` - Compares factory approaches

### Test Files
1. `tests/test_factory_functions.py` - Tests factory functions directly

## Removal Steps

### Phase 1: Immediate Removals (Safe)
These can be removed now as they're not directly used in examples:
- `create_order_manager()` 
- `create_position_manager()`
- `create_data_manager()`

### Phase 2: After Example Updates
These need examples updated first:
- `create_trading_suite()`
- `create_initialized_trading_suite()`
- `create_realtime_client()`

### Phase 3: Clean Up Exports
Remove from `__all__` in `__init__.py`:
- "create_data_manager"
- "create_initialized_trading_suite"
- "create_order_manager"
- "create_position_manager"
- "create_realtime_client"
- "create_trading_suite"

## Benefits of Removal

1. **Simpler API Surface**: 6 functions → 1 class
2. **Less Code**: ~500 lines removed
3. **No Confusion**: One obvious way to initialize
4. **Better Maintenance**: Single point of initialization logic
5. **Cleaner Documentation**: Focus on TradingSuite only

## Migration for Users

### Before (v2.x)
```python
suite = await create_trading_suite(
    instrument="MNQ",
    project_x=client,
    timeframes=["1min", "5min"],
    enable_orderbook=True,
    auto_connect=True,
    auto_subscribe=True,
    initial_days=5
)
```

### After (v3.0)
```python
suite = await TradingSuite.create(
    "MNQ",
    timeframes=["1min", "5min"],
    features=["orderbook"],
    initial_days=5
)
```

## Timeline

1. **NOW**: Create this removal plan ✅
2. **Day 2**: Update examples to use TradingSuite
3. **Day 2**: Remove all factory functions
4. **Day 2**: Update tests
5. **Day 2**: Clean up __init__.py exports