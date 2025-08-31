---
name: dev-workflow
description: Standard development workflow for project-x-py SDK - ensures TDD methodology, agent coordination, and project guidelines are followed
---

# Development Workflow Command

This command establishes the standard development workflow for the project-x-py async trading SDK, ensuring adherence to TDD principles, proper agent usage, and project guidelines.

## Workflow Steps

### 1. Project Context Review
First, I will review the project guidelines to understand:
- Current project status and version
- TDD methodology requirements
- Async-first architecture requirements
- Deprecation and backward compatibility policies
- Testing requirements using `./test.sh` for examples and `uv run pytest` for tests

### 2. Agent Pattern Explanation
I will explain the agent coordination pattern for this task:
- **Implementation Agents**: Write code (python-developer, code-refactor, etc.)
- **Analysis Agents**: Review and analyze (code-reviewer, code-standards-enforcer, etc.)
- **Coordinator Agents**: Orchestrate workflows (architecture-planner, test-orchestrator, etc.)

Agents have specific tool access defined in `.claude/agents/`:
- Only agents with write access can modify code
- Analysis agents are read-only for reviewing
- Coordinator agents delegate to specialized agents

### 3. Task Analysis
I will analyze the request to determine:
- Complexity level (simple fix vs. complex feature)
- Required agents for the task
- Whether coordinator agents are needed
- Testing strategy following TDD principles

### 4. TDD Implementation Strategy
Following Test-Driven Development:
1. **RED**: Write failing tests that define expected behavior
2. **GREEN**: Write minimal code to make tests pass
3. **REFACTOR**: Improve code while keeping tests green

Tests are the specification - code must conform to tests, not vice versa.

### 5. Agent Coordination Plan
Based on the task, I will:
- Select appropriate agents for each phase
- Use coordinator agents for complex multi-agent workflows
- Ensure proper delegation based on agent capabilities
- Follow established collaboration patterns

### 6. Execution Plan
I will outline the specific steps:
1. Test creation (if needed)
2. Implementation
3. Standards enforcement
4. Code review
5. Documentation updates

## Request to Process

**User Request**: {{request}}

## Workflow Execution

Based on the above workflow, here's how I'll approach your request:

### Step 1: Understanding Your Request
[Analyze the specific request and determine the type of task]

### Step 2: Agent Selection
[Identify which agents are needed based on the task complexity]

### Step 3: TDD Approach
[If code changes are needed, outline the TDD strategy]

### Step 4: Implementation Plan
[Provide detailed steps for completing the task]

### Step 5: Quality Assurance
[Describe how we'll ensure quality through testing and review]

Let me proceed with this development workflow for your request.
