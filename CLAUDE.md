# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status: v3.1.13 - Stable Production Release

**IMPORTANT**: This project uses a fully asynchronous architecture. All APIs are async-only, optimized for high-performance futures trading.

## Development Phase Guidelines

**IMPORTANT**: This project has reached stable production status. When making changes:

1. **Maintain Backward Compatibility**: Keep existing APIs functional with deprecation warnings
2. **Deprecation Policy**: Mark deprecated features with warnings, remove after 2 minor versions
3. **Semantic Versioning**: Follow semver strictly (MAJOR.MINOR.PATCH)
4. **Migration Paths**: Provide clear migration guides for breaking changes
5. **Modern Patterns**: Use the latest Python patterns while maintaining compatibility
6. **Gradual Refactoring**: Improve code quality without breaking existing interfaces
7. **Async-First**: All new code must use async/await patterns

Example approach:
- ✅ DO: Keep old method signatures with deprecation warnings
- ✅ DO: Provide new improved APIs alongside old ones
- ✅ DO: Add compatibility shims when necessary
- ✅ DO: Document migration paths clearly
- ❌ DON'T: Break existing APIs without major version bump
- ❌ DON'T: Remove deprecated features without proper notice period

### Deprecation Process
1. Mark as deprecated with `warnings.warn()` and `@deprecated` decorator
2. Document replacement in deprecation message
3. Keep deprecated feature for at least 2 minor versions
4. Remove only in major version releases (4.0.0, 5.0.0, etc.)

Example:
```python
import warnings
from typing import deprecated

@deprecated("Use new_method() instead. Will be removed in v4.0.0")
def old_method(self):
    warnings.warn(
        "old_method() is deprecated, use new_method() instead. "
        "Will be removed in v4.0.0",
        DeprecationWarning,
        stacklevel=2
    )
    return self.new_method()
```

## Development Commands

### Package Management (UV)
```bash
uv add [package]              # Add a dependency
uv add --dev [package]        # Add a development dependency
uv sync                       # Install/sync dependencies
uv run [command]              # Run command in virtual environment
```

### Testing
```bash
uv run pytest                # Run all tests
uv run pytest tests/test_client.py  # Run specific test file
uv run pytest -m "not slow"  # Run tests excluding slow ones
uv run pytest --cov=project_x_py --cov-report=html  # Generate coverage report
uv run pytest -k "async"     # Run only async tests
```

### Async Testing Patterns
```python
# Test async methods with pytest-asyncio
import pytest

@pytest.mark.asyncio
async def test_async_method():
    async with ProjectX.from_env() as client:
        await client.authenticate()
        result = await client.get_bars("MNQ", days=1)
        assert result is not None
```

### Code Quality
```bash
uv run ruff check .          # Lint code
uv run ruff check . --fix    # Auto-fix linting issues
uv run ruff format .         # Format code
uv run mypy src/             # Type checking
```

### Building and Distribution
```bash
uv build                     # Build wheel and source distribution
uv run python -m build       # Alternative build command
```

## Project Architecture

### Core Components (v3.0.2 - Multi-file Packages)

**ProjectX Client (`src/project_x_py/client/`)**
- Main async API client for TopStepX ProjectX Gateway
- Modular architecture with specialized modules:
  - `auth.py`: Authentication and JWT token management
  - `http.py`: Async HTTP client with retry logic
  - `cache.py`: Intelligent caching for instruments
  - `market_data.py`: Market data operations
  - `trading.py`: Trading operations
  - `rate_limiter.py`: Async rate limiting
  - `base.py`: Base class combining all mixins

**Specialized Managers (All Async)**
- `OrderManager` (`order_manager/`): Comprehensive async order operations
  - `core.py`: Main order operations
  - `bracket_orders.py`: OCO and bracket order logic
  - `position_orders.py`: Position-based order management
  - `tracking.py`: Order state tracking
  - `templates.py`: Order templates for common strategies
- `PositionManager` (`position_manager/`): Async position tracking and risk management
  - `core.py`: Position management core
  - `risk.py`: Risk calculations and limits
  - `analytics.py`: Performance analytics
  - `monitoring.py`: Real-time position monitoring
  - `tracking.py`: Position lifecycle tracking
