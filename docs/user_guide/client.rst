Client Usage Guide
==================

The ProjectX client is the core component for interacting with the TopStepX API.

Overview
--------

The ``ProjectX`` client provides async access to all API endpoints and manages authentication, session handling, and connection pooling.

Creating a Client
-----------------

Using Environment Variables (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import asyncio
   from project_x_py import ProjectX

   async def main():
       async with ProjectX.from_env() as client:
           await client.authenticate()
           print(f"Connected: {client.account_info.name}")

   asyncio.run(main())

Direct Instantiation
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async def main():
       async with ProjectX(
           username="your_username",
           api_key="your_api_key"
       ) as client:
           await client.authenticate()
           # Use client

Using TradingSuite (Simplified)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from project_x_py import TradingSuite

   async def main():
       # TradingSuite handles client creation and authentication
       suite = await TradingSuite.create("MNQ")
       
       # Access client through suite
       account = suite.client.account_info
       print(f"Account: {account.name}")
       
       await suite.disconnect()

   asyncio.run(main())

Core Operations
---------------

Account Information
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   async with ProjectX.from_env() as client:
       await client.authenticate()
       
       # Get account info
       account = client.account_info
       print(f"Balance: ${account.balance:,.2f}")
       print(f"Can Trade: {account.can_trade}")
       
       # List all accounts
       accounts = await client.list_accounts()
       for acc in accounts:
           print(f"{acc.name}: ${acc.balance:,.2f}")

Instrument Search
~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Search for instruments
   instruments = await client.search_instruments("MNQ")
   for inst in instruments:
       print(f"{inst.name}: {inst.description}")
       print(f"  Tick size: {inst.tick_size}")
       print(f"  Contract ID: {inst.id}")
   
   # Get specific instrument
   mnq = await client.get_instrument("MNQ")
   print(f"MNQ Contract: {mnq.id}")

Market Data
~~~~~~~~~~~

.. code-block:: python

   # Get historical bars
   data = await client.get_bars("MNQ", days=5, interval=15)
   print(f"Retrieved {len(data)} bars")
   
   # With specific time range (v3.1.5+)
   from datetime import datetime
   
   start = datetime(2025, 1, 1, 9, 30)
   end = datetime(2025, 1, 10, 16, 0)
   data = await client.get_bars(
       "MNQ", 
       start_time=start, 
       end_time=end,
       interval=60
   )

Performance Features
--------------------

Connection Pooling
~~~~~~~~~~~~~~~~~~

The client automatically manages HTTP connection pooling for optimal performance:

- Reuses connections across requests
- Automatic retry on network failures
- Configurable timeout and retry settings

Caching
~~~~~~~

Intelligent caching reduces API calls:

- Instrument data cached for session
- Account information cached with TTL
- Cache invalidation on updates

JWT Token Management
~~~~~~~~~~~~~~~~~~~~

Automatic token handling:

- Token refresh at 80% lifetime
- Seamless re-authentication
- No manual token management needed

Error Handling
--------------

.. code-block:: python

   from project_x_py import (
       ProjectXAuthenticationError,
       ProjectXOrderError,
       ProjectXRateLimitError
   )

   try:
       async with ProjectX.from_env() as client:
           await client.authenticate()
           # Operations
           
   except ProjectXAuthenticationError as e:
       print(f"Auth failed: {e}")
   except ProjectXRateLimitError as e:
       print(f"Rate limited: {e}")
   except Exception as e:
       print(f"Unexpected error: {e}")

Configuration
-------------

.. code-block:: python

   from project_x_py import ProjectXConfig

   config = ProjectXConfig(
       api_url="https://api.topstepx.com/api",
       websocket_url="wss://api.topstepx.com",
       timeout_seconds=30,
       retry_attempts=3,
       max_connections=10,
       cache_ttl=300
   )

   async with ProjectX.from_env(config=config) as client:
       await client.authenticate()

Best Practices
--------------

1. **Always use context managers**: Ensures proper cleanup
2. **Handle authentication errors**: Check credentials on failure
3. **Monitor rate limits**: Implement backoff strategies
4. **Enable logging for debugging**: Use ``setup_logging()``
5. **Cache frequently used data**: Reduce API calls

Advanced Usage
--------------

Custom Headers
~~~~~~~~~~~~~~

.. code-block:: python

   client = ProjectX.from_env()
   client.session.headers.update({
       "X-Custom-Header": "value"
   })

Health Checks
~~~~~~~~~~~~~

.. code-block:: python

   health = await client.get_health_status()
   print(f"API Status: {health['status']}")
   print(f"Authenticated: {health['authenticated']}")

Performance Stats
~~~~~~~~~~~~~~~~~

.. code-block:: python

   stats = await client.get_performance_stats()
   print(f"API Calls: {stats['api_calls']}")
   print(f"Cache Hits: {stats['cache_hits']}")
   print(f"Avg Response Time: {stats['avg_response_ms']}ms")

Next Steps
----------

- :doc:`market_data` - Working with market data
- :doc:`trading` - Order and position management
- :doc:`real_time` - Real-time data streaming
- :doc:`analysis` - Technical analysis tools