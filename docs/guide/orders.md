# Order Management Guide

This guide covers comprehensive order management using ProjectX Python SDK v3.3.4+. All order operations are fully asynchronous and provide real-time tracking capabilities.

## Overview

The OrderManager provides complete lifecycle management for all order types including market, limit, stop, OCO (One Cancels Other), and bracket orders. All operations are async-first for optimal performance in trading applications.

### Key Features

- **Multiple Order Types**: Market, limit, stop, OCO, and bracket orders
- **Real-time Tracking**: Live order status updates via WebSocket
- **Error Recovery**: Automatic retry logic and comprehensive error handling
- **Price Precision**: Automatic tick size alignment using Decimal arithmetic
- **Concurrent Operations**: Place and manage multiple orders simultaneously
- **Risk Integration**: Built-in integration with RiskManager when enabled

## Getting Started

### Basic Setup

```python
import asyncio
from decimal import Decimal
from project_x_py import TradingSuite

async def main():
    # Initialize with order management capabilities
    suite = await TradingSuite.create("MNQ")

    # Order manager is automatically available
    order_manager = suite.orders

    # Get instrument information for proper pricing
    instrument = await suite.client.get_instrument("MNQ")
    print(f"Tick size: ${instrument.tickSize}")
```

### Safety First

** WARNING**: Order examples in this guide place real orders on the market. Always:

- Use micro contracts (MNQ, MES) for testing
- Set small position sizes
- Have exit strategies ready
- Test in paper trading environments when available

## Order Types

### Market Orders

Market orders execute immediately at the current market price with guaranteed fills but no price control.

```python
async def place_market_order():
    suite = await TradingSuite.create("MNQ")

    try:
        # Place buy market order
        response = await suite.orders.place_market_order(
            contract_id="MNQ",  # Or use suite.instrument_info.id
            side=0,             # 0 = Buy, 1 = Sell
            size=1              # Number of contracts
        )

        print(f"Market order placed: {response.order_id}")
        print(f"Status: {response.status}")

        # Wait for fill confirmation
        await asyncio.sleep(2)
        order_status = await suite.orders.get_order_status(response.order_id)
        print(f"Final status: {order_status}")

    except Exception as e:
        print(f"Order failed: {e}")
    finally:
        await suite.disconnect()
```

### Limit Orders

Limit orders execute only at specified price or better, providing price control but no fill guarantee.

```python
async def place_limit_order():
    suite = await TradingSuite.create("MNQ")

    # Get current market price for context
    current_price = await suite.data.get_current_price()

    # Place buy limit order below market
    limit_price = Decimal(str(current_price)) - Decimal("25")  # $25 below market

    response = await suite.orders.place_limit_order(
        contract_id="MNQ",
        side=0,                    # Buy
        size=1,
        limit_price=limit_price,
        time_in_force="DAY"        # DAY, GTC, IOC, FOK
    )

    print(f"Limit order placed at ${limit_price}")
    print(f"Order ID: {response.order_id}")

    # Monitor order status
    while True:
        status = await suite.orders.get_order_status(response.order_id)
        print(f"Status: {status}")

        if status in ["FILLED", "CANCELLED", "REJECTED"]:
            break

        await asyncio.sleep(5)  # Check every 5 seconds
```

### Stop Orders

Stop orders become market orders when the stop price is reached, useful for exits and breakout entries.

```python
async def place_stop_order():
    suite = await TradingSuite.create("MNQ")

    current_price = await suite.data.get_current_price()

    # Stop loss order (sell stop below current price)
    stop_price = Decimal(str(current_price)) - Decimal("50")  # $50 below market

    response = await suite.orders.place_stop_order(
        contract_id="MNQ",
        side=1,                    # Sell (for stop loss)
        size=1,
        stop_price=stop_price,
        time_in_force="GTC"        # Good Till Cancelled
    )

    print(f"Stop order placed at ${stop_price}")

    # Or stop entry order (buy stop above current price for breakouts)
    breakout_price = Decimal(str(current_price)) + Decimal("30")

    breakout_response = await suite.orders.place_stop_order(
        contract_id="MNQ",
        side=0,                    # Buy
        size=1,
        stop_price=breakout_price
    )

    print(f"Breakout order placed at ${breakout_price}")
```

