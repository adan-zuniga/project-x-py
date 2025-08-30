# Code Quality and Validation Rules

**CRITICAL**: All code must meet strict quality standards before merge. Quality checks are mandatory, not optional.

## Type Safety Requirements

### 1. Modern Type Hints (MANDATORY)

**ALWAYS use Python 3.10+ modern union syntax:**
```python
# ✅ CORRECT: Modern union syntax
def process_data(value: int | None) -> dict[str, Any]:
    pass

def handle_error(exc: ValueError | TypeError) -> None:
    pass

# ❌ WRONG: Legacy Optional/Union syntax
from typing import Optional, Union, Dict, Any
def process_data(value: Optional[int]) -> Dict[str, Any]:
    pass
```

**ALWAYS use `X | Y` in isinstance calls:**
```python
# ✅ CORRECT: Modern isinstance syntax
if isinstance(value, int | float):
    pass

# ❌ WRONG: Tuple syntax
if isinstance(value, (int, float)):
    pass
```

### 2. Comprehensive Type Coverage

**MANDATORY type hints for:**
- All function parameters and return values
- All class attributes and properties
- All async functions with proper Coroutine types
- All callback functions and event handlers

**Example:**
```python
from collections.abc import Awaitable, Callable
from typing import Any

class OrderManager:
    def __init__(
        self,
        client: ProjectXClient,
        callback: Callable[[dict[str, Any]], Awaitable[None]] | None = None
    ) -> None:
        self._client = client
        self._callback = callback

    async def place_order(
        self,
        instrument: str,
        quantity: int,
        side: str
    ) -> dict[str, Any]:
        pass
```

### 3. Type Checking Enforcement

**MANDATORY tools that must pass:**
```bash
# Must pass without errors
uv run mypy src/

# No mypy overrides allowed except in specific cases
# When mypy override needed, document WHY in comment
```

## Error Handling Standards

### 4. Exception Handling Patterns

**ALWAYS wrap external API calls:**
```python
async def api_operation(self) -> dict[str, Any]:
    try:
        result = await self._client.make_request(endpoint)
        return result
    except httpx.HTTPError as e:
        self.logger.error(f"API error in {self.__class__.__name__}.api_operation: {e}")
        raise ProjectXAPIError(f"Operation failed: {e}") from e
    except Exception as e:
        self.logger.error(f"Unexpected error in {self.__class__.__name__}.api_operation: {e}")
        raise ProjectXError(f"Unexpected error: {e}") from e
```

**FORBIDDEN patterns:**
```python
# ❌ WRONG: Bare except
try:
    risky_operation()
except:  # Never use bare except
    pass

# ❌ WRONG: Swallowing exceptions
try:
    risky_operation()
except Exception:
    return None  # Hides errors

# ❌ WRONG: Generic logging
except Exception as e:
    logger.error(f"Error: {e}")  # No context
```

### 5. Validation Requirements

**ALWAYS implement validation methods:**
```python
def _validate_order_payload(self, payload: dict[str, Any]) -> None:
    """Validate order payload before processing."""
    required_fields = ["instrument", "quantity", "side"]

    for field in required_fields:
        if field not in payload:
            raise ValidationError(f"Missing required field: {field}")

    if not isinstance(payload["quantity"], int) or payload["quantity"] <= 0:
        raise ValidationError("Quantity must be positive integer")

    if payload["side"] not in ["BUY", "SELL"]:
        raise ValidationError("Side must be BUY or SELL")
```

**NEVER let validation errors crash application:**
```python
# ✅ CORRECT: Handle validation gracefully
try:
    self._validate_order_payload(payload)
    return await self._process_order(payload)
except ValidationError as e:
    self.logger.warning(f"Validation failed: {e}")
    return {"error": str(e), "success": False}
```

## Data Processing Standards

### 6. Polars-Only DataFrame Operations

**MANDATORY: Use only Polars, never Pandas:**
```python
import polars as pl

# ✅ CORRECT: Polars operations
def process_market_data(data: pl.DataFrame) -> pl.DataFrame:
    return (
        data
        .filter(pl.col("volume") > 0)
        .with_columns([
            pl.col("price").rolling_mean(20).alias("sma_20"),
            pl.col("volume").rolling_sum(10).alias("volume_10")
        ])
        .sort("timestamp")
    )

# ❌ FORBIDDEN: Any Pandas imports or usage
import pandas as pd  # NEVER import pandas
```

