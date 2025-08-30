# Architecture Guide

This guide explains the architecture and design patterns of the ProjectX Python SDK v3.5.0. Learn about the async-first design, **revolutionary multi-instrument support**, component interactions, and architectural decisions that enable high-performance futures trading across multiple contracts simultaneously.

## Architecture Overview

The ProjectX SDK is built with a modern, async-first architecture optimized for high-frequency trading and real-time data processing.

### Key Architectural Principles

1. **100% Async Architecture**: All operations use async/await for maximum concurrency
2. **Multi-Instrument Design (v3.5.0)**: Simultaneous management of multiple futures contracts
3. **Event-Driven Design**: Components communicate through a unified event system with instrument isolation
4. **Dependency Injection**: Components receive dependencies rather than creating them
5. **Protocol-Based Interfaces**: Type-safe contracts between components
6. **Memory Efficiency**: Sliding windows and automatic cleanup prevent memory leaks
7. **Performance Optimization**: Polars DataFrames and efficient data structures
8. **Container Protocol**: Dictionary-like access with `suite["SYMBOL"]` syntax
9. **Parallel Processing**: Concurrent initialization and operation of multiple instruments
10. **Resource Isolation**: Proper separation and cleanup between instrument contexts

### High-Level Architecture

```mermaid
graph TB
    subgraph "Application Layer"
        TS[TradingSuite Container]
        EX[Examples & Strategies]
    end

    subgraph "Multi-Instrument Layer (v3.5.0)"
        IC1[InstrumentContext MNQ]
        IC2[InstrumentContext ES]
        IC3[InstrumentContext MGC]
    end

    subgraph "Manager Layer (Per Instrument)"
        OM1[OrderManager MNQ]
        PM1[PositionManager MNQ]
        DM1[DataManager MNQ]
        OM2[OrderManager ES]
        PM2[PositionManager ES]
        DM2[DataManager ES]
        RM[RiskManager Shared]
    end

    subgraph "Client Layer (Shared)"
        PC[ProjectX Client]
        RC[RealtimeClient]
    end

    subgraph "Core Layer"
        EB1[EventBus MNQ]
        EB2[EventBus ES]
        IND[Indicators]
        STAT[Statistics]
        UTILS[Utils]
    end

    subgraph "External Services"
        API[ProjectX API]
        WS[WebSocket Feeds]
        DB[(Data Storage)]
    end

    TS --> IC1
    TS --> IC2
    TS --> IC3

    IC1 --> OM1
    IC1 --> PM1
    IC1 --> DM1
    IC2 --> OM2
    IC2 --> PM2
    IC2 --> DM2

    OM1 --> PC
    OM2 --> PC
    PM1 --> PC
    PM2 --> PC
    DM1 --> RC
    DM2 --> RC

    PC --> API
    RC --> WS

    OM1 --> EB1
    PM1 --> EB1
    DM1 --> EB1
    OM2 --> EB2
    PM2 --> EB2
    DM2 --> EB2

    DM1 --> IND
    DM2 --> IND
    OM1 --> STAT
    OM2 --> STAT
    PM1 --> STAT
    PM2 --> STAT
```

## Core Components

### TradingSuite (Multi-Instrument Container)

The `TradingSuite` has been revolutionized in v3.5.0 as a multi-instrument container:

```python
@dataclass(frozen=True)
class InstrumentContext:
    """Encapsulates all managers for a single instrument."""
    symbol: str
    instrument_info: InstrumentInfo
    data: RealtimeDataManager
    orders: OrderManager
    positions: PositionManager
    orderbook: Optional[OrderBook] = None
    risk_manager: Optional[RiskManager] = None
    event_bus: EventBus = field(default_factory=EventBus)

class TradingSuite:
    """Multi-instrument trading suite with container protocol."""

    def __init__(self, instrument_contexts: Dict[str, InstrumentContext]):
        self._instruments = instrument_contexts
        self._is_single_instrument = (len(self._instruments) == 1)
        if self._is_single_instrument:
            self._single_context = next(iter(self._instruments.values()))

    @classmethod
    async def create(
        cls,
        instruments: Union[str, List[str]],  # Multi-instrument support
        timeframes: List[str] = None,
        features: List[Features] = None,
        **kwargs
    ) -> "TradingSuite":
        """Factory method for parallel multi-instrument initialization."""
        # Normalize to list
        instrument_list = [instruments] if isinstance(instruments, str) else instruments

        # Parallel creation of all instrument contexts
        async def _create_context(symbol: str) -> Tuple[str, InstrumentContext]:
            # Create all managers for this instrument
            context = InstrumentContext(
                symbol=symbol,
                instrument_info=await get_instrument_info(symbol),
                data=RealtimeDataManager(symbol, timeframes),
                orders=OrderManager(client, symbol),
                positions=PositionManager(client, symbol),
                # Optional features per instrument
                orderbook=OrderBook(symbol) if Features.ORDERBOOK in features else None,
                risk_manager=RiskManager(symbol) if Features.RISK_MANAGER in features else None
            )
            return symbol, context

        # Execute all context creations in parallel
        tasks = [_create_context(symbol) for symbol in instrument_list]
        context_results = await asyncio.gather(*tasks)
        instrument_contexts = {symbol: context for symbol, context in context_results}

        return cls(instrument_contexts)

    # Container Protocol Implementation
    def __getitem__(self, symbol: str) -> InstrumentContext:
        """Dictionary-like access: suite['MNQ']"""
        return self._instruments[symbol]

    def __len__(self) -> int:
        """Number of managed instruments."""
        return len(self._instruments)

    def __iter__(self) -> Iterator[str]:
        """Iterate over instrument symbols."""
        return iter(self._instruments)

    def keys(self) -> KeysView[str]:
        """Get all instrument symbols."""
        return self._instruments.keys()

    def values(self) -> ValuesView[InstrumentContext]:
        """Get all instrument contexts."""
        return self._instruments.values()

    def items(self) -> ItemsView[str, InstrumentContext]:
        """Get all (symbol, context) pairs."""
        return self._instruments.items()

    # Backward Compatibility
    def __getattr__(self, name: str):
        """Legacy single-instrument access with deprecation warnings."""
        if self._is_single_instrument and hasattr(self._single_context, name):
            warnings.warn(
                f"Direct access to '{name}' is deprecated. "
                f"Please use suite['{self._single_context.symbol}'].{name} instead.",
                DeprecationWarning, stacklevel=2
            )
            return getattr(self._single_context, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
```

**Key Responsibilities**:
- **Multi-instrument orchestration**: Manage multiple futures contracts simultaneously
- **Container protocol**: Dictionary-like access with `suite["SYMBOL"]` syntax
- **Parallel initialization**: Concurrent setup of multiple instrument contexts
- **Event isolation**: Separate event buses for each instrument to prevent interference
- **Resource management**: Granular cleanup with fail-safe partial failure handling
- **Backward compatibility**: Seamless transition from single-instrument patterns
- **Cross-instrument operations**: Portfolio-level analytics and risk management
- **Performance optimization**: Shared resources where appropriate (client, authentication)

### Client Layer

#### ProjectX Client (HTTP API)

The `ProjectX` client handles all HTTP-based API operations:

```python
class ProjectX(
    AuthMixin,
    HttpMixin,
    MarketDataMixin,
    TradingMixin,
    CacheMixin
):
    """Main HTTP client with modular mixins."""

    def __init__(self, config: ProjectXConfig):
        self._session: Optional[aiohttp.ClientSession] = None
        self._auth_token: Optional[str] = None
        self._config = config

        # Initialize mixins
        self._setup_mixins()

    async def __aenter__(self) -> "ProjectX":
        """Async context manager entry."""
        await self._initialize_session()
        return self

    async def __aexit__(self, *args):
        """Async context manager exit."""
        await self.cleanup()
```

