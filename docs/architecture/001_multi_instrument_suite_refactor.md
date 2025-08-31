# Architecture Plan: Multi-Instrument TradingSuite Refactor

This document outlines the implementation plan for refactoring the `TradingSuite` class to support multiple financial instruments, while maintaining backward compatibility and adhering to clean, Pythonic design principles.

## 1. Recommended Design Pattern: Dictionary-as-Primary-Interface

The recommended approach is to implement a **dictionary-like container pattern**. The `TradingSuite` object will act as a manager for a collection of instrument-specific contexts, accessed via a dictionary-style key lookup (e.g., `suite["MES"]`).

- **Internal Structure**: A new `InstrumentContext` class will hold all managers for a single instrument. The main `TradingSuite` will contain a dictionary `_instruments: Dict[str, InstrumentContext]`.
- **Primary Interface**: `suite['INSTRUMENT_SYMBOL']`

### Pros of this Approach:
- **Pythonic and Intuitive**: `[]` is the standard for item access in Python.
- **Robust and Safe**: Handles all instrument symbols, even those with special characters (e.g., `EUR-USD`), and prevents namespace collisions with `TradingSuite` methods.
- **Discoverable and Iterable**: Naturally supports standard container methods (`.keys()`, `.items()`, `for instrument in suite:`).

### Alternative Considered (Attribute Access: `suite.MES`):
This was rejected due to major drawbacks:
- **Namespace Collisions**: An instrument named `items` would conflict with the `.items()` method.
- **Invalid Identifiers**: Fails for symbols that are not valid Python identifiers.

## 2. Code Implementation Skeletons

### a. `InstrumentContext`: The Single-Instrument Core

This class will encapsulate all logic for a single instrument.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class InstrumentContext:
    """
    Encapsulates all managers and data for a single financial instrument.
    """
    symbol: str
    instrument_info: object
    data: object             # Instance of DataManager
    orders: object           # Instance of OrderManager
    positions: object        # Instance of PositionManager
    orderbook: object        # Optional: Instance of OrderBook
    risk_manager: object     # Optional: Instance of RiskManager
```

### b. `TradingSuite`: The Multi-Instrument Container

The main `TradingSuite` is refactored into a container that manages `InstrumentContext` objects and ensures backward compatibility.

```python
import asyncio
import warnings
from typing import Dict, List, Union, Iterator

class TradingSuite:
    """A manager for one or more instrument trading contexts."""

    def __init__(self, instrument_contexts: Dict[str, InstrumentContext]):
        self._instruments = instrument_contexts
        self._is_single_instrument = (len(self._instruments) == 1)
        if self._is_single_instrument:
            self._single_context = next(iter(self._instruments.values()))

    @classmethod
    async def create(
        cls,
        instruments: Union[str, List[str]],
        timeframes: List[str],
        features: List[str] = None,
        initial_days: int = 0
    ) -> "TradingSuite":
        # 1. Normalize input to a list
        instrument_list = [instruments] if isinstance(instruments, str) else instruments

        # 2. Create all instrument contexts in parallel
        async def _create_context(symbol: str):
            # Logic to create and return a fully hydrated InstrumentContext
            await asyncio.sleep(0.1) # Simulate async work
            return symbol, InstrumentContext(symbol=symbol, ...) # Simplified

        tasks = [_create_context(symbol) for symbol in instrument_list]
        context_results = await asyncio.gather(*tasks)
        instrument_contexts = {symbol: context for symbol, context in context_results}
        return cls(instrument_contexts)

    # --- Container Protocol Methods ---
    def __getitem__(self, symbol: str) -> InstrumentContext:
        return self._instruments[symbol]

    def __len__(self) -> int:
        return len(self._instruments)

    def __iter__(self) -> Iterator[str]:
        return iter(self._instruments)

    # --- Backward Compatibility ---
    def __getattr__(self, name: str):
        if self._is_single_instrument and hasattr(self._single_context, name):
            warnings.warn(
                f"Direct access to '{name}' is deprecated. Please use suite['{self._single_context.symbol}'].{name} instead.",
                DeprecationWarning,
                stacklevel=2
            )
            return getattr(self._single_context, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
```

## 3. Usage Examples

### a. Creating a Suite

```python
# Single instrument (backward compatible)
suite_single = await TradingSuite.create(["MNQ"], timeframes=["1min", "5min"])

# Multiple instruments
suite_multi = await TradingSuite.create(
    instruments=["MNQ", "MCL", "MES"],
    timeframes=["1min", "5min"]
)
```

### b. Accessing Data and Features

```python
# Accessing data for a specific instrument
mcl_context = suite_multi["MCL"]
mcl_5min_bars = await mcl_context.data.get_data("5min")

# Placing an order for a different instrument
await suite_multi["MES"].orders.place_market_order(...)

# Iterating through all managed instruments
for symbol in suite_multi:
    price = await suite_multi[symbol].data.get_current_price()
    print(f"  - {symbol}: {price}")

# Backward compatibility (raises a DeprecationWarning)
mnq_data_legacy = suite_single.data
```
