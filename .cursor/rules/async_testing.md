# Async Testing Rules for ProjectX SDK

**CRITICAL**: This SDK is 100% async-first. All testing must follow async patterns correctly.

## Async Test Requirements

### 1. Async Test Decorators (MANDATORY)

**ALWAYS use for async test methods:**
```python
import pytest

@pytest.mark.asyncio
async def test_async_method():
    # Test implementation
    pass
```

**FORBIDDEN patterns:**
```python
# ❌ WRONG: Missing @pytest.mark.asyncio
async def test_async_method():
    pass

# ❌ WRONG: Using sync test for async code
def test_async_method():
    result = asyncio.run(async_method())
```

### 2. Async Context Manager Testing

**ALWAYS test async context managers properly:**
```python
@pytest.mark.asyncio
async def test_projectx_client_context_manager():
    async with ProjectX.from_env() as client:
        await client.authenticate()
        # Test within context
        assert client.is_authenticated
    # Test cleanup happened
```

### 3. Async Mock Patterns

**Use aioresponses for HTTP mocking:**
```python
from aioresponses import aioresponses
import pytest

@pytest.mark.asyncio
async def test_api_call():
    with aioresponses() as m:
        m.get("https://api.example.com/data", payload={"result": "success"})

        async with ProjectX.from_env() as client:
            result = await client.get_data()
            assert result["result"] == "success"
```

**Use AsyncMock for async methods:**
```python
from unittest.mock import AsyncMock
import pytest

@pytest.mark.asyncio
async def test_realtime_callback():
    callback = AsyncMock()
    manager = RealtimeDataManager(callback=callback)

    await manager.process_tick({"price": 100.0})

    callback.assert_called_once_with({"price": 100.0})
```

### 4. WebSocket Testing Patterns

**Test WebSocket connections with proper async handling:**
```python
@pytest.mark.asyncio
async def test_websocket_connection():
    async with create_realtime_client("token", "account") as client:
        await client.connect()
        assert client.is_connected

        await client.subscribe("MNQ")
        # Test subscription
```

### 5. Async Error Handling Tests

**Test async exceptions properly:**
```python
@pytest.mark.asyncio
async def test_api_error_handling():
    with aioresponses() as m:
        m.get("https://api.example.com/data", status=500)

        async with ProjectX.from_env() as client:
            with pytest.raises(ProjectXAPIError):
                await client.get_data()
```

## Async Test Organization

### 6. Test File Structure

**Organize async tests by component:**
```
tests/
├── unit/
│   ├── test_async_client.py          # Client async tests
│   ├── test_async_order_manager.py   # OrderManager async tests
│   └── test_async_realtime.py        # Realtime async tests
├── integration/
│   └── test_async_integration.py     # Cross-component async tests
└── e2e/
    └── test_async_e2e.py             # End-to-end async tests
```

### 7. Async Test Fixtures

**Create reusable async fixtures:**
```python
@pytest_asyncio.fixture
async def authenticated_client():
    async with ProjectX.from_env() as client:
        await client.authenticate()
        yield client

@pytest_asyncio.fixture
async def realtime_client(authenticated_client):
    client = await create_realtime_client(
        authenticated_client.jwt_token,
        str(authenticated_client.account_id)
    )
    yield client
    await client.close()
```

## Performance Testing for Async Code

### 8. Async Performance Tests

**Test async performance characteristics:**
```python
@pytest.mark.asyncio
async def test_concurrent_requests():
    async with ProjectX.from_env() as client:
        await client.authenticate()

        # Test concurrent execution
        tasks = [
            client.get_bars("MNQ", days=1),
            client.get_bars("ES", days=1),
            client.get_bars("RTY", days=1)
        ]

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time

        assert len(results) == 3
        assert duration < 5.0  # Should be faster than sequential
```

### 9. Memory Leak Testing

**Test for async memory leaks:**
```python
@pytest.mark.asyncio
async def test_no_memory_leaks():
    import gc
    import tracemalloc

    tracemalloc.start()

    for _ in range(100):
        async with ProjectX.from_env() as client:
            await client.authenticate()
            await client.get_bars("MNQ", days=1)

    gc.collect()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Memory should not grow unbounded
    assert current < peak * 1.1
```

## Critical Async Testing Violations

**These are NEVER acceptable:**

❌ **Using sync tests for async code**
❌ **Missing @pytest.mark.asyncio decorator**
❌ **Using asyncio.run() in test methods**
❌ **Blocking async code with .result() or similar**
❌ **Not properly cleaning up async resources**
❌ **Testing async code synchronously**
❌ **Ignoring async context manager lifecycle**

## Async Test Execution

**Use proper test execution:**
```bash
# ✅ CORRECT: Use test.sh for proper environment
./test.sh tests/test_async_client.py

# ✅ CORRECT: Run specific async tests
uv run pytest -k "async" tests/

# ✅ CORRECT: Run with asyncio mode
uv run pytest --asyncio-mode=auto tests/
```

## Required Dependencies

**Ensure these are in test dependencies:**
```toml
[project.optional-dependencies]
dev = [
    "pytest-asyncio>=0.21.0",
    "aioresponses>=0.7.4",
    "pytest>=7.0.0",
]
```

Remember: **Async code requires async tests. No exceptions.**
