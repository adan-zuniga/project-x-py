# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## CRITICAL: Testing and Running Examples

**ALWAYS use `./test.sh` to run tests and examples.** The environment variables are not set globally, but test.sh handles this automatically. 

```bash
# CORRECT - Always use test.sh:
./test.sh examples/01_basic_client_connection.py
./test.sh examples/21_statistics_usage.py  
./test.sh /tmp/test_script.py

# WRONG - Never use these directly:
uv run python examples/01_basic_client_connection.py
PROJECT_X_API_KEY="..." PROJECT_X_USERNAME="..." uv run python script.py
```

The test.sh script properly configures all required environment variables. DO NOT attempt to set PROJECT_X_API_KEY or PROJECT_X_USERNAME manually.

## Project Status: v3.3.0 - Complete Statistics Module Redesign

**IMPORTANT**: This project uses a fully asynchronous architecture. All APIs are async-only, optimized for high-performance futures trading.

## Development Phase Guidelines

**IMPORTANT**: This project has reached stable production status. When making changes:

1. **Maintain Backward Compatibility**: Keep existing APIs functional with deprecation warnings
2. **Deprecation Policy**: Mark deprecated features with warnings, remove after 2 minor versions
3. **Semantic Versioning**: Follow semver strictly (MAJOR.MINOR.PATCH)
4. **Migration Paths**: Provide clear migration guides for breaking changes
5. **Modern Patterns**: Use the latest Python patterns while maintaining compatibility
6. **Gradual Refactoring**: Improve code quality without breaking existing interfaces
7. **Async-First**: All new code must use async/await patterns

Example approach:
- ✅ DO: Keep old method signatures with deprecation warnings
- ✅ DO: Provide new improved APIs alongside old ones
- ✅ DO: Add compatibility shims when necessary
- ✅ DO: Document migration paths clearly
- ❌ DON'T: Break existing APIs without major version bump
- ❌ DON'T: Remove deprecated features without proper notice period

### Deprecation Process
1. Use the standardized `@deprecated` decorator from `project_x_py.utils.deprecation`
2. Provide clear reason, version info, and replacement path
3. Keep deprecated feature for at least 2 minor versions
4. Remove only in major version releases (4.0.0, 5.0.0, etc.)

Example:
```python
from project_x_py.utils.deprecation import deprecated, deprecated_class

# For functions/methods
@deprecated(
    reason="Method renamed for clarity",
    version="3.1.14",  # When deprecated
    removal_version="4.0.0",  # When it will be removed
    replacement="new_method()"  # What to use instead
)
def old_method(self):
    return self.new_method()

# For classes
@deprecated_class(
    reason="Integrated into TradingSuite",
    version="3.1.14",
    removal_version="4.0.0",
    replacement="TradingSuite"
)
class OldManager:
    pass
```

The standardized deprecation utilities provide:
- Consistent warning messages across the SDK
- Automatic docstring updates with deprecation info
- IDE support through the `deprecated` package
- Metadata tracking for deprecation management
- Support for functions, methods, classes, and parameters

## Specialized Agent Usage Guidelines

### IMPORTANT: Use Appropriate Subagents for Different Tasks

Claude Code includes specialized agents that should be used PROACTIVELY for specific development tasks. Each agent has specialized knowledge and tools optimized for their domain.

### When to Use Each Agent

#### **python-developer**
Use for project-x-py SDK development tasks:
- Writing async trading components (OrderManager, PositionManager, etc.)
- Implementing financial indicators with Polars DataFrames
- Optimizing real-time data processing and WebSocket connections
- Creating new TradingSuite features
- Ensuring 100% async architecture compliance
- Handling Decimal price precision requirements

Example scenarios:
- "Implement a new technical indicator"
- "Add WebSocket reconnection logic"
- "Create async order placement methods"

#### **code-standards-enforcer**
Use PROACTIVELY for maintaining SDK standards:
- **ALWAYS check IDE diagnostics first** via `mcp__ide__getDiagnostics`
- Before committing changes (enforce standards)
- PR review checks
- Release validation
- Verifying 100% async architecture
- Checking TradingSuite patterns compliance
- Ensuring Polars-only DataFrames usage
- Validating deprecation compliance
- Type safety with TypedDict/Protocol

Example scenarios:
- After implementing new features
- Before creating pull requests
- When refactoring existing code
- **After any code changes** - check IDE diagnostics immediately

