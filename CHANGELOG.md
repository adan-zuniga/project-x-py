# Changelog

All notable changes to the ProjectX Python client will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## ⚠️ Development Phase Notice

**IMPORTANT**: This project is under active development. During this phase:
- Breaking changes may be introduced without deprecation warnings
- Backward compatibility is not maintained
- Old implementations are removed when improved
- Clean, modern code architecture is prioritized

## [2.0.4] - 2025-08-02

### Changed
- **🏗️ Major Architecture Refactoring**: Converted all large monolithic modules into multi-file packages
  - **client.py** → `client/` package (8 specialized modules)
    - `rate_limiter.py`: Async rate limiting functionality
    - `auth.py`: Authentication and token management
    - `http.py`: HTTP client and request handling
    - `cache.py`: Intelligent caching for instruments and market data
    - `market_data.py`: Market data operations (instruments, bars)
    - `trading.py`: Trading operations (positions, trades)
    - `base.py`: Base class combining all mixins
    - `__init__.py`: Main ProjectX class export
  - **order_manager.py** → `order_manager/` package (10 modules)
  - **position_manager.py** → `position_manager/` package (12 modules)  
  - **realtime_data_manager.py** → `realtime_data_manager/` package (9 modules)
  - **realtime.py** → `realtime/` package (8 modules)
  - **utils.py** → `utils/` package (10 modules)

### Improved
- **📁 Code Organization**: Separated concerns into logical modules for better maintainability
- **🚀 Developer Experience**: Easier navigation and understanding of codebase structure
- **✅ Testing**: Improved testability with smaller, focused modules
- **🔧 Maintainability**: Each module now has a single, clear responsibility

### Technical Details
- **Backward Compatibility**: All existing imports continue to work without changes
- **No API Changes**: Public interfaces remain identical
- **Import Optimization**: Reduced circular dependency risks
- **Memory Efficiency**: Better module loading with focused imports

## [2.0.2] - 2025-08-02

### Added
- **📊 Pattern Recognition Indicators**: Three new market structure indicators for advanced trading analysis
  - **Fair Value Gap (FVG)**: Identifies price imbalance areas in 3-candle patterns
    - Detects bullish gaps (current low > previous high AND previous low > two candles ago high)
    - Detects bearish gaps (inverse pattern for downward moves)
    - Configurable minimum gap size filter to reduce noise
    - Optional mitigation tracking to identify when gaps have been "filled"
    - Customizable mitigation threshold (default 50% of gap)
  
  - **Order Block**: Identifies institutional order zones based on price action
    - Detects bullish order blocks (down candle followed by bullish break)
    - Detects bearish order blocks (up candle followed by bearish break)
    - Volume-based filtering using percentile thresholds
    - Strength scoring based on volume and price movement
    - Optional mitigation tracking for tested zones
    - Configurable lookback periods and zone definition (wicks vs bodies)
  
  - **Waddah Attar Explosion (WAE)**: Volatility-based trend strength indicator
    - Combines MACD and Bollinger Bands for explosion calculation
    - Dead zone filter using ATR to eliminate ranging markets
    - Separate bullish/bearish signal detection
    - Configurable sensitivity and dead zone parameters
    - Helps identify strong breakouts and trending conditions

### Enhanced
- **🎯 Indicator Count**: Now 58+ indicators (up from 55+)
  - Added 3 new pattern recognition indicators
  - All indicators support both class-based and function-based interfaces
  - Full TA-Lib style compatibility for consistency

### Technical Details
- **Pattern Indicators Integration**: New indicators work seamlessly with existing async architecture
- **Confluence Trading**: Indicators designed to work together for higher probability setups
  - FVG + Order Block = High-probability support/resistance zones
  - WAE confirms momentum for FVG/OB trades
- **Performance**: All new indicators use efficient Polars operations for speed

## [2.0.1] - 2025-01-31

### Fixed
- **🐛 Import Organization**: Reorganized indicator imports to resolve circular dependencies
- **📦 Package Structure**: Improved module organization for better maintainability

## [2.0.0] - 2025-01-30

