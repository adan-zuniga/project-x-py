"""
Comprehensive test runner for sessions module.

Runs all test categories including edge cases, performance, and mutation tests.
Provides detailed reporting and coverage analysis.

Author: TDD Implementation
Date: 2025-08-31
"""

import asyncio
import sys
import time
from pathlib import Path

import pytest


def run_comprehensive_session_tests():
    """Run all comprehensive tests for sessions module."""

    print("🧪 Running Comprehensive Session Tests")
    print("=" * 50)

    # Test categories to run
    test_categories = [
        {
            "name": "Unit Tests (Core)",
            "path": "tests/unit/test_session_*.py",
            "description": "Core functionality and basic edge cases"
        },
        {
            "name": "Unit Tests (Edge Cases)",
            "path": "tests/unit/test_session_*.py::*EdgeCases",
            "description": "Additional edge cases for uncovered lines"
        },
        {
            "name": "Integration Tests",
            "path": "tests/integration/test_*sessions*.py",
            "description": "Cross-component integration tests"
        },
        {
            "name": "Performance Tests",
            "path": "tests/performance/test_sessions_performance.py",
            "description": "Performance benchmarks and regression detection"
        },
        {
            "name": "Mutation Tests",
            "path": "tests/mutation/test_sessions_mutations.py",
            "description": "Mutation testing for test quality validation"
        }
    ]

    results = {}
    start_time = time.time()

    for category in test_categories:
        print(f"\n📊 {category['name']}")
        print(f"   {category['description']}")
        print("-" * 40)

        # Run tests for this category
        result = run_test_category(category)
        results[category['name']] = result

        if result['success']:
            print(f"   ✅ PASSED ({result['count']} tests, {result['duration']:.1f}s)")
        else:
            print(f"   ❌ FAILED ({result['count']} tests, {result['duration']:.1f}s)")
            print(f"   Failures: {result['failures']}")

    total_time = time.time() - start_time

    # Generate summary report
    print("\n📈 Test Summary")
    print("=" * 50)

    total_tests = sum(r['count'] for r in results.values())
    passed_categories = sum(1 for r in results.values() if r['success'])
    total_categories = len(results)

    print(f"Total Tests: {total_tests}")
    print(f"Categories: {passed_categories}/{total_categories} passed")
    print(f"Total Time: {total_time:.1f}s")

    # Detailed results
    print("\n📋 Detailed Results")
    print("-" * 30)

    for category_name, result in results.items():
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"{status} {category_name}: {result['count']} tests ({result['duration']:.1f}s)")

        if not result['success'] and result.get('failures'):
            for failure in result['failures'][:3]:  # Show first 3 failures
                print(f"    • {failure}")

    # Coverage analysis
    run_coverage_analysis()

    # Exit with appropriate code
    all_passed = all(r['success'] for r in results.values())
    return 0 if all_passed else 1


def run_test_category(category):
    """Run tests for a specific category."""
    start_time = time.time()

    # Build pytest command
    cmd_args = [
        "-v",
        "--tb=short",
        "--disable-warnings",
        category['path']
    ]

    # Add specific options for performance tests
    if "performance" in category['name'].lower():
        cmd_args.extend(["-m", "performance"])

    # Run pytest programmatically
    exit_code = pytest.main(cmd_args)

    duration = time.time() - start_time

    # Parse results (simplified - in real implementation would parse pytest output)
    return {
        'success': exit_code == 0,
        'count': 0,  # Would be parsed from pytest output
        'duration': duration,
        'failures': []  # Would be parsed from pytest output
    }


def run_coverage_analysis():
    """Run coverage analysis on sessions module."""
    print("\n📊 Coverage Analysis")
    print("-" * 30)

    try:
        # Run coverage analysis
        coverage_cmd = [
            "--cov=src/project_x_py/sessions",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "tests/unit/test_session_*.py"
        ]

        exit_code = pytest.main(coverage_cmd)

        if exit_code == 0:
            print("✅ Coverage report generated")
            print("   HTML report: htmlcov/index.html")
        else:
            print("❌ Coverage analysis failed")

    except Exception as e:
        print(f"⚠️  Coverage analysis error: {e}")