### OCO Orders (One Cancels Other)

OCO orders link two orders where filling one automatically cancels the other.

```python
async def place_oco_order():
    suite = await TradingSuite.create("MNQ")

    current_price = await suite.data.get_current_price()

    # OCO for profit target and stop loss
    profit_target = Decimal(str(current_price)) + Decimal("75")  # $75 above
    stop_loss = Decimal(str(current_price)) - Decimal("50")     # $50 below

    response = await suite.orders.place_oco_order(
        contract_id="MNQ",

        # First leg: Profit target (sell limit)
        first_side=1,              # Sell
        first_size=1,
        first_order_type="LIMIT",
        first_price=profit_target,

        # Second leg: Stop loss (sell stop)
        second_side=1,             # Sell
        second_size=1,
        second_order_type="STOP",
        second_price=stop_loss
    )

    print(f"OCO placed: Target ${profit_target}, Stop ${stop_loss}")
    print(f"OCO Group ID: {response.oco_group_id}")

    # Both order IDs are available
    print(f"Target Order: {response.first_order_id}")
    print(f"Stop Order: {response.second_order_id}")
```

### Bracket Orders

Bracket orders are the most sophisticated order type, combining entry, stop loss, and take profit in one operation.

```python
async def place_bracket_order():
    suite = await TradingSuite.create("MNQ")

    current_price = await suite.data.get_current_price()

    # Complete bracket order setup
    response = await suite.orders.place_bracket_order(
        contract_id="MNQ",
        side=0,                    # Buy entry
        size=1,

        # Entry order (optional - if None, uses market order)
        entry_price=Decimal(str(current_price)) - Decimal("10"),  # Buy limit

        # Risk management
        stop_offset=Decimal("40"),     # Stop loss $40 from entry
        target_offset=Decimal("80"),   # Take profit $80 from entry

        # Order timing
        time_in_force="DAY"
    )

    print(f"Bracket order placed:")
    print(f"  Entry: {response.main_order_id}")
    print(f"  Stop Loss: {response.stop_order_id}")
    print(f"  Take Profit: {response.target_order_id}")

    # Monitor bracket order progress
    await monitor_bracket_order(suite, response)

async def monitor_bracket_order(suite, bracket_response):
    """Monitor all three orders in a bracket."""

    while True:
        # Check main order status
        main_status = await suite.orders.get_order_status(
            bracket_response.main_order_id
        )

        print(f"Entry order: {main_status}")

        if main_status == "FILLED":
            print("Entry filled! Monitoring exit orders...")

            # Now monitor the exit orders
            while True:
                stop_status = await suite.orders.get_order_status(
                    bracket_response.stop_order_id
                )
                target_status = await suite.orders.get_order_status(
                    bracket_response.target_order_id
                )

                if stop_status == "FILLED":
                    print("Stop loss triggered!")
                    break
                elif target_status == "FILLED":
                    print("Take profit hit!")
                    break

                await asyncio.sleep(2)
            break

        elif main_status in ["CANCELLED", "REJECTED"]:
            print(f"Entry order {main_status}")
            break

        await asyncio.sleep(5)
```

## Order Lifecycle and Tracking

### Real-time Order Status

Track order status changes in real-time using events or polling:

