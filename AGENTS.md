# Repository Guidelines

## Project Structure & Module Organization
- `src/project_x_py/`: Library source (async client, order/position managers, indicators, utils).
- `tests/`: Pytest suite (`test_*.py`) with unit/integration markers.
- `examples/`: Usage patterns and reference strategies.
- `scripts/`: Dev utilities (`check_quality.sh`, docs, build helpers).
- `docs/` and `site/`: MkDocs docs and built site.
- `dist/`: Built wheels/sdists. Do not edit by hand.

## Build, Test, and Development Commands
- Setup: `uv sync` (or `pip install -e ".[dev]"`).
- Test all: `uv run pytest` (coverage and reports are enabled via config).
- Lint/format: `uv run ruff format .` then `uv run ruff check . --fix`.
- Type check: `uv run mypy src/`.
- Full quality gate: `./check_quality.sh`.
- Build artifacts: `uv run python -m build` (outputs to `dist/`).
- Docs (MkDocs): `./scripts/serve-docs.sh` (local) or `./scripts/deploy-docs.sh`.

## Coding Style & Naming Conventions
- Python 3.12+, async-first I/O; prefer `async/await` APIs.
- Formatting/linting via Ruff; line length 88, double quotes, space indentation.
- Use comprehensive type hints; prefer modern syntax (`dict[str, Any]`, `A | B`).
- Import order managed by Ruff/isort; first-party is `project_x_py`.
- Keep public APIs backward compatible; add deprecations before removals.

## Testing Guidelines
- Framework: Pytest with markers: `unit`, `integration`, `slow`, `realtime`.
- Naming: files `tests/test_*.py`, functions `test_*`.
- Run subsets: `uv run pytest -m "unit and not slow"`.
- Coverage runs by default; maintain or improve coverage for PRs.

## Commit & Pull Request Guidelines
- Prefer Conventional Commits (`feat:`, `fix:`, `docs:`). Version bumps use `vX.Y.Z: ...`.
- PRs must: describe changes, link issues, include tests/docs, and pass CI/`check_quality.sh`.
- Keep changes focused; update `CHANGELOG.md` when user-facing behavior changes.

## Security & Configuration Tips
- Never commit secrets. Use `.env` (see `.env.example`) and environment vars like `PROJECT_X_API_KEY`.
- Enable hooks: `uv run pre-commit install` then `uv run pre-commit run -a` before pushing.
- Run `uv run bandit -r src/` for security scans when touching critical paths.
