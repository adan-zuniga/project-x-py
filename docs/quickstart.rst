Quick Start Guide
=================

Get up and running with the ProjectX Python SDK in minutes to start building your trading applications.

Prerequisites
-------------

Before you begin, make sure you have:

1. Python 3.12 or higher installed
2. project-x-py package installed (see :doc:`installation`)
3. TopStepX account with API access
4. Your API credentials (username and API key)

Step 1: Set Up Credentials
---------------------------

Set your API credentials as environment variables::

   export PROJECT_X_API_KEY='your_api_key_here'
   export PROJECT_X_USERNAME='your_username_here'

On Windows::

   set PROJECT_X_API_KEY=your_api_key_here
   set PROJECT_X_USERNAME=your_username_here

Or create a ``.env`` file in your project directory::

   PROJECT_X_API_KEY=your_api_key_here
   PROJECT_X_USERNAME=your_username_here

Step 2: Create Your First Client
---------------------------------

.. code-block:: python

   import asyncio
   from project_x_py import ProjectX

   async def main():
       # Create client using environment variables
       async with ProjectX.from_env() as client:
           # Authenticate
           await client.authenticate()
           
           # Get account information
           print(f"Account: {client.account_info.name}")
           print(f"Balance: ${client.account_info.balance:,.2f}")

   # Run the async function
   asyncio.run(main())

Step 3: Get Market Data
-----------------------

.. code-block:: python

   async def get_market_data():
       async with ProjectX.from_env() as client:
           await client.authenticate()
           
           # Get historical data for Micro E-mini NASDAQ futures (V3: actual symbol)
           data = await client.get_bars('MNQ', days=5, interval=15)
           print(f"Retrieved {len(data)} bars of data")
           print(data.head())

           # Search for instruments
           instruments = await client.search_instruments('MNQ')
           for instrument in instruments:
               print(f"{instrument.name}: {instrument.description}")

   asyncio.run(get_market_data())

Step 4: Place Your First Order
-------------------------------

.. warning::
   The following examples place real orders! Make sure you're using a demo account for testing.

.. code-block:: python

   from project_x_py import TradingSuite

   async def place_order():
       # V3.1: Use TradingSuite for simplified initialization
       suite = await TradingSuite.create("MNQ")
       
       # Place a limit order using the integrated order manager
       response = await suite.orders.place_limit_order(
           contract_id=suite.instrument.id,  # Use pre-loaded instrument ID
           side=0,                     # 0=Buy, 1=Sell
           size=1,                     # 1 contract
           limit_price=21050.0         # Limit price
       )

       if response.success:
           print(f"Order placed! Order ID: {response.orderId}")
       else:
           print(f"Order failed: {response}")
       
       await suite.disconnect()

   asyncio.run(place_order())

Step 5: Monitor Positions
-------------------------

.. code-block:: python

   from project_x_py import TradingSuite

   async def monitor_positions():
       # V3.1: Use TradingSuite for all components
       suite = await TradingSuite.create("MNQ")
       
       # Get all open positions using integrated position manager
       positions = await suite.positions.get_all_positions()
       for position in positions:
           direction = "LONG" if position.side == 0 else "SHORT"
           print(f"{position.contract_id}: {direction} {position.size} @ ${position.average_price:.2f}")

       # Get portfolio metrics
       portfolio = await suite.positions.get_portfolio_pnl()
       print(f"Total positions: {portfolio['position_count']}")
       
       await suite.disconnect()

   asyncio.run(monitor_positions())

Step 6: Real-time Data (Optional)
----------------------------------

.. code-block:: python

   from project_x_py import TradingSuite, EventType

   async def setup_realtime():
       # V3.1: Use TradingSuite for complete setup
       suite = await TradingSuite.create(
           instrument='MNQ',
           timeframes=['1min', '5min', '15min']
       )

       # Register event handlers via integrated EventBus
       @suite.events.on(EventType.NEW_BAR)
       async def on_new_bar(event):
           print(f"New bar: {event.data['timeframe']} - {event.data['close']}")

       # Access live data (automatically initialized)
       live_data = await suite.data.get_data('5min')
       print(f"Live data: {len(live_data)} bars")
       
       # Keep running for 60 seconds to collect data
       await asyncio.sleep(60)
       await suite.disconnect()

   asyncio.run(setup_realtime())

Common Patterns
---------------

