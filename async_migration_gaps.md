# Async Migration Gaps and Action Items

## Critical Gaps to Address

### 1. Missing Methods in AsyncProjectX

#### High Priority (Core Functionality):
- [ ] **`get_account_info()` property**: Sync version has this as a property/method. Async version stores it but doesn't expose it as a property
  - **Action**: Add `@property` for `account_info` in AsyncProjectX
  
- [ ] **`get_session_token()` property**: Sync exposes JWT token retrieval
  - **Action**: Add `@property` for `session_token` in AsyncProjectX

#### Low Priority (Nice to Have):
- [ ] **`test_contract_selection()`**: Testing utility
  - **Action**: Consider if needed in async version

### 2. Method Signature Differences

#### Must Fix:
- [ ] **`get_instrument()`**: Async version missing `live` parameter
  - **Action**: Add `live: bool = False` parameter to async version
  
- [ ] **`list_accounts()`**: Return type mismatch
  - **Sync**: Returns `list[dict]`
  - **Async**: Returns `list[Account]`
  - **Action**: Verify if this is intentional improvement or needs alignment

### 3. Method Naming Inconsistencies

- [ ] **`get_data()` vs `get_bars()`**: Same functionality, different names
  - **Action**: Consider adding `get_data()` as alias for backwards compatibility

### 4. Authentication Pattern Differences

The async version requires explicit `authenticate()` call while sync does it automatically.
- **Action**: Document this clearly in migration guide

## Components Verification Status

### ✅ Fully Verified Components:
1. **Examples**: All 9 examples have working async versions
2. **Factory Functions**: All have async equivalents in `__init__.py`

### 🔄 Partially Verified Components:
1. **AsyncProjectX**: Missing some convenience methods/properties
2. **AsyncOrderManager**: Needs method-by-method verification
3. **AsyncPositionManager**: Needs method-by-method verification
4. **AsyncRealtimeDataManager**: Needs method-by-method verification
5. **AsyncOrderBook**: Refactored into module structure, needs verification

### ❓ Not Yet Verified:
1. Unit test coverage comparison
2. Performance benchmarks
3. Real-world usage patterns

## Immediate Action Items

1. **Add missing properties to AsyncProjectX**:
   ```python
   @property
   def account_info(self) -> Account | None:
       return self._account_info
   
   @property
   def session_token(self) -> str:
       return self._session_token
   ```

2. **Fix `get_instrument()` signature**:
   ```python
   async def get_instrument(self, symbol: str, live: bool = False) -> Instrument:
   ```

3. **Create detailed method comparison for remaining components**:
   - AsyncOrderManager vs OrderManager
   - AsyncPositionManager vs PositionManager
   - AsyncRealtimeDataManager vs ProjectXRealtimeDataManager
   - AsyncOrderBook vs OrderBook

## Migration Strategy Recommendations

1. **Phase 1**: Fix critical gaps (properties, method signatures)
2. **Phase 2**: Add deprecation warnings to sync versions
3. **Phase 3**: Create comprehensive migration guide with examples
4. **Phase 4**: Release v2.0.0 with async-only support

## Backwards Compatibility Options

Consider creating sync wrappers for critical methods:
```python
def get_data_sync(client: AsyncProjectX, *args, **kwargs):
    """Sync wrapper for backwards compatibility"""
    import asyncio
    return asyncio.run(client.get_bars(*args, **kwargs))
```

## Testing Requirements

Before removing sync versions:
1. Run all examples with both sync and async
2. Compare outputs for consistency
3. Benchmark performance differences
4. Test error handling scenarios
5. Verify real-time data handling