#### **code-refactor**
Use PROACTIVELY for architecture improvements:
- Migrating to TradingSuite patterns
- Optimizing Polars operations
- Consolidating WebSocket handling
- Modernizing async patterns
- Monolithic to modular transitions
- Event system optimization
- Memory management improvements

Example scenarios:
- "Refactor OrderManager to use EventBus"
- "Optimize DataFrame operations in indicators"
- "Migrate legacy sync code to async"

#### **code-documenter**
Use PROACTIVELY for documentation tasks:
- Documenting new TradingSuite APIs
- Writing indicator function docs
- Explaining WebSocket events
- Creating migration guides
- Maintaining README and examples/
- Writing deprecation notices
- Updating docstrings

Example scenarios:
- After adding new features
- When changing APIs
- Creating example scripts

#### **code-debugger**
Use PROACTIVELY for troubleshooting:
- WebSocket disconnection issues
- Order lifecycle failures
- Real-time data gaps
- Event deadlocks
- Price precision errors
- Memory leaks
- AsyncIO debugging
- SignalR tracing

Example scenarios:
- "Debug why orders aren't filling"
- "Fix WebSocket reconnection issues"
- "Trace event propagation problems"

#### **code-reviewer**
Use PROACTIVELY for code review:
- Reviewing async patterns
- Checking real-time performance
- Validating financial data integrity
- Ensuring API stability
- Before releases
- PR reviews

Example scenarios:
- Before merging pull requests
- After completing features
- Before version releases

### Agent Selection Best Practices

1. **Use agents concurrently** when multiple tasks can be parallelized
2. **Be specific** in task descriptions for agents
3. **Choose the right agent** based on the task type, not just keywords
4. **Use PROACTIVELY** - don't wait for user to request specific agents
5. **Combine agents** for complex tasks (e.g., refactor → standards → review)

### Example Multi-Agent Workflow

```python
# When implementing a new feature:
1. python-developer: Implement the feature
2. code-standards-enforcer: Verify compliance
3. code-documenter: Add documentation  
4. code-reviewer: Final review before commit
```

### Agent Command Requirements

**Note**: Tool permissions are configured at the system level. This section documents common commands agents need.

#### Commands Agents Typically Use

**All Agents**:
- `./test.sh [script]` - Run tests and examples with proper environment
- File operations (Read, Write, Edit, MultiEdit)
- `git status`, `git diff`, `git add` - Version control

**python-developer**:
- `uv run pytest` - Run test suite
- `uv add [package]` - Add dependencies
- `./test.sh examples/*.py` - Test example scripts

**code-standards-enforcer**:
- `mcp__ide__getDiagnostics` - **CHECK FIRST** - IDE diagnostics
- `uv run ruff check .` - Lint code
- `uv run ruff format .` - Format code  
- `uv run mypy src/` - Type checking
- `uv run pytest --cov` - Coverage reports

**code-debugger**:
- `./test.sh` with debug scripts
- `grep` and search operations
- Log analysis commands

**code-reviewer**:
- `git diff` - Review changes
- `uv run pytest` - Verify tests pass
- Static analysis tools

#### Example Agent Command Workflow

```bash
# Agent workflow for implementing a feature
1. python-developer:
   - Edit src/project_x_py/new_feature.py
   - ./test.sh tests/test_new_feature.py
   
2. code-standards-enforcer:
   - mcp__ide__getDiagnostics  # ALWAYS CHECK FIRST
   - uv run ruff check src/
   - uv run mypy src/
   - Fix any issues found
   
3. code-reviewer:
   - mcp__ide__getDiagnostics  # Verify no issues remain
   - git diff
   - uv run pytest
   - Review implementation
```

#### IDE Diagnostics Priority

**CRITICAL**: The `code-standards-enforcer` agent must ALWAYS:
1. **First** check `mcp__ide__getDiagnostics` for the modified files
2. **Fix** any IDE diagnostic errors/warnings before proceeding
3. **Then** run traditional linting tools (ruff, mypy)
4. **Verify** with IDE diagnostics again after fixes

This catches issues that mypy might miss, such as:
- Incorrect method names (e.g., `get_statistics` vs `get_position_stats`)
- Missing attributes on classes
- Type mismatches that IDE's type checker detects
- Real-time semantic errors

