# Test-Driven Development (TDD) Core Rules

**CRITICAL**: This project follows strict Test-Driven Development principles. Tests define the specification, not the implementation.

## Mandatory TDD Workflow

### 1. RED-GREEN-REFACTOR Cycle (NON-NEGOTIABLE)

**ALWAYS follow this exact sequence:**
```
1. RED: Write a failing test that defines expected behavior
2. GREEN: Write minimal code to make the test pass
3. REFACTOR: Improve code while keeping tests green
4. REPEAT: Continue for next feature/requirement
```

**NEVER skip steps or write implementation code before tests exist.**

### 2. Test-First Development Rules

- **MANDATORY**: Write tests BEFORE any implementation code
- **MANDATORY**: Tests must define the contract/specification of behavior
- **MANDATORY**: Run test to confirm it fails (RED phase) before writing code
- **FORBIDDEN**: Writing implementation code without corresponding test
- **FORBIDDEN**: Writing tests after implementation is complete

### 3. Tests as Source of Truth

- **PRINCIPLE**: Tests validate EXPECTED behavior, not current behavior
- **RULE**: If existing code fails a test, FIX THE CODE, not the test
- **RULE**: Tests document how the system SHOULD work
- **FORBIDDEN**: Writing tests that simply match faulty logic

### 4. Test Quality Standards

**Each test MUST:**
- Have a single, clear purpose (one assertion per concept)
- Be independent and isolated from other tests
- Use descriptive names that explain expected behavior
- Test outcomes and behavior, not implementation details
- Include proper async/await patterns for async code

**Example of CORRECT test naming:**
```python
# ✅ CORRECT: Describes expected behavior
async def test_bracket_order_creates_parent_stop_and_target_orders():

# ❌ WRONG: Describes implementation
async def test_place_bracket_order_method():
```

## TDD Enforcement Rules

### 5. Code Review Requirements

**Before any code merge:**
- [ ] Corresponding tests exist and were written FIRST
- [ ] Tests define expected behavior, not match current behavior
- [ ] All tests pass in RED-GREEN-REFACTOR cycle
- [ ] Test coverage includes edge cases and error scenarios
- [ ] No implementation details leak into test assertions

### 6. Bug Fix Process

**When fixing bugs:**
1. Write a test that reproduces the bug (RED)
2. Confirm test fails due to bug
3. Fix the implementation to make test pass (GREEN)
4. Refactor if needed while keeping test green
5. **NEVER** modify test to match buggy behavior

### 7. Refactoring Safety

**When refactoring:**
- Tests MUST pass before starting refactoring
- Tests MUST continue passing throughout refactoring
- If tests fail during refactoring, fix code not tests
- Only modify tests if requirements genuinely changed

## Critical TDD Violations

**These are NEVER acceptable:**

❌ **Writing implementation without tests**
❌ **Modifying tests to match broken code**
❌ **Skipping RED phase (not confirming test failure)**
❌ **Testing implementation details instead of behavior**
❌ **Writing multiple features before writing tests**
❌ **Commenting out failing tests instead of fixing code**

## TDD Success Metrics

**Measure TDD adherence by:**
- Tests written before implementation: 100%
- Bug fixes with reproduction tests: 100%
- Refactoring with passing tests: 100%
- Tests describing behavior vs implementation: 100%

Remember: **The test suite IS the specification. Code must conform to tests, not vice versa.**
