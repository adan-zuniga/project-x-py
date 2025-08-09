# ProjectX Python SDK Examples (v3.1.0)

This directory contains comprehensive working examples demonstrating all major features of the ProjectX Python SDK v3.1.0. All examples use **MNQ (Micro E-mini NASDAQ)** contracts to minimize risk during testing.

**Note:** Version 3.1.0 includes significant performance improvements with memory-mapped overflow storage, orjson integration, and WebSocket batching for 2-5x performance gains.

## ⚠️ Important Safety Notice

**These examples place REAL ORDERS on the market!**
- Only use with simulated/demo accounts
- MNQ micro contracts are used to reduce risk
- Always monitor positions closely
- Examples include safety confirmations before placing orders

## Quick Start

Use the provided `test.sh` script which sets the required environment variables:

```bash
# Make executable
chmod +x test.sh

# Run any example
./test.sh examples/01_basic_client_connection.py
```

Or set environment variables manually:

```bash
export PROJECT_X_API_KEY="your_api_key"
export PROJECT_X_USERNAME="your_username"  
export PROJECT_X_ACCOUNT_NAME="your_account_name"

uv run examples/01_basic_client_connection.py
```

## Examples Overview

### 01. Basic Client Connection (`01_basic_client_connection.py`)
**Foundation for all other examples**
- Client authentication using environment variables
- Account information and verification
- Instrument lookup and market data access
- JWT token generation for real-time features
- Basic position and order checks

**Key Learning:** How to connect and authenticate with ProjectX

### 02. Order Management (`02_order_management.py`)
**⚠️ Places REAL ORDERS - Use with caution!**
- Market, limit, and stop orders
- Bracket orders (entry + stop loss + take profit)
- Order modification and cancellation
- Real-time order status tracking
- Order cleanup and safety measures

**Key Learning:** Complete order lifecycle management

### 03. Position Management (`03_position_management.py`)
**Position tracking and risk management**
- Real-time position monitoring
- Portfolio P&L calculations
- Risk metrics and analysis
- Position sizing calculations
- Position alerts and callbacks
- Portfolio reporting

**Key Learning:** Professional position and risk management

### 04. Real-time Data Streaming (`04_realtime_data.py`)
**Multi-timeframe market data streaming**
- WebSocket connection management
- Multiple timeframe data (15sec, 1min, 5min, 15min, 1hr)
- Real-time callbacks and events
- Memory management and optimization
- Historical data initialization
- System health monitoring

**Key Learning:** Real-time market data integration

### 05. Orderbook Analysis (`05_orderbook_analysis.py`)
**Level 2 market microstructure analysis**
- Real-time bid/ask levels and depth
- Market imbalance detection
- Trade flow analysis
- Order type statistics
- Memory management for high-frequency data
- Market depth visualization

**Key Learning:** Advanced market microstructure analysis

### 06. Multi-Timeframe Strategy (`06_multi_timeframe_strategy.py`)
**⚠️ Complete trading strategy that places REAL ORDERS!**
- Multi-timeframe trend analysis (15min, 1hr, 4hr)
- Technical indicator integration
- Signal generation with confidence scoring
- Risk management and position sizing
- Real-time strategy monitoring
- Integrated order and position management

**Key Learning:** Complete algorithmic trading strategy implementation

### 07. Technical Indicators (`07_technical_indicators.py`)
**Comprehensive technical analysis**
- Trend indicators (SMA, EMA, MACD)
- Momentum indicators (RSI, Stochastic)
- Volatility indicators (Bollinger Bands, ATR)
- Volume indicators (OBV, Volume SMA)
- Multi-timeframe indicator analysis
- Real-time indicator updates

**Key Learning:** Professional technical analysis integration

## Running Examples Safely

### Recommended Learning Path

1. **Start with Basic Examples** (No order placement):
   ```bash
   ./test.sh examples/01_basic_client_connection.py
   ./test.sh examples/04_realtime_data.py
   ./test.sh examples/05_orderbook_analysis.py
   ./test.sh examples/07_technical_indicators.py
   ```