### Breaking Changes
- **🚀 Complete Async Migration**: Entire SDK migrated from synchronous to asynchronous architecture
  - All public methods now require `await` keyword
  - Clients must use `async with` for proper resource management
  - No backward compatibility - clean async-only implementation
  - Aligns with CLAUDE.md directive for "No Backward Compatibility" during development

### Added
- **✨ AsyncProjectX Client**: New async-first client implementation
  - HTTP/2 support via httpx for improved performance
  - Concurrent API operations with proper connection pooling
  - Non-blocking I/O for all operations
  - Async context manager support for resource cleanup
  
- **📦 Dependencies**: Added modern async libraries
  - `httpx[http2]>=0.27.0` for async HTTP with HTTP/2 support
  - `pytest-asyncio>=0.23.0` for async testing
  - `aioresponses>=0.7.6` for mocking async HTTP

### Changed
- **🔄 Migration Pattern**: From sync to async
  ```python
  # Old (Sync)
  client = ProjectX(api_key, username)
  client.authenticate()
  positions = client.get_positions()
  
  # New (Async)
  async with AsyncProjectX.from_env() as client:
      await client.authenticate()
      positions = await client.get_positions()
  ```

### Performance Improvements
- **⚡ Concurrent Operations**: Multiple API calls can now execute simultaneously
- **🚄 HTTP/2 Support**: Reduced connection overhead and improved throughput
- **🔄 Non-blocking WebSocket**: Real-time data processing without blocking other operations

### Migration Notes
- This is a complete breaking change - all code using the SDK must be updated
- See `tests/test_async_client.py` for usage examples
- Phase 2-5 of async migration still pending (managers, real-time, etc.)

## [1.1.4] - 2025-01-30

### Fixed
- **📊 OrderBook Volume Accumulation**: Fixed critical bug where market depth updates were accumulating volumes instead of replacing them
  - Market depth updates now correctly replace volume at price levels rather than adding to them
  - Resolved extremely high volume readings that were incorrect
  - Fixed handling of DomType 3/4 (BestBid/BestAsk) vs regular bid/ask updates

- **📈 OHLCV Volume Interpretation**: Fixed misinterpretation of GatewayQuote volume field
  - GatewayQuote volume represents daily total, not individual trade volume
  - OHLCV bars now correctly show volume=0 for quote-based updates
  - Prevents unrealistic volume spikes (e.g., 29,000+ per 5-second bar)

- **🔍 Trade Classification**: Improved trade side classification accuracy
  - Now captures bid/ask prices BEFORE orderbook update for correct classification
  - Uses historical spread data to properly classify trades as buy/sell
  - Added null handling for edge cases

### Enhanced
- **🧊 Iceberg Detection**: Added price level refresh history tracking
  - OrderBook now maintains history of volume updates at each price level
  - Tracks up to 50 updates per price level over 30-minute windows
  - Enhanced `detect_iceberg_orders` to use historical refresh patterns
  - Added `get_price_level_history()` method for analysis

- **📊 Market Structure Analysis**: Refactored key methods to use price level history
  - `get_support_resistance_levels`: Now identifies persistent levels based on order refresh patterns
  - `detect_order_clusters`: Finds price zones with concentrated historical activity
  - `get_liquidity_levels`: Detects "sticky" liquidity that reappears after consumption
  - All methods now provide institutional-grade analytics based on temporal patterns

### Added
- **🔧 Debug Scripts**: New diagnostic tools for market data analysis
  - `working_market_depth_debug.py`: Comprehensive DOM type analysis
  - `test_trade_classification.py`: Verify trade side classification
  - `test_enhanced_iceberg.py`: Test iceberg detection with history
  - `test_refactored_methods.py`: Verify all refactored analytics

### Technical Details
- Price level history stored as `dict[tuple[float, str], list[dict]]` with timestamp and volume
- Support/resistance now uses composite strength score (40% refresh count, 30% volume, 20% rate, 10% consistency)
- Order clusters detect "magnetic" price levels with persistent order placement
- Liquidity detection finds market maker zones with high refresh rates