### MCP Server Permissions for Agents

**Note**: MCP server access is system-configured. Agents should have access to relevant MCP servers for their tasks.

#### Essential MCP Servers for Agents

**All Agents Should Access**:
- `mcp__aakarsh-sasi-memory-bank-mcp` - Track progress and context
- `mcp__mcp-obsidian` - Document plans and decisions
- `mcp__smithery-ai-filesystem` - File operations

**python-developer**:
- `mcp__project-x-py_Docs` - Search project documentation
- `mcp__upstash-context-7-mcp` - Get library documentation
- `mcp__waldzellai-clear-thought` - Complex problem solving
- `mcp__itseasy-21-mcp-knowledge-graph` - Map component relationships

**code-standards-enforcer**:
- `mcp__project-x-py_Docs` - Verify against documentation
- `mcp__aakarsh-sasi-memory-bank-mcp` - Check architectural decisions

**code-refactor**:
- `mcp__waldzellai-clear-thought` - Plan refactoring strategy
- `mcp__itseasy-21-mcp-knowledge-graph` - Understand dependencies
- `mcp__aakarsh-sasi-memory-bank-mcp` - Log refactoring decisions

**code-documenter**:
- `mcp__mcp-obsidian` - Create documentation
- `mcp__project-x-py_Docs` - Reference existing docs
- `mcp__tavily-mcp` - Research external APIs

**code-debugger**:
- `mcp__waldzellai-clear-thought` - Analyze issues systematically
- `mcp__itseasy-21-mcp-knowledge-graph` - Trace data flow
- `mcp__ide` - Get diagnostics and errors

**code-reviewer**:
- `mcp__github` - Review PRs and issues
- `mcp__project-x-py_Docs` - Verify against standards
- `mcp__aakarsh-sasi-memory-bank-mcp` - Check design decisions

#### Example MCP Usage in Agent Workflows

```python
# python-developer agent workflow
1. Search existing patterns:
   await mcp__project_x_py_Docs__search_project_x_py_code(
       query="async def place_order"
   )

2. Track implementation:
   await mcp__aakarsh_sasi_memory_bank_mcp__track_progress(
       action="Implemented async order placement",
       description="Added bracket order support"
   )

3. Document in Obsidian:
   await mcp__mcp_obsidian__obsidian_append_content(
       filepath="Development/ProjectX SDK/Features/Order System.md",
       content="## Bracket Order Implementation\n..."
   )

# code-debugger agent workflow  
1. Analyze problem:
   await mcp__waldzellai_clear_thought__clear_thought(
       operation="debugging_approach",
       prompt="WebSocket disconnecting under load"
   )

2. Check component relationships:
   await mcp__itseasy_21_mcp_knowledge_graph__search_nodes(
       query="WebSocket RealtimeClient"
   )

3. Get IDE diagnostics:
   await mcp__ide__getDiagnostics()
```

#### MCP Server Best Practices for Agents

1. **Memory Bank**: Update after completing tasks
2. **Obsidian**: Document multi-session plans and decisions
3. **Clear Thought**: Use for complex analysis and planning
4. **Knowledge Graph**: Maintain component relationships
5. **Project Docs**: Reference before implementing
6. **GitHub**: Check issues and PRs for context

## Development Documentation with Obsidian

### Important: Use Obsidian for Development Plans and Progress Tracking

**ALWAYS use Obsidian MCP integration for**:
- Multi-session development plans
- Testing procedures and results
- Architecture decisions and design documents
- Feature planning and roadmaps
- Bug investigation notes
- Performance optimization tracking
- Release planning and checklists

**DO NOT create project files for**:
- Personal development notes (use Obsidian instead)
- Temporary planning documents
- Testing logs and results
- Work-in-progress documentation
- Meeting notes or discussions

### Obsidian Structure for ProjectX Development

When using Obsidian for this project, use the following structure:
```
Development/
  ProjectX SDK/
    Feature Planning/
      [Feature Name].md
    Testing Plans/
      [Version] Release Testing.md
    Architecture Decisions/
      [Decision Topic].md
    Bug Investigations/
      [Issue Number] - [Description].md
    Performance/
      [Optimization Area].md
```

### Example Obsidian Usage

