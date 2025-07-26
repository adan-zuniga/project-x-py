#!/usr/bin/env python3
"""
Version Synchronization Script for project-x-py

This script ensures all version references are synchronized with the single
source of truth in src/project_x_py/__init__.py before building.

Usage:
    python scripts/version_sync.py
    # Or as part of build process
    python scripts/version_sync.py && uv build
"""

import re
import sys
from pathlib import Path


def get_version_from_init():
    """Get version from the single source of truth."""
    init_file = Path("src/project_x_py/__init__.py")
    if not init_file.exists():
        raise FileNotFoundError(f"Cannot find {init_file}")

    content = init_file.read_text()
    match = re.search(r'__version__ = ["\']([^"\']+)["\']', content)
    if not match:
        raise ValueError("Cannot find __version__ in __init__.py")

    return match.group(1)


def update_pyproject_toml(version):
    """Update version in pyproject.toml."""
    pyproject_file = Path("pyproject.toml")
    if not pyproject_file.exists():
        print("⚠️  pyproject.toml not found, skipping")
        return False

    content = pyproject_file.read_text()
    new_content = re.sub(
        r'^version = ["\'][^"\']+["\']',
        f'version = "{version}"',
        content,
        flags=re.MULTILINE,
    )

    if content != new_content:
        pyproject_file.write_text(new_content)
        print(f"✅ Updated pyproject.toml to version {version}")
        return True
    else:
        print(f"✓  pyproject.toml already at version {version}")
        return False


def update_indicators_init(version):
    """Update version in indicators/__init__.py."""
    indicators_file = Path("src/project_x_py/indicators/__init__.py")
    if not indicators_file.exists():
        print("⚠️  indicators/__init__.py not found, skipping")
        return False

    content = indicators_file.read_text()
    new_content = re.sub(
        r'__version__ = ["\'][^"\']+["\']', f'__version__ = "{version}"', content
    )

    if content != new_content:
        indicators_file.write_text(new_content)
        print(f"✅ Updated indicators/__init__.py to version {version}")
        return True
    else:
        print(f"✓  indicators/__init__.py already at version {version}")
        return False


def update_readme(version):
    """Update version references in README.md."""
    readme_file = Path("README.md")
    if not readme_file.exists():
        print("⚠️  README.md not found, skipping")
        return False

    content = readme_file.read_text()
    changes_made = False

    # Update "Current Version" section
    new_content = re.sub(
        r"\*\*Current Version\*\*: v[\d.]+", f"**Current Version**: v{version}", content
    )

    # Update changelog section
    new_content = re.sub(
        r"### Version [\d.]+ \(Latest\)", f"### Version {version} (Latest)", new_content
    )

    if content != new_content:
        readme_file.write_text(new_content)
        print(f"✅ Updated README.md to version {version}")
        changes_made = True
    else:
        print(f"✓  README.md already at version {version}")

    return changes_made


def update_docs_conf(version):
    """Update version in docs/conf.py."""
    conf_file = Path("docs/conf.py")
    if not conf_file.exists():
        print("⚠️  docs/conf.py not found, skipping")
        return False

    content = conf_file.read_text()
    new_content = re.sub(
        r'release = ["\'][^"\']+["\']', f'release = "{version}"', content
    )
    new_content = re.sub(
        r'version = ["\'][^"\']+["\']', f'version = "{version}"', new_content
    )

    if content != new_content:
        conf_file.write_text(new_content)
        print(f"✅ Updated docs/conf.py to version {version}")
        return True
    else:
        print(f"✓  docs/conf.py already at version {version}")
        return False


def main():
    """Main synchronization process."""
    print("🔄 Synchronizing version numbers...")

    try:
        # Get the authoritative version
        version = get_version_from_init()
        print(f"📋 Source version: {version}")

        # Update all files
        changes = []
        changes.append(update_pyproject_toml(version))
        changes.append(update_indicators_init(version))
        changes.append(update_readme(version))
        changes.append(update_docs_conf(version))

        # Summary
        if any(changes):
            print(f"\n✅ Version synchronization complete! All files now at v{version}")
            print("   Ready for: uv build")
        else:
            print(f"\n✓  All files already synchronized at v{version}")

        return 0

    except Exception as e:
        print(f"\n❌ Error during version sync: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
