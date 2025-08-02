# Async/Await Refactoring Plan for project-x-py

## Summary

This issue outlines a comprehensive plan to refactor the project-x-py SDK from synchronous to asynchronous operations, enabling better performance, resource utilization, and natural integration with real-time trading workflows.

## Motivation

The current synchronous architecture has several limitations:

1. **Blocking I/O**: HTTP requests block the thread, preventing concurrent operations
2. **Inefficient for Real-time**: SignalR/WebSocket connections naturally fit async patterns
3. **Resource Utilization**: Can't efficiently handle multiple market data streams or order operations concurrently
4. **Modern Python Standards**: Async is the standard for I/O-heavy Python applications, especially in financial/trading contexts

## Benefits of Async Migration

- **Concurrent Operations**: Execute multiple API calls simultaneously (e.g., fetch positions while placing orders)
- **Non-blocking Real-time**: Process WebSocket events without blocking other operations
- **Better Resource Usage**: Single thread can handle many concurrent connections
- **Improved Responsiveness**: UI/strategy code won't freeze during API calls
- **Natural Event Handling**: Async/await patterns match event-driven trading systems

## Technical Analysis

### Current Architecture

1. **HTTP Client**: Uses `requests` library with session pooling
2. **WebSocket**: Uses `signalrcore` for SignalR connections
3. **Blocking Pattern**: All API calls block until completion
4. **Managers**: OrderManager, PositionManager, etc. all use synchronous methods

### Proposed Async Architecture

1. **HTTP Client**: Migrate to `httpx` (supports both sync/async)
2. **WebSocket**: Use `python-signalrcore-async` or create async wrapper for SignalR
3. **Async Pattern**: All public APIs become `async def` methods
4. **Managers**: Convert to async with proper concurrency handling

## Implementation Plan

### Progress Summary

**Phase 1 (Foundation) - COMPLETED on 2025-07-30**
- Created `AsyncProjectX` client with full async/await support
- Implemented HTTP/2 enabled httpx client with connection pooling
- Added comprehensive error handling with exponential backoff retry logic
- Created basic async methods: authenticate, get_positions, get_instrument, get_health_status
- Full test suite for async client with 9 passing tests

**Phase 2 (Core Client Migration) - COMPLETED on 2025-07-30**
- Implemented async rate limiter with sliding window algorithm
- Added account management: list_accounts, search_open_positions
- Implemented market data retrieval: get_bars with timezone conversion
- Added instrument search: search_instruments with live filter
- Implemented trade history: search_trades with date range filtering
- Enhanced caching for market data (5-minute TTL)
- Comprehensive test suite expanded to 14 passing tests

**Phase 3 (Manager Migration) - COMPLETED on 2025-07-31**
- Converted all managers to async: OrderManager, PositionManager, RealtimeDataManager, OrderBook
- Implemented proper async locking and thread safety
- Created comprehensive test suites for all managers (62 tests total)
- Ensured all managers can share ProjectXRealtimeClient instance

**Phase 4 (SignalR/WebSocket Integration) - COMPLETED on 2025-07-31**
- Created ProjectXRealtimeClient with async wrapper around SignalR
- Implemented async event handling and callback system
- Added JWT token refresh and reconnection support
- Created async factory functions for all components
- Full integration with dependency injection patterns

### Phase 1: Foundation (Week 1-2) ✅ COMPLETED

- [x] Add async dependencies to `pyproject.toml`:
  - `httpx[http2]` for async HTTP with HTTP/2 support
  - `python-signalrcore-async` or evaluate alternatives
  - Update `pytest-asyncio` for testing
- [x] Create async base client class (`AsyncProjectX`)
- [x] Implement async session management and connection pooling
- [x] Design async error handling and retry logic

### Phase 2: Core Client Migration (Week 2-3) ✅ COMPLETED

- [x] Convert authentication methods to async
- [x] Migrate account management endpoints
- [x] Convert market data methods (get_bars, get_instrument)
- [x] Implement async caching mechanisms
- [x] Add async rate limiting

### Phase 3: Manager Migration (Week 3-4) ✅ COMPLETED

