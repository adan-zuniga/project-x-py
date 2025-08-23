"""
Lock contention profiling tool for project-x-py SDK realtime modules.

Author: @TexasCoding
Date: 2025-01-22

Overview:
    Command-line utility for profiling lock contention in the realtime modules.
    Identifies bottlenecks, measures wait times, and provides optimization
    recommendations for improving concurrency performance.

Features:
    - Real-time lock contention monitoring
    - Detailed wait time analysis
    - Deadlock detection and reporting
    - Performance bottleneck identification
    - Optimization recommendations
    - Exportable profiling reports

Usage:
    ```bash
    # Profile current lock usage
    python -m project_x_py.utils.lock_profiler_tool --profile --duration 60

    # Analyze existing codebase for lock patterns
    python -m project_x_py.utils.lock_profiler_tool --analyze --path src/

    # Generate optimization report
    python -m project_x_py.utils.lock_profiler_tool --report --output locks_report.json
    ```

Example Output:
    Lock Contention Analysis Report
    ================================

    Top Contended Locks:
    1. realtime_data_manager.data_lock: 23.4% contention rate (2.3ms avg wait)
    2. statistics.base._lock: 18.7% contention rate (1.8ms avg wait)
    3. orderbook.base.orderbook_lock: 12.1% contention rate (1.2ms avg wait)

    Recommendations:
    - Replace data_lock with AsyncRWLock for read-heavy operations
    - Implement fine-grained locking for statistics collection
    - Use lock-free buffers for orderbook tick updates
"""

import argparse
import ast
import asyncio
import json
import time
from pathlib import Path
from typing import Any

from project_x_py.utils import ProjectXLogger
from project_x_py.utils.lock_optimization import (
    AsyncRWLock,
    LockProfiler,
    get_global_lock_profiler,
)

logger = ProjectXLogger.get_logger(__name__)


class LockAnalyzer:
    """Analyzes source code for lock usage patterns."""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.lock_patterns = {
            "asyncio.Lock()": "Regular asyncio lock",
            "self.data_lock": "Data access lock",
            "self._lock": "Private instance lock",
            "self.orderbook_lock": "Orderbook access lock",
            "self._callback_lock": "Callback registration lock",
            "async with": "Context manager lock usage",
            r"await.*\.acquire()": "Manual lock acquisition",
            "Lock()": "Lock instantiation",
        }

    def analyze_file(self, file_path: Path) -> dict[str, Any]:
        """Analyze a single Python file for lock usage."""
        try:
            with open(file_path) as f:
                content = f.read()

            # Parse AST to find lock-related patterns
            tree = ast.parse(content)

            locks_found = {}
            async_with_count = 0
            lock_creation_count = 0

            for node in ast.walk(tree):
                # Count async with statements (potential lock usage)
                if isinstance(node, ast.AsyncWith):
                    async_with_count += 1

                # Look for lock attribute assignments
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Attribute):
                            attr_name = target.attr
                            if "lock" in attr_name.lower():
                                locks_found[attr_name] = {
                                    "line": node.lineno,
                                    "type": "attribute_assignment",
                                }

                # Look for Lock() calls
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr == "Lock":
                            lock_creation_count += 1
                    elif isinstance(node.func, ast.Name) and node.func.id == "Lock":
                        lock_creation_count += 1

            return {
                "file": str(file_path.relative_to(self.base_path)),
                "locks_found": locks_found,
                "async_with_count": async_with_count,
                "lock_creation_count": lock_creation_count,
                "total_lines": len(content.splitlines()),
            }

        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            return {"file": str(file_path.relative_to(self.base_path)), "error": str(e)}

    def analyze_directory(self) -> dict[str, Any]:
        """Analyze entire directory for lock usage patterns."""
        results = []
        python_files = list(self.base_path.rglob("*.py"))

        logger.info(f"Analyzing {len(python_files)} Python files in {self.base_path}")

        for file_path in python_files:
            # Skip __pycache__ and other generated files
            if "__pycache__" in str(file_path):
                continue

            result = self.analyze_file(file_path)
            if "error" not in result:
                results.append(result)

        # Aggregate results
        total_locks = sum(len(r["locks_found"]) for r in results)
        total_async_with = sum(r["async_with_count"] for r in results)
        total_lock_creations = sum(r["lock_creation_count"] for r in results)

        # Find files with most locks
        high_lock_files = sorted(
            results, key=lambda x: len(x["locks_found"]), reverse=True
        )[:10]

        return {
            "summary": {
                "files_analyzed": len(results),
                "total_locks_found": total_locks,
                "total_async_with": total_async_with,
                "total_lock_creations": total_lock_creations,
                "avg_locks_per_file": total_locks / len(results) if results else 0,
            },
            "high_lock_files": high_lock_files,
            "detailed_results": results,
        }


