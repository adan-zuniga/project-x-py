# Changelog

All notable changes to the ProjectX Python SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.4.0] - 2025-08-28

### 🚀 New Feature: ETH vs RTH Trading Sessions (Experimental)

**IMPORTANT**: This is an experimental feature that has not been thoroughly tested with live market data. Use with caution in production environments.

This release introduces comprehensive trading session filtering, allowing you to separate Electronic Trading Hours (ETH) from Regular Trading Hours (RTH) for more precise market analysis and strategy execution.

### Added
- **Trading Sessions Module** (`src/project_x_py/sessions/`) with SessionConfig, SessionFilterMixin, and session-aware components
- **TradingSuite Integration** with new `session_config` parameter
- **Session-Aware Indicators** for calculating technical indicators on session-specific data
- **Session Statistics** for separate ETH vs RTH performance metrics
- **Maintenance Break Exclusion** (5-6 PM ET daily)
- **Comprehensive Example** in `examples/sessions/16_eth_vs_rth_sessions_demo.py`
- **Documentation** in `docs/guide/sessions.md`

### Known Limitations
- Session boundaries may need adjustment based on contract specifications
- Overnight session handling requires further testing
- Performance impact with large datasets not fully optimized
- Some futures products may have non-standard session times

### Related
- PR #59: ETH vs RTH Trading Sessions Feature

## [3.3.6] - 2025-08-28

### Major Quality Assurance Release
- Complete code quality compliance with zero mypy errors, zero linting issues, zero IDE diagnostics
- Order Manager module complete overhaul with protocol compliance
- Fixed TradingSuite duplicate subscription issues
- Added 100+ new comprehensive tests for edge cases
- Complete test coverage with all 1,300+ tests passing

## [3.3.4] - 2025-01-23

### Added
- Complete MkDocs documentation with Material theme
- GitHub Pages deployment workflow
- Versioned documentation support with Mike

### Changed
- Migrated from ReadTheDocs/Sphinx to MkDocs
- Updated documentation URL to GitHub Pages

### Removed
- ReadTheDocs configuration and dependencies
- Sphinx documentation files

## [3.3.0] - 2025-01-21

### Breaking Changes
- Complete statistics system redesign with 100% async-first architecture
- All statistics methods now require `await` for consistency and performance

### Added
- New statistics module with BaseStatisticsTracker, ComponentCollector, StatisticsAggregator
- Multi-format export (JSON, Prometheus, CSV, Datadog) with data sanitization
- Enhanced health monitoring with 0-100 scoring and configurable thresholds
- TTL caching, parallel collection, and circular buffers for performance optimization
- 45+ new tests covering all aspects of the async statistics system

### Fixed
- Eliminated all statistics-related deadlocks with single RW lock per component

### Removed
- Legacy statistics mixins (EnhancedStatsTrackingMixin, StatsTrackingMixin)

For the complete changelog, see the [GitHub releases](https://github.com/TexasCoding/project-x-py/releases).