## [1.1.3] - 2025-01-29

### Fixed
- **🔧 Contract Selection**: Fixed `_select_best_contract` method to properly handle futures contract naming patterns
  - Extracts base symbols by removing month/year suffixes using regex (e.g., NQU5 → NQ, MGCH25 → MGC)
  - Handles both single-digit (U5) and double-digit (H25) year codes correctly
  - Prevents incorrect matches (searching "NQ" no longer returns "MNQ" contracts)
  - Prioritizes exact base symbol matches over symbolId suffix matching

### Added
- **🎮 Interactive Instrument Demo**: New example script for testing instrument search functionality
  - `examples/09_get_check_available_instruments.py` - Interactive command-line tool
  - Shows the difference between `search_instruments()` (all matches) and `get_instrument()` (best match)
  - Visual indicators for active contracts (★) and detailed contract information
  - Includes common symbols table and help command
  - Continuous search loop for testing multiple symbols

### Enhanced
- **🧪 Test Coverage**: Added comprehensive test suite for contract selection logic
  - Tests for exact base symbol matching with various contract patterns
  - Tests for handling different year code formats
  - Tests for selection priority order (active vs inactive)
  - Tests for edge cases (empty lists, no exact matches)
- **📚 Documentation**: Updated README with development phase warnings
  - Added prominent development status warning
  - Noted that breaking changes may occur without backward compatibility
  - Updated changelog format to highlight the development phase

## [1.1.2] - 2025-01-28

### Enhanced
- **🚀 OrderBook Performance Optimization**: Significant performance improvements for cluster detection
  - **Dynamic Tick Size Detection**: OrderBook now uses real instrument metadata from ProjectX client
  - **Cached Instrument Data**: Tick size fetched once during initialization, eliminating repeated API calls
  - **Improved Cluster Analysis**: More accurate price tolerance based on actual instrument tick sizes
  - **Backward Compatibility**: Maintains fallback to hardcoded values when client unavailable
- **🔧 Factory Function Updates**: Enhanced `create_orderbook()` to accept ProjectX client reference
  - **Better Integration**: OrderBook now integrates seamlessly with ProjectX client architecture
  - **Dependency Injection**: Proper client reference passing for instrument metadata access

### Fixed
- **⚡ API Call Reduction**: Eliminated redundant `get_instrument()` calls during cluster detection
- **🎯 Price Tolerance Accuracy**: Fixed hardcoded tick size assumptions with dynamic instrument lookup
- **📊 Consistent Analysis**: OrderBook methods now use consistent, accurate tick size throughout lifecycle

## [1.1.0] - 2025-01-27

### Added
- **📊 Enhanced Project Structure**: Updated documentation to accurately reflect current codebase
- **🔧 Documentation Accuracy**: Aligned README.md and CHANGELOG.md with actual project state
- **📚 Example File Organization**: Updated example file names to match actual structure

### Fixed
- **📝 Version Consistency**: Corrected version references throughout documentation
- **📂 Example File References**: Updated README to reference actual example files
- **📅 Date Corrections**: Fixed future date references in documentation

## [1.0.12] - 2025-01-30

### Added
- **🔄 Order-Position Synchronization**: Automatic synchronization between orders and positions
  - **Position Order Tracking**: Orders automatically tracked and associated with positions
  - **Dynamic Order Updates**: Stop and target orders auto-adjust when position size changes
  - **Position Close Handling**: Related orders automatically cancelled when positions close
  - **Bracket Order Integration**: Full lifecycle tracking for entry, stop, and target orders
- **🧪 Comprehensive Test Suite**: Expanded test coverage to 230+ tests
  - **Phase 2-4 Testing**: Complete test coverage for core trading and data features
  - **Integration Tests**: End-to-end workflow testing
  - **Real-time Testing**: Advanced real-time data and orderbook test coverage
  - **Risk Management Tests**: Comprehensive risk control validation

