# Error Handling and Logging Migration Guide

This guide provides instructions for migrating existing code to use the new centralized error handling and logging utilities introduced in Phase 4 of the refactoring plan.

## Overview

The new error handling system provides:
- Consistent error handling patterns via decorators
- Structured logging with JSON support
- Automatic retry logic for network operations
- Standardized error messages and codes
- Better error context and debugging information

## Migration Steps

### 1. Replace Manual Error Handling with Decorators

#### Before:
```python
async def get_orders(self) -> list[Order]:
    try:
        response = await self._make_request("GET", "/orders")
        return [Order(**order) for order in response]
    except httpx.HTTPError as e:
        self.logger.error(f"Failed to fetch orders: {e}")
        raise ProjectXConnectionError(f"Failed to fetch orders: {e}") from e
    except Exception as e:
        self.logger.error(f"Unexpected error fetching orders: {e}")
        raise ProjectXError(f"Unexpected error: {e}") from e
```

#### After:
```python
from project_x_py.utils import handle_errors, validate_response

@handle_errors("fetch orders")
@validate_response(response_type=list)
async def get_orders(self) -> list[Order]:
    response = await self._make_request("GET", "/orders")
    return [Order(**order) for order in response]
```

### 2. Replace Manual Retry Logic

#### Before:
```python
async def _make_request(self, method: str, endpoint: str, retry_count: int = 0):
    try:
        response = await self.client.request(method, endpoint)
        return response.json()
    except httpx.ConnectError as e:
        if retry_count < self.config.retry_attempts:
            wait_time = 2 ** retry_count
            self.logger.warning(f"Connection error, retrying in {wait_time}s: {e}")
            await asyncio.sleep(wait_time)
            return await self._make_request(method, endpoint, retry_count + 1)
        raise ProjectXConnectionError(f"Failed to connect: {e}") from e
```

#### After:
```python
from project_x_py.utils import retry_on_network_error

@retry_on_network_error(max_attempts=3, initial_delay=1.0)
async def _make_request(self, method: str, endpoint: str):
    response = await self.client.request(method, endpoint)
    return response.json()
```

### 3. Use Structured Logging

#### Before:
```python
import logging

class OrderManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    async def place_order(self, order: OrderRequest):
        self.logger.info(f"Placing order: {order.symbol} {order.side} {order.size}")
        # ... implementation
        self.logger.info(f"Order placed successfully: {order_id}")
```

#### After:
```python
from project_x_py.utils import ProjectXLogger, LogMessages, log_api_call

class OrderManager:
    def __init__(self):
        self.logger = ProjectXLogger.get_logger(__name__)
        
    async def place_order(self, order: OrderRequest):
        self.logger.info(
            LogMessages.ORDER_PLACE,
            extra={
                "symbol": order.symbol,
                "side": order.side,
                "size": order.size,
                "order_type": order.order_type,
            }
        )
        
        # Track API performance
        start_time = time.time()
        response = await self._make_request("POST", "/orders", data=order.dict())
        
        log_api_call(
            self.logger,
            method="POST",
            endpoint="/orders",
            status_code=response.status_code,
            duration=time.time() - start_time,
            order_id=response.get("id"),
        )
```

### 4. Use Standardized Error Messages

#### Before:
```python
if not self.is_authenticated:
    raise ProjectXAuthenticationError("Not authenticated. Please login first.")

if order.size <= 0:
    raise ProjectXOrderError(f"Invalid order size: {order.size}")
    
if instrument is None:
    raise ProjectXInstrumentError(f"Instrument not found: {symbol}")
```

#### After:
```python
from project_x_py.utils import ErrorMessages, format_error_message

if not self.is_authenticated:
    raise ProjectXAuthenticationError(ErrorMessages.AUTH_SESSION_EXPIRED)

if order.size <= 0:
    raise ProjectXOrderError(
        format_error_message(ErrorMessages.ORDER_INVALID_SIZE, size=order.size)
    )
    
if instrument is None:
    raise ProjectXInstrumentError(
        format_error_message(ErrorMessages.INSTRUMENT_NOT_FOUND, symbol=symbol)
    )
```

### 5. Handle Rate Limiting