**ALWAYS validate DataFrame schemas:**
```python
def validate_ohlcv_schema(df: pl.DataFrame) -> None:
    """Validate OHLCV DataFrame schema."""
    required_columns = ["timestamp", "open", "high", "low", "close", "volume"]

    for col in required_columns:
        if col not in df.columns:
            raise ValidationError(f"Missing required column: {col}")

    # Validate data types
    expected_types = {
        "timestamp": pl.Datetime,
        "open": pl.Float64,
        "high": pl.Float64,
        "low": pl.Float64,
        "close": pl.Float64,
        "volume": pl.Int64
    }

    for col, expected_type in expected_types.items():
        if df[col].dtype != expected_type:
            raise ValidationError(f"Column {col} has wrong type: {df[col].dtype}")
```

### 7. Memory Management

**ALWAYS implement cleanup for data structures:**
```python
class DataManager:
    def __init__(self, max_bars: int = 1000):
        self._bars: dict[str, pl.DataFrame] = {}
        self._max_bars = max_bars

    def add_bars(self, timeframe: str, new_bars: pl.DataFrame) -> None:
        """Add bars with automatic cleanup."""
        if timeframe not in self._bars:
            self._bars[timeframe] = new_bars
        else:
            # Concatenate and limit size
            combined = pl.concat([self._bars[timeframe], new_bars])
            self._bars[timeframe] = combined.tail(self._max_bars)
```

## Performance Requirements

### 8. Time Window Filtering

**ALWAYS implement time-based filtering:**
```python
def analyze_recent_data(
    self,
    data: pl.DataFrame,
    time_window_minutes: int = 60
) -> dict[str, Any]:
    """Analyze recent data within time window."""
    if data.is_empty():
        return {"error": "No data available"}

    # Filter to recent time window BEFORE processing
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)
    recent_data = data.filter(pl.col("timestamp") >= cutoff_time)

    if recent_data.is_empty():
        return {"error": f"No data in last {time_window_minutes} minutes"}

    # Process only filtered data
    return self._calculate_metrics(recent_data)
```

### 9. Vectorized Operations

**PREFER vectorized over loops:**
```python
# ✅ CORRECT: Vectorized operation
def calculate_returns(prices: pl.DataFrame) -> pl.DataFrame:
    return prices.with_columns([
        (pl.col("close") / pl.col("close").shift(1) - 1).alias("returns")
    ])

# ❌ WRONG: Loop-based calculation
def calculate_returns_slow(prices: pl.DataFrame) -> pl.DataFrame:
    returns = []
    for i in range(1, len(prices)):
        ret = prices[i]["close"] / prices[i-1]["close"] - 1
        returns.append(ret)
    # ... convert back to DataFrame
```

## Testing Quality Standards

### 10. Test Structure Requirements

**MANDATORY test structure:**
```python
@pytest.mark.asyncio
async def test_specific_behavior_under_conditions():
    """Test that describes WHAT should happen WHEN."""
    # Arrange: Set up test conditions
    manager = OrderManager(mock_client)
    test_order = {"instrument": "MNQ", "quantity": 1, "side": "BUY"}

    # Act: Perform the operation
    result = await manager.place_order(**test_order)

    # Assert: Verify expected behavior
    assert result["success"] is True
    assert result["order_id"] is not None
    assert mock_client.place_order.called_once_with(test_order)
```

**ALWAYS test error scenarios:**
```python
@pytest.mark.asyncio
async def test_place_order_handles_api_error():
    """Test that API errors are properly handled and logged."""
    # Arrange: Set up error condition
    mock_client = Mock()
    mock_client.place_order.side_effect = httpx.HTTPError("API down")
    manager = OrderManager(mock_client)

    # Act & Assert: Verify error handling
    with pytest.raises(ProjectXAPIError):
        await manager.place_order("MNQ", 1, "BUY")

    # Verify logging happened
    assert "API error" in caplog.text
```

## Critical Quality Violations

**These are NEVER acceptable:**

❌ **Legacy type hints (Optional, Union, Dict, etc.)**
❌ **Missing type hints on public methods**
❌ **Pandas imports or usage**
❌ **Bare except clauses**
❌ **Swallowing exceptions without logging**
❌ **Missing validation for external data**
❌ **Unbounded data growth without cleanup**
❌ **Processing entire dataset when time window available**
❌ **Loop-based operations where vectorization possible**
❌ **Tests without proper error scenario coverage**

## Quality Checklist

Before any code submission:
- [ ] All type hints use modern Python 3.10+ syntax
- [ ] Mypy passes without errors or documented overrides
- [ ] All external API calls wrapped in try-catch
- [ ] Validation methods implemented for all payloads
- [ ] Only Polars used for DataFrame operations
- [ ] Memory cleanup implemented for data structures
- [ ] Time window filtering available for analysis methods
- [ ] Tests cover both success and error scenarios
- [ ] Performance characteristics documented and measured