```python
from project_x_py import EventType

async def setup_order_tracking():
    suite = await TradingSuite.create("MNQ")

    # Event-driven tracking (recommended)
    async def on_order_update(event):
        order_data = event.data
        print(f"Order {order_data['order_id']} status: {order_data['status']}")

        if order_data['status'] == 'FILLED':
            print(f"  Filled at ${order_data['fill_price']}")
            print(f"  Quantity: {order_data['filled_quantity']}")

    # Register for order events
    await suite.on(EventType.ORDER_UPDATED, on_order_update)
    await suite.on(EventType.ORDER_FILLED, on_order_update)

    # Place an order to demonstrate tracking
    response = await suite.orders.place_market_order("MNQ", 0, 1)
    print(f"Tracking order: {response.order_id}")

    # Keep connection alive for events
    await asyncio.sleep(30)

# Alternative: Polling-based tracking
async def poll_order_status(suite, order_id):
    """Poll order status until completion."""

    while True:
        try:
            status = await suite.orders.get_order_status(order_id)
            print(f"Order {order_id}: {status}")

            if status in ["FILLED", "CANCELLED", "REJECTED"]:
                # Get final order details
                order_details = await suite.orders.get_order(order_id)
                print(f"Final details: {order_details}")
                break

        except Exception as e:
            print(f"Error checking status: {e}")

        await asyncio.sleep(2)
```

### Order History and Reporting

```python
async def analyze_order_history():
    suite = await TradingSuite.create("MNQ")

    # Get recent orders
    recent_orders = await suite.orders.get_orders(
        limit=50,
        status_filter=["FILLED", "CANCELLED"]
    )

    print(f"Found {len(recent_orders)} recent orders")

    # Analyze order performance
    filled_orders = [o for o in recent_orders if o.status == "FILLED"]

    if filled_orders:
        avg_fill_time = sum(
            (o.filled_time - o.created_time).total_seconds()
            for o in filled_orders
        ) / len(filled_orders)

        print(f"Average fill time: {avg_fill_time:.2f} seconds")

    # Get orders for specific date range
    from datetime import datetime, timedelta

    yesterday = datetime.now() - timedelta(days=1)

    daily_orders = await suite.orders.get_orders(
        start_time=yesterday,
        end_time=datetime.now()
    )

    print(f"Orders in last 24h: {len(daily_orders)}")
```

## Order Modification and Cancellation

### Modifying Orders

```python
async def modify_orders():
    suite = await TradingSuite.create("MNQ")

    # Place initial limit order
    current_price = await suite.data.get_current_price()
    initial_price = Decimal(str(current_price)) - Decimal("50")

    response = await suite.orders.place_limit_order(
        "MNQ", 0, 1, initial_price
    )

    order_id = response.order_id
    print(f"Initial order at ${initial_price}")

    # Wait a moment
    await asyncio.sleep(5)

    # Modify the order price (move closer to market)
    new_price = Decimal(str(current_price)) - Decimal("25")

    modify_response = await suite.orders.modify_order(
        order_id=order_id,
        new_price=new_price,
        new_size=2  # Also increase size
    )

    print(f"Order modified to ${new_price}, size: 2")

    # Modify only specific fields
    await suite.orders.modify_order(
        order_id=order_id,
        new_size=3  # Only change size
    )
```

### Cancelling Orders

```python
async def cancel_orders():
    suite = await TradingSuite.create("MNQ")

    # Place multiple orders
    orders = []
    current_price = await suite.data.get_current_price()

    for i in range(3):
        price = Decimal(str(current_price)) - Decimal(str(10 * (i + 1)))
        response = await suite.orders.place_limit_order("MNQ", 0, 1, price)
        orders.append(response.order_id)

    print(f"Placed {len(orders)} orders")

    # Cancel individual order
    await suite.orders.cancel_order(orders[0])
    print("Cancelled first order")

    # Cancel multiple orders
    await suite.orders.cancel_orders(orders[1:])
    print("Cancelled remaining orders")

    # Cancel all open orders (nuclear option)
    await suite.orders.cancel_all_orders("MNQ")
    print("All orders cancelled")
```

## Advanced Order Features

### Order Templates

Create reusable order templates for common strategies:

```python
from project_x_py.order_manager.templates import OrderTemplate

async def use_order_templates():
    suite = await TradingSuite.create("MNQ")

    # Create scalping template
    scalp_template = OrderTemplate(
        name="scalp_template",
        order_type="bracket",
        side=0,  # Buy
        size=2,
        entry_offset=Decimal("5"),      # 5 points below market
        stop_offset=Decimal("15"),      # 15 point stop
        target_offset=Decimal("25"),    # 25 point target
        time_in_force="DAY"
    )

    # Apply template
    current_price = await suite.data.get_current_price()

    response = await suite.orders.place_from_template(
        template=scalp_template,
        contract_id="MNQ",
        reference_price=Decimal(str(current_price))
    )

    print(f"Template order placed: {response.main_order_id}")

    # Create swing template
    swing_template = OrderTemplate(
        name="swing_template",
        order_type="bracket",
        side=0,
        size=1,
        entry_offset=Decimal("0"),      # Market entry
        stop_offset=Decimal("100"),     # 100 point stop
        target_offset=Decimal("300"),   # 300 point target
        time_in_force="GTC"
    )
```

### Position-Based Orders

Place orders based on existing positions:

```python
async def position_based_orders():
    suite = await TradingSuite.create("MNQ", features=["risk_manager"])

    # Check current position
    position = await suite.positions.get_position("MNQ")

    if position and position.size > 0:
        print(f"Long position: {position.size} contracts")

        # Place protective stop based on position
        current_price = await suite.data.get_current_price()
        stop_price = Decimal(str(current_price)) - Decimal("75")

        # Close entire position if stop hit
        response = await suite.orders.place_position_exit_order(
            contract_id="MNQ",
            stop_price=stop_price,
            position_size=position.size
        )

        print(f"Protective stop placed: {response.order_id}")

    elif position and position.size < 0:
        print(f"Short position: {position.size} contracts")

        # Cover stop for short position
        current_price = await suite.data.get_current_price()
        cover_price = Decimal(str(current_price)) + Decimal("75")

        response = await suite.orders.place_position_exit_order(
            contract_id="MNQ",
            stop_price=cover_price,
            position_size=abs(position.size)  # Cover the short
        )

    else:
        print("No position - placing new entry order")

        # No position, place new bracket order
        response = await suite.orders.place_bracket_order(
            contract_id="MNQ",
            side=0, size=1,
            stop_offset=Decimal("50"),
            target_offset=Decimal("100")
        )
```

## Error Handling and Recovery

### Comprehensive Error Handling

```python
from project_x_py.exceptions import (
    ProjectXOrderError,
    ProjectXRateLimitError,
    ProjectXInsufficientMarginError
)

async def robust_order_placement():
    suite = await TradingSuite.create("MNQ")

    try:
        response = await suite.orders.place_bracket_order(
            contract_id="MNQ",
            side=0, size=1,
            stop_offset=Decimal("50"),
            target_offset=Decimal("100")
        )

        print(f"Order placed successfully: {response.main_order_id}")

    except ProjectXInsufficientMarginError as e:
        print(f"Insufficient margin: {e}")
        # Reduce position size or add funds

    except ProjectXOrderError as e:
        print(f"Order error: {e}")
        if "invalid price" in str(e).lower():
            # Price alignment issue - check tick size
            instrument = await suite.client.get_instrument("MNQ")
            print(f"Tick size: {instrument.tickSize}")

    except ProjectXRateLimitError as e:
        print(f"Rate limited: {e}")
        # Wait and retry
        await asyncio.sleep(1)
        # Retry logic here...

    except Exception as e:
        print(f"Unexpected error: {e}")
```

### Automatic Error Recovery

The OrderManager includes built-in error recovery:

```python
async def demonstrate_error_recovery():
    suite = await TradingSuite.create("MNQ")

    # Enable automatic retry for recoverable errors
    suite.orders.enable_auto_retry(
        max_attempts=3,
        backoff_factor=2.0,
        recoverable_errors=[
            "NetworkTimeout",
            "TemporaryUnavailable",
            "RateLimitExceeded"
        ]
    )

    # This will automatically retry on network issues
    try:
        response = await suite.orders.place_market_order("MNQ", 0, 1)
        print(f"Order placed with auto-retry: {response.order_id}")

    except Exception as e:
        print(f"Failed after all retries: {e}")
```

## Performance Optimization

