#!/usr/bin/env python3
"""
Generate changelog from git commits.
Python 3.12+ compatible.
"""

import re
import subprocess
from datetime import datetime


class ChangelogGenerator:
    """Generate changelog from conventional commits."""

    def __init__(self):
        self.categories = {
            "feat": "✨ Features",
            "fix": "🐛 Bug Fixes",
            "docs": "📚 Documentation",
            "style": "💎 Code Style",
            "refactor": "♻️ Refactoring",
            "perf": "⚡ Performance",
            "test": "✅ Testing",
            "build": "📦 Build System",
            "ci": "🎡 CI/CD",
            "chore": "🔧 Maintenance",
            "BREAKING": "💥 Breaking Changes",
        }

    def get_version(self) -> str:
        """Get current version from package."""
        try:
            result = subprocess.run(
                [
                    "python",
                    "-c",
                    "from project_x_py import __version__; print(__version__)",
                ],
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        except:
            return "Unknown"

    def get_last_tag(self) -> str:
        """Get the last git tag."""
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        except:
            return ""

    def get_commits(self, since: str = "") -> list[dict[str, str]]:
        """Get commits since last tag."""
        cmd = ["git", "log", "--pretty=format:%H|%s|%b|%an|%ae"]

        if since:
            cmd.append(f"{since}..HEAD")
        else:
            cmd.append("-20")  # Last 20 commits if no tag

        result = subprocess.run(cmd, capture_output=True, text=True)

        commits = []
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("|")
                if len(parts) >= 5:
                    commits.append(
                        {
                            "hash": parts[0][:8],
                            "subject": parts[1],
                            "body": parts[2],
                            "author": parts[3],
                            "email": parts[4],
                        }
                    )

        return commits

    def categorize_commits(
        self, commits: list[dict[str, str]]
    ) -> dict[str, list[dict[str, str]]]:
        """Categorize commits by type."""
        categorized: dict[str, list[dict[str, str]]] = {
            cat: [] for cat in self.categories.values()
        }
        categorized["Other"] = []

        for commit in commits:
            subject = commit["subject"]
            body = commit["body"]

            # Check for breaking changes
            if "BREAKING" in subject or "BREAKING" in body:
                categorized["💥 Breaking Changes"].append(commit)
                continue

            # Parse conventional commit format
            match = re.match(r"^(\w+)(?:\([^)]+\))?:\s*(.+)", subject)
            if match:
                commit_type = match.group(1)
                commit["clean_subject"] = match.group(2)

                category = self.categories.get(commit_type)
                if category:
                    categorized[category].append(commit)
                else:
                    categorized["Other"].append(commit)
            else:
                categorized["Other"].append(commit)

        # Remove empty categories
        return {k: v for k, v in categorized.items() if v}

    def generate(self) -> str:
        """Generate the changelog."""
        version = self.get_version()
        last_tag = self.get_last_tag()
        commits = self.get_commits(last_tag)
        categorized = self.categorize_commits(commits)

        # Build changelog
        lines = [
            f"# Release Notes for v{version}",
            "",
            f"**Date**: {datetime.now().strftime('%Y-%m-%d')}",
            "",
        ]

        # Add breaking changes first if any
        if "💥 Breaking Changes" in categorized:
            lines.extend(
                [
                    "## 💥 Breaking Changes",
                    "",
                    "⚠️ **This release contains breaking changes that may require code updates.**",
                    "",
                ]
            )
            for commit in categorized["💥 Breaking Changes"]:
                subject = commit.get("clean_subject", commit["subject"])
                lines.append(f"- {subject} ({commit['hash']})")
            lines.append("")

        # Add other categories
        for category, commits in categorized.items():
            if category == "💥 Breaking Changes":
                continue  # Already handled

            lines.extend([f"## {category}", ""])

            for commit in commits:
                subject = commit.get("clean_subject", commit["subject"])
                author = commit["author"]

                # Format line
                line = f"- {subject}"
                if author != "TexasCoding":  # Don't show default author
                    line += f" (by @{author})"
                line += f" ({commit['hash']})"

                lines.append(line)

            lines.append("")

        # Add contributors section
        contributors = set(
            commit["author"] for commits in categorized.values() for commit in commits
        )

        if len(contributors) > 1:
            lines.extend(
                [
                    "## 👥 Contributors",
                    "",
                    "Thanks to all contributors to this release:",
                    "",
                ]
            )
            for contributor in sorted(contributors):
                if contributor != "TexasCoding":
                    lines.append(f"- @{contributor}")
            lines.append("")

        # Add footer
        lines.extend(
            [
                "---",
                "",
                "**Full Changelog**: "
                + f"[{last_tag}...v{version}]"
                + f"(https://github.com/TexasCoding/project-x-py/compare/{last_tag}...v{version})",
            ]
        )

        return "\n".join(lines)


def main() -> None:
    """Main entry point."""
    generator = ChangelogGenerator()
    changelog = generator.generate()
    print(changelog)

    # Optionally save to file
    if "--save" in sys.argv:
        with open("RELEASE_NOTES.md", "w") as f:
            f.write(changelog)
        print("\nChangelog saved to RELEASE_NOTES.md")


if __name__ == "__main__":
    import sys

    main()