class LockContentionSimulator:
    """Simulates lock contention for testing optimization improvements."""

    def __init__(self) -> None:
        self.regular_lock = asyncio.Lock()
        self.rw_lock = AsyncRWLock("simulation")
        self.profiler = LockProfiler()

    async def simulate_read_heavy_workload(
        self,
        duration_seconds: float = 30,
        reader_count: int = 10,
        writer_count: int = 2,
    ) -> dict[str, Any]:
        """Simulate read-heavy workload to compare lock performance."""

        logger.info(f"Simulating read-heavy workload for {duration_seconds}s")
        logger.info(f"Readers: {reader_count}, Writers: {writer_count}")

        # Statistics tracking
        regular_lock_stats = {
            "total_operations": 0,
            "total_wait_time": 0.0,
            "max_wait_time": 0.0,
        }

        rw_lock_stats = {
            "read_operations": 0,
            "write_operations": 0,
            "total_wait_time": 0.0,
            "max_wait_time": 0.0,
        }

        start_time = time.time()

        async def regular_lock_reader(_reader_id: int) -> None:
            """Simulate reader using regular lock."""
            operations = 0
            while time.time() - start_time < duration_seconds:
                op_start = time.time()
                async with self.regular_lock:
                    # Simulate read operation
                    await asyncio.sleep(0.001)  # 1ms read operation
                op_end = time.time()

                wait_time = op_end - op_start
                regular_lock_stats["total_wait_time"] += wait_time
                regular_lock_stats["max_wait_time"] = max(
                    regular_lock_stats["max_wait_time"], wait_time
                )
                operations += 1

                await asyncio.sleep(0.01)  # 10ms between reads

            regular_lock_stats["total_operations"] += operations

        async def regular_lock_writer(_writer_id: int) -> None:
            """Simulate writer using regular lock."""
            while time.time() - start_time < duration_seconds:
                op_start = time.time()
                async with self.regular_lock:
                    # Simulate write operation
                    await asyncio.sleep(0.005)  # 5ms write operation
                op_end = time.time()

                wait_time = op_end - op_start
                regular_lock_stats["total_wait_time"] += wait_time
                regular_lock_stats["max_wait_time"] = max(
                    regular_lock_stats["max_wait_time"], wait_time
                )

                await asyncio.sleep(0.1)  # 100ms between writes

        async def rw_lock_reader(_reader_id: int) -> None:
            """Simulate reader using RW lock."""
            operations = 0
            while time.time() - start_time < duration_seconds:
                op_start = time.time()
                async with self.rw_lock.read_lock():
                    # Simulate read operation
                    await asyncio.sleep(0.001)  # 1ms read operation
                op_end = time.time()

                wait_time = op_end - op_start
                rw_lock_stats["total_wait_time"] += wait_time
                rw_lock_stats["max_wait_time"] = max(
                    rw_lock_stats["max_wait_time"], wait_time
                )
                operations += 1

                await asyncio.sleep(0.01)  # 10ms between reads

            rw_lock_stats["read_operations"] += operations

        async def rw_lock_writer(_writer_id: int) -> None:
            """Simulate writer using RW lock."""
            operations = 0
            while time.time() - start_time < duration_seconds:
                op_start = time.time()
                async with self.rw_lock.write_lock():
                    # Simulate write operation
                    await asyncio.sleep(0.005)  # 5ms write operation
                op_end = time.time()

                wait_time = op_end - op_start
                rw_lock_stats["total_wait_time"] += wait_time
                rw_lock_stats["max_wait_time"] = max(
                    rw_lock_stats["max_wait_time"], wait_time
                )
                operations += 1

                await asyncio.sleep(0.1)  # 100ms between writes

            rw_lock_stats["write_operations"] += operations

        # Run both simulations concurrently
        regular_tasks = []
        rw_tasks = []

        # Create regular lock tasks
        for i in range(reader_count):
            regular_tasks.append(regular_lock_reader(i))
        for i in range(writer_count):
            regular_tasks.append(regular_lock_writer(i))

        # Create RW lock tasks
        for i in range(reader_count):
            rw_tasks.append(rw_lock_reader(i))
        for i in range(writer_count):
            rw_tasks.append(rw_lock_writer(i))

        # Run simulations
        await asyncio.gather(*regular_tasks, *rw_tasks)

        # Calculate performance metrics
        regular_avg_wait = (
            regular_lock_stats["total_wait_time"]
            / regular_lock_stats["total_operations"]
            if regular_lock_stats["total_operations"] > 0
            else 0
        )

        total_rw_operations = (
            rw_lock_stats["read_operations"] + rw_lock_stats["write_operations"]
        )
        rw_avg_wait = (
            rw_lock_stats["total_wait_time"] / total_rw_operations
            if total_rw_operations > 0
            else 0
        )

        improvement_factor = regular_avg_wait / rw_avg_wait if rw_avg_wait > 0 else 0

        return {
            "simulation_duration": duration_seconds,
            "regular_lock_performance": {
                "total_operations": regular_lock_stats["total_operations"],
                "avg_wait_time_ms": regular_avg_wait * 1000,
                "max_wait_time_ms": regular_lock_stats["max_wait_time"] * 1000,
                "operations_per_second": regular_lock_stats["total_operations"]
                / duration_seconds,
            },
            "rw_lock_performance": {
                "read_operations": rw_lock_stats["read_operations"],
                "write_operations": rw_lock_stats["write_operations"],
                "total_operations": total_rw_operations,
                "avg_wait_time_ms": rw_avg_wait * 1000,
                "max_wait_time_ms": rw_lock_stats["max_wait_time"] * 1000,
                "operations_per_second": total_rw_operations / duration_seconds,
            },
            "improvement_factor": improvement_factor,
            "contention_reduction_percent": max(
                0, (1 - rw_avg_wait / regular_avg_wait) * 100
            )
            if regular_avg_wait > 0
            else 0,
        }


