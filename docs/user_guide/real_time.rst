Real-Time Data Guide
====================

Stream live market data and trading events through WebSocket connections.

Overview
--------

The SDK provides real-time data through WebSocket connections with automatic reconnection, message batching, and event-driven architecture.

Setting Up Real-Time Feeds
---------------------------

Basic Setup
~~~~~~~~~~~

.. code-block:: python

   from project_x_py import TradingSuite, EventType
   import asyncio

   async def setup_realtime():
       # TradingSuite automatically connects to real-time feeds
       suite = await TradingSuite.create(
           "MNQ",
           timeframes=["1min", "5min", "15min"],
           initial_days=3  # Load historical data first
       )
       
       print(f"Connected: {suite.realtime.is_connected()}")
       print(f"Subscribed to: {suite.instrument_id}")
       
       # Keep running to receive data
       await asyncio.sleep(60)
       await suite.disconnect()

   asyncio.run(setup_realtime())

Event Types
-----------

Available Events
~~~~~~~~~~~~~~~~

.. code-block:: python

   from project_x_py import EventType

   # Market data events
   EventType.TICK           # Individual price updates
   EventType.QUOTE_UPDATE   # Bid/ask changes
   EventType.TRADE_TICK     # Executed trades
   EventType.NEW_BAR        # New OHLCV bar created
   EventType.BAR_UPDATE     # Existing bar updated
   
   # Trading events
   EventType.ORDER_PLACED   # Order submitted
   EventType.ORDER_FILLED   # Order executed
   EventType.ORDER_CANCELLED # Order cancelled
   EventType.ORDER_REJECTED # Order rejected
   
   # Position events
   EventType.POSITION_OPENED  # New position created
   EventType.POSITION_UPDATE  # Position changed
   EventType.POSITION_CLOSED  # Position closed
   
   # System events
   EventType.CONNECTION_ESTABLISHED
   EventType.CONNECTION_LOST
   EventType.RECONNECTING
   EventType.ERROR

Registering Event Handlers
---------------------------

Using Decorators
~~~~~~~~~~~~~~~~

.. code-block:: python

   async def setup_handlers():
       suite = await TradingSuite.create("ES")
       
       @suite.events.on(EventType.TICK)
       async def handle_tick(event):
           tick = event.data
           print(f"Tick: ${tick['price']} Vol: {tick['volume']}")
       
       @suite.events.on(EventType.NEW_BAR)
       async def handle_new_bar(event):
           bar = event.data
           timeframe = bar['timeframe']
           data = bar['data']
           print(f"New {timeframe} bar: ${data['close']}")
       
       await asyncio.sleep(60)

Using await suite.on()
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def register_handlers():
       suite = await TradingSuite.create("MNQ")
       
       async def on_quote(event):
           quote = event.data
           spread = quote['ask'] - quote['bid']
           print(f"Bid: ${quote['bid']} Ask: ${quote['ask']} Spread: ${spread}")
       
       async def on_trade(event):
           trade = event.data
           print(f"Trade: {trade['size']} @ ${trade['price']}")
       
       await suite.on(EventType.QUOTE_UPDATE, on_quote)
       await suite.on(EventType.TRADE_TICK, on_trade)

Real-Time Data Access
---------------------

Current Market State
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def monitor_market():
       suite = await TradingSuite.create("MNQ")
       
       while True:
           # Get current price
           price = await suite.data.get_current_price()
           
           # Get latest bars
           bars_1m = await suite.data.get_data("1min", bars=1)
           bars_5m = await suite.data.get_data("5min", bars=1)
           
           # Get tick data
           ticks = await suite.data.get_recent_ticks(count=10)
           
           print(f"Price: ${price:,.2f}")
           print(f"Ticks in last batch: {len(ticks)}")
           
           await asyncio.sleep(5)

OrderBook (Level 2)
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def monitor_orderbook():
       suite = await TradingSuite.create(
           "ES",
           features=["orderbook"]
       )
       
       async def on_orderbook_update(event):
           # Get best bid/ask
           best = await suite.orderbook.get_best_bid_ask()
           print(f"Best Bid: ${best['bid']:,.2f} Ask: ${best['ask']:,.2f}")
           
           # Get market depth
           bids = await suite.orderbook.get_orderbook_bids(levels=5)
           asks = await suite.orderbook.get_orderbook_asks(levels=5)
           
           # Analyze imbalance
           imbalance = await suite.orderbook.get_market_imbalance()
           print(f"Imbalance: {imbalance:.2%}")
       
       await suite.on(EventType.ORDERBOOK_UPDATE, on_orderbook_update)

Performance Optimization
------------------------

Message Batching
~~~~~~~~~~~~~~~~

The SDK automatically batches WebSocket messages for efficiency:

.. code-block:: python

   # Messages are batched every 100ms by default
   # This reduces overhead while maintaining low latency
   
   suite = await TradingSuite.create(
       "MNQ",
       websocket_config={
           "batch_interval_ms": 50,  # Faster batching
           "max_batch_size": 100     # Maximum messages per batch
       }
   )

