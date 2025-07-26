.PHONY: version-sync build docs clean test lint help

# Version management
version-sync:
	@echo "🔄 Synchronizing version numbers..."
	@python scripts/version_sync.py

# Build with version sync
build: version-sync
	@echo "🔨 Building package with synchronized versions..."
	uv build

# Development build (faster, no version sync)
build-dev:
	@echo "🔨 Development build..."
	uv build

# Documentation build
docs: version-sync
	@echo "📚 Building documentation..."
	python scripts/build-docs.py

# Testing
test:
	@echo "🧪 Running tests..."
	uv run pytest

# Linting and formatting
lint:
	@echo "🔍 Running linters..."
	uv run ruff check .
	uv run mypy src/

format:
	@echo "✨ Formatting code..."
	uv run ruff format .

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.pyc" -delete

# Version bumping
bump-patch: version-sync
	@echo "📦 Bumping patch version..."
	@python -c "\
import re; \
from pathlib import Path; \
init_file = Path('src/project_x_py/__init__.py'); \
content = init_file.read_text(); \
current = re.search(r'__version__ = \"([^\"]+)\"', content).group(1); \
major, minor, patch = current.split('.'); \
new_version = f'{major}.{minor}.{int(patch)+1}'; \
new_content = re.sub(r'__version__ = \"[^\"]+\"', f'__version__ = \"{new_version}\"', content); \
init_file.write_text(new_content); \
print(f'Version bumped: {current} → {new_version}'); \
"
	@$(MAKE) version-sync

bump-minor: version-sync
	@echo "📦 Bumping minor version..."
	@python -c "\
import re; \
from pathlib import Path; \
init_file = Path('src/project_x_py/__init__.py'); \
content = init_file.read_text(); \
current = re.search(r'__version__ = \"([^\"]+)\"', content).group(1); \
major, minor, patch = current.split('.'); \
new_version = f'{major}.{int(minor)+1}.0'; \
new_content = re.sub(r'__version__ = \"[^\"]+\"', f'__version__ = \"{new_version}\"', content); \
init_file.write_text(new_content); \
print(f'Version bumped: {current} → {new_version}'); \
"
	@$(MAKE) version-sync

# Release process
release: clean test lint version-sync build
	@echo "🚀 Release package ready!"
	@echo "   Next steps:"
	@echo "   1. uv publish"
	@echo "   2. git tag v$$(python -c 'from src.project_x_py import __version__; print(__version__)')"
	@echo "   3. git push --tags"

# Help
help:
	@echo "📋 Available targets:"
	@echo "   version-sync   Sync version across all files"
	@echo "   build         Build package (with version sync)"
	@echo "   build-dev     Build package (no version sync)"
	@echo "   docs          Build documentation"
	@echo "   test          Run tests"
	@echo "   lint          Run linters"
	@echo "   format        Format code"
	@echo "   clean         Clean build artifacts"
	@echo "   bump-patch    Bump patch version"
	@echo "   bump-minor    Bump minor version"
	@echo "   release       Full release process"
	@echo "   help          Show this help" 