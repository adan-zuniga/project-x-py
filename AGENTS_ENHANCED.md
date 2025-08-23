# Enhanced Agent Configuration for ProjectX SDK

## Current Agents - Enhanced Configurations

### 1. python-developer
**Enhanced Capabilities:**
- Performance profiling with memory_profiler and py-spy
- Integration testing with mock market data generators
- Benchmark suite management for performance tracking
- Async pattern validation and optimization
- WebSocket load testing and stress testing

**Additional Tools Needed:**
```bash
uv add --dev memory_profiler py-spy pytest-benchmark pytest-asyncio-cooperative
```

**Enhanced Workflow:**
```python
# Profile memory usage
mprof run ./test.sh examples/04_realtime_data.py
mprof plot

# Async profiling
py-spy record -o profile.svg -- ./test.sh examples/00_trading_suite_demo.py

# Benchmark tests
uv run pytest tests/benchmarks/ --benchmark-only
```

### 2. code-standards-enforcer
**Enhanced Capabilities:**
- Automated pre-commit hook setup and validation
- Performance regression detection with benchmarks
- Memory leak detection via tracemalloc
- Security vulnerability scanning with bandit
- Dependency audit with pip-audit

**Additional Tools:**
```bash
uv add --dev pre-commit bandit pip-audit vulture
```

**Pre-commit Configuration (.pre-commit-config.yaml):**
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.9.0
    hooks:
      - id: mypy
        args: [--config-file, pyproject.toml]
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: [-r, src/]
```

### 3. code-debugger
**Enhanced Capabilities:**
- Production log analysis with structured logging
- Distributed tracing with OpenTelemetry
- Async debugging with aiomonitor
- Memory leak detection with objgraph and tracemalloc
- WebSocket packet analysis and replay

**Additional Tools:**
```bash
uv add --dev aiomonitor objgraph opentelemetry-api opentelemetry-sdk
```

**Debug Utilities:**
```python
# src/project_x_py/debug/async_monitor.py
import aiomonitor

async def start_monitor():
    """Start async monitor for debugging"""
    async with aiomonitor.start_monitor(
        loop=asyncio.get_running_loop(),
        port=50101
    ):
        # Your async code here
        pass

# Memory leak detection
import objgraph
objgraph.show_most_common_types(limit=20)
objgraph.show_growth()
```

### 4. code-documenter
**Enhanced Capabilities:**
- Interactive API documentation with mkdocs-material
- Automated changelog generation from commits
- Example notebook generation with papermill
- Video tutorial script generation
- API reference auto-generation with mkdocstrings

**Tools Setup:**
```bash
uv add --dev mkdocs mkdocs-material mkdocstrings[python] mkdocs-jupyter papermill
```

**Documentation Structure:**
```
docs/
├── index.md
├── getting-started/
│   ├── installation.md
│   ├── quickstart.md
│   └── authentication.md
├── api/
│   ├── client.md
│   ├── trading-suite.md
│   └── indicators.md
├── examples/
│   └── notebooks/
└── changelog.md
```

### 5. code-refactor
**Enhanced Capabilities:**
- AST-based code analysis for safe refactoring
- Dependency graph visualization
- API migration script generation
- Database schema migration support
- Performance impact analysis

**Tools:**
```bash
uv add --dev rope ast-grep libcst pydeps
```

### 6. code-reviewer
**Enhanced Capabilities:**
- Security-focused review with semgrep
- Complexity analysis with radon
- Test coverage delta reporting
- Breaking change detection
- Performance benchmark comparison

**Tools:**
```bash
uv add --dev semgrep radon coverage-badge diff-cover
```

## Recommended New Agents

### 7. performance-optimizer
**Purpose:** Performance tuning and optimization specialist

**Responsibilities:**
- Memory profiling and optimization
- Async performance tuning
- Cache optimization strategies
- Database query optimization
- WebSocket message batching
- DataFrame operation optimization

**Tools & Commands:**
```bash
# Memory profiling
mprof run ./test.sh [script]
mprof plot

# CPU profiling
py-spy top -- ./test.sh [script]

# Line profiling
kernprof -l -v ./test.sh [script]

# Benchmark comparisons
uv run pytest tests/benchmarks --benchmark-compare
```

**MCP Servers:**
- `mcp__waldzellai-clear-thought` - Optimization strategy planning
- `mcp__aakarsh-sasi-memory-bank-mcp` - Track optimization results

### 8. integration-tester
**Purpose:** End-to-end testing with market simulation

**Responsibilities:**
- Mock market data generation
- Order lifecycle simulation
- WebSocket stress testing
- Multi-timeframe backtesting
- Paper trading validation
- Market replay testing

**Implementation:**
```python
# src/project_x_py/testing/market_simulator.py
class MarketSimulator:
    """Simulate realistic market conditions"""

    async def generate_tick_stream(
        self,
        symbol: str,
        base_price: Decimal,
        volatility: float = 0.01,
        tick_rate: int = 100  # ticks per second
    ):
        """Generate realistic tick data"""
        pass

    async def simulate_order_fills(
        self,
        order: Order,
        market_conditions: MarketConditions
    ):
        """Simulate order execution"""
        pass
