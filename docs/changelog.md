# Changelog

All notable changes to the ProjectX Python SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