### Concurrent Order Operations

```python
async def concurrent_operations():
    suite = await TradingSuite.create("MNQ")

    current_price = await suite.data.get_current_price()

    # Place multiple orders concurrently
    tasks = []

    for i in range(5):
        price = Decimal(str(current_price)) - Decimal(str(10 * (i + 1)))

        task = suite.orders.place_limit_order(
            "MNQ", 0, 1, price, time_in_force="DAY"
        )
        tasks.append(task)

    # Execute all orders concurrently
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    successful_orders = []
    for i, response in enumerate(responses):
        if isinstance(response, Exception):
            print(f"Order {i} failed: {response}")
        else:
            successful_orders.append(response.order_id)
            print(f"Order {i} placed: {response.order_id}")

    print(f"Successfully placed {len(successful_orders)} orders")

    # Monitor all orders concurrently
    status_tasks = [
        suite.orders.get_order_status(order_id)
        for order_id in successful_orders
    ]

    statuses = await asyncio.gather(*status_tasks)
    for order_id, status in zip(successful_orders, statuses):
        print(f"Order {order_id}: {status}")
```

### Batch Operations

```python
async def batch_operations():
    suite = await TradingSuite.create("MNQ")

    # Batch cancel multiple orders
    order_ids = ["order1", "order2", "order3"]  # Your order IDs

    results = await suite.orders.batch_cancel_orders(order_ids)

    for order_id, result in results.items():
        if result["success"]:
            print(f"Cancelled {order_id}")
        else:
            print(f"Failed to cancel {order_id}: {result['error']}")

    # Batch status check
    statuses = await suite.orders.batch_get_status(order_ids)

    for order_id, status in statuses.items():
        print(f"Order {order_id}: {status}")
```

## Best Practices

### 1. Order Size and Risk Management

```python
# Always calculate position sizes based on risk
async def calculate_position_size(suite, entry_price, stop_price, risk_percent=0.01):
    """Calculate position size based on risk tolerance."""

    account_info = suite.client.account_info
    risk_amount = account_info.balance * Decimal(str(risk_percent))

    price_risk = abs(entry_price - stop_price)

    # Account for contract multiplier
    instrument = await suite.client.get_instrument("MNQ")
    multiplier = instrument.contractSize or Decimal("20")  # MNQ multiplier

    position_size = int(risk_amount / (price_risk * multiplier))

    return max(1, position_size)  # Minimum 1 contract
```

### 2. Price Precision

```python
# Always use Decimal for price calculations
from decimal import Decimal, ROUND_HALF_UP

async def align_to_tick_size(price: Decimal, tick_size: Decimal) -> Decimal:
    """Align price to instrument tick size."""

    return (price / tick_size).quantize(
        Decimal('1'), rounding=ROUND_HALF_UP
    ) * tick_size

# Usage
current_price = await suite.data.get_current_price()
instrument = await suite.client.get_instrument("MNQ")

entry_price = Decimal(str(current_price)) - Decimal("25")
aligned_price = await align_to_tick_size(
    entry_price,
    Decimal(str(instrument.tickSize))
)
```

### 3. Order Validation

```python
async def validate_order_before_placement(suite, contract_id, side, size, price=None):
    """Validate order parameters before placement."""

    # Check account margin
    account_info = suite.client.account_info

    # Get instrument info
    instrument = await suite.client.get_instrument(contract_id)

    # Validate size
    if size <= 0:
        raise ValueError("Order size must be positive")

    # Validate price alignment
    if price:
        tick_size = Decimal(str(instrument.tickSize))
        if price % tick_size != 0:
            raise ValueError(f"Price {price} not aligned to tick size {tick_size}")

    # Check position limits (if risk manager enabled)
    if hasattr(suite, 'risk_manager') and suite.risk_manager:
        current_position = await suite.positions.get_position(contract_id)
        new_size = (current_position.size if current_position else 0)

        if side == 0:  # Buy
            new_size += size
        else:  # Sell
            new_size -= size

        # Check if new position exceeds limits
        max_position = 10  # Your risk limit
        if abs(new_size) > max_position:
            raise ValueError(f"New position {new_size} exceeds limit {max_position}")

    return True
```