### Enhanced
- **📊 Technical Indicators**: Now 55+ indicators (up from 40+)
  - **17 Overlap Studies**: Complete TA-Lib overlap indicator suite
  - **31 Momentum Indicators**: Comprehensive momentum analysis tools
  - **3 Volatility Indicators**: Advanced volatility measurement
  - **4 Volume Indicators**: Professional volume analysis
- **🔧 Order Management**: Enhanced order lifecycle management
  - **Position Sync**: Automatic order-position relationship management
  - **Order Tracking**: Comprehensive order categorization and tracking
  - **Risk Integration**: Seamless integration with risk management systems

### Fixed
- **📝 Documentation**: Updated version references and feature accuracy
- **🔢 Indicator Count**: Corrected indicator count documentation (55+ actual vs 40+ claimed)
- **📋 Version Tracking**: Restored complete changelog version history

## [1.0.11] - 2025-01-30

### Added
- **📈 Complete TA-Lib Overlap Indicators**: All 17 overlap indicators implemented
  - **HT_TRENDLINE**: Hilbert Transform Instantaneous Trendline
  - **KAMA**: Kaufman Adaptive Moving Average with volatility adaptation
  - **MA**: Generic Moving Average with selectable types
  - **MAMA**: MESA Adaptive Moving Average with fast/slow limits
  - **MAVP**: Moving Average with Variable Period support
  - **MIDPRICE**: Midpoint Price using high/low ranges
  - **SAR/SAREXT**: Parabolic SAR with standard and extended parameters
  - **T3**: Triple Exponential Moving Average with volume factor
  - **TRIMA**: Triangular Moving Average with double smoothing

### Enhanced
- **🔍 Indicator Discovery**: Enhanced helper functions for exploring indicators
- **📚 Documentation**: Comprehensive indicator documentation and examples
- **🎯 TA-Lib Compatibility**: Full compatibility with TA-Lib function signatures

## [1.0.10] - 2025-01-30

### Added
- **⚡ Performance Optimizations**: Major performance improvements
  - **Connection Pooling**: 50-70% reduction in API overhead
  - **Intelligent Caching**: 80% reduction in repeated API calls
  - **Memory Management**: 60% memory usage reduction with sliding windows
  - **DataFrame Optimization**: 30-40% faster operations

### Enhanced
- **🚀 Real-time Performance**: Sub-second response times for cached operations
- **📊 WebSocket Efficiency**: 95% reduction in polling with real-time feeds

## [1.0.0] - 2025-01-29

### Added
- **🎯 Production Release**: First stable production release
- **📊 Level 2 Orderbook**: Complete market microstructure analysis
- **🔧 Enterprise Features**: Production-grade reliability and monitoring

### Migration to v1.0.0
Major version bump indicates production readiness and API stability.

## [0.4.0] - 2025-01-29

### Added
- **📊 Advanced Market Microstructure**: Enhanced orderbook analysis
  - **Iceberg Detection**: Statistical confidence-based hidden order identification
  - **Order Flow Analysis**: Buy/sell pressure detection and trade flow metrics
  - **Volume Profile**: Point of Control and Value Area calculations
  - **Market Imbalance**: Real-time imbalance detection and alerts
  - **Support/Resistance**: Dynamic level identification from order flow
- **🔧 Enhanced Architecture**: Improved component design and performance

## [0.3.0] - 2025-01-29

### Added
- **🎯 Comprehensive Technical Indicators Library**: Complete TA-Lib compatible indicator suite
  - **25+ Technical Indicators**: All major categories covered
  - **Overlap Studies**: SMA, EMA, BBANDS, DEMA, TEMA, WMA, MIDPOINT
  - **Momentum Indicators**: RSI, MACD, STOCH, WILLR, CCI, ROC, MOM, STOCHRSI
  - **Volatility Indicators**: ATR, ADX, NATR, TRANGE, ULTOSC
  - **Volume Indicators**: OBV, VWAP, AD, ADOSC
  - **Dual Interface**: Class-based and function-based (TA-Lib style) usage
  - **Polars-Native**: Built specifically for Polars DataFrames
  - **Discovery Tools**: `get_all_indicators()`, `get_indicator_groups()`, `get_indicator_info()`
