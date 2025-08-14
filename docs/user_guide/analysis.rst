Technical Analysis Guide
========================

Comprehensive guide to using 58+ technical indicators and pattern recognition tools.

Overview
--------

The SDK includes a full suite of TA-Lib compatible indicators built on Polars DataFrames for high performance.

Indicator Categories
--------------------

Available Indicators
~~~~~~~~~~~~~~~~~~~~

**Momentum Indicators**
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Stochastic Oscillator (STOCH)
- Williams %R (WILLR)
- Commodity Channel Index (CCI)
- Money Flow Index (MFI)
- Rate of Change (ROC)
- Ultimate Oscillator (ULTOSC)

**Trend Indicators**
- SMA (Simple Moving Average)
- EMA (Exponential Moving Average)
- WMA (Weighted Moving Average)
- DEMA (Double Exponential Moving Average)
- TEMA (Triple Exponential Moving Average)
- KAMA (Kaufman Adaptive Moving Average)
- ADX (Average Directional Index)
- Aroon Indicator

**Volatility Indicators**
- Bollinger Bands (BBANDS)
- Average True Range (ATR)
- Keltner Channels (KC)
- Donchian Channels (DC)
- Standard Deviation (STDDEV)

**Volume Indicators**
- On-Balance Volume (OBV)
- Volume Weighted Average Price (VWAP)
- Accumulation/Distribution (AD)
- Chaikin Money Flow (CMF)

**Pattern Recognition (v2.0.2+)**
- Fair Value Gap (FVG)
- Order Block (ORDERBLOCK)
- Waddah Attar Explosion (WAE)

Basic Usage
-----------

Function-Style Interface
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from project_x_py import TradingSuite
   from project_x_py.indicators import RSI, SMA, MACD, BBANDS
   import asyncio

   async def apply_indicators():
       suite = await TradingSuite.create("MNQ")
       
       # Get historical data
       data = await suite.client.get_bars("MNQ", days=30, interval=60)
       
       # Apply indicators using pipe
       data = (data
           .pipe(RSI, period=14)
           .pipe(SMA, period=20)
           .pipe(SMA, period=50, column_name="sma_50")
           .pipe(MACD, fast_period=12, slow_period=26, signal_period=9)
           .pipe(BBANDS, period=20, std_dev=2.0)
       )
       
       # Access indicator values
       latest = data.tail(1)
       print(f"RSI: {latest['rsi_14'][0]:.2f}")
       print(f"SMA(20): {latest['sma_20'][0]:.2f}")
       print(f"Upper Band: {latest['bb_upper_20'][0]:.2f}")
       
       await suite.disconnect()

   asyncio.run(apply_indicators())

Class-Based Interface
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from project_x_py.indicators import RSI, BollingerBands, MACD

   async def class_based_indicators():
       suite = await TradingSuite.create("ES")
       data = await suite.client.get_bars("ES", days=20, interval=15)
       
       # Create indicator instances
       rsi = RSI(period=14)
       bb = BollingerBands(period=20, std_dev=2.0)
       macd_indicator = MACD()
       
       # Calculate indicators
       data = rsi.calculate(data)
       data = bb.calculate(data)
       data = macd_indicator.calculate(data)
       
       # Get signals
       rsi_signals = rsi.get_signals(data)
       print(f"RSI Signal: {rsi_signals.tail(1)['signal'][0]}")

Pattern Recognition
-------------------

Fair Value Gap (FVG)
~~~~~~~~~~~~~~~~~~~~

Identifies price imbalances that may act as support/resistance:

.. code-block:: python

   from project_x_py.indicators import FVG

   async def detect_fvg():
       suite = await TradingSuite.create("MNQ")
       data = await suite.client.get_bars("MNQ", days=5, interval=15)
       
       # Detect Fair Value Gaps
       data_with_fvg = FVG(
           data,
           min_gap_size=0.001,      # Minimum 0.1% gap
           check_mitigation=True,    # Track if gaps are filled
           use_shadows=True          # Include wicks in analysis
       )
       
       # Find recent gaps
       gaps = data_with_fvg.filter(
           pl.col("fvg_bullish") | pl.col("fvg_bearish")
       )
       
       for row in gaps.tail(5).iter_rows(named=True):
           gap_type = "Bullish" if row['fvg_bullish'] else "Bearish"
           print(f"{row['timestamp']}: {gap_type} FVG")
           print(f"  Gap High: ${row['fvg_high']:.2f}")
           print(f"  Gap Low: ${row['fvg_low']:.2f}")
           if row['fvg_mitigated']:
               print(f"  Mitigated at: {row['fvg_mitigation_time']}")

