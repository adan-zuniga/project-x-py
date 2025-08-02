# Test Suite Refactoring Issue

## Overview
The current test suite has significant issues that prevent tests from running properly. Out of 27 test files with 226 tests collected, there are 8 import errors preventing test execution. Additionally, there are major gaps in test coverage and outdated test implementations.

## Critical Issues Found

### 1. Import Errors (8 files affected)
- Tests are importing non-existent classes/functions:
  - `RealtimeClient` should be `ProjectXRealtimeClient`
  - `ProjectXConfigError` doesn't exist in exceptions.py
  - Multiple tests using outdated async class names

### 2. Outdated Test References
- 9 test files still reference old async classes:
  - `AsyncProjectX` (now `ProjectX`)
  - `AsyncOrderManager` (now `OrderManager`)
  - `AsyncPositionManager` (now `PositionManager`)
  - `create_async_trading_suite` (now `create_trading_suite`)

### 3. Missing Test Coverage
Critical components with no test coverage:
- **Indicators module** (9 modules, 0 tests)
  - momentum indicators
  - overlap indicators
  - volatility indicators
  - volume indicators
  - base classes
- **Client module components** (refactored into submodules)
- **Realtime module components** (refactored into submodules)
- **Utils module components** (refactored into submodules)

### 4. Duplicate and Redundant Tests
- Multiple versions of same tests (async and sync)
- Test files for both old and new implementations
- Comprehensive test files that duplicate basic test files

## Specific Files Requiring Fixes

### Files with Import Errors:
1. `test_async_order_manager_comprehensive.py` - RealtimeClient import
2. `test_async_realtime.py` - RealtimeClient import
3. `test_config.py` - ProjectXConfigError import
4. `test_async_integration_comprehensive.py` - RealtimeClient import
5. `test_async_orderbook.py` - RealtimeClient import
6. `test_async_realtime_data_manager.py` - RealtimeClient import
7. `test_integration.py` - RealtimeClient import
8. `test_order_manager_init.py` - RealtimeClient import
9. `test_position_manager_init.py` - RealtimeClient import

### Files with Outdated References:
All async test files need updating to use new non-async class names.

## Proposed Action Plan

### Phase 1: Fix Import Errors
1. Update all `RealtimeClient` imports to `ProjectXRealtimeClient`
2. Remove or fix `ProjectXConfigError` references
3. Update all async class imports to new names

### Phase 2: Remove Redundant Tests
1. Consolidate duplicate async/sync test files
2. Remove tests for deprecated functionality
3. Merge comprehensive test files with basic ones

### Phase 3: Add Missing Test Coverage
1. Create test suite for indicators module:
   - Test each indicator category
   - Test class-based and function interfaces
   - Test Polars DataFrame operations
2. Add tests for refactored modules:
   - Client submodules
   - Realtime submodules
   - Utils submodules

### Phase 4: Modernize Test Structure
1. Use pytest fixtures consistently
2. Add proper mocking for external API calls
3. Implement test markers properly (unit, integration, slow)
4. Add async test support where needed

### Phase 5: Test Organization
1. Restructure tests to mirror source code structure:
   ```
   tests/
   ├── unit/
   │   ├── client/
   │   ├── indicators/
   │   ├── order_manager/
   │   ├── position_manager/
   │   └── utils/
   ├── integration/
   └── conftest.py
   ```

## Success Criteria
- [ ] All tests can be collected without import errors
- [ ] Test coverage > 80% for all modules
- [ ] No duplicate or redundant tests
- [ ] Clear separation between unit and integration tests
- [ ] All tests pass in CI/CD pipeline
- [ ] Tests follow modern pytest patterns

## Priority
**High** - The test suite is currently broken and preventing proper validation of code changes.

## Labels
- bug
- testing
- refactoring
- technical-debt