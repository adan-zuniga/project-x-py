# Sync to Async Migration Plan for project-x-py

## Overview
This document tracks the migration from synchronous to asynchronous implementations in the project-x-py SDK. Each sync component must have a fully functional async equivalent before removal.

## Core Components

### 1. Client Classes
- [ ] **Sync: ProjectX** → **Async: AsyncProjectX**
  - Location: `src/project_x_py/client.py` → `src/project_x_py/async_client.py`
  - Status: ✅ Async version exists
  - Verification needed:
    - [ ] All authentication methods
    - [ ] Account management
    - [ ] Instrument search/retrieval
    - [ ] Market data methods
    - [ ] Position/trade queries

### 2. Order Management
- [ ] **Sync: OrderManager** → **Async: AsyncOrderManager**
  - Location: `src/project_x_py/order_manager.py` → `src/project_x_py/async_order_manager.py`
  - Status: ✅ Async version exists
  - Verification needed:
    - [ ] Order placement (all types)
    - [ ] Order modification
    - [ ] Order cancellation
    - [ ] Order search/queries
    - [ ] Bracket order support
    - [ ] Real-time order updates

### 3. Position Management
- [ ] **Sync: PositionManager** → **Async: AsyncPositionManager**
  - Location: `src/project_x_py/position_manager.py` → `src/project_x_py/async_position_manager.py`
  - Status: ✅ Async version exists
  - Verification needed:
    - [ ] Position queries
    - [ ] Portfolio P&L calculations
    - [ ] Risk metrics
    - [ ] Position closure
    - [ ] Real-time position updates

### 4. Real-time Data Management
- [ ] **Sync: ProjectXRealtimeDataManager** → **Async: AsyncRealtimeDataManager**
  - Location: `src/project_x_py/realtime_data_manager.py` → `src/project_x_py/async_realtime_data_manager.py`
  - Status: ✅ Async version exists
  - Verification needed:
    - [ ] Historical data loading
    - [ ] Real-time data subscription
    - [ ] Multi-timeframe support
    - [ ] Data aggregation
    - [ ] Tick data handling

### 5. OrderBook
- [ ] **Sync: OrderBook** → **Async: AsyncOrderBook**
  - Location: `src/project_x_py/orderbook.py` → `src/project_x_py/async_orderbook/`
  - Status: ✅ Async version exists (refactored into module)
  - Verification needed:
    - [ ] Market depth tracking
    - [ ] Bid/ask spread calculations
    - [ ] Market imbalance detection
    - [ ] Iceberg order detection
    - [ ] Trade flow analysis

### 6. Real-time Client
- [ ] **Sync: ProjectXRealtimeClient** → **Async: AsyncProjectXRealtimeClient**
  - Location: `src/project_x_py/realtime.py` → `src/project_x_py/async_realtime.py`
  - Status: ✅ Async version exists
  - Verification needed:
    - [ ] WebSocket connection management
    - [ ] Market data subscriptions
    - [ ] User update subscriptions
    - [ ] Error handling/reconnection
    - [ ] Event callbacks

## Examples Migration Status

### Completed Async Examples:
1. ✅ `async_01_basic_sdk_usage.py` (from `01_basic_sdk_usage.py`)
2. ✅ `async_02_multi_timeframe_data.py` (from `02_multi_timeframe_data.py`)
3. ✅ `async_03_technical_indicators.py` (from `03_technical_indicators.py`)
4. ✅ `async_04_advanced_order_types.py` (from `04_advanced_order_types.py`)
5. ✅ `async_05_orderbook_analysis.py` (from `05_orderbook_analysis.py`)
6. ✅ `async_06_multi_timeframe_strategy.py` (from `06_multi_timeframe_strategy.py`)
7. ✅ `async_07_paper_trading_template.py` (from `07_paper_trading_template.py`)
8. ✅ `async_08_order_and_position_tracking.py` (from `08_order_and_position_tracking.py`)
9. ✅ `async_09_get_check_available_instruments.py` (from `09_get_check_available_instruments.py`)