#### Before:
```python
async def get_market_data(self, symbol: str):
    try:
        return await self._make_request("GET", f"/market/{symbol}")
    except ProjectXError as e:
        if e.error_code == 429:  # Rate limited
            # Manual rate limit handling
            retry_after = int(e.response_data.get("retry_after", 60))
            await asyncio.sleep(retry_after)
            return await self.get_market_data(symbol)
        raise
```

#### After:
```python
from project_x_py.utils import handle_rate_limit

@handle_rate_limit(fallback_delay=60.0)
async def get_market_data(self, symbol: str):
    return await self._make_request("GET", f"/market/{symbol}")
```

### 6. Batch Error Handling

#### Before:
```python
async def process_orders(self, orders: list[OrderRequest]):
    results = []
    errors = []
    
    for order in orders:
        try:
            result = await self.place_order(order)
            results.append(result)
        except Exception as e:
            errors.append((order.id, str(e)))
            self.logger.error(f"Failed to place order {order.id}: {e}")
            
    if errors:
        self.logger.error(f"Failed to place {len(errors)} orders")
        
    return results, errors
```

#### After:
```python
from project_x_py.utils import ErrorContext

async def process_orders(self, orders: list[OrderRequest]):
    results = []
    
    async with ErrorContext("process orders", logger=self.logger) as ctx:
        for order in orders:
            try:
                result = await self.place_order(order)
                results.append(result)
            except Exception as e:
                ctx.add_error(f"order_{order.id}", e)
                
    return results, ctx.errors
```

### 7. Enhanced Exception Context

#### Before:
```python
async def execute_trade(self, trade: TradeRequest):
    try:
        # ... implementation
    except Exception as e:
        self.logger.error(f"Trade execution failed: {e}")
        raise ProjectXError(f"Trade execution failed: {e}") from e
```

#### After:
```python
from project_x_py.utils import enhance_exception

async def execute_trade(self, trade: TradeRequest):
    try:
        # ... implementation
    except Exception as e:
        raise enhance_exception(
            e,
            operation="execute_trade",
            instrument=trade.instrument,
            size=trade.size,
            side=trade.side,
            strategy=trade.strategy_name,
        )
```

## Module-Specific Migration Examples

### Client HTTP Module

```python
# client/http.py
from project_x_py.utils import (
    handle_errors,
    retry_on_network_error,
    ProjectXLogger,
    LogMessages,
    log_api_call,
)

class HttpMixin:
    def __init__(self):
        self.logger = ProjectXLogger.get_logger(__name__)
    
    @handle_errors("API request")
    @retry_on_network_error(
        max_attempts=3,
        initial_delay=1.0,
        retry_on=(httpx.ConnectError, httpx.TimeoutException)
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
    ) -> dict:
        start_time = time.time()
        
        # Make request
        response = await self.client.request(
            method,
            self.base_url + endpoint,
            json=data,
        )
        
        # Log API call
        log_api_call(
            self.logger,
            method=method,
            endpoint=endpoint,
            status_code=response.status_code,
            duration=time.time() - start_time,
        )
        
        response.raise_for_status()
        return response.json()
```

### Order Manager Module

```python
# order_manager/core.py
from project_x_py.utils import (
    handle_errors,
    validate_response,
    ErrorMessages,
    format_error_message,
    LogContext,
)

class OrderManagerCore:
    @handle_errors("place market order")
    @validate_response(required_fields=["id", "status"])
    async def place_market_order(
        self,
        contract_id: str,
        side: int,
        size: int,
    ) -> OrderPlaceResponse:
        # Add logging context
        with LogContext(
            self.logger,
            operation="place_market_order",
            contract_id=contract_id,
            side=side,
            size=size,
        ):
            # Validate inputs
            if size <= 0:
                raise ProjectXOrderError(
                    format_error_message(
                        ErrorMessages.ORDER_INVALID_SIZE,
                        size=size
                    )
                )
            
            # Place order
            response = await self._submit_order(
                contract_id=contract_id,
                side=side,
                size=size,
                order_type="MARKET",
            )
            
            return OrderPlaceResponse(**response)
```

### WebSocket Module

