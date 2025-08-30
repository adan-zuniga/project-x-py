---
name: project-context
description: Establish project context by reading CLAUDE.md and understanding agent patterns before processing any development request
---

# Project Context and Development Workflow

This command ensures proper project context is established before any development work begins.

## Step 1: Project Guidelines Review

Reading CLAUDE.md to understand:

### Current Project Status
- Version: v3.3.0 - Complete Statistics Module Redesign
- Architecture: 100% async-only, optimized for high-performance futures trading
- Phase: Stable production status

### Critical Development Rules

1. **Testing Commands**:
   - `./test.sh` for running examples (handles environment variables)
   - `uv run pytest` for running tests
   - Never set PROJECT_X_API_KEY or PROJECT_X_USERNAME manually

2. **Backward Compatibility**:
   - Keep existing APIs functional with deprecation warnings
   - Mark deprecated features, remove after 2 minor versions
   - Follow semantic versioning strictly (MAJOR.MINOR.PATCH)

3. **TDD Methodology**:
   - Write tests BEFORE implementation
   - Tests define the specification
   - Code must conform to tests, not vice versa
   - Follow RED-GREEN-REFACTOR cycle

4. **Deprecation Process**:
   - Use `@deprecated` decorator from `project_x_py.utils.deprecation`
   - Keep deprecated features for at least 2 minor versions
   - Remove only in major version releases

## Step 2: Agent Pattern Understanding

### Agent Categories

1. **Implementation Agents** (Write Access):
   - `python-developer`: Core SDK development
   - `code-refactor`: Architecture improvements
   - `code-documenter`: Documentation creation
   - `integration-tester`: Test implementation
   - `release-manager`: Release execution

2. **Analysis Agents** (Read-Only):
   - `code-reviewer`: Code review
   - `code-standards-enforcer`: Standards compliance
   - `performance-optimizer`: Performance analysis
   - `security-auditor`: Security review
   - `code-debugger`: Issue investigation
   - `data-analyst`: Data validation

3. **Coordinator Agents** (Orchestration):
   - `architecture-planner`: System design
   - `test-orchestrator`: Test coordination
   - `deployment-coordinator`: Deployment orchestration

### Agent Tool Access
- Each agent has specific tools defined in `.claude/agents/[agent-name].md`
- Agents can only use tools explicitly granted to them
- Coordinator agents have minimal tools to enforce delegation

### Collaboration Patterns

#### Feature Development
```
architecture-planner → python-developer → integration-tester →
code-standards-enforcer → code-reviewer → code-documenter
```

#### Bug Fix
```
code-debugger → test-orchestrator → python-developer →
integration-tester → code-reviewer
```

#### Release
```
deployment-coordinator → code-standards-enforcer → security-auditor →
test-orchestrator → release-manager → code-documenter
```

## Step 3: Processing Development Request

**Your Request**: {{request}}

### Request Analysis

Based on the project context and agent patterns, I will now:

1. **Classify the request**:
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Refactoring
   - [ ] Documentation
   - [ ] Performance optimization
   - [ ] Testing

2. **Determine complexity**:
   - [ ] Simple (single agent)
   - [ ] Medium (2-3 agents)
   - [ ] Complex (coordinator + multiple agents)

3. **Select appropriate workflow**:
   - [ ] Direct implementation
   - [ ] TDD cycle required
   - [ ] Multi-agent coordination needed

4. **Identify required agents**:
   - Primary agent: [To be determined]
   - Supporting agents: [To be determined]
   - Coordinator needed: [Yes/No]

### Execution Plan

Based on the analysis, here's the development approach:

1. **Test Strategy** (if code changes required):
   - Write failing tests first (RED)
   - Define expected behavior
   - Set coverage targets

2. **Implementation**:
   - Use appropriate agents
   - Follow async-first architecture
   - Maintain backward compatibility

3. **Validation**:
   - Run tests with `uv run pytest`
   - Check standards compliance
   - Review code quality

4. **Documentation**:
   - Update relevant docs
   - Add examples if needed
   - Document any deprecations

## Next Steps

With the project context established and agent patterns understood, I'll now proceed with your specific request following the appropriate workflow...