Order Blocks
~~~~~~~~~~~~

Identifies institutional order zones:

.. code-block:: python

   from project_x_py.indicators import OrderBlock

   async def find_order_blocks():
       suite = await TradingSuite.create("ES")
       data = await suite.client.get_bars("ES", days=10, interval=60)
       
       # Detect order blocks
       ob = OrderBlock(
           lookback=10,              # Bars to look back
           min_volume_percentile=70, # High volume requirement
           use_wicks=True,           # Include wicks
           filter_overlap=True       # Remove overlapping blocks
       )
       
       data_with_blocks = ob.calculate(data)
       
       # Find active order blocks
       blocks = data_with_blocks.filter(
           pl.col("orderblock_bullish") | pl.col("orderblock_bearish")
       )
       
       for row in blocks.tail(3).iter_rows(named=True):
           block_type = "Bullish" if row['orderblock_bullish'] else "Bearish"
           print(f"{block_type} Order Block:")
           print(f"  Zone: ${row['orderblock_low']:.2f} - ${row['orderblock_high']:.2f}")
           print(f"  Volume: {row['orderblock_volume']:,}")
           print(f"  Strength: {row['orderblock_strength']:.2f}")

Waddah Attar Explosion
~~~~~~~~~~~~~~~~~~~~~~

Detects strong trends and breakouts:

.. code-block:: python

   from project_x_py.indicators import WAE

   async def waddah_attar():
       suite = await TradingSuite.create("MNQ")
       data = await suite.client.get_bars("MNQ", days=5, interval=5)
       
       # Apply WAE indicator
       data_with_wae = WAE(
           data,
           sensitivity=150,      # Sensitivity to price changes
           fast_period=20,        # Fast EMA period
           slow_period=40,        # Slow EMA period
           channel_period=20,     # Bollinger Band period
           channel_mult=2.0       # BB multiplier
       )
       
       # Find explosion signals
       explosions = data_with_wae.filter(
           pl.col("wae_explosion") > pl.col("wae_dead_zone")
       )
       
       for row in explosions.tail(5).iter_rows(named=True):
           trend = "Bullish" if row['wae_trend'] == 1 else "Bearish"
           print(f"{row['timestamp']}: {trend} Explosion")
           print(f"  Strength: {row['wae_explosion']:.4f}")
           print(f"  Above dead zone: {row['wae_explosion'] - row['wae_dead_zone']:.4f}")

Strategy Development
--------------------

Multi-Indicator Strategy
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def multi_indicator_strategy():
       suite = await TradingSuite.create("ES")
       
       # Get data and apply indicators
       data = await suite.client.get_bars("ES", days=20, interval=30)
       
       data = (data
           .pipe(RSI, period=14)
           .pipe(MACD)
           .pipe(SMA, period=20)
           .pipe(SMA, period=50, column_name="sma_50")
           .pipe(BBANDS, period=20)
           .pipe(ATR, period=14)
       )
       
       # Generate signals
       latest = data.tail(1).to_dict(as_series=False)
       
       rsi = latest['rsi_14'][0]
       macd = latest['macd'][0]
       signal = latest['macd_signal'][0]
       price = latest['close'][0]
       sma20 = latest['sma_20'][0]
       sma50 = latest['sma_50'][0]
       bb_upper = latest['bb_upper_20'][0]
       bb_lower = latest['bb_lower_20'][0]
       atr = latest['atr_14'][0]
       
       # Trading logic
       buy_signal = (
           rsi < 30 and                    # Oversold
           macd > signal and                # MACD bullish
           price > sma20 > sma50 and        # Uptrend
           price <= bb_lower                # At lower band
       )
       
       sell_signal = (
           rsi > 70 and                     # Overbought
           macd < signal and                 # MACD bearish
           price < sma20 < sma50 and        # Downtrend
           price >= bb_upper                 # At upper band
       )
       
       if buy_signal:
           print("BUY Signal Generated")
           print(f"Entry: ${price:.2f}")
           print(f"Stop: ${price - 2*atr:.2f}")
           print(f"Target: ${price + 3*atr:.2f}")
       elif sell_signal:
           print("SELL Signal Generated")