Basic Trading Workflow
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from project_x_py import ProjectX, create_order_manager, create_position_manager, create_realtime_client

   async def trading_workflow():
       # 1. Initialize client
       async with ProjectX.from_env() as client:
           await client.authenticate()
           
           # Get instrument details
           instrument = await client.get_instrument('MNQ')  # V3: actual symbol
           
           # 2. V3: Set up trading managers with JWT and account ID
           realtime_client = await create_realtime_client(
               jwt_token=client.jwt_token,
               account_id=str(client.account_id)
           )
           order_manager = create_order_manager(client, realtime_client)
           position_manager = create_position_manager(client, realtime_client)

           # 3. Check account status
           print(f"Account balance: ${client.account_info.balance:,.2f}")

           # 4. Get market data
           data = await client.get_bars('MNQ', days=1, interval=5)  # V3: actual symbol
           current_price = float(data.select('close').tail(1).item())

           # 5. Place bracket order (entry + stop + target)
           bracket = await order_manager.place_bracket_order(
               contract_id=instrument.id,
               side=0,                    # Buy
               size=1,
               entry_price=current_price - 5.0,   # Entry below market
               stop_loss_price=current_price - 10.0,  # $5 risk
               take_profit_price=current_price + 5.0  # $10 profit target
           )

           if bracket.success:
               print("Bracket order placed successfully!")

   asyncio.run(trading_workflow())

Market Analysis with Technical Indicators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from project_x_py.indicators import RSI, SMA, BBANDS, MACD

   async def analyze_market():
       async with ProjectX.from_env() as client:
           await client.authenticate()
           
           # Get data
           data = await client.get_bars('MNQ', days=30, interval=60)  # V3: actual symbol

           # Calculate technical indicators using TA-Lib style functions
           data = RSI(data, period=14)
           data = SMA(data, period=20)
           data = SMA(data, period=50)
           data = BBANDS(data, period=20, std_dev=2.0)
           data = MACD(data, fast_period=12, slow_period=26, signal_period=9)

           # Check latest values
           latest = data.tail(1)
           print(f"Current RSI: {latest['rsi_14'].item():.2f}")
           print(f"Price: ${latest['close'].item():.2f}")
           print(f"SMA(20): ${latest['sma_20'].item():.2f}")
           print(f"SMA(50): ${latest['sma_50'].item():.2f}")
           print(f"MACD: {latest['macd'].item():.4f}")

           # Simple signal logic
           rsi_val = latest['rsi_14'].item()
           price = latest['close'].item()
           sma_20 = latest['sma_20'].item()
           sma_50 = latest['sma_50'].item()
           
           if rsi_val < 30 and price > sma_20 > sma_50:
               print("🟢 Potential BUY signal: Oversold RSI + Uptrend")
           elif rsi_val > 70 and price < sma_20 < sma_50:
               print("🔴 Potential SELL signal: Overbought RSI + Downtrend")

   asyncio.run(analyze_market())

Error Handling
~~~~~~~~~~~~~~

.. code-block:: python

   from project_x_py import ProjectXError, ProjectXOrderError

   async def place_order_with_error_handling():
       try:
           async with ProjectX.from_env() as client:
               await client.authenticate()
               
               instrument = await client.get_instrument('MNQ')  # V3: actual symbol
               # V3: Create realtime client with JWT
               realtime_client = await create_realtime_client(
                   jwt_token=client.jwt_token,
                   account_id=str(client.account_id)
               )
               order_manager = create_order_manager(client, realtime_client)
               
               # Attempt to place order
               response = await order_manager.place_limit_order(
                   contract_id=instrument.id, 
                   side=0, 
                   size=1, 
                   limit_price=21050.0  # V3: realistic MNQ price
               )
               
       except ProjectXOrderError as e:
           print(f"Order error: {e}")
           
       except ProjectXError as e:
           print(f"API error: {e}")
           
       except Exception as e:
           print(f"Unexpected error: {e}")

   asyncio.run(place_order_with_error_handling())

Next Steps
----------

Now that you have the basics working:

1. **Technical Analysis**: Explore the :doc:`comprehensive indicators library <api/indicators>` (55+ TA-Lib compatible indicators)
2. **Learn the API**: Explore the :doc:`API reference <api/client>`
3. **Study Examples**: Check out :doc:`detailed examples <examples/basic_usage>`
4. **Configure Advanced Features**: See :doc:`configuration options <configuration>`
5. **Real-time Trading**: Learn about :doc:`real-time capabilities <user_guide/real_time>`
6. **Risk Management**: Read about :doc:`position management <user_guide/trading>`

Tips for Success
----------------

1. **Start with Demo**: Always test with a simulated account first
2. **Small Sizes**: Use minimal position sizes while learning
3. **Error Handling**: Always wrap API calls in try/catch blocks
4. **Rate Limits**: Be mindful of API rate limits
5. **Logging**: Enable debug logging during development::

      from project_x_py import setup_logging
      setup_logging(level='DEBUG')

Getting Help
------------

If you run into issues:

* Check the :doc:`troubleshooting section <installation>`
* Browse the :doc:`examples directory <examples/basic_usage>`
* Review the :doc:`API documentation <api/client>`
* Open an issue on `GitHub <https://github.com/TexasCoding/project-x-py/issues>`_ 