#!/usr/bin/env python3
"""
Check for 100% async compliance in project-x-py SDK.
Python 3.12+ compatible.
"""

import ast
import sys
from pathlib import Path


class AsyncChecker(ast.NodeVisitor):
    """Check for synchronous methods in async classes."""

    def __init__(self, filename: str):
        self.filename = filename
        self.issues: list[tuple[int, str]] = []
        self.in_async_class = False
        self.class_stack: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check if class should be async."""
        self.class_stack.append(node.name)

        # Check if class has any async methods
        has_async = any(isinstance(item, ast.AsyncFunctionDef) for item in node.body)

        # Check if it's a manager or client class
        is_async_class = (
            "Manager" in node.name
            or "Client" in node.name
            or "Suite" in node.name
            or "Realtime" in node.name
            or has_async
        )

        old_in_async = self.in_async_class
        if is_async_class:
            self.in_async_class = True

        self.generic_visit(node)

        self.in_async_class = old_in_async
        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check for sync methods in async classes."""
        if self.in_async_class:
            # Skip special methods and private methods
            if not (
                node.name.startswith("__")
                or node.name.startswith("_")
                or node.name in ["__init__", "__str__", "__repr__"]
                or "@property"
                in [d.id for d in node.decorator_list if isinstance(d, ast.Name)]
                or "@staticmethod"
                in [d.id for d in node.decorator_list if isinstance(d, ast.Name)]
                or "@classmethod"
                in [d.id for d in node.decorator_list if isinstance(d, ast.Name)]
            ):
                # Check if method performs I/O operations
                if self._has_io_operations(node):
                    class_name = ".".join(self.class_stack)
                    self.issues.append(
                        (
                            node.lineno,
                            f"Synchronous method '{node.name}' in async class '{class_name}' performs I/O",
                        )
                    )

        self.generic_visit(node)

    def _has_io_operations(self, node: ast.FunctionDef) -> bool:
        """Check if function has I/O operations."""
        for item in ast.walk(node):
            if isinstance(item, ast.Call):
                if isinstance(item.func, ast.Attribute):
                    # Check for common I/O operations
                    if item.func.attr in [
                        "get",
                        "post",
                        "put",
                        "delete",
                        "patch",  # HTTP
                        "connect",
                        "send",
                        "recv",
                        "close",  # Socket
                        "read",
                        "write",
                        "open",  # File I/O
                        "execute",
                        "fetch",
                        "commit",  # Database
                    ]:
                        return True
                elif isinstance(item.func, ast.Name):
                    # Check for built-in I/O functions
                    if item.func.id in ["open", "print"]:
                        return True
        return False


def check_file(filepath: Path) -> list[tuple[str, int, str]]:
    """Check a single file for async compliance."""
    try:
        with open(filepath, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(filepath))
    except SyntaxError as e:
        return [(str(filepath), e.lineno or 0, f"Syntax error: {e.msg}")]

    checker = AsyncChecker(str(filepath))
    checker.visit(tree)

    return [(str(filepath), line, msg) for line, msg in checker.issues]


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: check_async.py <file1> [file2] ...")
        return 1

    all_issues = []
    for filepath in sys.argv[1:]:
        path = Path(filepath)
        if path.exists() and path.suffix == ".py":
            issues = check_file(path)
            all_issues.extend(issues)

    if all_issues:
        print("Async compliance issues found:")
        for filepath, line, msg in all_issues:
            print(f"  {filepath}:{line}: {msg}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
