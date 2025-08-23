#!/usr/bin/env python3
"""
Comprehensive security audit for project-x-py SDK.
Python 3.12+ compatible.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class SecurityAuditor:
    """Run comprehensive security audits."""

    def __init__(self, project_root: Path = Path.cwd()):
        self.project_root = project_root
        self.results: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
            "checks": {},
        }

    def run_bandit(self) -> dict[str, Any]:
        """Run Bandit security scanner."""
        print("Running Bandit security scan...")
        try:
            result = subprocess.run(
                ["uv", "run", "bandit", "-r", "src/", "-ll", "-f", "json"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            data = json.loads(result.stdout) if result.stdout else {}

            return {
                "passed": len(data.get("results", [])) == 0,
                "issues": data.get("results", []),
                "metrics": data.get("metrics", {}),
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def run_safety(self) -> dict[str, Any]:
        """Run Safety dependency check."""
        print("Running Safety dependency check...")
        try:
            result = subprocess.run(
                ["uv", "run", "safety", "check", "--json"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            data = json.loads(result.stdout) if result.stdout else []

            return {"passed": len(data) == 0, "vulnerabilities": data}
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def run_pip_audit(self) -> dict[str, Any]:
        """Run pip-audit vulnerability check."""
        print("Running pip-audit...")
        try:
            result = subprocess.run(
                ["uv", "run", "pip-audit", "--format", "json"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            data = (
                json.loads(result.stdout) if result.stdout else {"vulnerabilities": []}
            )

            return {
                "passed": len(data.get("vulnerabilities", [])) == 0,
                "vulnerabilities": data.get("vulnerabilities", []),
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def check_secrets(self) -> dict[str, Any]:
        """Check for hardcoded secrets."""
        print("Checking for secrets...")
        try:
            # Initialize baseline if not exists
            baseline_file = self.project_root / ".secrets.baseline"
            if not baseline_file.exists():
                subprocess.run(
                    [
                        "uv",
                        "run",
                        "detect-secrets",
                        "scan",
                        "--baseline",
                        ".secrets.baseline",
                    ],
                    cwd=self.project_root,
                )

            # Scan for secrets
            result = subprocess.run(
                ["uv", "run", "detect-secrets", "scan"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            # Check against baseline
            audit_result = subprocess.run(
                ["uv", "run", "detect-secrets", "audit", ".secrets.baseline"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            return {
                "passed": "No secrets detected" in result.stdout
                or result.returncode == 0,
                "output": result.stdout,
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def check_api_key_usage(self) -> dict[str, Any]:
        """Check for proper API key handling."""
        print("Checking API key usage...")
        issues = []

        # Patterns to check
        bad_patterns = [
            r'api[_-]?key\s*=\s*["\'][^"\']+["\']',
            r'PROJECT_X_API_KEY\s*=\s*["\'][^"\']+["\']',
            r'password\s*=\s*["\'][^"\']+["\']',
        ]

        for py_file in self.project_root.glob("src/**/*.py"):
            content = py_file.read_text()

            for pattern in bad_patterns:
                import re

                if re.search(pattern, content, re.IGNORECASE):
                    issues.append(f"{py_file}: Potential hardcoded secret")

            # Check for environment variable usage
            if "os.environ" not in content and "PROJECT_X" in content:
                if "from_env" not in content:
                    issues.append(
                        f"{py_file}: Not using environment variables for config"
                    )

        return {"passed": len(issues) == 0, "issues": issues}

    def run_all_checks(self) -> None:
        """Run all security checks."""
        print("=" * 60)
        print("ProjectX SDK Security Audit")
        print("=" * 60)

        self.results["checks"]["bandit"] = self.run_bandit()
        self.results["checks"]["safety"] = self.run_safety()
        self.results["checks"]["pip_audit"] = self.run_pip_audit()
        self.results["checks"]["secrets"] = self.check_secrets()
        self.results["checks"]["api_keys"] = self.check_api_key_usage()

        # Calculate overall status
        all_passed = all(
            check.get("passed", False) for check in self.results["checks"].values()
        )

        self.results["overall_passed"] = all_passed

        # Print summary
        print("\n" + "=" * 60)
        print("Security Audit Summary")
        print("=" * 60)

        for check_name, check_result in self.results["checks"].items():
            status = "✅ PASSED" if check_result.get("passed") else "❌ FAILED"
            print(f"{check_name:20} {status}")

        print("=" * 60)
        overall = "✅ ALL CHECKS PASSED" if all_passed else "❌ SECURITY ISSUES FOUND"
        print(f"Overall Status: {overall}")

        # Save detailed report
        report_file = self.project_root / "security_audit_report.json"
        with open(report_file, "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\nDetailed report saved to: {report_file}")

        # Exit with appropriate code
        sys.exit(0 if all_passed else 1)


def main() -> None:
    """Main entry point."""
    auditor = SecurityAuditor()
    auditor.run_all_checks()


if __name__ == "__main__":
    main()
