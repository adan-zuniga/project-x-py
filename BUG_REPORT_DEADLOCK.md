# Bug Report: Deadlock in Event Handler Callbacks

## Summary
Calling `suite.data.get_current_price()` or `suite.data.get_data()` from within an EventBus event handler callback causes a deadlock, preventing the methods from completing.

## Severity
**HIGH** - This affects the usability of the event-driven API pattern

## Reproduction Steps

1. Register an event handler using `suite.on(EventType.NEW_BAR, handler)`
2. Within the handler, call any async method on `suite.data`:
   - `await suite.data.get_current_price()`
   - `await suite.data.get_data(timeframe, bars)`
3. The handler will receive the event but hang indefinitely on the async call

## Example Code That Reproduces The Issue

```python
async def on_new_bar(event):
    """This handler will deadlock"""
    current_price = await suite.data.get_current_price()  # HANGS HERE
    print(f"Current price: {current_price}")

await suite.on(EventType.NEW_BAR, on_new_bar)
```

## Workaround

Use a queue to decouple event reception from processing:

```python
event_queue = asyncio.Queue()

async def on_new_bar(event):
    """Queue the event instead of processing it"""
    await event_queue.put(event)

await suite.on(EventType.NEW_BAR, on_new_bar)

# Process events outside the handler context
while True:
    event = await event_queue.get()
    current_price = await suite.data.get_current_price()  # Works fine here
    print(f"Current price: {current_price}")
```

## Root Cause Analysis

The deadlock appears to occur because:

1. The event handler is executed within the EventBus's event processing context
2. The RealtimeDataManager's `get_current_price()` and `get_data()` methods may be trying to acquire locks or access resources that are held during event processing
3. This creates a circular wait condition where:
   - The event handler is waiting for the data manager methods to complete
   - The data manager methods are waiting for resources locked by the event processing

## Affected Components

- `TradingSuite`
- `RealtimeDataManager` 
- `EventBus`

## Suggested Fixes

1. **Short-term**: Document this limitation and provide the queue-based workaround pattern
2. **Medium-term**: Make data access methods non-blocking when called from event handlers
3. **Long-term**: Refactor the event processing to avoid holding locks during callback execution

## Files Demonstrating the Issue

- `/examples/realtime_data_manager/01_events_with_on.py` - Shows the deadlock
- `/examples/realtime_data_manager/01_events_with_on_simple.py` - Shows the workaround

## Discovery Date
2025-01-12

## Discovered By
User testing of event handler examples

## ✅ FIXED

### The Solution
Modified `src/project_x_py/realtime_data_manager/data_processing.py` to:

1. **Changed `_update_timeframe_data()` to return event data instead of triggering it directly**
2. **Moved event triggering outside the lock in `_process_tick_data()`**
3. **Made event emission non-blocking using `asyncio.create_task()`**
4. **Added missing `asyncio` import**

### Key Changes
```python
# Before (inside lock):
async with self.data_lock:
    for tf_key in self.timeframes:
        await self._update_timeframe_data(tf_key, timestamp, price, volume)
        # Event was triggered inside _update_timeframe_data while holding lock

# After (events triggered outside lock):
events_to_trigger = []
async with self.data_lock:
    for tf_key in self.timeframes:
        new_bar_event = await self._update_timeframe_data(tf_key, timestamp, price, volume)
        if new_bar_event:
            events_to_trigger.append(new_bar_event)

# Trigger events outside lock, non-blocking
for event in events_to_trigger:
    asyncio.create_task(self._trigger_callbacks("new_bar", event))
```

### Test Results
- ✅ Event handlers are called successfully
- ✅ `suite.data.get_current_price()` works from within handlers
- ✅ `suite.data.get_data()` works from within handlers
- ✅ No deadlock occurs
- ✅ API remains unchanged