- `RiskManager` (`risk_manager/`): Integrated risk management
  - `core.py`: Risk limits and validation
  - `monitoring.py`: Real-time risk monitoring
  - `analytics.py`: Risk metrics and reporting
- `ProjectXRealtimeDataManager` (`realtime_data_manager/`): Async WebSocket data
  - `core.py`: Main data manager
  - `callbacks.py`: Event callback handling
  - `data_processing.py`: OHLCV bar construction
  - `memory_management.py`: Efficient data storage
- `OrderBook` (`orderbook/`): Async Level 2 market depth
  - `base.py`: Core orderbook functionality
  - `analytics.py`: Market microstructure analysis
  - `detection.py`: Iceberg and spoofing detection
  - `profile.py`: Volume profile analysis

**Technical Indicators (`src/project_x_py/indicators/`)**
- TA-Lib compatible indicator library built on Polars
- 58+ indicators including pattern recognition:
  - **Momentum**: RSI, MACD, Stochastic, etc.
  - **Overlap**: SMA, EMA, Bollinger Bands, etc.
  - **Volatility**: ATR, Keltner Channels, etc.
  - **Volume**: OBV, VWAP, Money Flow, etc.
  - **Pattern Recognition** (NEW):
    - Fair Value Gap (FVG): Price imbalance detection
    - Order Block: Institutional order zone identification
    - Waddah Attar Explosion: Volatility-based trend strength
- All indicators work with Polars DataFrames for performance

**Configuration System**
- Environment variable based configuration
- JSON config file support (`~/.config/projectx/config.json`)
- ProjectXConfig dataclass for type safety
- ConfigManager for centralized configuration handling

**Event System**
- Unified EventBus for cross-component communication
- Type-safe event definitions
- Async event handlers with priority support
- Built-in event types for all trading events

### Available TradingSuite Features

The `Features` enum defines optional components that can be enabled:

- `ORDERBOOK = "orderbook"` - Level 2 market depth and analysis
- `RISK_MANAGER = "risk_manager"` - Position sizing and risk management
- `TRADE_JOURNAL = "trade_journal"` - Trade logging (future)
- `PERFORMANCE_ANALYTICS = "performance_analytics"` - Advanced metrics (future)
- `AUTO_RECONNECT = "auto_reconnect"` - Automatic reconnection (future)

**Note**: OrderManager and PositionManager are always included by default.

### Architecture Patterns

**Async Factory Functions**: Use async `create_*` functions for component initialization:
```python
# TradingSuite - Recommended approach (v3.0.0+)
async def setup_trading():
    # Simple one-line setup with TradingSuite
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["1min", "5min"],
        features=["orderbook"]
    )
    
    # Everything is ready - client authenticated, realtime connected
    return suite
```

**Dependency Injection**: Managers receive their dependencies (ProjectX client, realtime client) rather than creating them.

**Real-time Integration**: Single `ProjectXRealtimeClient` instance shared across managers for WebSocket connection efficiency.

**Context Managers**: Always use async context managers for proper resource cleanup:
```python
async with ProjectX.from_env() as client:
    # Client automatically handles auth, cleanup
    pass
```

### Data Flow

1. **Authentication**: ProjectX client authenticates and provides JWT tokens
2. **Real-time Setup**: Create ProjectXRealtimeClient with JWT for WebSocket connections
3. **Manager Initialization**: Pass clients to specialized managers via dependency injection
4. **Data Processing**: Polars DataFrames used throughout for performance
5. **Event Handling**: Real-time updates flow through WebSocket to respective managers

## Important Technical Details

### Indicator Functions
- All indicators follow TA-Lib naming conventions (uppercase function names allowed in `indicators/__init__.py`)
- Use Polars pipe() method for chaining: `data.pipe(SMA, period=20).pipe(RSI, period=14)`
- Indicators support both class instantiation and direct function calls

### Price Precision
- All price handling uses Decimal for precision
- Automatic tick size alignment in OrderManager
- Price formatting utilities in utils.py

### Error Handling
- Custom exception hierarchy in exceptions.py
- All API errors wrapped in ProjectX-specific exceptions
- Comprehensive error context and retry logic