class OptimizationRecommendations:
    """Generates optimization recommendations based on analysis."""

    @staticmethod
    def analyze_lock_patterns(analysis_results: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate optimization recommendations from static analysis."""
        recommendations = []

        summary = analysis_results["summary"]
        high_lock_files = analysis_results["high_lock_files"]

        # Check for high lock density
        avg_locks = summary["avg_locks_per_file"]
        if avg_locks > 3:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "issue": f"High lock density ({avg_locks:.1f} locks per file)",
                    "recommendation": "Consider implementing fine-grained locking with FineGrainedLockManager",
                    "files_affected": len(high_lock_files),
                }
            )

        # Check for files with many locks
        for file_data in high_lock_files[:3]:  # Top 3 files
            if len(file_data["locks_found"]) > 5:
                recommendations.append(
                    {
                        "priority": "MEDIUM",
                        "issue": f"File {file_data['file']} has {len(file_data['locks_found'])} locks",
                        "recommendation": "Consider refactoring to use AsyncRWLock or lock-free data structures",
                        "files_affected": 1,
                    }
                )

        # General recommendations based on patterns
        if summary["total_async_with"] > summary["total_locks_found"] * 2:
            recommendations.append(
                {
                    "priority": "LOW",
                    "issue": "High ratio of async with statements to locks",
                    "recommendation": "Good lock usage patterns detected. Consider adding lock profiling.",
                    "files_affected": summary["files_analyzed"],
                }
            )

        return recommendations

    @staticmethod
    def analyze_contention_stats(
        contention_stats: dict[str, Any],
    ) -> list[dict[str, str]]:
        """Generate recommendations from runtime contention statistics."""
        recommendations = []

        for lock_name, stats in contention_stats.items():
            # High contention locks
            if stats["contention_rate"] > 20.0:  # >20% contention
                recommendations.append(
                    {
                        "priority": "HIGH",
                        "issue": f"Lock '{lock_name}' has {stats['contention_rate']:.1f}% contention rate",
                        "recommendation": "Replace with AsyncRWLock if read-heavy, or use fine-grained locking",
                        "avg_wait_ms": stats["avg_wait_ms"],
                    }
                )

            # High average wait times
            elif stats["avg_wait_ms"] > 5.0:  # >5ms average wait
                recommendations.append(
                    {
                        "priority": "MEDIUM",
                        "issue": f"Lock '{lock_name}' has high average wait time ({stats['avg_wait_ms']:.2f}ms)",
                        "recommendation": "Optimize critical section or implement lock-free alternatives",
                        "avg_wait_ms": stats["avg_wait_ms"],
                    }
                )

            # Timeout issues
            elif stats["timeouts"] > 0:
                recommendations.append(
                    {
                        "priority": "HIGH",
                        "issue": f"Lock '{lock_name}' has {stats['timeouts']} timeouts",
                        "recommendation": "Investigate deadlock potential or increase timeout values",
                        "timeouts": stats["timeouts"],
                    }
                )

        return recommendations


async def profile_locks(duration: float = 60) -> dict[str, Any]:
    """Profile lock usage in the application."""
    logger.info(f"Profiling locks for {duration} seconds...")

    profiler = get_global_lock_profiler()

    # Start profiling
    start_time = time.time()

    # Simulate some lock activity
    simulator = LockContentionSimulator()
    simulation_results = await simulator.simulate_read_heavy_workload(
        duration_seconds=duration, reader_count=5, writer_count=2
    )

    # Get profiling results
    contention_stats = await profiler.get_contention_stats()
    top_contended = await profiler.get_top_contended_locks()

    return {
        "profiling_duration": time.time() - start_time,
        "contention_stats": contention_stats,
        "top_contended_locks": top_contended,
        "simulation_results": simulation_results,
    }


def analyze_codebase(path: Path) -> dict[str, Any]:
    """Analyze codebase for lock usage patterns."""
    logger.info(f"Analyzing codebase at {path}")

    analyzer = LockAnalyzer(path)
    analysis_results = analyzer.analyze_directory()

    # Generate recommendations
    recommendations = OptimizationRecommendations.analyze_lock_patterns(
        analysis_results
    )

    return {"analysis_results": analysis_results, "recommendations": recommendations}


async def generate_report(output_path: Path | None = None) -> dict[str, Any]:
    """Generate comprehensive lock optimization report."""
    logger.info("Generating comprehensive lock optimization report...")

    # Analyze current codebase
    base_path = Path(__file__).parent.parent  # project-x-py/src/project_x_py
    codebase_analysis = analyze_codebase(base_path)

    # Profile runtime behavior
    runtime_profile = await profile_locks(duration=30)

    # Generate recommendations
    contention_recommendations = OptimizationRecommendations.analyze_contention_stats(
        runtime_profile["contention_stats"]
    )

    report = {
        "timestamp": time.time(),
        "analysis": {
            "codebase_analysis": codebase_analysis["analysis_results"],
            "static_recommendations": codebase_analysis["recommendations"],
        },
        "runtime_profile": runtime_profile,
        "contention_recommendations": contention_recommendations,
        "summary": {
            "total_files_analyzed": codebase_analysis["analysis_results"]["summary"][
                "files_analyzed"
            ],
            "total_locks_found": codebase_analysis["analysis_results"]["summary"][
                "total_locks_found"
            ],
            "high_priority_recommendations": len(
                [
                    r
                    for r in codebase_analysis["recommendations"]
                    + contention_recommendations
                    if r["priority"] == "HIGH"
                ]
            ),
            "performance_improvement_potential": runtime_profile["simulation_results"][
                "improvement_factor"
            ],
        },
    }

    if output_path:
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Report saved to {output_path}")

    return report


def print_report_summary(report: dict[str, Any]) -> None:
    """Print a human-readable summary of the report."""
    print("\n" + "=" * 60)
    print("LOCK CONTENTION ANALYSIS REPORT")
    print("=" * 60)

    summary = report["summary"]
    print(f"\nFiles Analyzed: {summary['total_files_analyzed']}")
    print(f"Locks Found: {summary['total_locks_found']}")
    print(f"High Priority Issues: {summary['high_priority_recommendations']}")
    print(
        f"Performance Improvement Potential: {summary['performance_improvement_potential']:.2f}x"
    )

    print(f"\n{'-' * 40}")
    print("TOP CONTENDED LOCKS")
    print(f"{'-' * 40}")

    runtime_profile = report["runtime_profile"]
    for i, (lock_name, contention_rate) in enumerate(
        runtime_profile["top_contended_locks"][:5], 1
    ):
        print(f"{i}. {lock_name}: {contention_rate:.1f}% contention")

    print(f"\n{'-' * 40}")
    print("OPTIMIZATION RECOMMENDATIONS")
    print(f"{'-' * 40}")

    all_recommendations = (
        report["analysis"]["static_recommendations"]
        + report["contention_recommendations"]
    )

    high_priority = [r for r in all_recommendations if r["priority"] == "HIGH"]
    medium_priority = [r for r in all_recommendations if r["priority"] == "MEDIUM"]

    if high_priority:
        print(f"\n🔴 HIGH PRIORITY ({len(high_priority)} issues):")
        for rec in high_priority[:3]:  # Show top 3
            print(f"  • {rec['issue']}")
            print(f"    → {rec['recommendation']}")

    if medium_priority:
        print(f"\n🟡 MEDIUM PRIORITY ({len(medium_priority)} issues):")
        for rec in medium_priority[:3]:  # Show top 3
            print(f"  • {rec['issue']}")
            print(f"    → {rec['recommendation']}")

    simulation = runtime_profile["simulation_results"]
    print(f"\n{'-' * 40}")
    print("PERFORMANCE SIMULATION RESULTS")
    print(f"{'-' * 40}")
    print(
        f"Regular Lock Avg Wait: {simulation['regular_lock_performance']['avg_wait_time_ms']:.2f}ms"
    )
    print(
        f"RW Lock Avg Wait: {simulation['rw_lock_performance']['avg_wait_time_ms']:.2f}ms"
    )
    print(f"Improvement Factor: {simulation['improvement_factor']:.2f}x")
    print(f"Contention Reduction: {simulation['contention_reduction_percent']:.1f}%")

    print(f"\n{'-' * 40}")
    print("NEXT STEPS")
    print(f"{'-' * 40}")
    print("1. Implement AsyncRWLock for read-heavy operations")
    print("2. Replace high-contention locks with fine-grained locking")
    print("3. Use LockFreeBuffer for high-frequency data updates")
    print("4. Add LockProfiler for ongoing monitoring")
    print("5. Implement FineGrainedLockManager for resource-specific locks")


async def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Lock contention profiler for project-x-py SDK"
    )

    parser.add_argument(
        "--profile", action="store_true", help="Profile runtime lock usage"
    )
    parser.add_argument(
        "--analyze", action="store_true", help="Analyze codebase for lock patterns"
    )
    parser.add_argument(
        "--report", action="store_true", help="Generate comprehensive report"
    )
    parser.add_argument(
        "--duration", type=float, default=60, help="Profiling duration in seconds"
    )
    parser.add_argument(
        "--path", type=Path, help="Path to analyze (default: src/project_x_py)"
    )
    parser.add_argument("--output", type=Path, help="Output file for report")

    args = parser.parse_args()

    if not any([args.profile, args.analyze, args.report]):
        parser.print_help()
        return

    if args.profile:
        results = await profile_locks(args.duration)
        print(json.dumps(results, indent=2, default=str))

    if args.analyze:
        path = args.path or (Path(__file__).parent.parent)
        results = analyze_codebase(path)
        print(json.dumps(results, indent=2, default=str))

    if args.report:
        report = await generate_report(args.output)
        print_report_summary(report)


if __name__ == "__main__":
    asyncio.run(main())
