"""Interactive-friendly bootstrap for MsFang operator setup."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class InitOptions:
    yes: bool = False
    force: bool = False
    owner_cli_user: str = ""
    owner_slack_id: str = ""
    channels_csv: str = "cli,slack"
    default_executor: str = "openfang"
    default_profile: str = "codex_cli"


def run_init(root: Path, options: InitOptions) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    config_dir = root / "config"
    tickets_dir = root / "tickets"
    ops_upgrades = root / "ops" / "upgrades"
    docs_plans = root / "docs" / "plans"

    for p in [config_dir, tickets_dir, ops_upgrades, docs_plans]:
        p.mkdir(parents=True, exist_ok=True)

    (tickets_dir / ".gitkeep").touch(exist_ok=True)
    (ops_upgrades / ".gitkeep").touch(exist_ok=True)

    owner_cli = options.owner_cli_user.strip() or os.getenv("USER", "operator")
    owner_slack = options.owner_slack_id.strip()
    channels = _parse_csv(options.channels_csv) or ["cli", "slack"]
    default_executor = (options.default_executor or "openfang").strip().lower()
    default_profile = (options.default_profile or "codex_cli").strip()

    if not options.yes and _stdin_is_tty():
        owner_cli = _prompt("CLI owner username", owner_cli)
        owner_slack = _prompt("Slack user ID (optional)", owner_slack)
        channels = _parse_csv(_prompt("Channels csv", ",".join(channels))) or channels
        default_executor = _prompt("Default executor (openfang/hermes)", default_executor).strip().lower()
        default_profile = _prompt("Default OpenFang profile", default_profile).strip()

    identities = {
        "owner": {
            "slack_user_ids": [owner_slack] if owner_slack else [],
            "cli_os_users": [owner_cli],
        },
        "channels": channels,
    }

    policies = {
        "action_risk_map": {
            "os_change": "red",
            "package_change": "red",
            "service_change": "red",
            "credential_change": "red",
            "upgrade_apply": "amber",
            "config_change": "amber",
            "code_change": "green",
            "test_run": "green",
        },
        "approval_required_for": ["red"],
        "strike_threshold_red": 3,
        "max_history": 50,
        "code_intel_provider": "jcodemunch",
        "enforce_jcodemunch_for_code_ops": True,
    }

    delegation = {
        "enforce_routes": True,
        "default_executor": default_executor,
        "default_openfang_profile": default_profile,
        "allowed_executors": ["hermes", "openfang"],
        "action_routes": {
            "code_change": "openfang",
            "test_run": "openfang",
            "upgrade_apply": "openfang",
            "config_change": "hermes",
            "os_change": "hermes",
            "package_change": "hermes",
            "service_change": "hermes",
            "credential_change": "hermes",
        },
        "command_routes": {
            "preflight": "hermes",
            "plan": "hermes",
            "execute": "openfang",
            "delegate": "openfang",
            "accept": "hermes",
            "undo": "hermes",
            "prompt": "hermes",
        },
    }

    openfang_profiles = {
        "default_profile": default_profile,
        "profiles": {
            "codex_cli": {
                "agent": "coder",
                "instructions": (
                    "Use Codex-style execution discipline. Produce explicit steps, "
                    "concrete edits, and verification commands."
                ),
            },
            "claude_cli": {
                "agent": "researcher",
                "instructions": (
                    "Use Claude-style broad synthesis for planning and ambiguity reduction, "
                    "then return concise actionable output."
                ),
            },
            "critic_fast": {
                "agent": "critic",
                "instructions": "Validate outcomes quickly and flag only material risks/regressions.",
            },
        },
    }

    runtime_homes = {
        "hermes_home": "~/.msfang/hermes",
        "openfang_home": "~/.msfang/openfang",
        "jcodemunch_home": "~/.msfang/jcodemunch",
    }

    writes = []
    writes.extend(_write_config(config_dir / "identities.yaml", identities, options.force))
    writes.extend(_write_config(config_dir / "policies.yaml", policies, options.force))
    writes.extend(_write_config(config_dir / "delegation.yaml", delegation, options.force))
    writes.extend(_write_config(config_dir / "openfang_profiles.yaml", openfang_profiles, options.force))
    writes.extend(_write_config(config_dir / "runtime_homes.yaml", runtime_homes, options.force))

    return {
        "ok": True,
        "root": str(root),
        "writes": writes,
        "settings": {
            "owner_cli_user": owner_cli,
            "owner_slack_id": owner_slack,
            "channels": channels,
            "default_executor": default_executor,
            "default_profile": default_profile,
        },
        "next_steps": [
            "Run `msfang doctor`",
            "Run `msfang preflight <ticket_id> --criteria ... --cli-user <you>`",
            "Run `msfang delegate <ticket_id> --action-type code_change --task \"...\"`",
        ],
    }


def _write_config(path: Path, payload: dict[str, Any], force: bool) -> list[dict[str, str]]:
    if path.exists() and not force:
        return [{"path": str(path), "status": "kept"}]
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return [{"path": str(path), "status": "written"}]


def _stdin_is_tty() -> bool:
    try:
        return bool(os.isatty(0))
    except Exception:
        return False


def _prompt(label: str, default: str) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


def _parse_csv(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]