```python
# When creating multi-session plans:
await mcp__mcp_obsidian__obsidian_append_content(
    filepath="Development/ProjectX SDK/Feature Planning/WebSocket Improvements.md",
    content="# WebSocket Connection Improvements Plan\n..."
)

# When documenting test results:
await mcp__mcp_obsidian__obsidian_append_content(
    filepath="Development/ProjectX SDK/Testing Plans/v3.3.0 Release Testing.md",
    content="## Test Results\n..."
)
```

This keeps the project repository clean and focused on production code while maintaining comprehensive development documentation in Obsidian.

## Development Commands

### Package Management (UV)
```bash
uv add [package]              # Add a dependency
uv add --dev [package]        # Add a development dependency
uv sync                       # Install/sync dependencies
uv run [command]              # Run command in virtual environment
```

### Testing
```bash
uv run pytest                # Run all tests
uv run pytest tests/test_client.py  # Run specific test file
uv run pytest -m "not slow"  # Run tests excluding slow ones
uv run pytest --cov=project_x_py --cov-report=html  # Generate coverage report
uv run pytest -k "async"     # Run only async tests
```

### Async Testing Patterns
```python
# Test async methods with pytest-asyncio
import pytest

@pytest.mark.asyncio
async def test_async_method():
    async with ProjectX.from_env() as client:
        await client.authenticate()
        result = await client.get_bars("MNQ", days=1)
        assert result is not None
```

### Code Quality
```bash
uv run ruff check .          # Lint code
uv run ruff check . --fix    # Auto-fix linting issues
uv run ruff format .         # Format code
uv run mypy src/             # Type checking
```

### Building and Distribution
```bash
uv build                     # Build wheel and source distribution
uv run python -m build       # Alternative build command
```

## Project Architecture

### Core Components (v3.0.2 - Multi-file Packages)

**ProjectX Client (`src/project_x_py/client/`)**
- Main async API client for TopStepX ProjectX Gateway
- Modular architecture with specialized modules:
  - `auth.py`: Authentication and JWT token management
  - `http.py`: Async HTTP client with retry logic
  - `cache.py`: Intelligent caching for instruments
  - `market_data.py`: Market data operations
  - `trading.py`: Trading operations
  - `rate_limiter.py`: Async rate limiting
  - `base.py`: Base class combining all mixins

**Specialized Managers (All Async)**
- `OrderManager` (`order_manager/`): Comprehensive async order operations
  - `core.py`: Main order operations
  - `bracket_orders.py`: OCO and bracket order logic
  - `position_orders.py`: Position-based order management
  - `tracking.py`: Order state tracking
  - `templates.py`: Order templates for common strategies
- `PositionManager` (`position_manager/`): Async position tracking and risk management
  - `core.py`: Position management core
  - `risk.py`: Risk calculations and limits
  - `analytics.py`: Performance analytics
  - `monitoring.py`: Real-time position monitoring
  - `tracking.py`: Position lifecycle tracking
- `RiskManager` (`risk_manager/`): Integrated risk management
  - `core.py`: Risk limits and validation
  - `monitoring.py`: Real-time risk monitoring
  - `analytics.py`: Risk metrics and reporting
- `ProjectXRealtimeDataManager` (`realtime_data_manager/`): Async WebSocket data
  - `core.py`: Main data manager
  - `callbacks.py`: Event callback handling
  - `data_processing.py`: OHLCV bar construction
  - `memory_management.py`: Efficient data storage
- `OrderBook` (`orderbook/`): Async Level 2 market depth
  - `base.py`: Core orderbook functionality
  - `analytics.py`: Market microstructure analysis
  - `detection.py`: Iceberg and spoofing detection
  - `profile.py`: Volume profile analysis

**Technical Indicators (`src/project_x_py/indicators/`)**
- TA-Lib compatible indicator library built on Polars
- 58+ indicators including pattern recognition:
  - **Momentum**: RSI, MACD, Stochastic, etc.
  - **Overlap**: SMA, EMA, Bollinger Bands, etc.
  - **Volatility**: ATR, Keltner Channels, etc.
  - **Volume**: OBV, VWAP, Money Flow, etc.
  - **Pattern Recognition** (NEW):
    - Fair Value Gap (FVG): Price imbalance detection
    - Order Block: Institutional order zone identification
    - Waddah Attar Explosion: Volatility-based trend strength
- All indicators work with Polars DataFrames for performance

