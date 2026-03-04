"""Runtime diagnostics and environment checks."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class RuntimeCheck:
    name: str
    ok: bool
    detail: str


def _run(cmd: list[str], timeout: int = 5) -> tuple[bool, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        return proc.returncode == 0, out or err
    except Exception as exc:
        return False, str(exc)


def run_phase0_checks(root: Path) -> dict:
    checks: list[RuntimeCheck] = []

    for binary in ["hermes", "openfang", "jcodemunch-mcp", "gh"]:
        path = shutil.which(binary)
        checks.append(RuntimeCheck(name=f"bin:{binary}", ok=bool(path), detail=path or "missing"))

    ok_gh, out_gh = _run(["gh", "auth", "status"], timeout=4)
    checks.append(RuntimeCheck(name="github_auth", ok=ok_gh, detail=out_gh))

    lms_bin = Path.home() / ".lmstudio" / "bin" / "lms"
    if lms_bin.exists():
        ok_lms, out_lms = _run([str(lms_bin), "server", "status"], timeout=4)
        lms_text = out_lms.lower()
        lms_running = ok_lms and "running" in lms_text and "not running" not in lms_text
        checks.append(RuntimeCheck(name="lmstudio_server", ok=lms_running, detail=out_lms))

        ok_api, out_api = _run([
            "curl",
            "-sS",
            "-m",
            "3",
            "http://127.0.0.1:1234/v1/models",
        ])
        detail = out_api[:200] if out_api else "no response"
        checks.append(RuntimeCheck(name="lmstudio_api", ok=ok_api, detail=detail))
    else:
        checks.append(RuntimeCheck(name="lmstudio_server", ok=False, detail="lms binary missing"))
        checks.append(RuntimeCheck(name="lmstudio_api", ok=False, detail="lms binary missing"))

    runtime_homes = {
        "hermes": str(Path.home() / ".msfang" / "hermes"),
        "openfang": str(Path.home() / ".msfang" / "openfang"),
        "jcodemunch": str(Path.home() / ".msfang" / "jcodemunch"),
    }
    for key, path in runtime_homes.items():
        checks.append(RuntimeCheck(name=f"runtime_home:{key}", ok=Path(path).exists(), detail=path))

    ok_count = sum(1 for c in checks if c.ok)
    result = {
        "ok": ok_count == len(checks),
        "score": f"{ok_count}/{len(checks)}",
        "checks": [asdict(c) for c in checks],
        "root": str(root),
    }
    return result


def print_phase0_checks(root: Path) -> None:
    print(json.dumps(run_phase0_checks(root), indent=2, sort_keys=True))
