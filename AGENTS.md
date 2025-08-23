# Repository Guidelines

## Project Status: v3.1.1 - Stable Production Release

**IMPORTANT**: This project has reached stable production status. When making changes:

1. **Maintain Backward Compatibility**: Keep existing APIs functional with deprecation warnings
2. **Deprecation Policy**: Mark deprecated features with warnings, remove after 2 minor versions
3. **Semantic Versioning**: Follow semver strictly (MAJOR.MINOR.PATCH)
4. **Migration Paths**: Provide clear migration guides for breaking changes
5. **Modern Patterns**: Use the latest Python patterns while maintaining compatibility
6. **Gradual Refactoring**: Improve code quality without breaking existing interfaces
7. **Async-First**: All new code must use async/await patterns

### Deprecation Process
- Mark as deprecated with `warnings.warn()` and `@deprecated` decorator
- Document replacement in deprecation message
- Keep deprecated feature for at least 2 minor versions
- Remove only in major version releases (4.0.0, 5.0.0, etc.)

Example:
```python
import warnings
from typing import deprecated

@deprecated("Use new_method() instead. Will be removed in v4.0.0")
def old_method(self):
    warnings.warn(
        "old_method() is deprecated, use new_method() instead. "
        "Will be removed in v4.0.0",
        DeprecationWarning,
        stacklevel=2
    )
    return self.new_method()
```

## Project Structure & Module Organization
- Source: `src/project_x_py/` (core SDK: client, realtime, orderbook, indicators, utils, etc.).
- Tests: `tests/` (pytest; async tests supported).
- Examples: `examples/` (runnable end-to-end samples).
- Docs: `docs/` (Sphinx); helper script `scripts/build-docs.py`.
- Scripts: `scripts/` (build, docs, versioning). Build artifacts in `dist/` and coverage in `htmlcov/`.

## Build, Test, and Development Commands
- Install dev env: `uv sync` (or `pip install -e ".[dev]"`).
- Run tests + coverage: `uv run pytest` (HTML at `htmlcov/index.html`).
- Lint: `uv run ruff check .`  Format: `uv run ruff format .`  Types: `uv run mypy src`.
- Docs: `uv run python scripts/build-docs.py --clean --open`.
- CLI helpers: `uv run projectx-check` and `uv run projectx-config`.
- Run an example: `uv run python examples/01_basic_client_connection.py`.

## Coding Style & Naming Conventions
- Python 3.12+, 4-space indents, max line length 88.
- Format with Ruff formatter (Black-compatible); import order via Ruff/isort.
- Naming follows PEP 8; uppercase class names allowed in `indicators/` (see Ruff per-file ignores).
- Keep functions small, typed, and documented where behavior is non-obvious.

## Testing Guidelines
- Framework: pytest (+ pytest-asyncio). Place tests under `tests/` as `test_*.py`.
- Marks: `unit`, `integration`, `slow`, `realtime` (see `pyproject.toml`).
- Aim for meaningful coverage of public APIs; coverage reports are produced automatically.
- Prefer async-safe patterns; use fixtures and markers to isolate realtime or networked tests.

## Commit & Pull Request Guidelines
- Use Conventional Commits: `feat:`, `fix:`, `perf:`, `docs:`, `chore:`, etc. Add scope when helpful: `fix(orderbook): ...`.
- Keep subject ≤ 72 chars; body explains what/why and migration notes if breaking.
- Before PR: run `uv run ruff format . && uv run ruff check . && uv run mypy src && uv run pytest`.
- PRs include: clear description, linked issues, test updates, docs updates (if user-facing), and screenshots/logs when relevant.

## Security & Configuration Tips
- Auth via env vars `PROJECT_X_API_KEY`, `PROJECT_X_USERNAME`, or config at `~/.config/projectx/config.json`.
- Avoid committing secrets; prefer `.env` locally and CI secrets in GitHub.
- When adding realtime features, guard network calls in tests with markers.