**Modular Mixin Architecture**:

- **AuthMixin**: JWT authentication and token refresh
- **HttpMixin**: HTTP client with retry logic and rate limiting
- **MarketDataMixin**: Historical data retrieval and caching
- **TradingMixin**: Order placement and management
- **CacheMixin**: Intelligent caching for instruments and static data

#### Realtime Client (WebSocket)

The realtime client manages WebSocket connections for live data:

```python
class ProjectXRealtimeClient:
    """WebSocket client for real-time data."""

    def __init__(self, jwt_token: str, base_url: str):
        self._jwt_token = jwt_token
        self._base_url = base_url
        self._event_bus = EventBus()

        # Connection management
        self._market_connection: Optional[HubConnection] = None
        self._user_connection: Optional[HubConnection] = None

        # Circuit breaker for resilience
        self._circuit_breaker = CircuitBreaker()

    async def connect(self) -> None:
        """Establish WebSocket connections."""
        await self._connect_market_data()
        await self._connect_user_data()

    async def subscribe_to_ticks(self, symbol: str) -> None:
        """Subscribe to tick data for symbol."""
        if self._market_connection:
            await self._market_connection.invoke("SubscribeToTicks", symbol)
```

### Manager Layer

Each manager handles a specific domain of trading functionality:

#### Order Manager

Handles order placement, tracking, and lifecycle management:

```python
class OrderManager:
    """Async order management with advanced order types."""

    def __init__(
        self,
        client: ProjectXClientProtocol,
        realtime_client: Optional[ProjectXRealtimeClient] = None
    ):
        self._client = client
        self._realtime_client = realtime_client
        self._orders: Dict[str, Order] = {}
        self._order_lock = asyncio.RWLock()

    async def place_bracket_order(
        self,
        contract_id: str,
        side: int,
        size: int,
        stop_offset: Decimal,
        target_offset: Decimal
    ) -> BracketOrderResult:
        """Place OCO bracket order with stop and target."""
        async with self._order_lock.writer_lock:
            # Place main order
            main_order = await self._place_main_order(...)

            # Place OCO stop and target orders
            stop_order = await self._place_stop_order(...)
            target_order = await self._place_target_order(...)

            # Link orders for lifecycle management
            bracket = BracketOrderGroup(main_order, stop_order, target_order)
            self._track_bracket_order(bracket)

            return BracketOrderResult(...)
```

**Key Features**:
- Advanced order types (market, limit, stop, bracket, OCO)
- Order lifecycle tracking and management
- Real-time order status updates
- Automatic order cleanup and error recovery

#### Position Manager

Tracks positions and calculates performance metrics:

```python
class PositionManager:
    """Async position tracking and analytics."""

    def __init__(
        self,
        client: ProjectXClientProtocol,
        realtime_client: Optional[ProjectXRealtimeClient] = None
    ):
        self._client = client
        self._realtime_client = realtime_client
        self._positions: Dict[str, Position] = {}
        self._position_lock = asyncio.RWLock()

    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get current position for symbol."""
        async with self._position_lock.reader_lock:
            position = self._positions.get(symbol)
            if position:
                # Update with real-time P&L
                await self._update_position_pnl(position)
            return position

    async def calculate_portfolio_risk(self) -> Dict[str, float]:
        """Calculate portfolio-level risk metrics."""
        async with self._position_lock.reader_lock:
            positions = list(self._positions.values())

        # Calculate various risk metrics
        return {
            'total_exposure': self._calculate_exposure(positions),
            'var_95': self._calculate_var(positions, 0.95),
            'correlation_risk': self._calculate_correlation_risk(positions)
        }
```

#### Realtime Data Manager

Manages real-time data streams and OHLCV bar construction:

