Trading Guide
=============

Complete guide to order placement, position management, and risk control.

Order Management
----------------

Basic Order Types
~~~~~~~~~~~~~~~~~

.. code-block:: python

   from project_x_py import TradingSuite
   import asyncio

   async def place_orders():
       suite = await TradingSuite.create("MNQ")
       
       # Market order
       market_order = await suite.orders.place_market_order(
           contract_id=suite.instrument_id,
           side=0,  # 0=Buy, 1=Sell
           size=1
       )
       
       # Limit order
       current_price = await suite.data.get_current_price()
       limit_order = await suite.orders.place_limit_order(
           contract_id=suite.instrument_id,
           side=0,
           size=1,
           limit_price=current_price - 10  # Buy 10 points below market
       )
       
       # Stop order
       stop_order = await suite.orders.place_stop_order(
           contract_id=suite.instrument_id,
           side=1,  # Sell
           size=1,
           stop_price=current_price - 20  # Stop loss 20 points below
       )
       
       await suite.disconnect()

   asyncio.run(place_orders())

Bracket Orders
~~~~~~~~~~~~~~

Place entry, stop loss, and take profit in one operation:

.. code-block:: python

   async def place_bracket_order():
       suite = await TradingSuite.create("ES")
       
       current_price = await suite.data.get_current_price()
       
       # Bracket order with OCO (One-Cancels-Other)
       bracket = await suite.orders.place_bracket_order(
           contract_id=suite.instrument_id,
           side=0,  # Buy
           size=1,
           entry_price=current_price - 2,      # Entry below market
           stop_loss_price=current_price - 10, # Risk 8 points
           take_profit_price=current_price + 10 # Target 12 points
       )
       
       if bracket.success:
           print(f"Bracket order placed: {bracket}")
           print(f"Entry ID: {bracket.entry_order_id}")
           print(f"Stop ID: {bracket.stop_order_id}")
           print(f"Target ID: {bracket.limit_order_id}")

Order Modification
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def modify_orders():
       suite = await TradingSuite.create("MNQ")
       
       # Get open orders
       orders = await suite.orders.search_open_orders()
       
       for order in orders:
           if order.type == 1:  # Limit order
               # Modify price
               result = await suite.orders.modify_order(
                   order_id=order.id,
                   new_price=order.limit_price + 5
               )
               print(f"Modified order {order.id}: {result}")

Order Cancellation
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def cancel_orders():
       suite = await TradingSuite.create("MNQ")
       
       # Cancel specific order
       result = await suite.orders.cancel_order(order_id=12345)
       
       # Cancel all orders for instrument
       orders = await suite.orders.search_open_orders()
       for order in orders:
           if order.contract_id == suite.instrument_id:
               await suite.orders.cancel_order(order.id)

Position Management
-------------------

Tracking Positions
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def monitor_positions():
       suite = await TradingSuite.create("MNQ")
       
       # Get all positions
       positions = await suite.positions.get_all_positions()
       
       for position in positions:
           direction = "LONG" if position.is_long else "SHORT"
           pnl = position.unrealized_pnl
           
           print(f"{position.contract_id}:")
           print(f"  Direction: {direction}")
           print(f"  Size: {position.size}")
           print(f"  Avg Price: ${position.average_price:,.2f}")
           print(f"  P&L: ${pnl:,.2f}")
           
       # Get specific position
       mnq_position = await suite.positions.get_position("MNQ")
       if mnq_position:
           print(f"MNQ position: {mnq_position.size} @ ${mnq_position.average_price}")

Portfolio Analytics
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def portfolio_analysis():
       suite = await TradingSuite.create("MNQ")
       
       # Portfolio P&L
       portfolio = await suite.positions.get_portfolio_pnl()
       print(f"Total P&L: ${portfolio['total_pnl']:,.2f}")
       print(f"Open P&L: ${portfolio['unrealized_pnl']:,.2f}")
       print(f"Closed P&L: ${portfolio['realized_pnl']:,.2f}")
       print(f"Position count: {portfolio['position_count']}")
       
       # Performance metrics
       metrics = await suite.positions.get_performance_metrics()
       print(f"Win rate: {metrics['win_rate']:.1%}")
       print(f"Profit factor: {metrics['profit_factor']:.2f}")
       print(f"Average win: ${metrics['avg_win']:,.2f}")
       print(f"Average loss: ${metrics['avg_loss']:,.2f}")

Position Closing
~~~~~~~~~~~~~~~~

.. code-block:: python

   async def close_positions():
       suite = await TradingSuite.create("MNQ")
       
       # Close specific position
       await suite.positions.close_position("MNQ")
       
       # Close all positions
       await suite.positions.close_all_positions()
       
       # Partial close
       position = await suite.positions.get_position("ES")
       if position and position.size > 1:
           await suite.orders.place_market_order(
               contract_id="ES",
               side=1 if position.is_long else 0,  # Opposite side
               size=1  # Close 1 contract
           )

