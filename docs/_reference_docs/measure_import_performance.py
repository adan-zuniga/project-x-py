#!/usr/bin/env python3
"""
Measure import performance for the ProjectX SDK.

This script helps track import time improvements from lazy loading optimizations.

Author: TexasCoding
Date: January 2025
"""

import importlib
import subprocess
import sys
import time
from pathlib import Path


def measure_import_time(module_name: str, fresh: bool = True) -> float:
    """
    Measure the time to import a module.

    Args:
        module_name: Name of module to import
        fresh: Whether to clear import cache first

    Returns:
        Import time in seconds
    """
    if fresh:
        # Clear module from cache
        if module_name in sys.modules:
            del sys.modules[module_name]

        # Also clear any submodules
        modules_to_clear = [
            mod for mod in sys.modules.keys() if mod.startswith(f"{module_name}.")
        ]
        for mod in modules_to_clear:
            del sys.modules[mod]

    start_time = time.perf_counter()
    importlib.import_module(module_name)
    end_time = time.perf_counter()

    return end_time - start_time


def measure_subprocess_import(module_name: str) -> float:
    """
    Measure import time in a fresh subprocess.

    This gives the most accurate measurement as it includes all dependencies.
    """
    code = f"""
import time
start = time.perf_counter()
import {module_name}
end = time.perf_counter()
print(end - start)
"""

    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env={**subprocess.os.environ, "PYTHONPATH": str(Path.cwd() / "src")},
    )

    if result.returncode != 0:
        print(f"Error importing {module_name}:")
        print(result.stderr)
        return -1.0

    return float(result.stdout.strip())


def main() -> None:
    """Run import performance measurements."""
    print("ProjectX SDK Import Performance Measurement")
    print("=" * 50)
    print()

    # Modules to test
    test_modules = [
        # Core modules
        ("project_x_py", "Full SDK"),
        ("project_x_py.client", "Client module"),
        ("project_x_py.exceptions", "Exceptions"),
        ("project_x_py.models", "Data models"),
        ("project_x_py.config", "Configuration"),
        # Heavy modules
        ("project_x_py.indicators", "All indicators"),
        ("project_x_py.indicators.momentum", "Momentum indicators"),
        ("project_x_py.orderbook", "Orderbook module"),
        ("project_x_py.utils", "Utilities"),
        # Managers
        ("project_x_py.order_manager", "Order manager"),
        ("project_x_py.position_manager", "Position manager"),
        ("project_x_py.realtime_data_manager", "Realtime data manager"),
    ]

    print("Testing import times (fresh subprocess for each)...")
    print()
    print(f"{'Module':<40} {'Time (ms)':<12} {'Description':<30}")
    print("-" * 82)

    total_time = 0.0
    failed_modules = []

    for module_name, description in test_modules:
        import_time = measure_subprocess_import(module_name)

        if import_time < 0:
            failed_modules.append(module_name)
            print(f"{module_name:<40} {'FAILED':<12} {description:<30}")
        else:
            time_ms = import_time * 1000
            total_time += import_time
            print(f"{module_name:<40} {time_ms:<12.1f} {description:<30}")

    print("-" * 82)
    print(f"{'TOTAL':<40} {total_time * 1000:<12.1f} {'All modules':<30}")
    print()

    if failed_modules:
        print(f"Failed to import: {', '.join(failed_modules)}")
        print()

    print("\nPerformance Tips:")
    print("- Import only what you need (e.g., 'from project_x_py import ProjectX')")
    print("- The SDK uses TYPE_CHECKING to minimize import overhead")
    print("- Import times are dominated by dependencies (polars, httpx) not SDK code")


if __name__ == "__main__":
    main()
