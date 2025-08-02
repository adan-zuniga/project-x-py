# Async Migration Guide for project-x-py

This guide helps you migrate from the synchronous ProjectX SDK to the new async/await architecture.  
**Note:** All public classes and factory functions are now async-ready by default—no Async* prefix is required.

## Table of Contents

1. [Overview](#overview)
2. [Key Benefits](#key-benefits)
3. [Breaking Changes](#breaking-changes)
4. [Migration Steps](#migration-steps)
5. [Code Examples](#code-examples)
6. [Common Patterns](#common-patterns)
7. [Troubleshooting](#troubleshooting)
8. [Performance Tips](#performance-tips)

## Overview

The project-x-py SDK has been completely refactored to use Python's async/await patterns. This enables:

- **Concurrent Operations**: Execute multiple API calls simultaneously
- **Non-blocking I/O**: Process WebSocket events without blocking other operations
- **Better Resource Usage**: Single thread can handle many concurrent connections
- **Improved Responsiveness**: UI/strategy code won't freeze during API calls

## Key Benefits

### 1. Concurrent API Calls

**Before (Synchronous):**
```python
# Sequential - takes 3+ seconds
positions = client.get_positions()  # 1 second
orders = client.get_orders()        # 1 second  
instruments = client.search_instruments("MNQ")  # 1 second
```

**After (Async):**
```python
# Concurrent - takes ~1 second total
positions, orders, instruments = await asyncio.gather(
    client.get_positions(),
    client.get_orders(),
    client.search_instruments("MNQ")
)
```

### 2. Real-time Event Handling

**Before:**
```python
# Blocking callback
def on_position_update(data):
    process_data(data)  # Blocks other events
    
realtime_client.add_callback("position_update", on_position_update)
```

**After:**
```python
# Non-blocking async callback
async def on_position_update(data):
    await process_data(data)  # Doesn't block
    
await realtime_client.add_callback("position_update", on_position_update)
```

## Breaking Changes

1. **All API methods are now async** - Must use `await`
2. **Context managers are async** - Use `async with`
3. **Callbacks can be async** - Better event handling
4. **Imports updated** - All classes and factory functions are async-ready and use the canonical names (no Async* prefix).

## Migration Steps

### Step 1: Update Imports

```python
# Old imports
from project_x_py import ProjectX, create_trading_suite

# New imports (all classes/factories are async-ready by default)
from project_x_py import ProjectX, create_trading_suite
```

### Step 2: Update Client Creation

```python
# Old synchronous client
client = ProjectX.from_env()
client.authenticate()

# New async client
async with ProjectX.from_env() as client:
    await client.authenticate()
```

### Step 3: Update API Calls

```python
# Old synchronous calls
positions = client.search_open_positions()
instrument = client.get_instrument("MGC")
data = client.get_data("MGC", days=5)

# New async calls
positions = await client.search_open_positions()
instrument = await client.get_instrument("MGC")
data = await client.get_data("MGC", days=5)
```

### Step 4: Update Manager Usage

```python
# Old synchronous managers
order_manager = create_order_manager(client)
position_manager = create_position_manager(client)

# New async managers (all managers are now async-ready by default)
order_manager = create_order_manager(client)
await order_manager.initialize()

position_manager = create_position_manager(client)
await position_manager.initialize()
```

## Code Examples

### Basic Connection

**Synchronous:**
```python
from project_x_py import ProjectX

def main():
    client = ProjectX.from_env()
    account = client.get_account_info()
    print(f"Connected as: {account.name}")
```

**Async (now using canonical names):**
```python
import asyncio
from project_x_py import ProjectX

async def main():
    async with ProjectX.from_env() as client:
        await client.authenticate()
        print(f"Connected as: {client.account_info.name}")

asyncio.run(main())
```

### Order Management

**Synchronous:**
```python
order_manager = create_order_manager(client)
response = order_manager.place_market_order("MGC", 0, 1)
orders = order_manager.search_open_orders()
```

**Async (now using canonical names):**
```python
order_manager = create_order_manager(client)
await order_manager.initialize()

response = await order_manager.place_market_order("MGC", 0, 1)
orders = await order_manager.search_open_orders()
```

### Real-time Data

**Synchronous:**
```python
realtime_client = create_realtime_client(jwt_token, account_id)
data_manager = create_data_manager("MGC", client, realtime_client)

realtime_client.connect()
data_manager.initialize()
data_manager.start_realtime_feed()
```

**Async (now using canonical names):**
```python
realtime_client = create_realtime_client(jwt_token, account_id)
data_manager = create_data_manager("MGC", client, realtime_client)

await realtime_client.connect()
await data_manager.initialize()
await data_manager.start_realtime_feed()
```

### Complete Trading Suite

**Synchronous:**
```python
suite = create_trading_suite(
    "MGC", client, jwt_token, account_id,
    timeframes=["5min", "15min"]
)

suite["realtime_client"].connect()
suite["data_manager"].initialize()
```

**Async (now using canonical names):**
```python
suite = await create_trading_suite(
    "MGC", client, jwt_token, account_id,
    timeframes=["5min", "15min"]
)

await suite["realtime_client"].connect()
await suite["data_manager"].initialize()
```

## Common Patterns

All public classes and factory functions are async-ready—use canonical names (no Async* prefix).

### 1. Concurrent Operations

```python
# Fetch multiple datasets concurrently
async def get_market_overview(client):
    tasks = []
    for symbol in ["MGC", "MNQ", "MES"]:
        tasks.append(client.get_data(symbol, days=1))
    
    results = await asyncio.gather(*tasks)
    return dict(zip(["MGC", "MNQ", "MES"], results))
```

### 2. Error Handling

```python
# Proper async error handling
async def safe_order_placement(order_manager, symbol, side, size):
    try:
        response = await order_manager.place_market_order(symbol, side, size)
        return response
    except ProjectXOrderError as e:
        logger.error(f"Order failed: {e}")
        return None
```

### 3. Event-Driven Patterns

```python
# Async event handlers
async def setup_event_handlers(realtime_client, order_manager):
    async def on_order_fill(data):
        # Non-blocking processing
        await process_fill(data)
        await send_notification(data)
    
    await realtime_client.add_callback("order_update", on_order_fill)
```

### 4. Background Tasks

```python
# Run background monitoring
async def monitor_positions(position_manager):
    while True:
        positions = await position_manager.get_all_positions()
        pnl = await position_manager.get_portfolio_pnl()
        
        if pnl < -1000:  # Stop loss
            await close_all_positions(position_manager)
            break
            
        await asyncio.sleep(5)  # Check every 5 seconds

# Run as background task
monitor_task = asyncio.create_task(monitor_positions(position_manager))
```

## Troubleshooting

### Common Issues

1. **"RuntimeError: This event loop is already running"**
   - Don't use `asyncio.run()` inside Jupyter notebooks
   - Use `await` directly in notebook cells

2. **"coroutine was never awaited"**
   - You forgot to use `await` with an async method
   - Add `await` before the method call

3. **"async with outside async function"**
   - Wrap your code in an async function
   - Use `asyncio.run(main())` to execute

4. **Mixing sync and async code**
   - Use all async components together
   - Don't mix sync and async managers

### Best Practices

1. **Always use async context managers:**
   ```python
   async with ProjectX.from_env() as client:
       # Client is properly cleaned up
   ```

2. **Group related operations:**
   ```python
   # Good - concurrent execution
   positions, orders = await asyncio.gather(
       position_manager.get_all_positions(),
       order_manager.search_open_orders()
   )
   ```

3. **Handle cleanup properly:**
   ```python
   try:
       await realtime_client.connect()
       # ... do work ...
   finally:
       await realtime_client.cleanup()
   ```

## Performance Tips

### 1. Use Concurrent Operations

```python
# Slow - sequential
for symbol in symbols:
    data = await client.get_data(symbol)
    process(data)

# Fast - concurrent
tasks = [client.get_data(symbol) for symbol in symbols]
all_data = await asyncio.gather(*tasks)
for data in all_data:
    process(data)
```

### 2. Avoid Blocking Operations

```python
# Bad - blocks event loop
def heavy_calculation(data):
    time.sleep(1)  # Blocks!
    return result

# Good - non-blocking
async def heavy_calculation(data):
    await asyncio.sleep(1)  # Non-blocking
    # Or run in executor for CPU-bound work
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, cpu_bound_work, data)
```

### 3. Batch Operations

```python
# Efficient batch processing
async def process_orders_batch(order_manager, orders):
    tasks = []
    for order in orders:
        task = order_manager.place_limit_order(**order)
        tasks.append(task)
    
    # Place all orders concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

## Example: Complete Migration

Here's a complete example showing a trading bot migration:

**Old Synchronous Bot:**
```python
from project_x_py import ProjectX, create_trading_suite

def trading_bot():
    client = ProjectX.from_env()
    
    suite = create_trading_suite(
        "MGC", client, client.session_token, 
        client.account_info.id
    )
    
    suite["realtime_client"].connect()
    suite["data_manager"].initialize()
    
    while True:
        data = suite["data_manager"].get_data("5min")
        positions = suite["position_manager"].get_all_positions()
        
        signal = analyze(data)
        if signal:
            suite["order_manager"].place_market_order("MGC", 0, 1)
        
        time.sleep(60)
```

**New Async Bot (now using canonical names):**
```python
import asyncio
from project_x_py import ProjectX, create_trading_suite

async def trading_bot():
    async with ProjectX.from_env() as client:
        await client.authenticate()
        
        suite = await create_trading_suite(
            "MGC", client, client.jwt_token, 
            client.account_info.id
        )
        
        await suite["realtime_client"].connect()
        await suite["data_manager"].initialize()
        
        while True:
            # Concurrent data fetching
            data, positions = await asyncio.gather(
                suite["data_manager"].get_data("5min"),
                suite["position_manager"].get_all_positions()
            )
            
            signal = analyze(data)
            if signal:
                await suite["order_manager"].place_market_order("MGC", 0, 1)
            
            await asyncio.sleep(60)

# Run the bot
asyncio.run(trading_bot())
```

## Summary

The async migration provides significant benefits:

- **3-5x faster** for concurrent operations
- **Non-blocking** real-time event handling
- **Better resource usage** with single-threaded concurrency
- **Modern Python** patterns for cleaner code

Start by migrating small scripts, then move to larger applications. The async patterns will quickly become natural and you'll appreciate the performance benefits!

For more examples, see the `examples/async_*.py` files in the repository.