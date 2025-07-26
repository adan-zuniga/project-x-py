#!/usr/bin/env python3
"""
Build script for project-x-py that ensures version synchronization.

Usage:
    python scripts/build.py
    # Or with uv
    uv run scripts/build.pys
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: str, description: str) -> bool:
    """Run a command and return success status."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(
            cmd, shell=True, check=True, capture_output=True, text=True
        )
        if result.stdout.strip():
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(e.stdout)
        print(e.stderr)
        return False


def main():
    """Main build process with version synchronization."""
    print("🚀 Building project-x-py with version synchronization...")

    # Ensure we're in the project root
    project_root = Path(__file__).parent.parent
    original_cwd = Path.cwd()
    try:
        import os

        os.chdir(project_root)

        # Step 1: Sync versions
        if not run_command("python scripts/version_sync.py", "Synchronizing versions"):
            return 1

        # Step 2: Clean previous builds
        if not run_command(
            "rm -rf dist/ build/ *.egg-info/", "Cleaning build artifacts"
        ):
            print("⚠️  Clean failed, continuing...")

        # Step 3: Build package
        if not run_command("uv build", "Building package"):
            return 1

        print("✅ Build complete! Package ready in dist/")
        return 0

    finally:
        os.chdir(original_cwd)


if __name__ == "__main__":
    sys.exit(main())
