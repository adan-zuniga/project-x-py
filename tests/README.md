# ProjectX Python SDK Test Suite

This directory contains comprehensive tests for the ProjectX Python SDK client module.

## Test Structure

The test suite is organized by module and component:

- `tests/conftest.py`: Common fixtures and test utilities
- `tests/test_client.py`: Basic smoke tests for the client module
- `tests/client/`: Detailed component tests
  - `test_client_auth.py`: Authentication and token management tests
  - `test_http.py`: HTTP client functionality tests
  - `test_cache.py`: Caching system tests
  - `test_market_data.py`: Market data operations tests
  - `test_trading.py`: Trading operations tests
  - `test_rate_limiter.py`: Rate limiting functionality tests
  - `test_client_integration.py`: Integration tests with multiple components

## Running Tests

To run the full test suite:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=project_x_py

# Run specific test module
pytest tests/client/test_http.py

# Run specific test class
pytest tests/client/test_client_auth.py::TestClientAuth

# Run specific test
pytest tests/client/test_client_auth.py::TestClientAuth::test_authenticate_success
```

## Test Design

The tests are designed with the following principles:

1. **Isolated**: Tests don't make real API calls but use mocks
2. **Complete**: Tests cover both success and failure cases
3. **Efficient**: Tests share fixtures to minimize duplication
4. **Fast**: No unnecessary external dependencies or slow operations
5. **Comprehensive**: All public methods and critical internal methods are tested

## Key Fixtures

- `mock_response`: Creates configurable HTTP responses
- `mock_httpx_client`: Mock HTTP client for testing API calls
- `mock_auth_response`: Standard authentication response
- `mock_instrument`: Sample instrument object
- `mock_bars_data`: Sample OHLCV bar data
- `mock_positions_data`: Sample position data
- `mock_trades_data`: Sample trade data

## Adding New Tests

When adding new tests:

1. Follow the existing structure and naming conventions
2. Use appropriate fixtures from `conftest.py`
3. Test both success and error cases
4. Add docstrings to test classes and methods
5. Use descriptive assertion messages

## Future Improvements

Areas for future test improvements:

- Integration with CI/CD pipeline
- Property-based testing for complex scenarios
- Performance benchmarks
- Snapshot testing for response structures

## Order Manager Tests

The `order_manager` test suite provides high-coverage, unit-level tests for all major flows in `src/project_x_py/order_manager/`. Coverage includes order placement, bracket/position helpers, utils, and price alignment logic.

**To run only Order Manager tests:**
```bash
pytest tests/order_manager/
```

All network/API operations are mocked for speed and determinism. See `tests/order_manager/conftest.py` for local fixtures and helpers.