### 4. Event-Driven Order Management

```python
class OrderEventHandler:
    def __init__(self, suite):
        self.suite = suite
        self.active_orders = {}

    async def setup_event_handlers(self):
        """Setup comprehensive order event handling."""

        await self.suite.on(EventType.ORDER_PLACED, self.on_order_placed)
        await self.suite.on(EventType.ORDER_FILLED, self.on_order_filled)
        await self.suite.on(EventType.ORDER_CANCELLED, self.on_order_cancelled)
        await self.suite.on(EventType.ORDER_REJECTED, self.on_order_rejected)

    async def on_order_placed(self, event):
        """Handle order placement confirmation."""
        order_data = event.data
        self.active_orders[order_data['order_id']] = order_data
        print(f" Order placed: {order_data['order_id']}")

    async def on_order_filled(self, event):
        """Handle order fills."""
        order_data = event.data
        order_id = order_data['order_id']

        print(f"< Order filled: {order_id}")
        print(f"   Price: ${order_data['fill_price']}")
        print(f"   Quantity: {order_data['filled_quantity']}")

        # Remove from active orders
        if order_id in self.active_orders:
            del self.active_orders[order_id]

        # Handle bracket order logic
        if 'bracket_group_id' in order_data:
            await self.handle_bracket_fill(order_data)

    async def handle_bracket_fill(self, order_data):
        """Handle bracket order fills specially."""
        group_id = order_data['bracket_group_id']

        if order_data['order_type'] == 'entry':
            print(f"Bracket entry filled - monitoring exits for group {group_id}")
        elif order_data['order_type'] in ['stop', 'target']:
            print(f"Bracket exit filled - group {group_id} complete")
            # Cancel remaining exit order if needed

# Usage
async def run_with_event_handling():
    suite = await TradingSuite.create("MNQ")

    handler = OrderEventHandler(suite)
    await handler.setup_event_handlers()

    # Your trading logic here...
    response = await suite.orders.place_bracket_order(
        "MNQ", 0, 1,
        stop_offset=Decimal("50"),
        target_offset=Decimal("100")
    )

    # Events will be handled automatically
    await asyncio.sleep(60)  # Keep running for events
```

## Integration with Risk Management

When the RiskManager feature is enabled, order placement is automatically validated:

```python
async def risk_managed_trading():
    # Enable risk management
    suite = await TradingSuite.create("MNQ", features=["risk_manager"])

    # Risk manager validates all orders automatically
    try:
        response = await suite.orders.place_bracket_order(
            contract_id="MNQ",
            side=0, size=5,  # Large size
            stop_offset=Decimal("25"),
            target_offset=Decimal("75")
        )

    except ProjectXRiskViolationError as e:
        print(f"Risk check failed: {e}")
        # Order was rejected due to risk limits

    # Set custom risk parameters
    await suite.risk_manager.set_position_limit("MNQ", max_contracts=3)
    await suite.risk_manager.set_daily_loss_limit(Decimal("1000"))

    # Now retry with smaller size
    response = await suite.orders.place_bracket_order(
        contract_id="MNQ",
        side=0, size=2,  # Safer size
        stop_offset=Decimal("50"),
        target_offset=Decimal("100")
    )
```

## Summary

The ProjectX OrderManager provides comprehensive order management capabilities:

- **Multiple order types** with full async support
- **Real-time tracking** via WebSocket events
- **Error recovery** with automatic retry logic
- **Price precision** handling with tick alignment
- **Risk integration** when RiskManager is enabled
- **Concurrent operations** for high-performance trading
- **Event-driven architecture** for responsive applications

All order operations are designed for production trading environments with proper error handling, logging, and performance optimization. Always test thoroughly with small positions before deploying live trading strategies.

---

**Next**: [Position Management Guide](positions.md) | **Previous**: [Trading Suite Guide](trading-suite.md)
