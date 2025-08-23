#!/usr/bin/env python3
"""
Check for Python 3.12+ compatibility.
"""

import ast
import sys


class Python312Checker(ast.NodeVisitor):
    """Check for Python 3.12+ features and compatibility."""

    def __init__(self):
        self.warnings: list[tuple[int, str]] = []

    def visit_Match(self, node: ast.Match) -> None:
        """Match statements are good - Python 3.10+."""
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Type annotations are good."""
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check for deprecated patterns."""
        if isinstance(node.func, ast.Name):
            # Check for deprecated functions
            if node.func.id in ["execfile", "reload"]:
                self.warnings.append(
                    (node.lineno, f"Deprecated function '{node.func.id}' used")
                )
        self.generic_visit(node)


def check_python_version() -> int:
    """Check Python version."""
    if sys.version_info < (3, 12):
        print(f"Error: Python 3.12+ required, got {sys.version}")
        return 1

    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return 0


def main() -> int:
    """Main entry point."""
    return check_python_version()


if __name__ == "__main__":
    sys.exit(main())
