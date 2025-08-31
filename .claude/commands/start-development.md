---
name: start-development
description: Master command to initiate proper development workflow - reads project context, explains agents, and executes TDD methodology
---

# Start Development Workflow

This is the master command for initiating any development work on the project-x-py SDK. It ensures proper context, agent coordination, and TDD methodology.

## 🔍 Phase 1: Establishing Project Context

### Reading CLAUDE.md Guidelines

**Project Status**: v3.3.0 - Stable Production
- 100% async architecture required
- Strict TDD methodology enforced
- Semantic versioning with deprecation policy
- Testing: `./test.sh` for examples, `uv run pytest` for tests

**Key Principles**:
1. **Tests First**: Tests define specification, not implementation
2. **Async Only**: All APIs must be async
3. **Backward Compatible**: Deprecate gracefully over 2 minor versions
4. **Agent Coordination**: Use specialized agents for their domains

## 🤖 Phase 2: Agent Architecture Explanation

### Three-Tier Agent System

```
┌─────────────────────────────────────────────────────────┐
│                  COORDINATOR AGENTS                      │
│  (Orchestrate but don't implement - minimal tools)       │
│  • architecture-planner                                  │
│  • test-orchestrator                                     │
│  • deployment-coordinator                                │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│               IMPLEMENTATION AGENTS                      │
│        (Write code - full tool access)                   │
│  • python-developer    • code-refactor                   │
│  • code-documenter     • integration-tester              │
│  • release-manager                                       │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│              ANALYSIS & REVIEW AGENTS                    │
│         (Read-only - no write access)                    │
│  • code-reviewer       • code-standards-enforcer         │
│  • performance-optimizer • security-auditor              │
│  • code-debugger       • data-analyst                    │
└─────────────────────────────────────────────────────────┘
```

### Tool Access Philosophy
- **Write Access**: Only for agents that create/modify code
- **Read Access**: For analysis and review agents
- **Minimal Access**: For coordinator agents to enforce delegation

## 📋 Phase 3: Request Analysis

**Development Request**: {{request}}

### Analyzing Your Request...

Let me determine:
1. **Task Type**: [Bug Fix | Feature | Refactor | Test | Documentation]
2. **Complexity**: [Simple | Medium | Complex]
3. **Agents Needed**: [List of required agents]
4. **TDD Required**: [Yes | No]

## 🔄 Phase 4: TDD Workflow (if applicable)

If code changes are required, we follow:

### RED → GREEN → REFACTOR

1. **RED Phase** (Write Failing Tests):
   ```python
   # Test defines expected behavior
   @pytest.mark.asyncio
   async def test_new_functionality():
       # This test MUST fail initially
       assert expected_behavior()
   ```

2. **GREEN Phase** (Minimal Implementation):
   - Write just enough code to pass
   - Don't optimize yet
   - Focus on making tests green

3. **REFACTOR Phase** (Improve Quality):
   - Optimize implementation
   - Maintain green tests
   - Enhance readability

## 🎯 Phase 5: Execution Strategy

### Selected Workflow Pattern

Based on your request, I'll use:

**[Workflow Name]**
```
Step 1: [Agent] → [Action]
Step 2: [Agent] → [Action]
Step 3: [Agent] → [Action]
...
```

### Quality Checkpoints
- [ ] Tests written first (if code changes)
- [ ] All tests passing
- [ ] Type checking clean (`mypy`)
- [ ] Linting passed (`ruff`)
- [ ] Documentation updated
- [ ] Examples tested with `./test.sh`

## 🚀 Phase 6: Implementation

Now executing the development workflow for your request:

### Step-by-Step Execution

1. **Initial Setup**
   [Specific actions for your request]

2. **Test Creation** (if needed)
   [Test strategy for your request]

3. **Implementation**
   [Development approach]

4. **Validation**
   [Quality assurance steps]

5. **Documentation**
   [Documentation updates needed]

## 📊 Progress Tracking

Using TodoWrite to track progress:
- [ ] Context established
- [ ] Agents selected
- [ ] Tests written (if applicable)
- [ ] Implementation complete
- [ ] Quality validated
- [ ] Documentation updated

## 🎬 Beginning Development

With the context established, agents understood, and TDD methodology ready, I'm now proceeding with your specific development request...

---

*This workflow ensures consistency with project standards, proper agent utilization, and adherence to TDD principles throughout the development process.*
