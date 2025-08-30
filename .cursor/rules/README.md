# ProjectX SDK Development Rules

This directory contains precise, focused development rules for the ProjectX Python SDK. Each rule file covers a specific aspect of development and must be followed strictly.

## Rule Files Overview

### 🔴 [TDD Core Rules](./tdd_core.md)
**CRITICAL**: Test-Driven Development enforcement
- RED-GREEN-REFACTOR cycle requirements
- Test-first development mandates
- Tests as source of truth principles
- Bug fix and refactoring processes

### ⚡ [Async Testing Rules](./async_testing.md)
**CRITICAL**: Async-first testing patterns
- @pytest.mark.asyncio requirements
- Async context manager testing
- WebSocket testing patterns
- Async performance and memory testing

### 🔍 [Code Quality Rules](./code_quality.md)
**CRITICAL**: Quality standards and validation
- Modern type hints (Python 3.10+)
- Error handling patterns
- Polars-only DataFrame operations
- Memory management requirements

### 🔄 [Development Workflow](./development_workflow.md)
**CRITICAL**: Development process enforcement
- TDD cycle workflow
- Quality gate requirements
- Testing execution standards
- Release and debugging workflows

## Rule Priority

**All rules are MANDATORY**. Priority for conflicts:

1. **TDD Core Rules** - Fundamental development methodology
2. **Async Testing Rules** - SDK-specific async requirements
3. **Code Quality Rules** - Technical implementation standards
4. **Development Workflow** - Process and automation

## Quick Reference

### TDD Cycle (MANDATORY)
```bash
# 1. RED: Write failing test
./test.sh tests/test_new_feature.py  # MUST FAIL

# 2. GREEN: Minimal implementation
./test.sh tests/test_new_feature.py  # MUST PASS

# 3. REFACTOR: Improve while keeping tests green
./test.sh  # ALL tests must pass
```

### Quality Gates (MANDATORY)
```bash
uv run mypy src/           # Type checking
uv run ruff check . --fix  # Linting
uv run ruff format .       # Formatting
./test.sh                  # Full test suite
```

### Async Test Pattern (MANDATORY)
```python
@pytest.mark.asyncio
async def test_expected_behavior():
    # Test async functionality correctly
    pass
```

## Enforcement

These rules are enforced through:
- Cursor AI assistant guidance
- Pre-commit hooks (when available)
- Code review checklists
- CI/CD pipeline checks
- Memory tracking of violations

## Rule Updates

When updating rules:
1. Follow TDD to write tests for rule enforcement
2. Update relevant rule files
3. Update this README if structure changes
4. Document changes in memory for team awareness

## Violations

Rule violations are **NEVER acceptable**:
- ❌ Writing implementation before tests
- ❌ Using legacy type syntax
- ❌ Missing async decorators
- ❌ Skipping quality gates
- ❌ Any pattern marked as FORBIDDEN in rule files

**Remember: These rules ensure SDK quality and maintainability. No exceptions.**
