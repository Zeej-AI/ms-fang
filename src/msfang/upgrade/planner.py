"""Upgrade planner: turn scout report into actionable markdown."""

from __future__ import annotations


def build_plan(report: dict) -> str:
    lines = ["# Upgrade Plan", "", "## Candidates"]
    for comp in report.get("components", []):
        lines.append(
            f"- {comp['component']}: pinned `{comp['pinned']}` -> discovered `{comp['discovered']}` "
            f"(available={comp['update_available']}, risk={comp['risk']})"
        )
    lines.extend(
        [
            "",
            "## Validation Steps",
            "1. Run adapter compatibility tests.",
            "2. Run smoke tests in isolated runtime homes.",
            "3. Canary one low-risk ticket.",
            "",
            "## Rollback",
            "- Re-pin to previous ref in providers.lock.yaml and restart services.",
        ]
    )
    return "\n".join(lines) + "\n"
