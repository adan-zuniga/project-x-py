# ProjectX Python SDK

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Performance](https://img.shields.io/badge/performance-optimized-brightgreen.svg)](#performance-optimizations)
[![Async](https://img.shields.io/badge/async-native-brightgreen.svg)](#async-architecture)

A **high-performance async Python SDK** for the [ProjectX Trading Platform](https://www.projectx.com/) Gateway API. This library enables developers to build sophisticated trading strategies and applications by providing comprehensive async access to futures trading operations, historical market data, real-time streaming, technical analysis, and advanced market microstructure tools with enterprise-grade performance optimizations.

> **Note**: This is a **client library/SDK**, not a trading strategy. It provides the tools and infrastructure to help developers create their own trading strategies that integrate with the ProjectX platform.

## 🎯 What is ProjectX?

[ProjectX](https://www.projectx.com/) is a cutting-edge web-based futures trading platform that provides:
- **TradingView Charts**: Advanced charting with hundreds of indicators
- **Risk Controls**: Auto-liquidation, profit targets, daily loss limits
- **Unfiltered Market Data**: Real-time depth of market data with millisecond updates
- **REST API**: Comprehensive API for custom integrations
- **Mobile & Web Trading**: Native browser-based trading platform

This Python SDK acts as a bridge between your trading strategies and the ProjectX platform, handling all the complex API interactions, data processing, and real-time connectivity.

## 🚀 v2.0.2 - Async-First Architecture with Enhanced Indicators

**BREAKING CHANGE**: Version 2.0.0 is a complete rewrite with async-only architecture. All synchronous APIs have been removed in favor of high-performance async implementations.

### Why Async?

- **Concurrent Operations**: Execute multiple API calls simultaneously
- **Non-blocking I/O**: Handle real-time data feeds without blocking
- **Better Resource Usage**: Single thread handles thousands of concurrent operations
- **WebSocket Native**: Perfect for real-time trading applications
- **Modern Python**: Leverages Python 3.12+ async features

### Migration from v1.x

If you're upgrading from v1.x, all APIs now require `async/await`:

```python
# Old (v1.x)
client = ProjectX.from_env()
data = client.get_bars("MGC", days=5)

# New (v2.0.0)
async with ProjectX.from_env() as client:
    await client.authenticate()
    data = await client.get_bars("MGC", days=5)
```

## ✨ Key Features

### Core Trading Operations (All Async)
- **Authentication & Account Management**: Multi-account support with async session management
- **Order Management**: Place, modify, cancel orders with real-time async updates
- **Position Tracking**: Real-time position monitoring with P&L calculations
- **Market Data**: Historical and real-time data with async streaming
- **Risk Management**: Portfolio analytics and risk metrics

### Advanced Features
- **58+ Technical Indicators**: Full TA-Lib compatibility with Polars optimization including new pattern indicators
- **Level 2 OrderBook**: Depth analysis, iceberg detection, market microstructure
- **Real-time WebSockets**: Async streaming for quotes, trades, and account updates
- **Performance Optimized**: Connection pooling, intelligent caching, memory management
- **Pattern Recognition**: Fair Value Gaps, Order Blocks, and Waddah Attar Explosion indicators

## 📦 Installation

### Using UV (Recommended)
```bash
uv add project-x-py
```

### Using pip
```bash
pip install project-x-py
```

### Development Installation
```bash
git clone https://github.com/yourusername/project-x-py.git
cd project-x-py
uv sync  # or: pip install -e ".[dev]"
```

## 🚀 Quick Start

### Basic Usage

```python
import asyncio
from project_x_py import ProjectX

async def main():
    # Create client using environment variables
    async with ProjectX.from_env() as client:
        # Authenticate
        await client.authenticate()
        print(f"Connected to account: {client.account_info.name}")
        
        # Get instrument
        instrument = await client.get_instrument("MGC")
        print(f"Trading {instrument.name} - Tick size: ${instrument.tickSize}")
        
        # Get historical data
        data = await client.get_bars("MGC", days=5, interval=15)
        print(f"Retrieved {len(data)} bars")
        
        # Get positions
        positions = await client.get_positions()
        for position in positions:
            print(f"Position: {position.size} @ ${position.averagePrice}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Real-time Trading Suite

```python
import asyncio
from project_x_py import ProjectX, create_trading_suite

async def on_tick(tick_data):
    print(f"Price: ${tick_data['price']}")

async def main():
    async with ProjectX.from_env() as client:
        await client.authenticate()
        
        # Create complete trading suite
        suite = await create_trading_suite(
            instrument="MNQ",
            project_x=client,
            timeframes=["1min", "5min", "15min"]
        )
        
        # Connect real-time services
        await suite["realtime_client"].connect()
        await suite["data_manager"].initialize(initial_days=5)
        
        # Subscribe to real-time data
        suite["data_manager"].add_tick_callback(on_tick)
        await suite["data_manager"].start_realtime_feed()
        
        # Place a bracket order
        response = await suite["order_manager"].place_bracket_order(
            contract_id=instrument.id,
            side=0,  # Buy
            size=1,
            entry_price=current_price,
            stop_loss_price=current_price - 10,
            take_profit_price=current_price + 15
        )
        
        print(f"Order placed: {response}")
        
        # Monitor for 60 seconds
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
```

## 📚 Documentation

### Authentication

Set environment variables:
```bash
export PROJECT_X_API_KEY="your_api_key"
export PROJECT_X_USERNAME="your_username"
```

Or use a config file (`~/.config/projectx/config.json`):
```json
{
    "api_key": "your_api_key",
    "username": "your_username",
    "api_url": "https://api.topstepx.com/api",
    "websocket_url": "wss://api.topstepx.com",
    "timezone": "US/Central"
}
```

### Component Overview

#### ProjectX Client
The main async client for API operations:
```python
async with ProjectX.from_env() as client:
    await client.authenticate()
    # Use client for API operations
```

#### OrderManager
Async order lifecycle management:
```python
order_manager = suite["order_manager"]
await order_manager.place_market_order(contract_id, side=0, size=1)
await order_manager.modify_order(order_id, new_price=100.50)
await order_manager.cancel_order(order_id)
```

#### PositionManager
Async position tracking and analytics:
```python
position_manager = suite["position_manager"]
positions = await position_manager.get_all_positions()
pnl = await position_manager.get_portfolio_pnl()
await position_manager.close_position(contract_id)
```

#### RealtimeDataManager
Async multi-timeframe data management:
```python
data_manager = suite["data_manager"]
await data_manager.initialize(initial_days=5)
data = await data_manager.get_data("15min")
current_price = await data_manager.get_current_price()
```

#### OrderBook
Async Level 2 market depth analysis:
```python
orderbook = suite["orderbook"]
spread = await orderbook.get_bid_ask_spread()
imbalance = await orderbook.get_market_imbalance()
icebergs = await orderbook.detect_iceberg_orders()
```

### Technical Indicators

All 58+ indicators work with async data pipelines:
```python
import polars as pl
from project_x_py.indicators import RSI, SMA, MACD, FVG, ORDERBLOCK, WAE

# Get data
data = await client.get_bars("ES", days=30)

# Apply traditional indicators
data = data.pipe(SMA, period=20).pipe(RSI, period=14)

# Apply pattern recognition indicators
data_with_fvg = FVG(data, min_gap_size=0.001, check_mitigation=True)
data_with_ob = ORDERBLOCK(data, min_volume_percentile=70)
data_with_wae = WAE(data, sensitivity=150)

# Or use class-based interface
from project_x_py.indicators import OrderBlock, FVG, WAE
ob = OrderBlock()
data_with_ob = ob.calculate(data, use_wicks=True)
```

#### New Pattern Indicators (v2.0.2)
- **Fair Value Gap (FVG)**: Identifies price imbalance areas
- **Order Block**: Detects institutional order zones
- **Waddah Attar Explosion (WAE)**: Strong trend and breakout detection

## 🏗️ Examples

The `examples/` directory contains comprehensive async examples:

1. **01_basic_client_connection.py** - Async authentication and basic operations
2. **02_order_management.py** - Async order placement and management
3. **03_position_management.py** - Async position tracking and P&L
4. **04_realtime_data.py** - Real-time async data streaming
5. **05_orderbook_analysis.py** - Async market depth analysis
6. **06_multi_timeframe_strategy.py** - Async multi-timeframe trading
7. **07_technical_indicators.py** - Using indicators with async data
8. **08_order_and_position_tracking.py** - Integrated async monitoring
9. **09_get_check_available_instruments.py** - Interactive async instrument search

## 🔧 Configuration

### ProjectXConfig Options

```python
from project_x_py import ProjectXConfig

config = ProjectXConfig(
    api_url="https://api.topstepx.com/api",
    websocket_url="wss://api.topstepx.com",
    timeout_seconds=30.0,
    retry_attempts=3,
    timezone="US/Central"
)
```

### Performance Tuning

Configure caching and memory limits:
```python
# In OrderBook
orderbook = OrderBook(
    instrument="ES",
    max_trades=10000,  # Trade history limit
    max_depth_entries=1000,  # Depth per side
    cache_ttl=300  # 5 minutes
)

# In RealtimeDataManager
data_manager = RealtimeDataManager(
    instrument="NQ",
    max_bars_per_timeframe=1000,
    tick_buffer_size=1000
)
```

## 🔍 Error Handling

All async operations use typed exceptions:

```python
from project_x_py.exceptions import (
    ProjectXAuthenticationError,
    ProjectXOrderError,
    ProjectXRateLimitError
)

try:
    async with ProjectX.from_env() as client:
        await client.authenticate()
except ProjectXAuthenticationError as e:
    print(f"Authentication failed: {e}")
except ProjectXRateLimitError as e:
    print(f"Rate limit exceeded: {e}")
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup
```bash
# Clone repository
git clone https://github.com/yourusername/project-x-py.git
cd project-x-py

# Install with dev dependencies
uv sync

# Run tests
uv run pytest

# Format code
uv run ruff format .

# Lint
uv run ruff check .
```

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## 🔗 Resources

- [ProjectX Platform](https://www.projectx.com/)
- [API Documentation](https://documenter.getpostman.com/view/24500417/2s9YRCXrKF)
- [GitHub Repository](https://github.com/yourusername/project-x-py)
- [PyPI Package](https://pypi.org/project/project-x-py/)

## ⚠️ Disclaimer

This SDK is for educational and development purposes. Trading futures involves substantial risk of loss and is not suitable for all investors. Past performance is not indicative of future results. Always test your strategies thoroughly before using real funds.