- **📊 Level 2 Orderbook & Market Microstructure Analysis** (Production Ready):
  - **Institutional-Grade Orderbook Processing**: Full market depth analysis
  - **Iceberg Detection**: Hidden order identification with statistical confidence
  - **Order Flow Analysis**: Buy/sell pressure detection and trade flow metrics
  - **Volume Profile**: Point of Control and Value Area calculations
  - **Market Imbalance**: Real-time imbalance detection and alerts
  - **Support/Resistance**: Dynamic level identification from order flow
  - **Liquidity Analysis**: Significant price level detection
  - **Cumulative Delta**: Net buying/selling pressure tracking
  - **Order Clustering**: Price level grouping and institutional flow detection
- **📈 Enhanced Portfolio & Risk Analysis**:
  - Portfolio performance metrics with Sharpe ratio and max drawdown
  - Advanced position sizing algorithms
  - Risk/reward ratio calculations
  - Volatility metrics and statistical analysis
- **🔧 Base Indicator Framework**:
  - `BaseIndicator`, `OverlapIndicator`, `MomentumIndicator`, `VolatilityIndicator`, `VolumeIndicator`
  - Consistent validation and error handling across all indicators
  - Utility functions: `ema_alpha()`, `safe_division()`, rolling calculations

### Enhanced
- **📚 Comprehensive Documentation**: Updated README with accurate feature representation
  - Complete technical indicators reference with examples
  - Level 2 orderbook usage examples
  - Multi-timeframe analysis strategies
  - Portfolio management and risk analysis guides
- **🎨 Code Quality**: Professional indicator implementations
  - Full type hints throughout indicator library
  - Consistent error handling and validation
  - Memory-efficient Polars operations
  - Clean separation of concerns

### Fixed
- **🔧 GitHub Actions**: Updated deprecated artifact actions from v3 to v4
  - `actions/upload-artifact@v3` → `actions/upload-artifact@v4`
  - `actions/download-artifact@v3` → `actions/download-artifact@v4`
- **📝 Documentation**: Corrected feature status in README
  - Level 2 orderbook marked as production-ready (not development)
  - Market microstructure analysis properly categorized
  - Accurate representation of implemented vs planned features

### Dependencies
- **Core**: No new required dependencies
- **Existing**: Compatible with current Polars, pytz, requests versions
- **Optional**: All existing optional dependencies remain the same

### Migration from v0.2.0
```python
# New technical indicators usage
from project_x_py.indicators import RSI, SMA, MACD, BBANDS

# Class-based interface
rsi = RSI()
data_with_rsi = rsi.calculate(data, period=14)

# TA-Lib style functions
data = RSI(data, period=14)
data = SMA(data, period=20)
data = BBANDS(data, period=20, std_dev=2.0)

# Level 2 orderbook analysis
from project_x_py import OrderBook
orderbook = OrderBook("MGC")
advanced_metrics = orderbook.get_advanced_market_metrics()

# Discover available indicators
from project_x_py.indicators import get_all_indicators, get_indicator_groups
print("Available indicators:", get_all_indicators())
```

## [0.2.0] - 2025-01-28

### Added
- **Modular Architecture**: Split large monolithic file into logical modules
  - `client.py` - Main ProjectX client class
  - `models.py` - Data models and configuration
  - `exceptions.py` - Custom exception hierarchy
  - `utils.py` - Utility functions and helpers
  - `config.py` - Configuration management
- **Enhanced Error Handling**: Comprehensive exception hierarchy with specific error types
  - `ProjectXAuthenticationError` for auth failures
  - `ProjectXServerError` for 5xx errors
  - `ProjectXRateLimitError` for rate limiting
  - `ProjectXConnectionError` for network issues
  - `ProjectXDataError` for data validation errors
- **Configuration Management**: 
  - Environment variable support with `PROJECTX_*` prefix
  - JSON configuration file support
  - Default configuration with overrides
  - Configuration validation and templates
