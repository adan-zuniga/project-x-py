#!/usr/bin/env python3
"""Script to run all client module tests."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_client_tests(test_path=None, stop_on_first_failure=True):
    """Run client module tests and generate coverage report.

    Args:
        test_path: Optional path to specific test file or directory
        stop_on_first_failure: Stop after first test failure
    """
    # Get the directory of this script
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Default to all client tests if no path specified
    if not test_path:
        test_path = os.path.join(script_dir, "client")

    # Build command
    cmd = [
        "python",
        "-m",
        "pytest",
        test_path,
        "-v",  # Verbose output
    ]

    # Add option to stop on first failure
    if stop_on_first_failure:
        cmd.append("-xvs")

    # Add coverage options
    cmd.extend(
        [
            "--cov=project_x_py.client",
            "--cov-report=term",
        ]
    )

    # Execute the command
    try:
        subprocess.run(cmd, check=True, cwd=project_root)
        print("\nTests completed successfully!")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Error running tests: {e}")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run client module tests")
    parser.add_argument("--test-path", help="Specific test file or directory to run")
    parser.add_argument(
        "--continue-on-failure",
        action="store_true",
        help="Continue running tests after failures",
    )

    args = parser.parse_args()

    sys.exit(
        run_client_tests(
            test_path=args.test_path, stop_on_first_failure=not args.continue_on_failure
        )
    )