**Configuration System**
- Environment variable based configuration
- JSON config file support (`~/.config/projectx/config.json`)
- ProjectXConfig dataclass for type safety
- ConfigManager for centralized configuration handling

**Event System**
- Unified EventBus for cross-component communication
- Type-safe event definitions
- Async event handlers with priority support
- Built-in event types for all trading events

### Available TradingSuite Features

The `Features` enum defines optional components that can be enabled:

- `ORDERBOOK = "orderbook"` - Level 2 market depth and analysis
- `RISK_MANAGER = "risk_manager"` - Position sizing and risk management
- `TRADE_JOURNAL = "trade_journal"` - Trade logging (future)
- `PERFORMANCE_ANALYTICS = "performance_analytics"` - Advanced metrics (future)
- `AUTO_RECONNECT = "auto_reconnect"` - Automatic reconnection (future)

**Note**: OrderManager and PositionManager are always included by default.

### Architecture Patterns

**Async Factory Functions**: Use async `create_*` functions for component initialization:
```python
# TradingSuite - Recommended approach (v3.0.0+)
async def setup_trading():
    # Simple one-line setup with TradingSuite
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["1min", "5min"],
        features=["orderbook"]
    )
    
    # Everything is ready - client authenticated, realtime connected
    return suite
```

**Dependency Injection**: Managers receive their dependencies (ProjectX client, realtime client) rather than creating them.

**Real-time Integration**: Single `ProjectXRealtimeClient` instance shared across managers for WebSocket connection efficiency.

**Context Managers**: Always use async context managers for proper resource cleanup:
```python
async with ProjectX.from_env() as client:
    # Client automatically handles auth, cleanup
    pass
```

### Data Flow

1. **Authentication**: ProjectX client authenticates and provides JWT tokens
2. **Real-time Setup**: Create ProjectXRealtimeClient with JWT for WebSocket connections
3. **Manager Initialization**: Pass clients to specialized managers via dependency injection
4. **Data Processing**: Polars DataFrames used throughout for performance
5. **Event Handling**: Real-time updates flow through WebSocket to respective managers

## Important Technical Details

### Indicator Functions
- All indicators follow TA-Lib naming conventions (uppercase function names allowed in `indicators/__init__.py`)
- Use Polars pipe() method for chaining: `data.pipe(SMA, period=20).pipe(RSI, period=14)`
- Indicators support both class instantiation and direct function calls

### Price Precision
- All price handling uses Decimal for precision
- Automatic tick size alignment in OrderManager
- Price formatting utilities in utils.py

### Error Handling
- Custom exception hierarchy in exceptions.py
- All API errors wrapped in ProjectX-specific exceptions
- Comprehensive error context and retry logic

### Testing Strategy
- Pytest with async support and mocking
- Test markers: unit, integration, slow, realtime
- High test coverage required (configured in pyproject.toml)
- Mock external API calls in unit tests

## Environment Setup

Required environment variables:
- `PROJECT_X_API_KEY`: TopStepX API key
- `PROJECT_X_USERNAME`: TopStepX username

Optional configuration:
- `PROJECTX_API_URL`: Custom API endpoint
- `PROJECTX_TIMEOUT_SECONDS`: Request timeout
- `PROJECTX_RETRY_ATTEMPTS`: Retry attempts

## MCP Server Integration

Several MCP (Model Context Protocol) servers are available to enhance development workflow:

### Essential Development MCPs

#### Memory Bank (`mcp__aakarsh-sasi-memory-bank-mcp`)
Tracks development progress and maintains context across sessions:
```python
# Track feature implementation progress
await mcp__aakarsh_sasi_memory_bank_mcp__track_progress(
    action="Implemented bracket order system",
    description="Added OCO and bracket order support with automatic stop/target placement"
)

# Log architectural decisions
await mcp__aakarsh_sasi_memory_bank_mcp__log_decision(
    title="Event System Architecture",
    context="Need unified event handling across components",
    decision="Implement EventBus with async handlers and priority support",
    alternatives=["Direct callbacks", "Observer pattern", "Pub/sub with Redis"],
    consequences=["Better decoupling", "Easier testing", "Slight performance overhead"]
)

# Switch development modes
await mcp__aakarsh_sasi_memory_bank_mcp__switch_mode("debug")  # architect, code, debug, test
```

