Technical Indicators
===================

Comprehensive technical analysis library with 58+ TA-Lib compatible indicators built specifically for Polars DataFrames, including advanced pattern recognition indicators.

Overview
--------

The indicators module provides both class-based and function-based interfaces for technical analysis, similar to TA-Lib but optimized for Polars DataFrames.

.. currentmodule:: project_x_py.indicators

.. automodule:: project_x_py.indicators
   :members:
   :undoc-members:
   :show-inheritance:
   :no-index:

Quick Start
-----------

.. code-block:: python

   import asyncio
   from project_x_py.indicators import RSI, SMA, MACD, BBANDS
   from project_x_py import ProjectX
   
   async def analyze_market():
       # Get market data
       async with ProjectX.from_env() as client:
           await client.authenticate()
           data = await client.get_bars('MNQ', days=30, interval=60)  # V3: actual symbol
       
       # Class-based interface
       rsi = RSI()
       data_with_rsi = rsi.calculate(data, period=14)
       
       # TA-Lib style functions (direct usage)
       data = RSI(data, period=14)        # Add RSI
       data = SMA(data, period=20)        # Add 20-period SMA
       data = BBANDS(data, period=20)     # Add Bollinger Bands
       
       return data
   
   # Run the analysis
   data = asyncio.run(analyze_market())

Base Classes
------------

.. autoclass:: BaseIndicator
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: OverlapIndicator
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: MomentumIndicator
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: VolatilityIndicator
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: VolumeIndicator
   :members:
   :undoc-members:
   :show-inheritance:

Overlap Studies (Trend Indicators)
----------------------------------

.. autoclass:: SMA
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: EMA
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: BBANDS
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: DEMA
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: TEMA
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: WMA
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: MIDPOINT
   :members:
   :undoc-members:
   :show-inheritance:

Momentum Indicators
------------------

.. autoclass:: RSI
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: MACD
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: STOCH
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: WILLR
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: CCI
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: ROC
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: MOM
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: STOCHRSI
   :members:
   :undoc-members:
   :show-inheritance:

Volatility Indicators
---------------------

.. autoclass:: ATR
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: ADX
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: NATR
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: TRANGE
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: ULTOSC
   :members:
   :undoc-members:
   :show-inheritance:

Volume Indicators
-----------------

.. autoclass:: OBV
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: VWAP
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: AD
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: ADOSC
   :members:
   :undoc-members:
   :show-inheritance:

Pattern Recognition Indicators
------------------------------

.. autoclass:: FVG
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: OrderBlock
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: WAE
   :members:
   :undoc-members:
   :show-inheritance:

Convenience Functions
--------------------

Overlap Studies
~~~~~~~~~~~~~~~

.. autofunction:: calculate_sma
.. autofunction:: calculate_ema
.. autofunction:: calculate_bollinger_bands

Momentum Indicators
~~~~~~~~~~~~~~~~~~

.. autofunction:: calculate_rsi
.. autofunction:: calculate_macd
.. autofunction:: calculate_stochastic
.. autofunction:: calculate_williams_r
.. autofunction:: calculate_commodity_channel_index

Volatility Indicators
~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: calculate_atr
.. autofunction:: calculate_adx

Volume Indicators
~~~~~~~~~~~~~~~~~

.. autofunction:: calculate_obv
.. autofunction:: calculate_vwap

Pattern Recognition
~~~~~~~~~~~~~~~~~~~

.. autofunction:: calculate_fvg
.. autofunction:: calculate_order_block
.. autofunction:: calculate_wae

Discovery Functions
-------------------

.. autofunction:: get_all_indicators
.. autofunction:: get_indicator_groups
.. autofunction:: get_indicator_info

Utility Functions
-----------------

.. autofunction:: ema_alpha
.. autofunction:: safe_division

Usage Examples
--------------

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   import asyncio
   from project_x_py.indicators import RSI, SMA, MACD
   from project_x_py import ProjectX
   
   async def basic_analysis():
       # Load your data (Polars DataFrame with OHLCV columns)
       async with ProjectX.from_env() as client:
           await client.authenticate()
           data = await client.get_bars('MNQ', days=30, interval=60)  # V3: actual symbol
       
       # Add indicators using TA-Lib style functions
       data = RSI(data, period=14)
       data = SMA(data, period=20)
       data = SMA(data, period=50) 
       data = MACD(data, fast_period=12, slow_period=26, signal_period=9)
       
       # Check latest values
       latest = data.tail(1)
       print(f"RSI: {latest['rsi_14'].item():.2f}")
       print(f"SMA(20): ${latest['sma_20'].item():.2f}")
   
   asyncio.run(basic_analysis())

Class-Based Interface
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from project_x_py.indicators import RSI, SMA, BBANDS
   
   # Create indicator instances
   rsi = RSI()
   sma = SMA()
   bb = BBANDS()
   
   # Calculate indicators
   data_with_rsi = rsi.calculate(data, period=14)
   data_with_sma = sma.calculate(data_with_rsi, period=20)
   data_with_bb = bb.calculate(data_with_sma, period=20, std_dev=2.0)