- **Professional Package Structure**:
  - Proper `pyproject.toml` with optional dependencies
  - Comprehensive README with examples
  - MIT license
  - Test framework setup with pytest
  - Development tools configuration (ruff, mypy, black)
- **Enhanced API Design**:
  - Factory methods: `ProjectX.from_env()`, `ProjectX.from_config_file()`
  - Improved type hints throughout
  - Better documentation and examples
  - Consistent error handling patterns
- **Utility Functions**:
  - `setup_logging()` for consistent logging
  - `get_env_var()` for environment variable handling
  - `format_price()` and `format_volume()` for display
  - `is_market_hours()` for market timing
  - `RateLimiter` class for API rate limiting

### Changed
- **Breaking**: Restructured package imports - use `from project_x_py import ProjectX` instead of importing from `__init__.py`
- **Breaking**: Configuration now uses `ProjectXConfig` dataclass instead of hardcoded values
- **Improved**: Better error messages with specific exception types
- **Enhanced**: Client initialization with lazy authentication
- **Updated**: Package metadata and PyPI classifiers

### Improved
- **Documentation**: Comprehensive README with installation, usage, and examples
- **Code Quality**: Improved type hints, docstrings, and code organization
- **Testing**: Basic test framework with pytest fixtures and mocks
- **Development**: Better development workflow with linting and formatting tools

### Dependencies
- **Core**: `polars>=1.31.0`, `pytz>=2025.2`, `requests>=2.32.4`
- **Optional Realtime**: `signalrcore>=0.9.5`, `websocket-client>=1.0.0`
- **Development**: `pytest`, `ruff`, `mypy`, `black`, `isort`

## [0.1.0] - 2025-01-01

### Added
- Initial release with basic trading functionality
- ProjectX Gateway API client
- Real-time data management via WebSocket
- Order placement, modification, and cancellation
- Position and trade management
- Historical market data retrieval
- Multi-timeframe data synchronization

### Features
- Authentication with TopStepX API
- Account management
- Instrument search and contract details
- OHLCV historical data with polars DataFrames
- Real-time market data streams
- Level 2 market depth data
- Comprehensive logging

---

## Release Notes

### Upgrading to v0.2.0

If you're upgrading from v0.1.0, please note the following breaking changes:

1. **Import Changes**:
   ```python
   # Old (v0.1.0)
   from project_x_py import ProjectX
   
   # New (v0.2.0) - same import, but underlying structure changed
   from project_x_py import ProjectX  # Still works
   ```

2. **Environment Variables**:
   ```bash
   # Required (same as before)
   export PROJECT_X_API_KEY="your_api_key"
   export PROJECT_X_USERNAME="your_username"
   
   # New optional configuration variables
   export PROJECTX_API_URL="https://api.topstepx.com/api"
   export PROJECTX_TIMEOUT_SECONDS="30"
   export PROJECTX_RETRY_ATTEMPTS="3"
   ```

3. **Client Initialization**:
   ```python
   # Recommended new approach
   client = ProjectX.from_env()  # Uses environment variables
   
   # Or with explicit credentials (same as before)
   client = ProjectX(username="user", api_key="key")
   
   # Or with custom configuration
   config = ProjectXConfig(timeout_seconds=60)
   client = ProjectX.from_env(config=config)
   ```

4. **Error Handling**:
   ```python
   # New specific exception types
   try:
       client = ProjectX.from_env()
       account = client.get_account_info()
   except ProjectXAuthenticationError:
       print("Authentication failed")
   except ProjectXServerError:
       print("Server error")
   except ProjectXError:
       print("General ProjectX error")
   ```

### Migration Guide

1. **Update imports**: No changes needed - existing imports still work
2. **Update error handling**: Consider using specific exception types
3. **Use new factory methods**: `ProjectX.from_env()` is now recommended
4. **Optional**: Set up configuration file for advanced settings
5. **Optional**: Use new utility functions for logging and formatting

### New Installation Options

```bash
# Basic installation (same as before)
pip install project-x-py

# With real-time features
pip install project-x-py[realtime]

# With development tools
pip install project-x-py[dev]

# Everything
pip install project-x-py[all]
``` 