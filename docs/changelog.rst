Changelog
=========

For the complete changelog, see the ``CHANGELOG.md`` file in the repository root.

Recent Releases
---------------

v3.3.4 (Latest)
^^^^^^^^^^^^^^^^

- **🚨 CRITICAL FIXES**: All 27 critical issues resolved
- **Risk Manager**: Financial precision with Decimal type, async task management, thread safety
- **OrderBook**: Comprehensive spoofing detection with 6 pattern types
- **Memory Management**: Bounded price histories and automatic cleanup
- **Performance**: 80% faster spoofing detection, optimized algorithms
- **Type Safety**: Zero mypy errors in critical modules

v3.3.3
^^^^^^^

- **Fixed**: Position Manager race conditions with queue-based processing
- **Enhanced**: Memory management with bounded statistics
- **Improved**: Dynamic resource limits and circuit breaker protection

v3.3.2
^^^^^^^

- **Added**: Comprehensive DST handling and timezone management
- **Fixed**: ManagedTrade execution and error handling
- **Enhanced**: Configuration validation and logging

v3.3.1
^^^^^^^

- **Improved**: Statistics system reliability and performance
- **Fixed**: Health monitoring edge cases
- **Enhanced**: Memory tracking and cleanup

v3.3.0
^^^^^^^

- **NEW**: 100% async-first statistics system with health monitoring
- **NEW**: Multi-format export (JSON, Prometheus, CSV, Datadog)
- **NEW**: Component-specific tracking for all managers
- **NEW**: Health scoring (0-100) with degradation detection
- **Performance**: TTL caching, parallel collection, circular buffers

v3.2.0
^^^^^^^

- **Major**: Type system improvements with comprehensive TypedDict and Protocol definitions
- **Enhanced**: StatsTrackingMixin for error and memory tracking
- **Improved**: Type checking (reduced errors from 100+ to 13)
- **Added**: 47 new tests for complete type system coverage
- **Standardized**: Deprecation system across SDK

v3.1.11
^^^^^^^

- **Fixed**: ManagedTrade ``_get_market_price()`` implementation
- **Added**: Multi-timeframe price fallback for ManagedTrade
- **Updated**: TradingSuite passes data_manager to ManagedTrade

v3.1.10
^^^^^^^

- Minor updates and improvements

v3.1.9
^^^^^^

- **Fixed**: Tick price alignment in real-time data manager
- **Documented**: ProjectX volume data limitation

v3.1.8
^^^^^^

- **Fixed**: Real-time data processing for E-mini contracts
- **Added**: Bar timer mechanism for low-volume periods
- **Improved**: Symbol matching for contract resolution

See ``CHANGELOG.md`` for complete version history.
