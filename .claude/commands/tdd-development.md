---
name: tdd-development
description: Execute TDD-based development workflow with proper agent coordination for project-x-py SDK
---

# TDD Development Workflow

This command ensures strict adherence to Test-Driven Development principles and proper agent coordination for the project-x-py async trading SDK.

## Pre-Execution Checklist

### 1. Read Project Guidelines
- [ ] Review CLAUDE.md for current project status
- [ ] Understand TDD methodology requirements
- [ ] Check deprecation and versioning policies
- [ ] Note testing requirements (`./test.sh` for examples, `uv run pytest` for tests)

### 2. Understand Agent Architecture
- [ ] Implementation agents have write access
- [ ] Analysis agents are read-only
- [ ] Coordinator agents orchestrate but don't implement
- [ ] Check `.claude/agents/` for specific capabilities

### 3. TDD Principles
- [ ] Tests define the specification
- [ ] Write tests BEFORE implementation
- [ ] Code must conform to tests
- [ ] Never modify tests to match buggy code

## Development Request

**Task**: {{request}}

## Workflow Execution

### Phase 1: Requirements Analysis
Using appropriate agents to understand the request:
- **architecture-planner**: For complex features requiring design
- **data-analyst**: For validation and data analysis needs
- **test-orchestrator**: For test strategy planning

### Phase 2: Test Definition (RED)
Following TDD, tests must be written first:
```python
# Example test structure
@pytest.mark.asyncio
async def test_expected_behavior():
    """Test that defines the specification"""
    # Arrange
    suite = await TradingSuite.create("MNQ")

    # Act
    result = await suite.new_feature()

    # Assert
    assert result.meets_requirements()
```

### Phase 3: Implementation (GREEN)
Minimal code to make tests pass:
- **python-developer**: Implement async components
- **integration-tester**: Create integration tests
- Follow 100% async architecture requirement

### Phase 4: Refactoring (REFACTOR)
Improve code quality while maintaining green tests:
- **code-refactor**: Optimize patterns
- **performance-optimizer**: Profile and optimize
- **code-standards-enforcer**: Ensure compliance

### Phase 5: Review and Documentation
Final quality checks:
- **code-reviewer**: Comprehensive review
- **security-auditor**: Security validation
- **code-documenter**: Update documentation

## Execution Steps

1. **Analyze Request**
   - Determine if this is a bug fix, feature, or refactoring
   - Identify affected components
   - Assess complexity level

2. **Plan Testing Strategy**
   - Define test scenarios
   - Set coverage targets (>95% for critical paths)
   - Plan unit, integration, and E2E tests

3. **Write Failing Tests**
   - Create tests that define expected behavior
   - Ensure tests fail initially (RED phase)
   - Tests should be deterministic and independent

4. **Implement Solution**
   - Write minimal code to pass tests
   - Use async/await throughout
   - Follow existing patterns in codebase

5. **Validate Quality**
   - Run `uv run pytest` for test suite
   - Check with `uv run mypy src/` for type safety
   - Ensure `uv run ruff check .` passes

6. **Document Changes**
   - Update docstrings
   - Add examples if needed
   - Document any deprecations

## Common Patterns

### Feature Implementation
```
test-orchestrator → python-developer → integration-tester → code-reviewer
```

### Bug Fix
```
code-debugger → test-orchestrator → python-developer → code-reviewer
```

### Performance Optimization
```
performance-optimizer → code-refactor → integration-tester → code-reviewer
```

### Complex Feature
```
architecture-planner → test-orchestrator → python-developer →
integration-tester → code-standards-enforcer → code-reviewer
```

## Quality Gates

Before considering task complete:
- [ ] All tests passing (including new ones)
- [ ] Coverage targets met (>90% overall)
- [ ] Type checking passes
- [ ] Linting clean
- [ ] Documentation updated
- [ ] Examples work with `./test.sh`

## Now Processing Your Request

Let me apply this TDD workflow to your specific request...