2. **Position Management** (No order placement):
   ```bash
   ./test.sh examples/03_position_management.py
   ```

3. **Order Management** (⚠️ Places real orders):
   ```bash
   ./test.sh examples/02_order_management.py
   ```

4. **Complete Strategy** (⚠️ Places real orders):
   ```bash
   ./test.sh examples/06_multi_timeframe_strategy.py
   ```

### Safety Features

All examples include:
- User confirmation prompts before placing orders
- Order cleanup and cancellation
- Risk management and position sizing
- Error handling and graceful degradation
- Comprehensive logging and status reporting

### Account Requirements

- **API Access**: Valid ProjectX API credentials
- **Trading Permissions**: Account must have trading enabled
- **Simulated Account**: Strongly recommended for testing
- **Balance**: Sufficient margin for MNQ micro contracts

## Key Concepts Demonstrated

### Architecture Patterns
- **Factory Functions**: Using `create_*` functions for component initialization
- **Dependency Injection**: Components receive their dependencies
- **Real-time Integration**: Single WebSocket connection shared across managers
- **Error Handling**: Comprehensive exception handling and recovery

### Data Management
- **Polars DataFrames**: High-performance data structures throughout
- **Memory Optimization**: Sliding windows and automatic cleanup
- **Multi-timeframe Sync**: Synchronized data across timeframes
- **Caching Strategies**: Efficient data caching and retrieval

### Trading Features
- **Order Types**: Market, limit, stop, bracket orders
- **Position Tracking**: Real-time position monitoring and P&L
- **Risk Management**: Position sizing and risk metrics
- **Technical Analysis**: Professional indicator library

### Real-time Features
- **WebSocket Connections**: Efficient real-time data streaming
- **Event Callbacks**: Custom event handling and notifications
- **System Health**: Connection monitoring and automatic recovery
- **Performance Monitoring**: Memory usage and system statistics

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify API key and username are correct
   - Check account name matches your account
   - Ensure account has API access enabled

2. **Trading Errors**
   - Verify account has trading permissions
   - Check sufficient margin/balance
   - Ensure market hours for futures trading

3. **Data Issues**
   - Check internet connection for real-time feeds
   - Verify instrument symbols (MNQ should work)
   - Check if market is open for live data

4. **WebSocket Errors**
   - JWT token may have expired (automatically refreshed)
   - Network issues or firewall blocking connections
   - Check firewall settings for WebSocket connections

### Debug Mode

Enable debug logging by modifying examples:

```python
logger = setup_logging(level="DEBUG")  # Change from INFO to DEBUG
```

### Getting Help

- Review the main SDK documentation
- Check the CLAUDE.md file for development guidance
- Look at error messages and stack traces
- Test with the basic client connection example first

## Performance Notes

### Expected Performance
- **50-70% reduction in API calls** through intelligent caching
- **Sub-second response times** for cached operations
- **95% reduction in polling** with real-time WebSocket feeds
- **Efficient memory usage** through sliding windows

### Memory Limits (Configurable)
- `max_trades = 10000` (OrderBook trade history)
- `max_depth_entries = 1000` (OrderBook depth per side)
- `max_bars_per_timeframe = 1000` (Real-time data per timeframe)
- `tick_buffer_size = 1000` (Tick data buffer)

## Next Steps

After running these examples:

1. **Study the Source Code**: Examine how each feature is implemented
2. **Build Custom Strategies**: Use examples as templates for your strategies
3. **Integrate with Your Systems**: Adapt patterns to your trading infrastructure
4. **Test Thoroughly**: Always test with simulated accounts first
5. **Monitor Performance**: Use built-in performance monitoring tools

## Contributing

When creating new examples:
- Follow the established naming convention
- Include comprehensive error handling
- Add safety confirmations for order placement
- Use MNQ for consistency
- Document key learning objectives
- Include cleanup procedures