```

### 9. security-auditor
**Purpose:** Security and compliance checking

**Responsibilities:**
- API key security validation
- WebSocket authentication audit
- Data encryption verification
- PII handling compliance
- Dependency vulnerability scanning
- Secret scanning in codebase

**Security Checklist:**
```yaml
security_checks:
  - api_keys_in_env_vars
  - no_hardcoded_secrets
  - websocket_auth_required
  - data_encryption_at_rest
  - secure_random_generation
  - input_validation
  - rate_limiting_enabled
  - audit_logging_configured
```

**Tools:**
```bash
# Security scanning
uv run bandit -r src/
uv run safety check
uv run pip-audit

# Secret scanning
trufflehog filesystem .
```

### 10. release-manager
**Purpose:** Release preparation and deployment

**Responsibilities:**
- Semantic versioning validation
- Breaking change detection
- Migration script generation
- Release notes compilation
- PyPI deployment automation
- Git tag management

**Release Workflow:**
```bash
# Version bump
bump2version patch  # or minor, major

# Generate changelog
git-changelog -o CHANGELOG.md

# Build distributions
uv build

# Check package
twine check dist/*

# Test PyPI upload
twine upload --repository testpypi dist/*

# Production release
twine upload dist/*
```

### 11. data-analyst
**Purpose:** Market data analysis and validation

**Responsibilities:**
- Indicator accuracy testing
- Market microstructure analysis
- Order flow analysis
- Statistical validation
- Backtest result analysis
- Performance attribution

**Analysis Tools:**
```python
# src/project_x_py/analysis/indicator_validator.py
class IndicatorValidator:
    """Validate indicator calculations"""

    async def compare_with_talib(
        self,
        data: pl.DataFrame,
        indicator: str,
        **params
    ):
        """Compare our indicators with TA-Lib"""
        pass

    async def statistical_validation(
        self,
        indicator_output: pl.Series,
        expected_properties: Dict
    ):
        """Validate statistical properties"""
        pass
```

## Agent Collaboration Patterns

### Pattern 1: Feature Development
```
1. data-analyst: Analyze requirements and validate approach
2. python-developer: Implement the feature
3. integration-tester: Create comprehensive tests
4. code-standards-enforcer: Ensure compliance
5. performance-optimizer: Optimize if needed
6. code-documenter: Create documentation
7. code-reviewer: Final review
8. release-manager: Prepare for release
```

### Pattern 2: Bug Investigation
```
1. code-debugger: Investigate and identify root cause
2. integration-tester: Reproduce with test case
3. python-developer: Implement fix
4. code-standards-enforcer: Verify fix quality
5. code-reviewer: Review the fix
```

### Pattern 3: Performance Issue
```
1. performance-optimizer: Profile and identify bottlenecks
2. code-refactor: Plan optimization strategy
3. python-developer: Implement optimizations
4. integration-tester: Verify performance improvements
5. code-reviewer: Review changes
```

### Pattern 4: Security Audit
```
1. security-auditor: Comprehensive security scan
2. code-debugger: Investigate vulnerabilities
3. python-developer: Implement fixes
4. code-standards-enforcer: Verify secure coding
5. integration-tester: Test security measures
```

## MCP Server Assignments

### Core MCP Servers (All Agents)
- `mcp__aakarsh-sasi-memory-bank-mcp` - Progress tracking
- `mcp__mcp-obsidian` - Documentation and planning
- `mcp__smithery-ai-filesystem` - File operations
- `mcp__ide` - IDE diagnostics and errors

### Specialized MCP Servers

**Development & Analysis:**
- `mcp__project-x-py_Docs` - Project documentation
- `mcp__upstash-context-7-mcp` - Library documentation
- `mcp__waldzellai-clear-thought` - Complex problem solving
- `mcp__itseasy-21-mcp-knowledge-graph` - Component relationships

**External Research:**
- `mcp__tavily-mcp` - Web search and documentation extraction

## Implementation Priority

1. **Immediate** (Critical for current workflow):
   - Enhance python-developer with profiling tools
   - Add pre-commit hooks to code-standards-enforcer
   - Implement performance-optimizer agent

2. **Short-term** (Next sprint):
   - Create integration-tester for market simulation
   - Enhance code-debugger with production debugging tools
   - Add security-auditor for compliance

3. **Medium-term** (Next release):
   - Implement release-manager for automated releases
   - Create data-analyst for indicator validation
   - Enhance documentation generation

## Success Metrics

- **Code Quality**: <5 issues per 1000 lines of code
- **Test Coverage**: >95% for critical paths
- **Performance**: <100ms API response time, <10ms tick processing
- **Security**: Zero high-severity vulnerabilities
- **Documentation**: 100% public API documentation
- **Release Cadence**: Bi-weekly patch releases, monthly minor releases