- [x] Convert OrderManager to async ✅ COMPLETED on 2025-07-30
- [x] Convert PositionManager to async ✅ COMPLETED on 2025-07-30
- [x] Convert RealtimeDataManager to async ✅ COMPLETED on 2025-07-31
- [x] Update OrderBook for async operations ✅ COMPLETED on 2025-07-31
- [x] Ensure managers can share async ProjectXRealtimeClient ✅ COMPLETED on 2025-07-31

**OrderManager Async Conversion Summary:**
- Created AsyncOrderManager with full async/await support
- Implemented all order operations: market, limit, stop, bracket orders
- Added async-safe locking for thread safety
- Converted order search, modification, and cancellation to async
- Full test suite with 12 passing tests covering all functionality
- Fixed deadlock issues in bracket orders by removing nested locks
- Properly handles dataclass conversions and model structures

**PositionManager Async Conversion Summary:**
- Created AsyncPositionManager with complete async/await support
- Implemented all position tracking and management operations
- Added async portfolio P&L calculation and risk metrics
- Converted position closure operations (direct, partial, bulk) to async
- Implemented async position monitoring with alerts
- Full test suite with 17 passing tests covering all functionality
- Proper validation for ProjectX position payload formats
- Async-safe operations with asyncio locks

**RealtimeDataManager Async Conversion Summary:**
- Created AsyncRealtimeDataManager with full async/await support
- Implemented multi-timeframe OHLCV data management
- Converted tick processing and data aggregation to async
- Added async memory cleanup and optimization
- Full test suite with 16 passing tests
- Proper timezone handling with Polars DataFrames
- Supports both sync and async callbacks for flexibility

**OrderBook Async Conversion Summary:**
- Created AsyncOrderBook with complete async functionality
- Implemented Level 2 market depth processing
- Converted iceberg detection and volume analysis to async
- Added async liquidity distribution analysis
- Full test suite with 17 passing tests
- Fixed timezone-aware datetime issues with Polars
- Proper memory management with sliding windows

### Phase 4: SignalR/WebSocket Integration (Week 4-5) ✅ COMPLETED

- [x] Research SignalR async options: ✅ COMPLETED on 2025-07-31
  - Option A: `python-signalrcore-async` (if mature enough) - Not available
  - Option B: Create async wrapper around current `signalrcore` ✅ CHOSEN
  - Option C: Use `aiohttp` with custom SignalR protocol implementation - Too complex
- [x] Implement async event handling ✅ COMPLETED on 2025-07-31
- [x] Convert callback system to async-friendly pattern ✅ COMPLETED on 2025-07-31
- [x] Test reconnection logic with async ✅ COMPLETED on 2025-07-31

**AsyncProjectXRealtimeClient Implementation Summary:**
- Created full async wrapper around synchronous SignalR client
- Implemented async connection management with asyncio locks
- Added support for both sync and async callbacks
- Created non-blocking event forwarding with asyncio.create_task()
- Full test suite with 20 passing tests
- Proper JWT token refresh and reconnection support
- Thread-safe operations using asyncio.Lock
- Runs synchronous SignalR operations in executor for compatibility

**Async Factory Functions Created (now canonical, async-ready by default):**
- `create_client()` - Create ProjectX client
- `create_realtime_client()` - Create real-time WebSocket client
- `create_order_manager()` - Create order manager
- `create_position_manager()` - Create position manager
- `create_data_manager()` - Create OHLCV data manager
- `create_orderbook()` - Create market depth orderbook
- `create_trading_suite()` - Create complete async trading toolkit

**Integration Features:**
- All async managers share single AsyncProjectXRealtimeClient instance
- Proper dependency injection throughout
- No duplicate WebSocket connections
- Efficient event routing to multiple managers
- Coordinated cleanup across all components

### Phase 5: Testing & Documentation (Week 5-6)

- [ ] Convert all tests to async using `pytest-asyncio`
- [ ] Add integration tests for concurrent operations
- [ ] Update all examples to use async/await
- [ ] Document migration guide for users
- [ ] Performance benchmarks (sync vs async)

## API Design Decisions