#### Knowledge Graph (`mcp__itseasy-21-mcp-knowledge-graph`)
Maps component relationships and data flow:
```python
# Map trading system relationships
await mcp__itseasy_21_mcp_knowledge_graph__create_entities(
    entities=[
        {"name": "TradingSuite", "entityType": "Core", 
         "observations": ["Central orchestrator", "Manages all components"]},
        {"name": "OrderManager", "entityType": "Manager",
         "observations": ["Handles order lifecycle", "Supports bracket orders"]}
    ]
)

await mcp__itseasy_21_mcp_knowledge_graph__create_relations(
    relations=[
        {"from": "TradingSuite", "to": "OrderManager", "relationType": "manages"},
        {"from": "OrderManager", "to": "ProjectXClient", "relationType": "uses"}
    ]
)
```

#### Clear Thought Reasoning (`mcp__waldzellai-clear-thought`)
For complex problem-solving and architecture decisions:
```python
# Analyze performance bottlenecks
await mcp__waldzellai_clear_thought__clear_thought(
    operation="debugging_approach",
    prompt="WebSocket connection dropping under high message volume",
    context="Real-time data manager processing 1000+ ticks/second"
)

# Plan refactoring strategy
await mcp__waldzellai_clear_thought__clear_thought(
    operation="systems_thinking",
    prompt="Refactor monolithic client into modular mixins",
    context="Need better separation of concerns without breaking existing API"
)
```

### Documentation & Research MCPs

#### Project Documentation (`mcp__project-x-py_Docs`)
Quick access to project-specific documentation:
```python
# Search project documentation
await mcp__project_x_py_Docs__search_project_x_py_documentation(
    query="bracket order implementation"
)

# Search codebase
await mcp__project_x_py_Docs__search_project_x_py_code(
    query="async def place_bracket_order"
)
```

#### External Research (`mcp__tavily-mcp`)
Research trading APIs and async patterns:
```python
# Search for solutions
await mcp__tavily_mcp__tavily_search(
    query="python asyncio websocket reconnection pattern futures trading",
    max_results=5,
    search_depth="advanced"
)

# Extract documentation
await mcp__tavily_mcp__tavily_extract(
    urls=["https://docs.python.org/3/library/asyncio-task.html"],
    format="markdown"
)
```

### Best Practices for MCP Usage

1. **Memory Bank**: Update after completing significant features or making architectural decisions
2. **Knowledge Graph**: Maintain when adding new components or changing relationships
3. **Clear Thought**: Use for complex debugging, performance analysis, or architecture planning
4. **Documentation MCPs**: Reference before implementing new features to understand existing patterns

### When to Use Each MCP

- **Starting a new feature**: Check Memory Bank for context, use Clear Thought for planning
- **Debugging complex issues**: Clear Thought for analysis, Knowledge Graph for understanding relationships
- **Making architectural decisions**: Log with Memory Bank, analyze with Clear Thought
- **Understanding existing code**: Project Docs for internal code, Tavily for external research
- **Tracking progress**: Memory Bank for TODO tracking and progress updates

## Performance Optimizations

### Connection Pooling & Caching (client.py)
- HTTP connection pooling with retry strategies for 50-70% fewer connection overhead
- Instrument caching reduces repeated API calls by 80%
- Preemptive JWT token refresh at 80% lifetime prevents authentication delays
- Session-based requests with automatic retry on failures

### Memory Management
- **OrderBook**: Sliding windows with configurable limits (max 10K trades, 1K depth entries)
- **RealtimeDataManager**: Automatic cleanup maintains 1K bars per timeframe
- **Indicators**: LRU cache for repeated calculations (100 entry limit)
- Periodic garbage collection after large data operations

### Optimized DataFrame Operations
- **Chained operations** reduce intermediate DataFrame creation by 30-40%
- **Lazy evaluation** with Polars for better memory efficiency  
- **Efficient datetime parsing** with cached timezone objects
- **Vectorized operations** in orderbook analysis

### Performance Monitoring
Use async built-in methods to monitor performance:
```python
# Client performance stats (async)
async with ProjectX.from_env() as client:
    await client.authenticate()
    
    # Check performance metrics
    stats = await client.get_performance_stats()
    print(f"API calls: {stats['api_calls']}")
    print(f"Cache hits: {stats['cache_hits']}")
    
    # Health check
    health = await client.get_health_status()
    
    # Memory usage monitoring
    orderbook_stats = await orderbook.get_memory_stats()
    data_manager_stats = await data_manager.get_memory_stats()
```

