# ProjectX Python SDK Testing Guide

## Testing Suite Overview

We've implemented a comprehensive testing suite for the ProjectX Python SDK client module that covers:

1. **Unit Tests**: Testing individual components and functions
2. **Component Tests**: Testing interaction between related components
3. **Integration Tests**: Testing complete workflows and processes

The testing architecture is designed to be:
- **Isolated**: No real network calls during tests
- **Comprehensive**: Covering success and error paths
- **Fast**: Quick to execute for development feedback
- **Maintainable**: Well-organized and documented

## Test Files Structure

```
tests/
├── conftest.py                # Shared fixtures and utilities
├── test_client.py             # Basic client smoke tests
├── run_client_tests.py        # Test runner script
├── README.md                  # Test documentation
├── client/
│   ├── __init__.py            # Package marker
│   ├── test_client_auth.py    # Authentication tests
│   ├── test_http.py           # HTTP client tests
│   ├── test_cache.py          # Cache system tests
│   ├── test_market_data.py    # Market data operations tests
│   ├── test_trading.py        # Trading operations tests
│   ├── test_rate_limiter.py   # Rate limiting tests
│   └── test_client_integration.py # Integration tests
```

## Key Testing Components

### Mock Responses and Clients

We use fixtures to mock HTTP responses and clients to avoid making real network calls:

- `mock_response`: Factory for creating HTTP responses with specific status codes and data
- `mock_httpx_client`: Mocked `httpx.AsyncClient` for intercepting API calls
- `mock_auth_response`: Standard authentication response sequence
- `mock_instrument`: Sample instrument data
- `mock_bars_data`: Sample OHLCV market data
- `mock_positions_data`: Sample position data
- `mock_trades_data`: Sample trade execution data

### Test Coverage Areas

1. **Authentication**
   - Login and token handling
   - Account selection
   - Token expiry and refresh
   - Error handling

2. **HTTP Client**
   - Request handling
   - Error handling
   - Retry logic
   - Rate limiting

3. **Caching**
   - Cache hits and misses
   - Cache expiration
   - Cache cleanup
   - Cache statistics

4. **Market Data**
   - Instrument lookup
   - Historical data retrieval
   - Data transformation
   - Error handling

5. **Trading**
   - Position retrieval
   - Trade history
   - Account operations
   - Error handling

6. **Integration**
   - Complete workflows
   - Component interactions
   - End-to-end processes
   - Error recovery

## Running Tests

### Running All Client Tests

```bash
# Using the provided script
./tests/run_client_tests.py

# Or using pytest directly
pytest tests/client tests/test_client.py -v
```

### Running Specific Test Files

```bash
# Run a specific test file
pytest tests/client/test_http.py

# Run with coverage
pytest tests/client/test_http.py --cov=project_x_py.client.http
```

### Running Specific Tests

```bash
# Run specific test class
pytest tests/client/test_client_auth.py::TestClientAuth

# Run specific test method
pytest tests/client/test_client_auth.py::TestClientAuth::test_authenticate_success
```

## Adding New Tests

When adding new tests:

1. Follow the existing file structure and naming conventions
2. Use appropriate fixtures from `conftest.py`
3. Test both success and error cases
4. Add docstrings explaining the purpose of each test
5. Make sure all API interactions are properly mocked

## Coverage Goals

The test suite aims to achieve high coverage of the client module:

- Line coverage: > 90%
- Branch coverage: > 85%
- Function coverage: 100%

Focus is placed on testing:
- Error handling paths
- Edge cases
- Concurrent operations
- Rate limiting and retry logic

## Continuous Integration

The test suite is designed to integrate with CI/CD pipelines. Tests run automatically on:
- Pull requests
- Main branch changes
- Release tags

## Order Manager Tests

To run just the Order Manager test suite:

```bash
pytest tests/order_manager/
```

This suite covers:
- `OrderManager` core API (place/search/cancel/modify)
- Order type helpers (market, limit, stop, trailing-stop)
- Bracket order validation and flows
- Position order tracking and helpers
- Utility price alignment functions

All network and API interactions are fully mocked using pytest and unittest.mock. Test execution is fast (<50ms per test).
