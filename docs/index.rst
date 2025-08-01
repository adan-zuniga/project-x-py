project-x-py Documentation
==========================

.. image:: https://img.shields.io/pypi/v/project-x-py.svg
   :target: https://pypi.org/project/project-x-py/
   :alt: PyPI version

.. image:: https://img.shields.io/pypi/pyversions/project-x-py.svg
   :target: https://pypi.org/project/project-x-py/
   :alt: Python versions

.. image:: https://img.shields.io/github/license/TexasCoding/project-x-py.svg
   :target: https://github.com/TexasCoding/project-x-py/blob/main/LICENSE
   :alt: License

.. image:: https://readthedocs.org/projects/project-x-py/badge/?version=latest
   :target: https://project-x-py.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

**project-x-py** is a high-performance **async Python SDK** for the `ProjectX Trading Platform <https://www.projectx.com/>`_ Gateway API. This library enables developers to build sophisticated trading strategies and applications by providing comprehensive async access to futures trading operations, real-time market data, Level 2 orderbook analysis, and a complete technical analysis suite with 55+ TA-Lib compatible indicators.

.. note::
   **Version 2.0.0**: Complete async-first rewrite. All APIs now require ``async/await`` for better performance and concurrent operations.

.. warning::
   **Development Phase**: This project is under active development. New updates may introduce breaking changes without backward compatibility. During this development phase, we prioritize clean, modern code architecture over maintaining legacy implementations.

.. note::
   **Important**: This is a **client library/SDK**, not a trading strategy. It provides the tools and infrastructure to help developers create their own trading strategies that integrate with the ProjectX platform.

Quick Start
-----------

Install the package::

   uv add project-x-py

Or with pip::

   pip install project-x-py

Set up your credentials::

   export PROJECT_X_API_KEY='your_api_key'
   export PROJECT_X_USERNAME='your_username'

Start trading::

   import asyncio
   from project_x_py import ProjectX
   from project_x_py.indicators import RSI, SMA, MACD
   
   async def main():
       # Create client with async context manager
       async with ProjectX.from_env() as client:
           await client.authenticate()
           
           # Get market data with technical analysis
           data = await client.get_bars('MGC', days=30, interval=60)
           data = RSI(data, period=14)         # Add RSI
           data = SMA(data, period=20)         # Add moving average
           data = MACD(data)                   # Add MACD
           
           # Place an order
           from project_x_py import create_order_manager, create_realtime_client
           instrument = await client.get_instrument('MGC')
           realtime_client = create_realtime_client(client.session_token)
           order_manager = create_order_manager(client, realtime_client)
           response = await order_manager.place_limit_order(
               contract_id=instrument.id, 
               side=0, 
               size=1, 
               limit_price=2050.0
           )
   
   # Run the async function
   asyncio.run(main())

Key Features
------------

🚀 **Core Trading Features**
   * Complete order management (market, limit, stop, bracket orders)
   * Real-time position tracking and portfolio management
   * Advanced risk management and position sizing
   * Multi-account support

📊 **Market Data & Analysis**
   * Async historical OHLCV data with multiple timeframes
   * Real-time market data feeds via async WebSocket
   * **Level 2 orderbook analysis** with institutional-grade features
   * **55+ Technical Indicators** with TA-Lib compatibility (RSI, MACD, Bollinger Bands, etc.)
   * **Advanced market microstructure** analysis (iceberg detection, order flow, volume profile)

🔧 **Developer Tools**
   * Comprehensive Python typing support
   * Extensive examples and tutorials
   * Built-in logging and debugging tools
   * Flexible configuration management

⚡ **Real-time Capabilities**
   * Async live market data streaming
   * Real-time order and position updates
   * Async event-driven architecture
   * WebSocket-based connections with async handlers

Table of Contents
-----------------

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   installation
   quickstart
   authentication
   configuration

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   user_guide/client
   user_guide/market_data
   user_guide/trading
   user_guide/real_time
   user_guide/analysis

.. toctree::
   :maxdepth: 2
   :caption: Examples

   examples/basic_usage
   examples/trading_strategies
   examples/real_time_data
   examples/portfolio_management

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/client
   api/trading
   api/data
   api/orderbook
   api/indicators
   api/models
   api/utilities

Indices and Search
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. toctree::
   :maxdepth: 2
   :caption: Advanced Topics

   advanced/architecture
   advanced/performance
   advanced/debugging
   advanced/contributing

.. toctree::
   :maxdepth: 1
   :caption: Additional Information

   changelog
   license
   support

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search` 