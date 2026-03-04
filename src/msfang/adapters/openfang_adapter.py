"""OpenFang worker runtime adapter (v1 thin stub)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WorkerResult:
    success: bool
    output: str
    needs_input: bool = False
    failed: bool = False


class OpenFangAdapter:
    def run_task(self, task: str, context: str = "") -> WorkerResult:
        # Thin placeholder contract. Real implementation will call OpenFang APIs.
        output = f"openfang_stub: task={task}; context={context}"
        return WorkerResult(success=True, output=output)