```python
# realtime.py
from project_x_py.utils import (
    handle_errors,
    retry_on_network_error,
    ErrorContext,
    LogMessages,
)

class ProjectXRealtimeClient:
    @handle_errors("WebSocket connection")
    @retry_on_network_error(max_attempts=5, initial_delay=2.0)
    async def connect(self) -> bool:
        self.logger.info(LogMessages.WS_CONNECT)
        
        try:
            await self._ws.connect()
            self.logger.info(LogMessages.WS_CONNECTED)
            return True
        except Exception as e:
            self.logger.error(
                LogMessages.WS_CONNECTION_FAILED,
                extra={"reason": str(e)}
            )
            raise
```

## Best Practices

### 1. Decorator Order
When using multiple decorators, apply them in this order:
```python
@handle_errors("operation name")  # Outermost - catches all errors
@handle_rate_limit()              # Handle rate limits
@retry_on_network_error()         # Retry on network errors
@validate_response()              # Innermost - validates response
async def my_method():
    pass
```

### 2. Logging Context
Use structured logging with extra fields:
```python
self.logger.info(
    "Processing order",
    extra={
        "order_id": order.id,
        "symbol": order.symbol,
        "size": order.size,
        "user_id": self.user_id,
    }
)
```

### 3. Error Messages
Always use error message constants:
```python
# Good
raise ProjectXError(
    format_error_message(ErrorMessages.ORDER_NOT_FOUND, order_id=order_id)
)

# Bad
raise ProjectXError(f"Order not found: {order_id}")
```

### 4. Performance Logging
Track operation performance:
```python
from project_x_py.utils import log_performance

start_time = time.time()
result = await expensive_operation()
log_performance(
    self.logger,
    "expensive_operation",
    start_time,
    items_processed=len(result),
)
```

## Configuration

### SDK-Wide Logging Configuration
```python
# In your application startup
from project_x_py.utils import configure_sdk_logging

# Development
configure_sdk_logging(
    level=logging.DEBUG,
    format_json=False,
)

# Production
configure_sdk_logging(
    level=logging.INFO,
    format_json=True,
    log_file="/var/log/projectx/app.log",
)
```

### Environment Variables
```bash
# Control logging
export PROJECTX_LOG_LEVEL=DEBUG
export PROJECTX_LOG_FORMAT=json

# Control error handling
export PROJECTX_MAX_RETRIES=5
export PROJECTX_RETRY_DELAY=2.0
```

## Testing

When testing code with error handling decorators:

```python
import pytest
from unittest.mock import Mock

@pytest.mark.asyncio
async def test_with_error_handling():
    # Mock the logger to verify error logging
    mock_logger = Mock()
    
    # Test successful case
    result = await my_decorated_function()
    assert result is not None
    
    # Test error case
    with pytest.raises(ProjectXError):
        await my_failing_function()
        
    # Verify error was logged
    mock_logger.error.assert_called()
```

## Gradual Migration Strategy

1. **Phase 1**: Migrate critical paths (authentication, order placement)
2. **Phase 2**: Migrate all API client methods
3. **Phase 3**: Migrate WebSocket and real-time components
4. **Phase 4**: Migrate utility functions and helpers
5. **Phase 5**: Remove old error handling code

## Checklist

For each module being migrated:

- [ ] Replace manual try/except with `@handle_errors`
- [ ] Add `@retry_on_network_error` to network operations
- [ ] Add `@handle_rate_limit` to API methods
- [ ] Add `@validate_response` where appropriate
- [ ] Replace logger creation with `ProjectXLogger.get_logger()`
- [ ] Use `LogMessages` constants for common operations
- [ ] Replace hardcoded error strings with `ErrorMessages`
- [ ] Add structured logging with `extra` fields
- [ ] Use `ErrorContext` for batch operations
- [ ] Add performance logging for slow operations
- [ ] Update tests to work with decorators
- [ ] Remove old error handling code

## Benefits After Migration

1. **Consistent Error Messages**: Users see standardized, helpful error messages
2. **Better Debugging**: Structured logs with context make debugging easier
3. **Automatic Retries**: Network issues are handled automatically
4. **Performance Tracking**: Built-in performance metrics
5. **Reduced Code**: Less boilerplate error handling code
6. **Better Testing**: Easier to test with consistent patterns