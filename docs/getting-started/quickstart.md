# Quick Start

This guide will help you get started with the ProjectX Python SDK.

## Basic Setup

```python
import asyncio
from project_x_py import TradingSuite

async def main():
    # Create a trading suite with all components
    suite = await TradingSuite.create(
        instrument="MNQ",  # Micro E-mini NASDAQ
        timeframes=["1min", "5min"],
        features=["orderbook"],  # Optional features
        initial_days=5  # Historical data to load
    )

    # Everything is now connected and ready
    print(f"Connected to: {suite.client.account_info.name}")

    # Access current market data
    current_price = await suite.data.get_current_price()
    print(f"Current price: ${current_price:,.2f}")

    # Clean shutdown
    await suite.disconnect()

# Run the async function
asyncio.run(main())
```

## Simple Trading Example

```python
async def trading_example():
    suite = await TradingSuite.create("MNQ")

    # Place a market order
    order = await suite.orders.place_market_order(
        contract_id=suite.instrument_info.id,
        side=0,  # 0=Buy, 1=Sell
        size=1
    )
    print(f"Order placed: {order.order_id}")

    # Check position
    position = await suite.positions.get_position("MNQ")
    if position:
        print(f"Position: {position.net_position} @ ${position.average_price:,.2f}")

    # Place a stop loss
    if position and position.net_position > 0:
        stop_order = await suite.orders.place_stop_order(
            contract_id=suite.instrument_info.id,
            side=1,  # Sell
            size=position.net_position,
            stop_price=position.average_price - 20  # 20 points below entry
        )
        print(f"Stop loss placed: {stop_order.order_id}")

    await suite.disconnect()
```

## Real-time Data Streaming

```python
from project_x_py import EventType

async def stream_data():
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["1min", "5min"]
    )

    # Register event handlers
    async def on_new_bar(event):
        data = event.data
        timeframe = data.get('timeframe')
        bar = data.get('data')
        if bar:
            print(f"New {timeframe} bar: ${bar['close']:,.2f} Vol: {bar['volume']:,}")

    async def on_quote(event):
        quote = event.data
        print(f"Quote: Bid ${quote['bid']:,.2f} Ask ${quote['ask']:,.2f}")

    # Subscribe to events
    await suite.on(EventType.NEW_BAR, on_new_bar)
    await suite.on(EventType.QUOTE_UPDATE, on_quote)

    # Keep streaming for 30 seconds
    await asyncio.sleep(30)

    await suite.disconnect()
```

## Next Steps

- [Trading Suite Guide](../guide/trading-suite.md) - Complete guide to TradingSuite
- [Order Management](../guide/orders.md) - Advanced order types and management
- [Technical Indicators](../guide/indicators.md) - Using indicators with market data
- [Examples](../examples/basic.md) - More code examples
