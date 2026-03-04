"""OpenFang runtime adapter backed by the OpenFang CLI."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class WorkerResult:
    success: bool
    output: str
    needs_input: bool = False
    failed: bool = False


@dataclass
class OpenFangAdapterConfig:
    executable: str = "openfang"
    config_path: Path | None = None
    profiles_path: Path | None = None
    timeout_seconds: int = 120


class OpenFangAdapter:
    def __init__(self, config: OpenFangAdapterConfig | None = None):
        self.config = config or OpenFangAdapterConfig()

    def _base_cmd(self) -> list[str]:
        cmd = [self.config.executable]
        if self.config.config_path:
            cmd.extend(["--config", str(self.config.config_path)])
        return cmd

    def _run(self, args: list[str]) -> tuple[bool, str, str]:
        cmd = self._base_cmd() + args
        env = os.environ.copy()
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.config.timeout_seconds,
            env=env,
        )
        return proc.returncode == 0, proc.stdout.strip(), proc.stderr.strip()

    def status(self) -> dict:
        ok, out, err = self._run(["status", "--json"])
        if ok:
            try:
                return {"ok": True, "data": json.loads(out)}
            except Exception:
                return {"ok": True, "data": out}
        return {"ok": False, "error": err or out}

    def health(self) -> dict:
        ok, out, err = self._run(["health", "--json"])
        if ok:
            try:
                return {"ok": True, "data": json.loads(out)}
            except Exception:
                return {"ok": True, "data": out}
        return {"ok": False, "error": err or out}

    def start(self) -> dict:
        ok, out, err = self._run(["start"])
        return {"ok": ok, "output": out, "error": err}

    def run_task(self, agent: str, task: str, context: str = "") -> WorkerResult:
        text = task if not context else f"{task}\n\nContext:\n{context}"
        ok, out, err = self._run(["message", "--json", agent, text])
        if ok:
            return WorkerResult(success=True, output=out)

        merged = (err or out).strip()
        needs_input = any(x in merged.lower() for x in ["no daemon", "missing api key", "not found"])
        return WorkerResult(success=False, output=merged, needs_input=needs_input, failed=True)

    def run_profile(self, profile_name: str, task: str, context: str = "", profiles_path: Path | None = None) -> WorkerResult:
        path = profiles_path or self.config.profiles_path
        if not path:
            return WorkerResult(success=False, output="openfang profiles path is not configured", needs_input=True, failed=True)
        if not path.exists():
            return WorkerResult(
                success=False,
                output=f"openfang profiles file not found: {path}",
                needs_input=True,
                failed=True,
            )

        data = _parse_yaml_or_json(path.read_text(encoding="utf-8"))
        profiles = data.get("profiles", {})
        if not isinstance(profiles, dict):
            return WorkerResult(success=False, output="invalid openfang profiles payload", needs_input=True, failed=True)

        profile = profiles.get(profile_name)
        if not isinstance(profile, dict):
            return WorkerResult(
                success=False,
                output=f"unknown openfang profile: {profile_name}",
                needs_input=True,
                failed=True,
            )

        agent = str(profile.get("agent", "coder")).strip() or "coder"
        instructions = str(profile.get("instructions", "")).strip()

        composed_task = task
        if instructions:
            composed_task = f"Profile Instructions:\n{instructions}\n\nTask:\n{task}"

        return self.run_task(agent=agent, task=composed_task, context=context)


def _parse_yaml_or_json(text: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore

        parsed = yaml.safe_load(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
