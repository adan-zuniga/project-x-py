# Development Workflow Rules

**CRITICAL**: Follow these workflow rules to maintain code quality and ensure TDD compliance.

## Pre-Development Requirements

### 1. Environment Setup Verification

**ALWAYS verify environment before starting work:**
```bash
# Check UV environment
uv --version

# Sync dependencies
uv sync

# Verify test environment
./test.sh --version  # Should show pytest version
```

### 2. Memory and Context Checks

**BEFORE starting any work:**
- Check memory for relevant context and user preferences
- Review related memory facts about the component being modified
- Document decisions and progress in memory for multi-session work

## Development Cycle (MANDATORY)

### 3. TDD Cycle Enforcement

**EXACT sequence for ALL development:**

```bash
# Step 1: RED - Write failing test
echo "Writing test for feature X..."
# Create test that defines expected behavior
./test.sh tests/test_new_feature.py::test_specific_behavior
# MUST FAIL - confirm RED phase

# Step 2: GREEN - Minimal implementation
echo "Implementing minimal code to pass test..."
# Write just enough code to make test pass
./test.sh tests/test_new_feature.py::test_specific_behavior
# MUST PASS - confirm GREEN phase

# Step 3: REFACTOR - Improve while keeping tests green
echo "Refactoring implementation..."
# Improve code quality, performance, structure
./test.sh tests/test_new_feature.py
# ALL tests must continue passing

# Step 4: REPEAT for next feature/requirement
```

**FORBIDDEN workflow violations:**
- Writing implementation before tests
- Skipping test failure confirmation (RED)
- Modifying tests to match broken code
- Implementing multiple features before writing tests

### 4. Code Quality Gates

**MANDATORY checks before ANY commit:**

```bash
# 1. Type checking
uv run mypy src/
# Must pass without errors

# 2. Linting with auto-fix
uv run ruff check . --fix
uv run ruff format .
# Must pass without violations

# 3. Full test suite
./test.sh
# All tests must pass

# 4. Coverage check (if applicable)
uv run pytest --cov=project_x_py --cov-report=term-missing
# Maintain or improve coverage
```

## Testing Workflow

### 5. Test Execution Standards

**ALWAYS use ./test.sh for examples and integration tests:**
```bash
# ✅ CORRECT: Use test.sh wrapper
./test.sh examples/01_basic_client_connection.py
./test.sh tests/test_order_manager.py

# ❌ WRONG: Direct execution without environment
uv run python examples/01_basic_client_connection.py
```

**For unit tests, either method works:**
```bash
# Both acceptable for unit tests
uv run pytest tests/unit/
./test.sh tests/unit/
```

### 6. Test Organization by Phase

**Organize development tests by TDD phase:**

```bash
# RED phase: Create failing test
./test.sh tests/test_new_feature.py::test_red_phase -v
# Should show FAILED

# GREEN phase: Minimal implementation
./test.sh tests/test_new_feature.py::test_red_phase -v
# Should show PASSED

# Additional tests for edge cases
./test.sh tests/test_new_feature.py -v
# All should pass
```

### 7. Test Marking and Execution

**Use appropriate test markers:**
```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_fast_isolated_behavior():
    pass

@pytest.mark.integration
@pytest.mark.asyncio
async def test_component_interaction():
    pass

@pytest.mark.slow
@pytest.mark.asyncio
async def test_full_workflow():
    pass
```

**Run tests by category:**
```bash
# Fast feedback cycle
uv run pytest -m "unit and not slow"

# Integration testing
uv run pytest -m "integration"

# Full test suite
./test.sh
```

## Code Review Workflow

### 8. Self-Review Checklist

**Before requesting review:**
- [ ] TDD cycle followed for all changes
- [ ] Tests written before implementation
- [ ] All quality gates pass
- [ ] Memory updated with decisions and progress
- [ ] No implementation details in test assertions
- [ ] Error scenarios tested
- [ ] Type hints use modern Python 3.10+ syntax
- [ ] Only Polars used for DataFrame operations
- [ ] Async patterns correctly implemented

### 9. Deprecation Workflow

**When deprecating features:**
```python
from project_x_py.utils.deprecation import deprecated

@deprecated(
    reason="Replaced with new async implementation",
    version="3.4.0",  # Current version when deprecated
    removal_version="4.0.0",  # When it will be removed
    replacement="new_async_method()"
)
def old_method(self):
    """Original method with deprecation."""
    warnings.warn(
        "old_method() is deprecated. Use new_async_method() instead. "
        "Will be removed in v4.0.0",
        DeprecationWarning,
        stacklevel=2
    )
    return self.new_async_method()
```

## Debugging Workflow

### 10. TDD-Based Debugging

**When fixing bugs:**
```bash
# 1. Reproduce bug with test (RED)
# Write test that demonstrates the bug
./test.sh tests/test_bug_reproduction.py
# Should FAIL due to bug

# 2. Fix implementation (GREEN)
# Modify code to make test pass
./test.sh tests/test_bug_reproduction.py
# Should PASS with fix

# 3. Verify no regression
./test.sh
# All existing tests should still pass
```

### 11. Performance Debugging

**For performance issues:**
```bash
# Profile specific operations
uv run python -m cProfile -o profile.stats examples/performance_test.py

# Memory profiling
uv run mprof run ./test.sh examples/memory_intensive_test.py
uv run mprof plot

# Async profiling
uv run py-spy record -o profile.svg -- ./test.sh examples/async_test.py
```

## Release Workflow

### 12. Pre-Release Checklist

**Before any version bump:**
- [ ] All TDD cycles completed for new features
- [ ] Full test suite passes: `./test.sh`
- [ ] Type checking passes: `uv run mypy src/`
- [ ] Linting passes: `uv run ruff check .`
- [ ] Performance benchmarks within acceptable range
- [ ] Memory usage tests pass
- [ ] Documentation updated for new features
- [ ] Migration guide prepared for breaking changes
- [ ] Deprecation warnings in place for removed features

### 13. Version Management

**Follow semantic versioning strictly:**
- **PATCH** (x.y.Z): Bug fixes, no breaking changes
- **MINOR** (x.Y.z): New features, maintain backward compatibility
- **MAJOR** (X.y.z): Breaking changes, remove deprecated features

## Emergency Hotfix Workflow

### 14. Production Issue Response

**For critical production bugs:**
```bash
# 1. Create reproduction test immediately
# Test should demonstrate the exact failure scenario
./test.sh tests/test_hotfix_reproduction.py
# MUST FAIL showing the bug

# 2. Implement minimal fix
# Only change what's necessary to fix the bug
./test.sh tests/test_hotfix_reproduction.py
# MUST PASS with fix

# 3. Verify no side effects
./test.sh
# Full suite must pass

# 4. Fast-track review and deploy
```

## Workflow Violations (FORBIDDEN)

**These workflows are NEVER acceptable:**

❌ **Writing implementation without tests**
❌ **Committing code that fails quality gates**
❌ **Modifying tests to avoid fixing bugs**
❌ **Skipping TDD cycle for "simple" changes**
❌ **Using direct execution instead of ./test.sh for examples**
❌ **Committing without running full test suite**
❌ **Breaking backward compatibility without major version bump**
❌ **Removing deprecated features without proper notice period**

## Workflow Success Metrics

**Track these metrics to ensure workflow compliance:**
- TDD cycle adherence: 100%
- Quality gate pass rate: 100%
- Test-first development: 100%
- Bug fix reproduction tests: 100%
- Zero failing tests in main branch: 100%

Remember: **Discipline in workflow ensures quality in output. No shortcuts allowed.**