### Option 1: Pure Async (Recommended per CLAUDE.md)
```python
# All methods become async
client = AsyncProjectX(api_key, username)
await client.authenticate()
positions = await client.get_positions()
```

### Option 2: Dual API (Not recommended due to complexity)
```python
# Both sync and async clients
sync_client = ProjectX(api_key, username)
async_client = AsyncProjectX(api_key, username)
```

Given the CLAUDE.md directive for "No Backward Compatibility" and "Clean Code Priority", **Option 1 (Pure Async) is recommended**.

## Breaking Changes

This refactoring will introduce breaking changes:

1. All public methods become `async`
2. Clients must use `async with` for proper cleanup
3. Event handlers must be async functions
4. Example code and integrations need updates

## Migration Guide

```python
# Old (Sync)
client = ProjectX(api_key, username)
client.authenticate()
positions = client.get_positions()

# New (Async-ready, canonical names)
async with ProjectX(api_key, username) as client:
    await client.authenticate()
    positions = await client.get_positions()
```

## Technical Considerations

### SignalR Compatibility

ProjectX requires SignalR for real-time connections. Options:

1. **python-signalrcore-async**: Check maturity and compatibility
2. **Async Wrapper**: Create async wrapper around sync signalrcore
3. **Custom Implementation**: Use aiohttp with SignalR protocol (complex but most control)

### Connection Management

- Use async context managers for resource cleanup
- Implement proper connection pooling for HTTP/2
- Handle WebSocket reconnection in async context

### Performance Targets

- Concurrent API calls should show 3-5x throughput improvement
- WebSocket event processing latency < 1ms
- Memory usage should remain comparable to sync version

## Dependencies to Add

```toml
[project.dependencies]
httpx = ">=0.27.0"
# SignalR async solution (TBD based on research)

[project.optional-dependencies.dev]
pytest-asyncio = ">=0.23.0"
aioresponses = ">=0.7.6"  # For mocking async HTTP
```

## Example: Async Trading Bot

```python
import asyncio
from project_x_py import ProjectX, create_trading_suite

async def trading_bot():
    async with ProjectX(api_key, username) as client:
        await client.authenticate()
        
        # Create trading suite (now async-ready by default)
        suite = await create_trading_suite(
            instrument="MGC",
            project_x=client,
            jwt_token=client.session_token,
            account_id=client.account_info.id
        )
        
        # Concurrent operations
        positions_task = asyncio.create_task(
            suite["position_manager"].get_positions()
        )
        market_data_task = asyncio.create_task(
            suite["data_manager"].get_bars("1m", 100)
        )
        
        positions, market_data = await asyncio.gather(
            positions_task, market_data_task
        )
        
        # Real-time event handling
        async for tick in suite["data_manager"].stream_ticks():
            await process_tick(tick)

async def process_tick(tick):
    # Async tick processing
    pass

if __name__ == "__main__":
    asyncio.run(trading_bot())
```

## Timeline

- **Total Duration**: 5-6 weeks
- **Testing Phase**: Additional 1 week
- **Documentation**: Ongoing throughout

## Success Criteria

1. All tests pass with async implementation
2. Performance benchmarks show improvement
3. Real-time SignalR connections work reliably
4. Clean async API without sync remnants
5. Comprehensive documentation and examples

## Open Questions

1. Which SignalR async library to use?
2. Should we provide any sync compatibility layer?
3. How to handle existing users during transition?
4. Performance benchmarking methodology?

## References

- [ProjectX SignalR Documentation](https://gateway.docs.projectx.com/docs/realtime/)
- [httpx Documentation](https://www.python-httpx.org/)
- [Python Async Best Practices](https://docs.python.org/3/library/asyncio-task.html)
- [SignalR Protocol Specification](https://github.com/dotnet/aspnetcore/tree/main/src/SignalR/docs/specs)

---

**Note:** All public classes and factory functions are now async-ready by default. The Async* prefix is no longer used—simply use the canonical names shown in the latest examples above.

**Note**: This refactoring aligns with the CLAUDE.md directive for "No Backward Compatibility" and "Clean Code Priority" during active development.