Multi-Indicator Strategy
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import asyncio
   import polars as pl
   from project_x_py.indicators import *
   from project_x_py import ProjectX
   
   async def multi_indicator_analysis():
       # Get data
       async with ProjectX.from_env() as client:
           await client.authenticate()
           data = await client.get_bars('MNQ', days=60, interval=60)  # V3: actual symbol
       
       # Comprehensive technical analysis
       analysis = (
           data
           # Trend indicators
           .pipe(SMA, period=20)
           .pipe(SMA, period=50)
           .pipe(EMA, period=21)
           .pipe(BBANDS, period=20, std_dev=2.0)
           
           # Momentum indicators  
           .pipe(RSI, period=14)
           .pipe(MACD, fast_period=12, slow_period=26, signal_period=9)
           .pipe(STOCH, k_period=14, d_period=3)
           
           # Volatility indicators
           .pipe(ATR, period=14)
           .pipe(ADX, period=14)
           
           # Volume indicators
           .pipe(OBV)
           .pipe(VWAP, period=20)
           
           # Pattern recognition
           .pipe(FVG, min_gap_size=0.001, check_mitigation=True)
           .pipe(ORDERBLOCK, min_volume_percentile=70)
           .pipe(WAE, sensitivity=150)
       )
       
       return analysis
   
   # Run the strategy
   result = asyncio.run(multi_indicator_analysis())

Pattern Recognition Examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from project_x_py.indicators import FVG, OrderBlock, WAE
   
   # Fair Value Gap Detection
   fvg = FVG()
   data_with_fvg = fvg.calculate(
       data,
       min_gap_size=0.001,  # 0.1% minimum gap
       check_mitigation=True,  # Track if gaps get filled
       mitigation_threshold=0.5  # 50% fill threshold
   )
   
   # Order Block Identification
   ob = OrderBlock()
   data_with_ob = ob.calculate(
       data,
       min_volume_percentile=70,  # Top 30% volume
       lookback_periods=3,  # Look for 3-candle patterns
       use_wicks=True  # Consider wicks in patterns
   )
   
   # Waddah Attar Explosion
   wae = WAE()
   data_with_wae = wae.calculate(
       data,
       sensitivity=150,  # Trend sensitivity
       dead_zone_period=100,  # ATR period for filtering
       dead_zone_mult=3.6  # Dead zone multiplier
   )
   
   # Confluence Trading: Combine all three
   confluence_data = (
       data
       .pipe(FVG, check_mitigation=True)
       .pipe(ORDERBLOCK, min_volume_percentile=80)
       .pipe(WAE, sensitivity=150)
   )
   
   # Find strong signals where patterns align
   strong_bullish = confluence_data.filter(
       (pl.col("fvg_bullish") == True) & 
       (pl.col("ob_bullish") == True) & 
       (pl.col("wae_explosion_up") > 0)
   )

Indicator Discovery
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from project_x_py.indicators import get_all_indicators, get_indicator_groups
   
   # List all available indicators
   all_indicators = get_all_indicators()
   print(f"Total indicators: {len(all_indicators)}")
   
   # Get indicators by category
   groups = get_indicator_groups()
   for category, indicators in groups.items():
       print(f"{category}: {indicators}")
   
   # Get information about specific indicator
   rsi_info = get_indicator_info('RSI')
   print(f"RSI: {rsi_info}")

Error Handling
~~~~~~~~~~~~~~

.. code-block:: python

   from project_x_py.indicators import IndicatorError
   
   try:
       # This will raise an error if the column doesn't exist
       data_with_rsi = RSI(data, column='nonexistent_column', period=14)
   except IndicatorError as e:
       print(f"Indicator error: {e}")
   
   try:
       # This will raise an error if period is too large
       data_with_sma = SMA(data, period=1000)  # More than available data
   except IndicatorError as e:
       print(f"Invalid period: {e}")

Performance Tips
----------------

1. **Use Polars methods**: Indicators are optimized for Polars DataFrames
2. **Chain operations**: Use ``.pipe()`` for efficient chaining
3. **Reuse instances**: Create indicator instances once and reuse them
4. **Batch calculations**: Calculate multiple indicators in one pass when possible
5. **Async data fetching**: Fetch data once and apply all indicators

.. code-block:: python

   async def efficient_analysis():
       # Fetch data once
       async with ProjectX.from_env() as client:
           await client.authenticate()
           data = await client.get_bars('MNQ', days=30)  # V3: actual symbol
       
       # Efficient: Chain multiple indicators
       data = (
           data
           .pipe(RSI, period=14)
           .pipe(SMA, period=20)
           .pipe(MACD)
       )
       
       # Less efficient: Separate calculations
       # data = RSI(data, period=14)
       # data = SMA(data, period=20) 
       # data = MACD(data)
       
       return data

TA-Lib Compatibility
--------------------

The indicators are designed to be compatible with TA-Lib naming and parameter conventions:

.. list-table:: TA-Lib Compatibility
   :header-rows: 1
   :widths: 25 25 50

   * - TA-Lib Function
     - project-x-py Equivalent
     - Notes
   * - ``talib.SMA(close, timeperiod=20)``
     - ``SMA(data, period=20)``
     - Uses 'close' column by default
   * - ``talib.RSI(close, timeperiod=14)``
     - ``RSI(data, period=14)``
     - Identical calculation method
   * - ``talib.BBANDS(close, timeperiod=20)``
     - ``BBANDS(data, period=20, std_dev=2.0)``
     - Returns upper, middle, lower bands
   * - ``talib.MACD(close)``
     - ``MACD(data)``
     - Returns MACD line, signal, histogram

Exception Classes
-----------------

.. autoclass:: IndicatorError
   :members:
   :undoc-members:
   :show-inheritance: 