Memory Management
~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def memory_efficient_streaming():
       suite = await TradingSuite.create(
           "ES",
           timeframes=["1min", "5min"],
           config={
               "max_bars_per_timeframe": 500,  # Limit bar storage
               "tick_buffer_size": 1000,        # Circular tick buffer
               "enable_compression": True        # Compress old data
           }
       )
       
       # Monitor memory usage
       stats = suite.data.get_memory_stats()
       print(f"Memory usage: {stats['memory_mb']:.2f} MB")
       print(f"Bars stored: {stats['total_bars']}")
       print(f"Ticks processed: {stats['ticks_processed']}")

Connection Management
---------------------

Monitoring Connection
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def monitor_connection():
       suite = await TradingSuite.create("MNQ")
       
       # Check connection status
       print(f"Connected: {suite.realtime.is_connected()}")
       print(f"User hub: {suite.realtime.user_connected}")
       print(f"Market hub: {suite.realtime.market_connected}")
       
       # Handle connection events
       async def on_disconnect(event):
           print("Connection lost, will auto-reconnect...")
       
       async def on_reconnect(event):
           print("Reconnected successfully")
       
       await suite.on(EventType.CONNECTION_LOST, on_disconnect)
       await suite.on(EventType.CONNECTION_ESTABLISHED, on_reconnect)

Manual Reconnection
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def handle_reconnection():
       suite = await TradingSuite.create("MNQ")
       
       # Force reconnection if needed
       if not suite.realtime.is_connected():
           await suite.realtime.disconnect()
           await suite.realtime.connect()
           
           # Re-subscribe to market data
           await suite.data.start_realtime_feed()

Building Trading Strategies
---------------------------

Event-Driven Strategy
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def moving_average_strategy():
       suite = await TradingSuite.create("MNQ")
       
       async def on_new_bar(event):
           if event.data['timeframe'] != "5min":
               return
           
           # Get recent data
           data = await suite.data.get_data("5min", bars=50)
           if data is None or len(data) < 50:
               return
           
           # Calculate moving averages
           ma20 = data['close'].tail(20).mean()
           ma50 = data['close'].tail(50).mean()
           current = data['close'].tail(1)[0]
           
           # Trading logic
           position = await suite.positions.get_position("MNQ")
           
           if ma20 > ma50 and current > ma20 and not position:
               # Buy signal
               await suite.orders.place_market_order(
                   contract_id=suite.instrument_id,
                   side=0,
                   size=1
               )
           elif ma20 < ma50 and current < ma20 and position and position.is_long:
               # Sell signal
               await suite.positions.close_position("MNQ")
       
       await suite.on(EventType.NEW_BAR, on_new_bar)

Tick Scalping
~~~~~~~~~~~~~

.. code-block:: python

   async def tick_scalper():
       suite = await TradingSuite.create(
           "ES",
           features=["orderbook"]
       )
       
       position_size = 0
       entry_price = None
       
       async def on_tick(event):
           nonlocal position_size, entry_price
           
           tick = event.data
           price = tick['price']
           
           # Get orderbook imbalance
           imbalance = await suite.orderbook.get_market_imbalance()
           
           if position_size == 0:
               # Entry logic
               if imbalance > 0.7:  # Strong buy pressure
                   result = await suite.orders.place_market_order(
                       contract_id=suite.instrument_id,
                       side=0,
                       size=1
                   )
                   if result.success:
                       position_size = 1
                       entry_price = price
           else:
               # Exit logic
               profit = price - entry_price
               if profit >= 2 or profit <= -1:  # 2 point target or 1 point stop
                   await suite.orders.place_market_order(
                       contract_id=suite.instrument_id,
                       side=1,
                       size=1
                   )
                   position_size = 0
                   entry_price = None
       
       await suite.on(EventType.TICK, on_tick)

Best Practices
--------------

1. **Handle disconnections gracefully**: Implement reconnection logic
2. **Process events asynchronously**: Don't block event handlers
3. **Use appropriate timeframes**: Balance between granularity and performance
4. **Monitor memory usage**: Clean up old data in long-running applications
5. **Implement error handling**: Catch and log exceptions in handlers
6. **Test with replay data**: Use historical data to test strategies

Troubleshooting
---------------

.. code-block:: python

   from project_x_py import setup_logging

   # Enable debug logging for WebSocket
   setup_logging(level='DEBUG')

   async def debug_connection():
       suite = await TradingSuite.create("MNQ")
       
       # Check what's happening
       if not suite.realtime.is_connected():
           print("Not connected to WebSocket")
           
       # Check subscriptions
       print(f"Subscribed instruments: {suite.realtime.subscriptions}")
       
       # Check data flow
       await asyncio.sleep(5)
       stats = suite.data.get_memory_stats()
       if stats['ticks_processed'] == 0:
           print("No ticks received - check market hours")

Next Steps
----------

- :doc:`analysis` - Technical analysis tools
- :doc:`../examples/real_time_data` - Complete examples
- :doc:`../api/orderbook` - OrderBook API reference