```python
class RealtimeDataManager:
    """High-performance real-time data processing."""

    def __init__(
        self,
        timeframes: List[str],
        max_bars_per_timeframe: int = 1000
    ):
        # Use deque with maxlen for automatic memory management
        self._bars = defaultdict(lambda: deque(maxlen=max_bars_per_timeframe))
        self._tick_buffer = deque(maxlen=10000)

        # Bar builders for each timeframe
        self._bar_builders = {
            tf: BarBuilder(tf) for tf in timeframes
        }

        # Data access lock
        self._data_lock = asyncio.RWLock()

    async def process_tick(self, tick_data: Dict) -> None:
        """Process incoming tick and update bars."""
        async with self._data_lock.writer_lock:
            # Store tick
            self._tick_buffer.append(tick_data)

            # Update bar builders
            for timeframe, builder in self._bar_builders.items():
                new_bar = await builder.process_tick(tick_data)
                if new_bar:
                    self._bars[timeframe].append(new_bar)
                    # Emit event for new bar
                    await self._event_bus.emit(
                        EventType.NEW_BAR,
                        {**new_bar, 'timeframe': timeframe}
                    )
```

### Event System Architecture

The event system enables loose coupling between components:

```python
class EventBus:
    """Async event bus with priority support."""

    def __init__(self):
        self._handlers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        self._handler_lock = asyncio.RLock()

    async def on(
        self,
        event_type: EventType,
        handler: Callable,
        priority: int = 0
    ) -> None:
        """Register event handler with priority."""
        async with self._handler_lock:
            event_handler = EventHandler(handler, priority)
            self._handlers[event_type].append(event_handler)
            # Sort by priority (higher first)
            self._handlers[event_type].sort(key=lambda h: h.priority, reverse=True)

    async def emit(self, event_type: EventType, data: Any) -> None:
        """Emit event to all registered handlers."""
        async with self._handler_lock:
            handlers = self._handlers[event_type].copy()

        if handlers:
            # Create event object
            event = Event(event_type, data, datetime.utcnow())

            # Execute handlers concurrently
            tasks = [handler.callback(event) for handler in handlers]
            await asyncio.gather(*tasks, return_exceptions=True)
```

**Event Types**:
- `NEW_BAR`: New OHLCV bar constructed
- `TICK`: New tick data received
- `ORDER_FILLED`: Order execution
- `ORDER_CANCELLED`: Order cancellation
- `POSITION_CHANGED`: Position update
- `CONNECTION_STATUS`: WebSocket connection status

## Multi-Instrument Architecture (v3.5.0)

### InstrumentContext Design

The `InstrumentContext` is the core abstraction that encapsulates all functionality for a single instrument:

```python
@dataclass(frozen=True)
class InstrumentContext:
    """Complete context for a single trading instrument."""
    symbol: str
    instrument_info: InstrumentInfo

    # Core managers (always present)
    data: RealtimeDataManager
    orders: OrderManager
    positions: PositionManager

    # Optional features
    orderbook: Optional[OrderBook] = None
    risk_manager: Optional[RiskManager] = None

    # Event isolation
    event_bus: EventBus = field(default_factory=EventBus)

    # Lifecycle management
    async def cleanup(self) -> None:
        """Clean up all resources for this instrument."""
        await asyncio.gather(
            self.data.cleanup(),
            self.orders.cleanup(),
            self.positions.cleanup(),
            self.orderbook.cleanup() if self.orderbook else asyncio.sleep(0),
            self.risk_manager.cleanup() if self.risk_manager else asyncio.sleep(0),
            return_exceptions=True
        )
```

### Parallel Creation Pattern

Multiple instruments are created concurrently for optimal performance:

```python
async def _create_instrument_contexts(
    self,
    instruments: List[str],
    **kwargs
) -> Dict[str, InstrumentContext]:
    """Create multiple instrument contexts in parallel."""

    async def _create_single_context(symbol: str) -> Tuple[str, InstrumentContext]:
        # Parallel initialization of all managers
        instrument_info = await self._get_instrument_info(symbol)

        # Create managers concurrently
        data_manager, order_manager, position_manager = await asyncio.gather(
            RealtimeDataManager.create(symbol, self._timeframes),
            OrderManager.create(self._client, symbol),
            PositionManager.create(self._client, symbol)
        )

        # Optional features
        optional_features = await asyncio.gather(
            OrderBook.create(symbol) if self._has_orderbook else None,
            RiskManager.create(symbol) if self._has_risk_manager else None,
            return_exceptions=True
        )

        context = InstrumentContext(
            symbol=symbol,
            instrument_info=instrument_info,
            data=data_manager,
            orders=order_manager,
            positions=position_manager,
            orderbook=optional_features[0],
            risk_manager=optional_features[1]
        )

        return symbol, context

    # Execute all context creations in parallel
    tasks = [_create_single_context(symbol) for symbol in instruments]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle partial failures gracefully
    contexts = {}
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Failed to create context: {result}")
        else:
            symbol, context = result
            contexts[symbol] = context

    return contexts
```

### Event Isolation Architecture

Each instrument maintains its own event bus to prevent cross-contamination:

```python
class EventIsolationManager:
    """Manages event isolation between instruments."""

    def __init__(self):
        self._instrument_events: Dict[str, EventBus] = {}
        self._global_events = EventBus()  # Portfolio-level events

    async def emit_instrument_event(
        self,
        symbol: str,
        event_type: EventType,
        data: Any
    ) -> None:
        """Emit event for specific instrument only."""
        if symbol in self._instrument_events:
            await self._instrument_events[symbol].emit(event_type, data)

    async def emit_portfolio_event(
        self,
        event_type: EventType,
        data: Any
    ) -> None:
        """Emit portfolio-level event to all instruments."""
        tasks = [
            event_bus.emit(event_type, data)
            for event_bus in self._instrument_events.values()
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
```

### Resource Management

Granular resource management with fail-safe cleanup:

```python
class ResourceManager:
    """Manages resources across multiple instruments."""

    def __init__(self):
        self._cleanup_lock = asyncio.Lock()
        self._created_contexts: Dict[str, InstrumentContext] = {}

    async def cleanup_contexts(
        self,
        contexts: Dict[str, InstrumentContext]
    ) -> None:
        """Clean up contexts with proper error handling."""
        async with self._cleanup_lock:
            cleanup_tasks = []

            for symbol, context in contexts.items():
                cleanup_task = self._cleanup_single_context(symbol, context)
                cleanup_tasks.append(cleanup_task)

            # Execute all cleanups concurrently
            results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)

            # Log any cleanup failures
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    symbol = list(contexts.keys())[i]
                    logger.error(f"Cleanup failed for {symbol}: {result}")

    async def _cleanup_single_context(
        self,
        symbol: str,
        context: InstrumentContext
    ) -> None:
        """Clean up a single instrument context."""
        try:
            await context.cleanup()
        except Exception as e:
            logger.error(f"Failed to cleanup {symbol}: {e}")
            # Continue with other cleanups
```

### Cross-Instrument Operations

Portfolio-level operations across multiple instruments:

```python
class PortfolioOperations:
    """Portfolio-level operations across instruments."""

    def __init__(self, suite: TradingSuite):
        self._suite = suite

    async def get_total_exposure(self) -> Decimal:
        """Calculate total portfolio exposure."""
        exposure_tasks = []

        for symbol, context in self._suite.items():
            async def get_exposure(ctx):
                position = await ctx.positions.get_position(symbol)
                if position:
                    return abs(position.size * position.current_price)
                return Decimal('0')

            exposure_tasks.append(get_exposure(context))

        exposures = await asyncio.gather(*exposure_tasks)
        return sum(exposures, Decimal('0'))

    async def get_correlation_matrix(self) -> Dict[str, Dict[str, float]]:
        """Calculate correlation matrix between instruments."""
        symbols = list(self._suite.keys())
        if len(symbols) < 2:
            return {}

        # Get price data for all instruments
        price_data = {}
        for symbol, context in self._suite.items():
            bars = await context.data.get_data("5min", count=100)
            if len(bars) > 0:
                price_data[symbol] = bars["close"].to_list()

        # Calculate correlations
        correlations = {}
        for symbol1 in symbols:
            correlations[symbol1] = {}
            for symbol2 in symbols:
                if symbol1 in price_data and symbol2 in price_data:
                    corr = self._calculate_correlation(
                        price_data[symbol1],
                        price_data[symbol2]
                    )
                    correlations[symbol1][symbol2] = corr
                else:
                    correlations[symbol1][symbol2] = 0.0

        return correlations

    def _calculate_correlation(self, series1: List[float], series2: List[float]) -> float:
        """Calculate correlation between two price series."""
        import statistics

        if len(series1) != len(series2) or len(series1) < 2:
            return 0.0

        # Convert to returns
        returns1 = [series1[i]/series1[i-1] - 1 for i in range(1, len(series1))]
        returns2 = [series2[i]/series2[i-1] - 1 for i in range(1, len(series2))]

        try:
            return statistics.correlation(returns1, returns2)
        except statistics.StatisticsError:
            return 0.0
```

## Data Flow Architecture

### Multi-Instrument Data Flow

```mermaid
sequenceDiagram
    participant WS as WebSocket Feed
    participant RC as RealtimeClient
    participant TS as TradingSuite
    participant IC1 as InstrumentContext MNQ
    participant IC2 as InstrumentContext ES
    participant DM1 as DataManager MNQ
    participant DM2 as DataManager ES
    participant EB1 as EventBus MNQ
    participant EB2 as EventBus ES

    WS->>RC: Multi-Symbol Tick Data
    RC->>TS: Route by Symbol
    TS->>IC1: MNQ Tick Data
    TS->>IC2: ES Tick Data

    IC1->>DM1: Process MNQ Tick
    IC2->>DM2: Process ES Tick

    DM1->>EB1: Emit MNQ NEW_BAR
    DM2->>EB2: Emit ES NEW_BAR

    Note over EB1,EB2: Events isolated by instrument

    EB1->>IC1: MNQ Handlers Only
    EB2->>IC2: ES Handlers Only
```

### Real-time Data Flow

```mermaid
sequenceDiagram
    participant WS as WebSocket Feed
    participant RC as RealtimeClient
    participant DM as DataManager
    participant EB as EventBus
    participant OM as OrderManager
    participant PM as PositionManager

    WS->>RC: Tick Data
    RC->>DM: Process Tick
    DM->>DM: Update Bars
    DM->>EB: Emit NEW_BAR
    EB->>OM: Bar Event
    EB->>PM: Bar Event

    WS->>RC: Order Fill
    RC->>EB: Emit ORDER_FILLED
    EB->>OM: Update Order
    EB->>PM: Update Position
```

### Multi-Instrument Order Lifecycle

```mermaid
stateDiagram-v2
    [*] --> MultiOrder: Create Multi-Instrument Order

    state MultiOrder {
        [*] --> MNQOrder
        [*] --> ESOrder
        [*] --> MGCOrder

        state MNQOrder {
            [*] --> MNQPending
            MNQPending --> MNQSubmitted
            MNQSubmitted --> MNQWorking
            MNQWorking --> MNQFilled
            MNQWorking --> MNQCancelled
        }

        state ESOrder {
            [*] --> ESPending
            ESPending --> ESSubmitted
            ESSubmitted --> ESWorking
            ESWorking --> ESFilled
            ESWorking --> ESCancelled
        }

        state MGCOrder {
            [*] --> MGCPending
            MGCPending --> MGCSubmitted
            MGCSubmitted --> MGCWorking
            MGCWorking --> MGCFilled
            MGCWorking --> MGCCancelled
        }
    }

    MNQFilled --> PortfolioUpdate
    ESFilled --> PortfolioUpdate
    MGCFilled --> PortfolioUpdate
    PortfolioUpdate --> [*]
```