### Expected Performance Improvements
- **50-70% reduction in API calls** through intelligent caching
- **30-40% faster indicator calculations** via chained operations
- **60% less memory usage** through sliding windows and cleanup
- **Sub-second response times** for cached operations
- **95% reduction in polling** with real-time WebSocket feeds

### Memory Limits (Configurable)
- `max_trades = 10000` (OrderBook trade history)
- `max_depth_entries = 1000` (OrderBook depth per side)
- `max_bars_per_timeframe = 1000` (Real-time data per timeframe)
- `tick_buffer_size = 1000` (Tick data buffer)
- `cache_max_size = 100` (Indicator cache entries)

## Recent Changes

### v3.3.0 - Latest Release (2025-01-21)
- **Breaking**: Complete statistics system redesign with 100% async-first architecture
- **Added**: New statistics module with BaseStatisticsTracker, ComponentCollector, StatisticsAggregator
- **Added**: Multi-format export (JSON, Prometheus, CSV, Datadog) with data sanitization
- **Added**: Enhanced health monitoring with 0-100 scoring and configurable thresholds
- **Added**: TTL caching, parallel collection, and circular buffers for performance optimization
- **Added**: 45+ new tests covering all aspects of the async statistics system
- **Fixed**: Eliminated all statistics-related deadlocks with single RW lock per component
- **Changed**: All statistics methods now require `await` for consistency and performance
- **Removed**: Legacy statistics mixins (EnhancedStatsTrackingMixin, StatsTrackingMixin)

### v3.2.1 - Previous Release (2025-08-19)
- **Added**: Complete statistics and analytics system with health monitoring and performance tracking
- **Added**: Fine-grained locking system to prevent deadlocks (replaced single `_stats_lock` with category-specific locks)
- **Added**: Consistent synchronous statistics API across all components for thread-safe access
- **Fixed**: Critical deadlock when OrderManager and StatisticsAggregator accessed locks in opposite order
- **Fixed**: API consistency issues - all `get_memory_stats()` methods now synchronous
- **Enhanced**: StatisticsAggregator with 5-second TTL caching and cross-component metrics
- **Enhanced**: Health scoring algorithm (0-100) with intelligent system monitoring

### v3.2.0 - Previous Release (2025-08-17)
- **Added**: Comprehensive type system overhaul with TypedDict and Protocol definitions
- **Added**: StatsTrackingMixin for error and memory tracking across all managers
- **Added**: Standardized deprecation system with @deprecated decorators
- **Fixed**: Type hierarchy issues between ProjectXBase and ProjectXClientProtocol
- **Fixed**: Response type handling for dict|list union types
- **Improved**: Test coverage with 47 new tests for type system
- **Improved**: Reduced type errors from 100+ to just 13 edge cases

### v3.1.13
- **Fixed**: Event system data structure mismatches causing order fill detection failures
  - Bracket orders now properly detect fills without 60-second timeouts
  - Event handlers handle both `order_id` and nested `order` object structures
  - ManagedTrade correctly listens to ORDER_FILLED instead of ORDER_MODIFIED
- **Fixed**: Type annotations for SignalR hub connections
  - Created HubConnection type alias for proper IDE support
  - market_connection and user_connection now have proper types instead of Any
- **Improved**: Real-time connection stability with circuit breaker pattern
- **Improved**: Data storage robustness with thread-safety and performance optimizations
- **Enhanced**: Test coverage increased from 30% to 93% for client module
- **Fixed**: Multiple asyncio deprecation warnings

### v3.1.12
- **Enhanced**: Significantly improved `01_events_with_on.py` real-time data example
  - Added CSV export functionality with interactive prompts
  - Plotly-based candlestick chart generation
  - Non-blocking user input handling
  - Better bar display formatting and visual indicators
  - Automatic browser opening for generated charts

### v3.1.11
- **Fixed**: ManagedTrade `_get_market_price()` implementation
  - ManagedTrade can now fetch current market prices from data manager
  - Automatic fallback through multiple timeframes (1sec, 15sec, 1min, 5min)
  - Enables risk-managed trades without explicit entry prices
  - Proper integration with TradingSuite's data manager

### v3.1.10
- Minor version bump for internal improvements