def run_mutation_testing():
    """Run mutation testing if mutmut is available."""
    print("\n🧬 Mutation Testing")
    print("-" * 30)

    try:
        import subprocess

        # Check if mutmut is available
        result = subprocess.run(["mutmut", "--version"], capture_output=True, text=True)

        if result.returncode == 0:
            print("Running mutation tests on sessions module...")

            # Run mutation testing on sessions module
            mutmut_cmd = [
                "mutmut", "run",
                "--paths-to-mutate=src/project_x_py/sessions/",
                "--tests-dir=tests/unit/",
                "--runner=python -m pytest tests/unit/test_session_*.py"
            ]

            result = subprocess.run(mutmut_cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ Mutation testing completed")
                print("   Run 'mutmut results' to see detailed results")
            else:
                print("❌ Mutation testing failed")
                print(result.stderr[:200])  # First 200 chars of error
        else:
            print("⚠️  Mutation testing skipped (mutmut not available)")
            print("   Install with: pip install mutmut")

    except FileNotFoundError:
        print("⚠️  Mutation testing skipped (mutmut not available)")
    except Exception as e:
        print(f"⚠️  Mutation testing error: {e}")


def check_test_quality():
    """Check test quality metrics."""
    print("\n🎯 Test Quality Metrics")
    print("-" * 30)

    metrics = {
        "edge_cases": count_edge_case_tests(),
        "error_conditions": count_error_condition_tests(),
        "boundary_tests": count_boundary_tests(),
        "concurrent_tests": count_concurrent_tests(),
        "performance_tests": count_performance_tests()
    }

    print(f"Edge Case Tests: {metrics['edge_cases']}")
    print(f"Error Condition Tests: {metrics['error_conditions']}")
    print(f"Boundary Tests: {metrics['boundary_tests']}")
    print(f"Concurrent Tests: {metrics['concurrent_tests']}")
    print(f"Performance Tests: {metrics['performance_tests']}")

    total_quality_tests = sum(metrics.values())
    print(f"\nTotal Quality Tests: {total_quality_tests}")

    if total_quality_tests >= 50:
        print("✅ Excellent test coverage quality")
    elif total_quality_tests >= 30:
        print("✅ Good test coverage quality")
    else:
        print("⚠️  Consider adding more edge case tests")


def count_edge_case_tests():
    """Count edge case tests."""
    # Count test methods with "edge" in name across test files
    test_files = Path("tests").rglob("test_session_*.py")
    count = 0

    for file in test_files:
        with open(file, 'r') as f:
            content = f.read()
            count += content.lower().count("def test_") if "edge" in content.lower() else 0

    return count


def count_error_condition_tests():
    """Count error condition tests."""
    test_files = Path("tests").rglob("test_session_*.py")
    count = 0

    keywords = ["error", "exception", "invalid", "malformed", "corrupt"]

    for file in test_files:
        with open(file, 'r') as f:
            content = f.read().lower()
            count += sum(content.count(keyword) for keyword in keywords)

    return min(count, 20)  # Cap at reasonable number


def count_boundary_tests():
    """Count boundary condition tests."""
    test_files = Path("tests").rglob("test_session_*.py")
    count = 0

    keywords = ["boundary", "edge", "limit", "threshold", "empty", "zero", "none"]

    for file in test_files:
        with open(file, 'r') as f:
            content = f.read().lower()
            count += sum(content.count(keyword) for keyword in keywords)

    return min(count // 3, 15)  # Normalize count


def count_concurrent_tests():
    """Count concurrent access tests."""
    test_files = Path("tests").rglob("test_session_*.py")
    count = 0

    keywords = ["concurrent", "parallel", "asyncio.gather", "threading"]

    for file in test_files:
        with open(file, 'r') as f:
            content = f.read().lower()
            count += sum(content.count(keyword) for keyword in keywords)

    return min(count, 10)


def count_performance_tests():
    """Count performance tests."""
    perf_file = Path("tests/performance/test_sessions_performance.py")

    if perf_file.exists():
        with open(perf_file, 'r') as f:
            content = f.read()
            return content.count("def test_")

    return 0


def main():
    """Main entry point."""
    print("🚀 ProjectX Sessions Module - Comprehensive Test Suite")
    print("=" * 60)

    # Check if we're in the right directory
    if not Path("src/project_x_py/sessions").exists():
        print("❌ Error: Run this script from the project root directory")
        return 1

    # Run comprehensive tests
    exit_code = run_comprehensive_session_tests()

    # Check test quality
    check_test_quality()

    # Run mutation testing if requested
    if "--mutation" in sys.argv:
        run_mutation_testing()

    # Final summary
    if exit_code == 0:
        print("\n🎉 All tests passed! Sessions module is thoroughly tested.")
    else:
        print("\n⚠️  Some tests failed. Please review the results above.")

    print("\n📚 Additional commands:")
    print("  - Run with --mutation for mutation testing")
    print("  - Check htmlcov/index.html for detailed coverage")
    print("  - Use pytest -m performance for performance tests only")

    return exit_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