## Memory Management Architecture

### Sliding Window Pattern

Components use sliding windows to prevent memory bloat:

```python
class SlidingWindowManager:
    """Memory-efficient sliding window for time series data."""

    def __init__(self, max_size: int = 1000):
        self._data = deque(maxlen=max_size)
        self._lock = asyncio.RLock()

    async def append(self, item: Any) -> None:
        """Add item with automatic size management."""
        async with self._lock:
            self._data.append(item)
            # Deque automatically removes oldest items

    async def get_latest(self, count: int = None) -> List[Any]:
        """Get latest items efficiently."""
        async with self._lock:
            if count is None:
                return list(self._data)
            return list(itertools.islice(self._data, max(0, len(self._data) - count), None))
```

### Memory Cleanup Strategies

1. **Automatic Cleanup**: Deques with maxlen parameter
2. **Periodic Cleanup**: Background tasks that clean old data
3. **Reference Management**: Weak references where appropriate
4. **Resource Pooling**: Reuse expensive objects

## Performance Architecture

### Async Concurrency Patterns

```python
class ConcurrentOperationManager:
    """Manage concurrent operations efficiently."""

    def __init__(self, max_concurrent: int = 10):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_operations: Set[asyncio.Task] = set()

    async def execute_concurrent(
        self,
        operations: List[Callable],
        return_exceptions: bool = True
    ) -> List[Any]:
        """Execute operations with concurrency control."""
        async def bounded_operation(op):
            async with self._semaphore:
                return await op()

        # Create bounded tasks
        tasks = [
            asyncio.create_task(bounded_operation(op))
            for op in operations
        ]

        # Track active tasks
        self._active_operations.update(tasks)

        try:
            results = await asyncio.gather(*tasks, return_exceptions=return_exceptions)
        finally:
            self._active_operations.difference_update(tasks)

        return results
```

### Caching Architecture

```python
class MultiLevelCache:
    """Multi-level caching system."""

    def __init__(self):
        # L1: In-memory cache (fastest)
        self._memory_cache: Dict[str, Any] = {}
        self._cache_lock = asyncio.RLock()

        # L2: Time-based cache with TTL
        self._ttl_cache: Dict[str, Tuple[Any, float]] = {}

        # Cache statistics
        self._stats = CacheStats()

    async def get(self, key: str, ttl: float = 300) -> Optional[Any]:
        """Get from cache with TTL support."""
        async with self._cache_lock:
            # Check memory cache first
            if key in self._memory_cache:
                self._stats.hit()
                return self._memory_cache[key]

            # Check TTL cache
            if key in self._ttl_cache:
                value, expiry = self._ttl_cache[key]
                if time.time() < expiry:
                    self._stats.hit()
                    # Promote to memory cache
                    self._memory_cache[key] = value
                    return value
                else:
                    # Expired, remove
                    del self._ttl_cache[key]

            self._stats.miss()
            return None
```

## Error Handling Architecture

### Hierarchical Exception System

```python
class ProjectXException(Exception):
    """Base exception for all ProjectX errors."""

    def __init__(self, message: str, context: Dict = None):
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.timestamp = datetime.utcnow()

class APIException(ProjectXException):
    """API-related exceptions."""

    def __init__(self, message: str, status_code: int = None, **kwargs):
        super().__init__(message, kwargs)
        self.status_code = status_code

class OrderRejectedError(APIException):
    """Order rejection with specific reason."""
    pass

class InsufficientMarginError(OrderRejectedError):
    """Insufficient margin for order."""
    pass

class ConnectionError(ProjectXException):
    """Connection-related errors."""
    pass
```