### v3.1.9
- **Fixed**: Tick price alignment in real-time data manager
  - All OHLC prices now properly aligned to instrument tick size
  - `get_current_price()` returns tick-aligned values
  - Prevents invalid prices (e.g., $23,927.62 for NQ now snaps to $23,927.50)
- **Documented**: ProjectX volume data limitation (platform-specific, not full exchange volume)

### v3.1.8 - Previous Release  
- **Fixed**: Real-time data processing for E-mini contracts (NQ/ES) that resolve to different symbols
- **Added**: Bar timer mechanism to create empty bars during low-volume periods
- **Improved**: Symbol matching to handle contract resolution (e.g., NQ→ENQ)
- **Enhanced**: Real-time data manager now properly processes all futures contracts

### v3.1.7
- Minor updates and improvements
- Documentation enhancements

### v3.1.6 - Critical Deadlock Fix
- **Fixed**: Deadlock when calling `suite.data` methods from event handler callbacks (Issue #39)
- **Improved**: Event emission now non-blocking to prevent handler deadlocks
- **Enhanced**: Event triggering moved outside lock scope for better concurrency
- **Added**: Missing asyncio import in data_processing module
- **Maintained**: Full API compatibility - no breaking changes

### v3.1.5 - Enhanced Bar Data Retrieval
- **Added**: Optional `start_time` and `end_time` parameters to `get_bars()` method
- **Improved**: Precise time range specification for historical data queries
- **Enhanced**: Full timezone support with automatic UTC conversion
- **Maintained**: Complete backward compatibility with existing `days` parameter

### v3.1.4 - WebSocket Connection Fix
- **Fixed**: Critical WebSocket error with missing `_use_batching` attribute
- **Improved**: Proper mixin initialization in ProjectXRealtimeClient
- **Enhanced**: More robust real-time connection handling

### v3.0.2 - Bug Fixes and Improvements
- **Order Lifecycle Tracking**: Fixed asyncio concurrency and field reference issues
- **Order Templates**: Fixed instrument lookup to use cached object
- **Cleanup Functionality**: Added comprehensive order/position cleanup
- **Documentation**: Updated all docs to reflect current version

### v3.0.1 - Production Ready
- **Performance Optimizations**: Enhanced connection pooling and caching
- **Event Bus System**: Unified event handling across all components
- **Risk Management**: Integrated risk manager with position limits and monitoring
- **Order Tracking**: Comprehensive order lifecycle tracking and management
- **Memory Management**: Optimized sliding windows and automatic cleanup
- **Enhanced Models**: Improved data models with better type safety

### v3.0.0 - Major Architecture Improvements
- **Trading Suite**: Unified trading suite with all managers integrated
- **Advanced Order Types**: OCO, bracket orders, and position-based orders
- **Real-time Integration**: Seamless WebSocket data flow across all components
- **Protocol-based Design**: Type-safe protocols for all major interfaces

### v2.0.4 - Package Refactoring
- Converted monolithic modules to multi-file packages
- All core modules organized as packages with focused submodules
- Improved code organization and maintainability

### Trading Suite Usage (v3.0.0+)
```python
# Complete trading suite with all managers
from project_x_py import TradingSuite

async def main():
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["1min", "5min"],
        features=["orderbook", "risk_manager"],  # Optional features
        initial_days=5
    )
    
    # All managers are integrated and ready
    # No need to call start() - already connected
    
    # Access individual managers
    order = await suite.orders.place_market_order(
        contract_id=suite.instrument_info.id,
        side=0,  # Buy
        size=1
    )
    
    position = await suite.positions.get_position("MNQ")
    bars = await suite.data.get_data("1min")
```

### Key Async Examples
```python
# Basic usage
async with ProjectX.from_env() as client:
    await client.authenticate()
    bars = await client.get_bars("MNQ", days=5)
    
# Real-time data with TradingSuite
async def stream_data():
    suite = await TradingSuite.create(
        "MNQ",
        timeframes=["1min", "5min"]
    )
    
    # Register event handlers
    from project_x_py import EventType
    
    async def handle_bar(event):
        print(f"New bar: {event.data}")
    
    await suite.on(EventType.NEW_BAR, handle_bar)
    
    # Data is already streaming
    # Access current data
    current_price = await suite.data.get_current_price()
    bars = await suite.data.get_data("1min")
```