Risk Management
---------------

Using ManagedTrade (v3.1.11+)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def risk_managed_trade():
       suite = await TradingSuite.create(
           "MNQ",
           features=["risk_manager"]
       )
       
       current_price = await suite.data.get_current_price()
       
       # Managed trade with automatic risk control
       async with suite.managed_trade(max_risk_percent=0.01) as trade:
           # Entry price fetched automatically if not provided
           result = await trade.enter_long(
               stop_loss=current_price - 50,
               take_profit=current_price + 100
           )
           
           print(f"Trade entered: {result}")
           
           # Optional: Adjust stop to breakeven
           if result['position']:
               await trade.adjust_stop(current_price)
       
       # Automatic cleanup on exit
       await suite.disconnect()

Position Sizing
~~~~~~~~~~~~~~~

.. code-block:: python

   async def calculate_position_size():
       suite = await TradingSuite.create(
           "MNQ",
           features=["risk_manager"]
       )
       
       account = suite.client.account_info
       risk_amount = account.balance * 0.01  # Risk 1% of account
       
       current_price = await suite.data.get_current_price()
       stop_loss = current_price - 50
       
       # Calculate position size based on risk
       risk_per_contract = abs(current_price - stop_loss)
       position_size = int(risk_amount / risk_per_contract)
       
       print(f"Account: ${account.balance:,.2f}")
       print(f"Risk amount: ${risk_amount:,.2f}")
       print(f"Position size: {position_size} contracts")

Advanced Features
-----------------

OCO Orders
~~~~~~~~~~

.. code-block:: python

   async def place_oco_orders():
       suite = await TradingSuite.create("ES")
       
       current_price = await suite.data.get_current_price()
       
       # One-Cancels-Other: Stop loss and take profit
       oco = await suite.orders.place_oco_order(
           contract_id=suite.instrument_id,
           stop_price=current_price - 20,    # Stop loss
           stop_size=1,
           limit_price=current_price + 30,   # Take profit
           limit_size=1
       )
       
       print(f"OCO placed: {oco}")

Trailing Stops
~~~~~~~~~~~~~~

.. code-block:: python

   async def trailing_stop():
       suite = await TradingSuite.create("MNQ")
       
       # Monitor position and adjust stop
       position = await suite.positions.get_position("MNQ")
       if position and position.is_long:
           current_price = await suite.data.get_current_price()
           trail_distance = 20  # Points
           
           # Find existing stop order
           orders = await suite.orders.search_open_orders()
           stop_order = next(
               (o for o in orders 
                if o.type == 3 and o.contract_id == suite.instrument_id),
               None
           )
           
           if stop_order:
               new_stop = current_price - trail_distance
               if new_stop > stop_order.stop_price:
                   # Trail the stop up
                   await suite.orders.modify_order(
                       order_id=stop_order.id,
                       new_price=new_stop
                   )

Order Templates
~~~~~~~~~~~~~~~

.. code-block:: python

   from project_x_py import OrderTemplate

   async def use_templates():
       suite = await TradingSuite.create("MNQ")
       
       # Create reusable templates
       scalp_template = OrderTemplate(
           side=0,
           size=2,
           order_type="limit",
           offset_points=2  # Enter 2 points from market
       )
       
       # Use template
       current_price = await suite.data.get_current_price()
       order = await suite.orders.place_order_from_template(
           template=scalp_template,
           contract_id=suite.instrument_id,
           base_price=current_price
       )

Event-Driven Trading
--------------------

.. code-block:: python

   from project_x_py import EventType

   async def event_trading():
       suite = await TradingSuite.create("ES")
       
       # React to order fills
       async def on_order_fill(event):
           order = event.data
           print(f"Order filled: {order['id']} at ${order['filled_price']}")
           
           # Place stop loss after fill
           if order['side'] == 0:  # Buy filled
               await suite.orders.place_stop_order(
                   contract_id=order['contract_id'],
                   side=1,
                   size=order['size'],
                   stop_price=order['filled_price'] - 10
               )
       
       await suite.on(EventType.ORDER_FILLED, on_order_fill)
       
       # React to position changes
       async def on_position_update(event):
           position = event.data
           print(f"Position updated: {position['size']} @ ${position['average_price']}")
       
       await suite.on(EventType.POSITION_UPDATE, on_position_update)

Best Practices
--------------

1. **Always use stop losses**: Protect capital with proper risk management
2. **Check order status**: Verify fills before assuming position
3. **Handle partial fills**: Orders may fill in multiple parts
4. **Monitor margin**: Ensure sufficient margin before placing orders
5. **Test with small sizes**: Start with minimum position sizes
6. **Use paper trading**: Test strategies in simulation first

Next Steps
----------

- :doc:`real_time` - Real-time data and events
- :doc:`analysis` - Technical analysis tools
- :doc:`../api/trading` - Complete API reference