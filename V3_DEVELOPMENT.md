# V3.0.0 Development Process

## Branch Strategy

This document outlines the development process for v3.0.0 of the ProjectX Python SDK.

### Current Setup
- **Branch**: `refactor_v3` 
- **Target**: v3.0.0 production-ready release
- **Base**: `main` (v2.x stable)

## Development Workflow

### 1. All v3 Development in `refactor_v3` Branch
```bash
# Always work in the refactor_v3 branch
git checkout refactor_v3

# Regular commits as you implement features
git add .
git commit -m "feat: implement feature X"
git push origin refactor_v3
```

### 2. Keep Branch Updated with Main (Optional)
```bash
# Periodically sync with main if needed
git checkout refactor_v3
git merge main
# Resolve any conflicts
git push origin refactor_v3
```

### 3. Pull Request Strategy

#### Option A: Draft PR (Recommended)
Create a single draft PR that remains open during development:
```bash
gh pr create --base main --head refactor_v3 --draft \
  --title "feat: v3.0.0 Major Refactor" \
  --body "See SDK_IMPROVEMENTS_PLAN.md"
```

Benefits:
- Track progress in one place
- Run CI/CD on each push
- Easy to review changes
- Convert to ready when done

#### Option B: Feature PRs to `refactor_v3`
Create separate PRs for each major feature:
```bash
# Create feature branch from refactor_v3
git checkout refactor_v3
git checkout -b feat/event-system

# Work on feature
git add .
git commit -m "feat: implement unified event system"

# PR to refactor_v3, not main!
gh pr create --base refactor_v3 --head feat/event-system
```

Benefits:
- Smaller, focused reviews
- Better commit history
- Easier to revert features

### 4. Final Merge to Main
When v3.0.0 is complete:
```bash
# Update version to remove -dev
# Update CHANGELOG.md
# Final testing

# Convert draft to ready or create final PR
gh pr ready <PR-NUMBER>

# Squash merge to main
# Tag as v3.0.0
```

## Implementation Phases

Following SDK_IMPROVEMENTS_PLAN.md:

### Week 1: Foundation
- [ ] Simplified Initialization (TradingSuite class)
- [ ] Better Type Hints (Enums, TypedDict)

### Week 2: Core Enhancements
- [ ] Event-Driven Architecture (EventBus)

### Week 3: Data and Orders
- [ ] Simplified Data Access
- [ ] Strategy-Friendly Data Structures

### Week 4: Advanced Features
- [ ] Order Lifecycle Management

### Week 5: Risk and Recovery
- [ ] Built-in Risk Management
- [ ] Better Error Recovery

## Testing Strategy

### Continuous Testing in Branch
- All tests must pass in `refactor_v3`
- Update tests as you refactor
- Add new tests for new features

### Integration Testing
```bash
# Run full test suite
uv run pytest

# Run with coverage
uv run pytest --cov=project_x_py --cov-report=html
```

## Documentation Updates

### During Development
- Update docstrings immediately
- Keep examples working
- Document breaking changes

### Before Merge
- Complete API documentation
- Migration guide from v2 to v3
- Update all examples

## Version Management

### During Development
- Version: `3.0.0-dev`
- Update both `pyproject.toml` and `__init__.py`

### Pre-release Testing
- Version: `3.0.0-rc1`, `3.0.0-rc2`, etc.
- Tag pre-releases for testing

### Final Release
- Version: `3.0.0`
- Tag and create GitHub release

## Breaking Changes Documentation

Track all breaking changes in `BREAKING_CHANGES_V3.md`:
- Old API vs New API
- Migration examples
- Removal list

## Communication

### Progress Updates
- Update PR description weekly
- Use PR comments for decisions
- Link related issues

### Team Sync
- Regular reviews of refactor_v3
- Discuss major decisions before implementation
- Test early and often