### Examples without Async Versions:
- None identified

## Factory Functions and Utilities

### Factory Functions (`__init__.py`):
- [ ] `create_trading_suite()` → `create_async_trading_suite()` ✅
- [ ] `create_order_manager()` → `create_async_order_manager()` ✅
- [ ] `create_position_manager()` → `create_async_position_manager()` ✅
- [ ] `create_orderbook()` → `create_async_orderbook()` ✅

## Method-by-Method Verification Checklist

### AsyncProjectX Methods to Verify:
```python
# Authentication & Setup
- [ ] from_env()
- [ ] from_config_file()
- [ ] authenticate()
- [ ] list_accounts()

# Market Data
- [ ] get_instrument()
- [ ] search_instruments()
- [ ] get_bars()
- [ ] get_positions()
- [ ] search_open_positions()
- [ ] search_trades()

# Utilities
- [ ] get_health_status()
```

### AsyncOrderManager Methods to Verify:
```python
# Order Operations
- [ ] place_market_order()
- [ ] place_limit_order()
- [ ] place_stop_order()
- [ ] place_stop_limit_order()
- [ ] place_bracket_order()
- [ ] modify_order()
- [ ] cancel_order()
- [ ] cancel_all_orders()

# Order Queries
- [ ] get_order()
- [ ] search_orders()
- [ ] search_open_orders()
- [ ] get_order_status()
```

### AsyncPositionManager Methods to Verify:
```python
# Position Operations
- [ ] get_all_positions()
- [ ] get_position()
- [ ] close_position()
- [ ] close_position_market()
- [ ] close_position_direct()
- [ ] close_all_positions()

# Analytics
- [ ] get_portfolio_pnl()
- [ ] get_position_analytics()
- [ ] calculate_portfolio_metrics()
```

### AsyncRealtimeDataManager Methods to Verify:
```python
# Data Operations
- [ ] initialize()
- [ ] start_realtime_feed()
- [ ] stop_realtime_feed()
- [ ] get_data()
- [ ] get_current_price()
- [ ] get_tick_data()
- [ ] add_bar_callback()
- [ ] add_tick_callback()
```

### AsyncOrderBook Methods to Verify:
```python
# OrderBook Operations
- [ ] get_best_bid_ask()
- [ ] get_bid_ask_spread()
- [ ] get_orderbook_snapshot()
- [ ] get_market_imbalance()
- [ ] get_orderbook_depth()
- [ ] detect_iceberg_orders()
- [ ] get_trade_flow_summary()
```

## Testing Requirements

Before removing sync versions, we need to:

1. **Unit Tests**: Ensure all async methods have equivalent test coverage
2. **Integration Tests**: Verify async components work together
3. **Performance Tests**: Confirm async versions perform equal or better
4. **Example Scripts**: All examples must run without errors
5. **Documentation**: Update all docs to use async examples

## Migration Steps

1. **Phase 1: Verification** (Current)
   - Complete this checklist
   - Run all async examples
   - Compare outputs with sync versions

2. **Phase 2: Documentation**
   - Update README.md
   - Update all docstrings
   - Create migration guide

3. **Phase 3: Deprecation**
   - Add deprecation warnings to sync versions
   - Release version with warnings

4. **Phase 4: Removal**
   - Remove all sync implementations
   - Update imports
   - Final testing

## Risks and Considerations

1. **Breaking Changes**: This is a major breaking change for all users
2. **Migration Path**: Need clear guide for users to migrate their code
3. **Backwards Compatibility**: Consider keeping sync wrappers temporarily
4. **Performance**: Ensure async doesn't degrade performance for simple use cases

## Next Steps

1. Run through each verification checklist
2. Create detailed comparison tests
3. Document any missing functionality
4. Create user migration guide