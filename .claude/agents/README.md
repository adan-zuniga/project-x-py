# ProjectX SDK Agent Configuration

This directory contains specialized agent configurations for the project-x-py async trading SDK development.

## Agent Directory

### Core Development Agents

1. **[python-developer](./python-developer.md)**
   - Async trading component development
   - Performance profiling and optimization
   - Integration testing with mock market data

2. **[code-standards-enforcer](./code-standards-enforcer.md)**
   - **ALWAYS checks IDE diagnostics first**
   - Enforces 100% async architecture
   - Pre-commit hooks and security scanning

3. **[code-debugger](./code-debugger.md)**
   - WebSocket and real-time debugging
   - Memory leak detection
   - Production log analysis

4. **[code-documenter](./code-documenter.md)**
   - API documentation generation
   - Migration guides and changelogs
   - Interactive documentation with MkDocs

5. **[code-refactor](./code-refactor.md)**
   - Architecture improvements
   - AST-based safe refactoring
   - Performance optimizations

6. **[code-reviewer](./code-reviewer.md)**
   - Comprehensive code reviews
   - Security and performance analysis
   - PR review automation

### Specialized Agents

7. **[performance-optimizer](./performance-optimizer.md)** 🆕
   - Memory and CPU profiling
   - Cache optimization
   - WebSocket message batching

8. **[integration-tester](./integration-tester.md)** 🆕
   - Market simulation
   - End-to-end testing
   - Load testing

9. **[security-auditor](./security-auditor.md)** 🆕
   - API key security
   - Vulnerability scanning
   - Compliance checks

10. **[release-manager](./release-manager.md)** 🆕
    - Semantic versioning
    - PyPI deployment
    - Release automation

11. **[data-analyst](./data-analyst.md)** 🆕
    - Indicator validation
    - Market analysis
    - Backtest metrics

## Agent Selection Guide

### By Task Type

#### Feature Development
- Primary: `python-developer`
- Support: `code-documenter`, `integration-tester`
- Review: `code-standards-enforcer`, `code-reviewer`

#### Bug Fixing
- Primary: `code-debugger`
- Support: `integration-tester`
- Review: `code-reviewer`

#### Performance Issues
- Primary: `performance-optimizer`
- Support: `code-refactor`, `code-debugger`
- Review: `code-reviewer`

#### Security Audit
- Primary: `security-auditor`
- Support: `code-debugger`
- Review: `code-reviewer`

#### Release Preparation
- Primary: `release-manager`
- Support: `code-standards-enforcer`, `security-auditor`
- Review: `code-reviewer`

#### Market Analysis
- Primary: `data-analyst`
- Support: `python-developer`
- Review: `code-reviewer`

## Collaboration Workflows

### Feature Implementation
```
1. data-analyst: Analyze requirements
2. python-developer: Implement feature
3. integration-tester: Create tests
4. code-standards-enforcer: Ensure compliance
5. performance-optimizer: Optimize if needed
6. code-documenter: Document feature
7. code-reviewer: Final review
```

### Production Issue
```
1. code-debugger: Investigate issue
2. integration-tester: Reproduce problem
3. python-developer: Implement fix
4. code-standards-enforcer: Verify quality
5. code-reviewer: Review fix
```

### Performance Optimization
```
1. performance-optimizer: Profile and identify bottlenecks
2. code-refactor: Plan optimization
3. python-developer: Implement improvements
4. integration-tester: Verify performance
5. code-reviewer: Review changes
```

### Security Audit
```
1. security-auditor: Comprehensive scan
2. code-debugger: Investigate vulnerabilities
3. python-developer: Fix issues
4. code-standards-enforcer: Verify secure coding
5. integration-tester: Test security measures
```

### Release Process
```
1. code-standards-enforcer: Pre-release checks
2. security-auditor: Security validation
3. integration-tester: Full test suite
4. release-manager: Version and deploy
5. code-documenter: Update docs
```

## MCP Server Usage

### Universal Access (All Agents)
- `mcp__aakarsh-sasi-memory-bank-mcp` - Progress tracking
- `mcp__mcp-obsidian` - Documentation
- `mcp__smithery-ai-filesystem` - File operations
- `mcp__ide` - IDE diagnostics

### Specialized Access
- `mcp__project-x-py_Docs` - Project documentation
- `mcp__upstash-context-7-mcp` - Library docs
- `mcp__waldzellai-clear-thought` - Problem solving
- `mcp__itseasy-21-mcp-knowledge-graph` - Dependencies
- `mcp__tavily-mcp` - External research
- `mcp__github` - GitHub operations

## Quick Start

### Using an Agent
```bash
# Example: Using python-developer agent
1. Read the agent documentation: .claude/agents/python-developer.md
2. Follow the agent's workflow and tools
3. Use specified MCP servers for the task
4. Apply the quality checklist before completion
```

### Multi-Agent Task
```bash
# Example: Implementing a new feature
1. Start with data-analyst for requirements
2. Use python-developer for implementation
3. Apply code-standards-enforcer checks
4. Create tests with integration-tester
5. Document with code-documenter
6. Final review with code-reviewer
```

## Best Practices

1. **Always start with IDE diagnostics** when using code-standards-enforcer
2. **Use agents concurrently** when tasks can be parallelized
3. **Document decisions** in Memory Bank and Obsidian
4. **Run tests frequently** during development
5. **Profile before optimizing** with performance-optimizer
6. **Security scan before release** with security-auditor

## Agent Capabilities Summary

| Agent | Primary Focus | Key Tools | MCP Servers |
|-------|--------------|-----------|-------------|
| python-developer | Async development | pytest, py-spy, mprof | Project docs, Clear Thought |
| code-standards-enforcer | Quality enforcement | IDE diagnostics, ruff, mypy | IDE, Project docs |
| code-debugger | Issue investigation | aiomonitor, objgraph | Clear Thought, IDE |
| code-documenter | Documentation | mkdocs, sphinx | Obsidian, Project docs |
| code-refactor | Architecture improvement | AST, libcst, pydeps | Clear Thought, Knowledge Graph |
| code-reviewer | Code review | semgrep, radon | GitHub, Project docs |
| performance-optimizer | Performance tuning | py-spy, mprof, benchmarks | Clear Thought, Memory Bank |
| integration-tester | E2E testing | Mock market, pytest | Memory Bank, Obsidian |
| security-auditor | Security validation | bandit, safety, trufflehog | Tavily, GitHub |
| release-manager | Release automation | bump2version, twine | GitHub, Memory Bank |
| data-analyst | Market analysis | TA-Lib, scipy, sklearn | Clear Thought, Obsidian |

## Updates and Maintenance

- Agents are version-controlled with the project
- Update agent configurations as tools evolve
- Add new agents as project needs grow
- Remove deprecated agents after migration period

Last Updated: 2025-01-23