### Circuit Breaker Pattern

```python
class CircuitBreaker:
    """Circuit breaker for resilient connections."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._expected_exception = expected_exception

        # State management
        self._failure_count = 0
        self._last_failure_time = None
        self._state = CircuitBreakerState.CLOSED
        self._lock = asyncio.RLock()

    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        async with self._lock:
            if self._state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitBreakerState.HALF_OPEN
                else:
                    raise CircuitBreakerOpenError("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except self._expected_exception as e:
            await self._on_failure()
            raise
```

## Testing Architecture

### Test Dependency Injection

```python
class TestDependencies:
    """Dependency injection for tests."""

    @staticmethod
    def create_mock_client() -> AsyncMock:
        """Create properly configured mock client."""
        client = AsyncMock(spec=ProjectXClientProtocol)
        client.authenticate.return_value = True
        client.get_account_info.return_value = AccountInfo(...)
        return client

    @staticmethod
    def create_test_suite(
        mock_client: AsyncMock = None,
        mock_realtime: AsyncMock = None
    ) -> TradingSuite:
        """Create test suite with mocked dependencies."""
        client = mock_client or TestDependencies.create_mock_client()
        realtime = mock_realtime or AsyncMock(spec=ProjectXRealtimeClient)

        return TradingSuite(
            client=client,
            realtime_client=realtime,
            instrument_info=InstrumentInfo(...),
            timeframes=["1min"],
            features=[]
        )
```

## Configuration Architecture

### Hierarchical Configuration

```python
@dataclass
class ProjectXConfig:
    """Centralized configuration management."""

    # API Configuration
    api_key: str
    username: str
    account_name: str
    api_url: str = "https://api.projectx.com"
    timeout_seconds: int = 30
    retry_attempts: int = 3

    # WebSocket Configuration
    websocket_url: str = "wss://api.projectx.com/ws"
    reconnect_interval: int = 5
    max_reconnect_attempts: int = 10

    # Performance Configuration
    max_concurrent_requests: int = 10
    cache_ttl_seconds: int = 300
    memory_limit_mb: int = 512

    # Risk Configuration
    max_position_size: int = 100
    max_daily_loss: Decimal = Decimal("10000")

    @classmethod
    def from_env(cls) -> "ProjectXConfig":
        """Load configuration from environment."""
        return cls(
            api_key=os.getenv("PROJECT_X_API_KEY", ""),
            username=os.getenv("PROJECT_X_USERNAME", ""),
            account_name=os.getenv("PROJECT_X_ACCOUNT_NAME", ""),
            # ... load other settings
        )

    @classmethod
    def from_file(cls, path: Path) -> "ProjectXConfig":
        """Load configuration from JSON file."""
        with open(path) as f:
            data = json.load(f)
        return cls(**data)
```

## Monitoring and Observability

### Statistics and Health Monitoring

```python
class ComponentHealth:
    """Health monitoring for components."""

    def __init__(self, component_name: str):
        self.component_name = component_name
        self._metrics = defaultdict(int)
        self._last_update = time.time()
        self._health_score = 100.0

    async def record_operation(
        self,
        operation: str,
        success: bool,
        duration: float = 0
    ) -> None:
        """Record operation for health scoring."""
        self._metrics[f"{operation}_total"] += 1
        if success:
            self._metrics[f"{operation}_success"] += 1
        else:
            self._metrics[f"{operation}_failure"] += 1

        self._metrics[f"{operation}_duration"] += duration
        self._last_update = time.time()

        # Update health score
        await self._calculate_health_score()

    async def get_health_score(self) -> float:
        """Get current health score (0-100)."""
        return self._health_score
```

This architecture provides a solid foundation for high-performance, scalable futures trading applications while maintaining code quality, testability, and maintainability.
