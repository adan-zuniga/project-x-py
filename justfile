# project-x-py development commands

# Default recipe to display help
default:
    @just --list

# Sync version numbers across all files
version-sync:
    @echo "🔄 Synchronizing version numbers..."
    python scripts/version_sync.py

# Build package with version sync
build: version-sync
    @echo "🔨 Building package with synchronized versions..."
    uv build

# Development build (faster, no version sync)
build-dev:
    @echo "🔨 Development build..."
    uv build

# Build documentation with version sync
docs: version-sync
    @echo "📚 Building documentation..."
    python scripts/build-docs.py

# Run tests
test:
    @echo "🧪 Running tests..."
    uv run pytest

# Run linters
lint:
    @echo "🔍 Running linters..."
    uv run ruff check .
    uv run mypy src/

# Format code
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

# Bump patch version (1.0.1 -> 1.0.2)
bump-patch: version-sync
    #!/usr/bin/env python3
    import re
    from pathlib import Path
    
    init_file = Path("src/project_x_py/__init__.py")
    content = init_file.read_text()
    current = re.search(r'__version__ = "([^"]+)"', content).group(1)
    major, minor, patch = current.split(".")
    new_version = f"{major}.{minor}.{int(patch)+1}"
    new_content = re.sub(r'__version__ = "[^"]+"', f'__version__ = "{new_version}"', content)
    init_file.write_text(new_content)
    print(f"Version bumped: {current} → {new_version}")
    just version-sync

# Bump minor version (1.0.1 -> 1.1.0)
bump-minor: version-sync
    #!/usr/bin/env python3
    import re
    from pathlib import Path
    
    init_file = Path("src/project_x_py/__init__.py")
    content = init_file.read_text()
    current = re.search(r'__version__ = "([^"]+)"', content).group(1)
    major, minor, patch = current.split(".")
    new_version = f"{major}.{int(minor)+1}.0"
    new_content = re.sub(r'__version__ = "[^"]+"', f'__version__ = "{new_version}"', content)
    init_file.write_text(new_content)
    print(f"Version bumped: {current} → {new_version}")
    just version-sync

# Bump major version (1.0.1 -> 2.0.0)
bump-major: version-sync
    #!/usr/bin/env python3
    import re
    from pathlib import Path
    
    init_file = Path("src/project_x_py/__init__.py")
    content = init_file.read_text()
    current = re.search(r'__version__ = "([^"]+)"', content).group(1)
    major, minor, patch = current.split(".")
    new_version = f"{int(major)+1}.0.0"
    new_content = re.sub(r'__version__ = "[^"]+"', f'__version__ = "{new_version}"', content)
    init_file.write_text(new_content)
    print(f"Version bumped: {current} → {new_version}")
    just version-sync

# Full release process
release: clean test lint version-sync build
    @echo "🚀 Release package ready!"
    @echo "   Next steps:"
    @echo "   1. uv publish"
    @echo "   2. git tag v$(python -c 'from src.project_x_py import __version__; print(__version__)')"
    @echo "   3. git push --tags"

# Show current version
version:
    @python -c "from src.project_x_py import __version__; print(f'Current version: v{__version__}')"

# Check if versions are synchronized
check-version:
    @echo "🔍 Checking version synchronization..."
    python scripts/version_sync.py 