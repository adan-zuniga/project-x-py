Market Data Guide
=================

Access historical and real-time market data through the ProjectX SDK.

Historical Data
---------------

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from project_x_py import TradingSuite
   import asyncio

   async def get_historical_data():
       suite = await TradingSuite.create("MNQ")
       
       # Get last 5 days of 15-minute bars
       data = await suite.client.get_bars("MNQ", days=5, interval=15)
       print(f"Retrieved {len(data)} bars")
       
       # Display OHLCV data
       for row in data.head(5).iter_rows(named=True):
           print(f"{row['timestamp']}: O={row['open']} H={row['high']} "
                 f"L={row['low']} C={row['close']} V={row['volume']}")
       
       await suite.disconnect()

   asyncio.run(get_historical_data())

Time Range Queries
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from datetime import datetime, timedelta
   
   async def get_specific_range():
       suite = await TradingSuite.create("ES")
       
       # Get data for specific date range
       end_time = datetime.now()
       start_time = end_time - timedelta(days=30)
       
       data = await suite.client.get_bars(
           "ES",
           start_time=start_time,
           end_time=end_time,
           interval=60  # 1-hour bars
       )
       
       print(f"Data from {start_time} to {end_time}")
       print(f"Total bars: {len(data)}")

Multiple Timeframes
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def multi_timeframe_analysis():
       suite = await TradingSuite.create(
           "MNQ",
           timeframes=["1min", "5min", "15min", "1hr", "1day"]
       )
       
       # Data manager handles multiple timeframes
       for timeframe in ["1min", "5min", "15min"]:
           data = await suite.data.get_data(timeframe)
           if data is not None:
               print(f"{timeframe}: {len(data)} bars")

Real-Time Data
--------------

Setting Up Real-Time Feeds
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from project_x_py import TradingSuite, EventType

   async def setup_realtime():
       suite = await TradingSuite.create(
           "MNQ",
           timeframes=["1min", "5min"],
           initial_days=3  # Load 3 days of history
       )
       
       # Register callbacks for real-time updates
       async def on_tick(event):
           tick = event.data
           print(f"Tick: ${tick['price']} @ {tick['timestamp']}")
       
       async def on_new_bar(event):
           bar = event.data
           print(f"New {bar['timeframe']} bar: ${bar['data']['close']}")
       
       await suite.on(EventType.TICK, on_tick)
       await suite.on(EventType.NEW_BAR, on_new_bar)
       
       # Keep running to receive updates
       await asyncio.sleep(60)
       await suite.disconnect()

Accessing Current Data
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def monitor_prices():
       suite = await TradingSuite.create("MNQ")
       
       while True:
           # Get current price
           current = await suite.data.get_current_price()
           print(f"Current price: ${current:,.2f}")
           
           # Get latest bar
           data = await suite.data.get_data("1min", bars=1)
           if data is not None and not data.is_empty():
               latest = data.tail(1)
               for row in latest.iter_rows(named=True):
                   print(f"Latest bar: {row['timestamp']} - ${row['close']}")
           
           await asyncio.sleep(5)

Data Quality
------------

Tick Alignment
~~~~~~~~~~~~~~

All prices are automatically aligned to instrument tick size:

.. code-block:: python

   # Prices are automatically aligned
   # For MNQ (tick size 0.25):
   # 23927.62 → 23927.50
   # 23927.88 → 23928.00

Volume Considerations
~~~~~~~~~~~~~~~~~~~~~

.. note::
   Volume data represents trades executed through the ProjectX platform only, not full exchange volume from CME.

.. code-block:: python

   async def analyze_volume():
       suite = await TradingSuite.create("MNQ")
       data = await suite.client.get_bars("MNQ", days=1, interval=5)
       
       # Calculate volume metrics
       total_volume = data['volume'].sum()
       avg_volume = data['volume'].mean()
       
       print(f"Total volume: {total_volume:,}")
       print(f"Average volume per bar: {avg_volume:.2f}")

Data Processing
---------------

Working with Polars DataFrames
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import polars as pl

   async def process_data():
       suite = await TradingSuite.create("ES")
       data = await suite.client.get_bars("ES", days=10, interval=60)
       
       # Polars operations
       daily_stats = data.group_by(
           pl.col("timestamp").dt.date()
       ).agg([
           pl.col("high").max().alias("day_high"),
           pl.col("low").min().alias("day_low"),
           pl.col("volume").sum().alias("day_volume"),
           (pl.col("close").last() - pl.col("open").first()).alias("day_change")
       ])
       
       print(daily_stats)

Adding Custom Columns
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def add_custom_metrics():
       suite = await TradingSuite.create("MNQ")
       data = await suite.client.get_bars("MNQ", days=5, interval=15)
       
       # Add custom calculations
       data = data.with_columns([
           ((pl.col("high") - pl.col("low")) / pl.col("close") * 100).alias("range_pct"),
           (pl.col("close") - pl.col("open")).alias("bar_change"),
           (pl.col("volume").rolling_mean(window_size=20)).alias("vol_ma20")
       ])
       
       print(data.columns)

Memory Management
-----------------

The SDK automatically manages memory for large datasets:

.. code-block:: python

   async def memory_efficient():
       suite = await TradingSuite.create(
           "ES",
           timeframes=["1min", "5min", "15min"],
           initial_days=30  # Large dataset
       )
       
       # Data manager automatically manages memory
       # - Sliding windows for real-time data
       # - Maximum bars per timeframe: 1000 (configurable)
       # - Automatic cleanup of old data
       
       stats = suite.data.get_memory_stats()
       print(f"Memory usage: {stats['memory_mb']:.2f} MB")
       print(f"Total bars: {stats['total_bars']:,}")
       print(f"Ticks processed: {stats['ticks_processed']:,}")

Caching Strategies
------------------

.. code-block:: python

   from project_x_py import TradingSuite

   async def cached_operations():
       suite = await TradingSuite.create("MNQ")
       
       # First call fetches from API
       data1 = await suite.client.get_bars("MNQ", days=1, interval=5)
       
       # Subsequent calls may use cache (within TTL)
       data2 = await suite.client.get_bars("MNQ", days=1, interval=5)
       
       # Force refresh by using different parameters
       data3 = await suite.client.get_bars("MNQ", days=2, interval=5)

Best Practices
--------------

1. **Use appropriate timeframes**: Don't request 1-minute data for months of history
2. **Implement data validation**: Check for None/empty responses
3. **Handle missing data**: Markets are closed on weekends/holidays
4. **Monitor memory usage**: Use sliding windows for long-running applications
5. **Cache frequently used data**: Reduce API calls

Error Handling
--------------

.. code-block:: python

   from project_x_py import ProjectXDataError

   async def safe_data_fetch():
       try:
           suite = await TradingSuite.create("MNQ")
           data = await suite.client.get_bars("MNQ", days=5)
           
           if data is None or data.is_empty():
               print("No data available")
               return
           
           # Process data
           print(f"Processing {len(data)} bars")
           
       except ProjectXDataError as e:
           print(f"Data error: {e}")
       except Exception as e:
           print(f"Unexpected error: {e}")

Next Steps
----------

- :doc:`trading` - Place and manage orders
- :doc:`real_time` - Real-time data streaming
- :doc:`analysis` - Technical analysis