### Testing Strategy
- Pytest with async support and mocking
- Test markers: unit, integration, slow, realtime
- High test coverage required (configured in pyproject.toml)
- Mock external API calls in unit tests

## Environment Setup

Required environment variables:
- `PROJECT_X_API_KEY`: TopStepX API key
- `PROJECT_X_USERNAME`: TopStepX username

Optional configuration:
- `PROJECTX_API_URL`: Custom API endpoint
- `PROJECTX_TIMEOUT_SECONDS`: Request timeout
- `PROJECTX_RETRY_ATTEMPTS`: Retry attempts

## Performance Optimizations

### Connection Pooling & Caching (client.py)
- HTTP connection pooling with retry strategies for 50-70% fewer connection overhead
- Instrument caching reduces repeated API calls by 80%
- Preemptive JWT token refresh at 80% lifetime prevents authentication delays
- Session-based requests with automatic retry on failures

### Memory Management
- **OrderBook**: Sliding windows with configurable limits (max 10K trades, 1K depth entries)
- **RealtimeDataManager**: Automatic cleanup maintains 1K bars per timeframe
- **Indicators**: LRU cache for repeated calculations (100 entry limit)
- Periodic garbage collection after large data operations

### Optimized DataFrame Operations
- **Chained operations** reduce intermediate DataFrame creation by 30-40%
- **Lazy evaluation** with Polars for better memory efficiency  
- **Efficient datetime parsing** with cached timezone objects
- **Vectorized operations** in orderbook analysis

### Performance Monitoring
Use async built-in methods to monitor performance:
```python
# Client performance stats (async)
async with ProjectX.from_env() as client:
    await client.authenticate()
    
    # Check performance metrics
    stats = await client.get_performance_stats()
    print(f"API calls: {stats['api_calls']}")
    print(f"Cache hits: {stats['cache_hits']}")
    
    # Health check
    health = await client.get_health_status()
    
    # Memory usage monitoring
    orderbook_stats = await orderbook.get_memory_stats()
    data_manager_stats = await data_manager.get_memory_stats()
```

### Expected Performance Improvements
- **50-70% reduction in API calls** through intelligent caching
- **30-40% faster indicator calculations** via chained operations
- **60% less memory usage** through sliding windows and cleanup
- **Sub-second response times** for cached operations
- **95% reduction in polling** with real-time WebSocket feeds

### Memory Limits (Configurable)
- `max_trades = 10000` (OrderBook trade history)
- `max_depth_entries = 1000` (OrderBook depth per side)
- `max_bars_per_timeframe = 1000` (Real-time data per timeframe)
- `tick_buffer_size = 1000` (Tick data buffer)
- `cache_max_size = 100` (Indicator cache entries)

## Recent Changes

### v3.1.13 - Latest Release
- **Fixed**: Event system data structure mismatches causing order fill detection failures
  - Bracket orders now properly detect fills without 60-second timeouts
  - Event handlers handle both `order_id` and nested `order` object structures
  - ManagedTrade correctly listens to ORDER_FILLED instead of ORDER_MODIFIED
- **Fixed**: Type annotations for SignalR hub connections
  - Created HubConnection type alias for proper IDE support
  - market_connection and user_connection now have proper types instead of Any
- **Improved**: Real-time connection stability with circuit breaker pattern
- **Improved**: Data storage robustness with thread-safety and performance optimizations
- **Enhanced**: Test coverage increased from 30% to 93% for client module
- **Fixed**: Multiple asyncio deprecation warnings

### v3.1.12
- **Enhanced**: Significantly improved `01_events_with_on.py` real-time data example
  - Added CSV export functionality with interactive prompts
  - Plotly-based candlestick chart generation
  - Non-blocking user input handling
  - Better bar display formatting and visual indicators
  - Automatic browser opening for generated charts

### v3.1.11
- **Fixed**: ManagedTrade `_get_market_price()` implementation
  - ManagedTrade can now fetch current market prices from data manager
  - Automatic fallback through multiple timeframes (1sec, 15sec, 1min, 5min)
  - Enables risk-managed trades without explicit entry prices
  - Proper integration with TradingSuite's data manager

### v3.1.10
- Minor version bump for internal improvements

