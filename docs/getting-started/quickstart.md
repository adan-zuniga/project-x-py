# Quick Start

This guide will help you get started with the ProjectX Python SDK. Some examples will place live trades and orders. Please use with caution!!

## Basic Setup

### Single Instrument (Traditional)

```python
import asyncio

from project_x_py import TradingSuite


async def main():
    # Create a trading suite for single instrument
    suite = await TradingSuite.create(
        instruments=["MNQ"],  # List notation (recommended)
        timeframes=["1min", "5min"],
        features=["orderbook"],  # Optional features
        initial_days=5,  # Historical data to load
    )

    # Access the instrument context
    mnq = suite["MNQ"]

    if suite.client.account_info is None:
        raise Exception("Account info is None")

    # Everything is now connected and ready
    print(f"Connected to: {suite.client.account_info.name}")

    # Access current market data
    current_price = await mnq.data.get_current_price()
    print(f"MNQ Current price: ${current_price:,.2f}")

    # Clean shutdown
    await suite.disconnect()


# Run the async function
asyncio.run(main())
```

### Multi-Instrument Setup (v3.5.0)

```python
import asyncio

from project_x_py import TradingSuite


async def multi_instrument_setup():
    # Create suite for multiple instruments
    suite = await TradingSuite.create(
        instruments=["MNQ", "ES", "MGC"],  # Multiple futures
        timeframes=["1min", "5min"],
        features=["orderbook", "risk_manager"],
    )

    print(f"Managing {len(suite)} instruments: {list(suite.keys())}")

    # Access individual instruments
    for symbol, context in suite.items():
        current_price = await context.data.get_current_price()
        print(f"{symbol}: ${current_price:,.2f}")

    await suite.disconnect()


asyncio.run(multi_instrument_setup())
```

## Simple Trading Example

### Single Instrument Trading

```python
import asyncio

from project_x_py import TradingSuite


async def trading_example():
    suite = await TradingSuite.create(["MNQ"])  # List notation
    mnq = suite["MNQ"]  # Get instrument context

    # Place a market order
    order = await mnq.orders.place_market_order(
        contract_id=mnq.instrument_info.id,
        side=0,  # 0=Buy, 1=Sell
        size=1,
    )
    print(f"Order placed: {order.orderId}")

    # Check position
    position = await mnq.positions.get_position("MNQ")
    if position:
        print(f"Position: {position.size} @ ${position.averagePrice:,.2f}")

    # Place a stop loss
    if position and position.size > 0:
        stop_order = await mnq.orders.place_stop_order(
            contract_id=mnq.instrument_info.id,
            side=1,  # Sell
            size=position.size,
            stop_price=position.averagePrice - 20,  # 20 points below entry
        )
        print(f"Stop loss placed: {stop_order.orderId}")

    await suite.disconnect()

asyncio.run(trading_example())
```

### Multi-Instrument Pairs Trading

```python
import asyncio

from project_x_py import TradingSuite


async def pairs_trading_example():
    suite = await TradingSuite.create(["ES", "MNQ"])  # S&P 500 vs NASDAQ

    es_context = suite["ES"]
    mnq_context = suite["MNQ"]

    # Get current prices
    es_price = await es_context.data.get_current_price()
    mnq_price = await mnq_context.data.get_current_price()

    if es_price is None or mnq_price is None:
        raise Exception("No price data available")

    # Calculate spread (normalize by contract values)
    spread = (es_price * 50) - (mnq_price * 20)
    print(f"ES/MNQ Spread: ${spread:.2f}")

    # Simple spread trading logic
    if spread > 500:  # ES expensive relative to MNQ
        await es_context.orders.place_market_order(
            contract_id=es_context.instrument_info.id,
            side=1,
            size=1,  # Sell ES
        )
        await mnq_context.orders.place_market_order(
            contract_id=mnq_context.instrument_info.id,
            side=0,
            size=1,  # Buy MNQ
        )
        print("Executed pairs trade: Short ES, Long MNQ")

    await suite.disconnect()


asyncio.run(pairs_trading_example())
```

## Real-time Data Streaming

### Single Instrument Streaming

```python
import asyncio

from project_x_py import EventType, TradingSuite
from project_x_py.event_bus import Event


async def stream_data():
    suite = await TradingSuite.create(["MNQ"], timeframes=["15sec", "1min"])

    mnq = suite["MNQ"]

    # Register event handlers
    async def on_new_bar(event: Event):
        data = event.data
        timeframe = data.get("timeframe")
        bar = data.get("data")
        if bar:
            print(
                f"MNQ New {timeframe} bar: ${bar['close']:,.2f} Vol: {bar['volume']:,}"
            )

    async def on_quote(event: Event):
        quote = event.data

        if quote["bid"] is None or quote["ask"] is None:
            return

        print(f"MNQ Quote: Bid ${quote['bid']:,.2f} Ask ${quote['ask']:,.2f}")

    # Subscribe to events for MNQ
    await mnq.on(EventType.NEW_BAR, on_new_bar)
    await mnq.on(EventType.QUOTE_UPDATE, on_quote)

    # Keep streaming for 30 seconds
    await asyncio.sleep(30)

    await suite.disconnect()


asyncio.run(stream_data())
```

### Multi-Instrument Streaming

```python
import asyncio

from project_x_py import EventType, TradingSuite
from project_x_py.event_bus import Event


async def multi_stream_data():
    suite = await TradingSuite.create(
        ["MNQ", "ES", "MGC"],
        timeframes=["15sec", "1min"],
    )

    # Register handlers for each instrument
    for symbol, context in suite.items():

        async def make_handler(sym):
            async def on_new_bar(event: Event):
                data = event.data
                if data.get("timeframe") == "1min":
                    bar = data.get("data")
                    print(f"{sym} 1min: ${bar['close']:,.2f}")

            return on_new_bar

        handler = await make_handler(symbol)
        await context.on(EventType.NEW_BAR, handler)

    # Stream all instruments simultaneously
    await asyncio.sleep(30)
    await suite.disconnect()


asyncio.run(multi_stream_data())
```

## Next Steps

- [Trading Suite Guide](../guide/trading-suite.md) - Complete guide to multi-instrument TradingSuite
- [Order Management](../guide/orders.md) - Advanced order types and management
- [Technical Indicators](../guide/indicators.md) - Using indicators with market data
- [Multi-Instrument API](../api/trading-suite.md) - Detailed API reference for v3.5.0
- [Examples](../examples/basic.md) - More code examples including multi-instrument patterns
- [Migration Guide](../migration/v3-to-v4.md) - Upgrading to multi-instrument patterns