Backtesting Support
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def backtest_strategy():
       suite = await TradingSuite.create("MNQ")
       
       # Get historical data
       data = await suite.client.get_bars("MNQ", days=60, interval=60)
       
       # Apply indicators
       data = (data
           .pipe(RSI, period=14)
           .pipe(SMA, period=20)
       )
       
       # Simulate trades
       trades = []
       position = None
       
       for row in data.iter_rows(named=True):
           if position is None:
               # Check entry
               if row['rsi_14'] < 30 and row['close'] > row['sma_20']:
                   position = {
                       'entry_time': row['timestamp'],
                       'entry_price': row['close'],
                       'side': 'long'
                   }
           else:
               # Check exit
               if row['rsi_14'] > 70:
                   position['exit_time'] = row['timestamp']
                   position['exit_price'] = row['close']
                   position['pnl'] = row['close'] - position['entry_price']
                   trades.append(position)
                   position = None
       
       # Calculate statistics
       if trades:
           total_pnl = sum(t['pnl'] for t in trades)
           win_rate = sum(1 for t in trades if t['pnl'] > 0) / len(trades)
           
           print(f"Total trades: {len(trades)}")
           print(f"Win rate: {win_rate:.1%}")
           print(f"Total P&L: ${total_pnl:.2f}")

Custom Indicators
-----------------

Creating Custom Indicators
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import polars as pl
   
   def custom_momentum_indicator(
       data: pl.DataFrame,
       period: int = 10,
       smoothing: int = 3
   ) -> pl.DataFrame:
       """Custom momentum indicator with smoothing."""
       
       # Calculate raw momentum
       momentum = data.with_columns([
           (pl.col("close") - pl.col("close").shift(period))
           .alias(f"momentum_{period}")
       ])
       
       # Apply smoothing
       momentum = momentum.with_columns([
           pl.col(f"momentum_{period}")
           .rolling_mean(window_size=smoothing)
           .alias(f"momentum_smooth_{period}")
       ])
       
       # Generate signals
       momentum = momentum.with_columns([
           pl.when(pl.col(f"momentum_smooth_{period}") > 0)
           .then(1)
           .when(pl.col(f"momentum_smooth_{period}") < 0)
           .then(-1)
           .otherwise(0)
           .alias("momentum_signal")
       ])
       
       return momentum
   
   async def use_custom_indicator():
       suite = await TradingSuite.create("ES")
       data = await suite.client.get_bars("ES", days=10, interval=15)
       
       # Apply custom indicator
       data = custom_momentum_indicator(data, period=10, smoothing=3)
       
       # Check signals
       latest = data.tail(1)
       signal = latest['momentum_signal'][0]
       
       if signal == 1:
           print("Bullish momentum")
       elif signal == -1:
           print("Bearish momentum")

Performance Tips
----------------

1. **Chain operations**: Use `.pipe()` for efficient chaining
2. **Vectorized calculations**: Leverage Polars' columnar operations
3. **Avoid loops**: Use DataFrame operations instead of iterating
4. **Cache results**: Store calculated indicators for reuse
5. **Use appropriate periods**: Balance accuracy vs noise

Best Practices
--------------

1. **Validate data**: Check for None/empty DataFrames
2. **Handle edge cases**: Insufficient data for indicator calculations
3. **Normalize inputs**: Ensure consistent data types
4. **Test thoroughly**: Validate indicators against known implementations
5. **Document parameters**: Clear descriptions of indicator settings

Next Steps
----------

- :doc:`../api/indicators` - Complete indicator API reference
- :doc:`../examples/trading_strategies` - Strategy examples
- :doc:`trading` - Executing trades based on signals