### v3.1.9
- **Fixed**: Tick price alignment in real-time data manager
  - All OHLC prices now properly aligned to instrument tick size
  - `get_current_price()` returns tick-aligned values
  - Prevents invalid prices (e.g., $23,927.62 for NQ now snaps to $23,927.50)
- **Documented**: ProjectX volume data limitation (platform-specific, not full exchange volume)

### v3.1.8 - Previous Release  
- **Fixed**: Real-time data processing for E-mini contracts (NQ/ES) that resolve to different symbols
- **Added**: Bar timer mechanism to create empty bars during low-volume periods
- **Improved**: Symbol matching to handle contract resolution (e.g., NQ→ENQ)
- **Enhanced**: Real-time data manager now properly processes all futures contracts

### v3.1.7
- Minor updates and improvements
- Documentation enhancements

### v3.1.6 - Critical Deadlock Fix
- **Fixed**: Deadlock when calling `suite.data` methods from event handler callbacks (Issue #39)
- **Improved**: Event emission now non-blocking to prevent handler deadlocks
- **Enhanced**: Event triggering moved outside lock scope for better concurrency
- **Added**: Missing asyncio import in data_processing module
- **Maintained**: Full API compatibility - no breaking changes

### v3.1.5 - Enhanced Bar Data Retrieval
- **Added**: Optional `start_time` and `end_time` parameters to `get_bars()` method
- **Improved**: Precise time range specification for historical data queries
- **Enhanced**: Full timezone support with automatic UTC conversion
- **Maintained**: Complete backward compatibility with existing `days` parameter

### v3.1.4 - WebSocket Connection Fix
- **Fixed**: Critical WebSocket error with missing `_use_batching` attribute
- **Improved**: Proper mixin initialization in ProjectXRealtimeClient
- **Enhanced**: More robust real-time connection handling

### v3.0.2 - Bug Fixes and Improvements
- **Order Lifecycle Tracking**: Fixed asyncio concurrency and field reference issues
- **Order Templates**: Fixed instrument lookup to use cached object
- **Cleanup Functionality**: Added comprehensive order/position cleanup
- **Documentation**: Updated all docs to reflect current version

### v3.0.1 - Production Ready
- **Performance Optimizations**: Enhanced connection pooling and caching
- **Event Bus System**: Unified event handling across all components
- **Risk Management**: Integrated risk manager with position limits and monitoring
- **Order Tracking**: Comprehensive order lifecycle tracking and management
- **Memory Management**: Optimized sliding windows and automatic cleanup
- **Enhanced Models**: Improved data models with better type safety

### v3.0.0 - Major Architecture Improvements
- **Trading Suite**: Unified trading suite with all managers integrated
- **Advanced Order Types**: OCO, bracket orders, and position-based orders
- **Real-time Integration**: Seamless WebSocket data flow across all components
- **Protocol-based Design**: Type-safe protocols for all major interfaces

### v2.0.4 - Package Refactoring
- Converted monolithic modules to multi-file packages
- All core modules organized as packages with focused submodules
- Improved code organization and maintainability

### Trading Suite Usage (v3.0.0+)
```python
# Complete trading suite with all managers
from project_x_py import TradingSuite

async def main():
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["1min", "5min"],
        features=["orderbook", "risk_manager"],  # Optional features
        initial_days=5
    )
    
    # All managers are integrated and ready
    # No need to call start() - already connected
    
    # Access individual managers
    order = await suite.orders.place_market_order(
        contract_id=suite.instrument_info.id,
        side=0,  # Buy
        size=1
    )
    
    position = await suite.positions.get_position("MNQ")
    bars = await suite.data.get_data("1min")
```

### Key Async Examples
```python
# Basic usage
async with ProjectX.from_env() as client:
    await client.authenticate()
    bars = await client.get_bars("MNQ", days=5)
    
# Real-time data with TradingSuite
async def stream_data():
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["1min", "5min"]
    )
    
    # Register event handlers
    from project_x_py import EventType
    
    async def handle_bar(event):
        print(f"New bar: {event.data}")
    
    await suite.on(EventType.NEW_BAR, handle_bar)
    
    # Data is already streaming
    # Access current data
    current_price = await suite.data.get_current_price()
    bars = await suite.data.get_data("1min")
```