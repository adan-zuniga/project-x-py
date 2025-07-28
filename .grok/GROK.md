# GROK.md

This file provides guidance to Grok CLI (x.ai/grok) when assisting with file editing, coding tasks, and system operations in this repository.

## Project Overview
This is a Python SDK/client library for the ProjectX Trading Platform Gateway API. It enables developers to build trading strategies with access to real-time market data, order management, and analysis using Polars for high-performance data processing.

**Note**: Focus on toolkit development, not on creating trading strategies.

## Tool Usage Guidelines
As Grok CLI, you have access to tools like view_file, create_file, str_replace_editor, bash, search, and todo lists. Use them efficiently for tasks.

- **ALWAYS** create a todo list for complex tasks.
- **NEVER** overwrite existing files with create_file; use str_replace_editor.
- **ALWAYS** view files before editing.
- For searches, use the search tool or bash commands like grep.

## Development Commands
Use bash tool to execute these:

### Package Management (UV)
uv add [package]              # Add a dependency
uv add --dev [package]        # Add a development dependency
uv sync                       # Install/sync dependencies
uv run [command]              # Run command in virtual environment

### Testing
uv run pytest                # Run all tests
uv run pytest tests/test_client.py  # Run specific test file

### Code Quality
uv run ruff check .          # Lint code
uv run ruff check . --fix    # Auto-fix linting issues
uv run ruff format .         # Format code
uv run mypy src/             # Type checking

## Project Architecture
Refer to CLAUDE.md for details, but when editing:
- Use dependency injection in clients and managers.
- Handle real-time data with WebSockets.
- Ensure thread safety with locks.

## Coding Rules for Edits
When using str_replace_editor:
- **ALWAYS** use modern Python 3.10+ features.
- **PREFER** Polars over Pandas.
- **ALWAYS** add type hints using | for unions.
- **HANDLE** errors with custom exceptions.

## Performance Considerations
- Implement memory management in edits (e.g., sliding windows).
- Optimize DataFrame operations with chaining and lazy evaluation.

## Integration with ProjectX API
- Use configurable endpoints.
- Validate payloads strictly.
- Map enums correctly.

For any updates, ensure consistency with .cursorrules and CLAUDE.md.

