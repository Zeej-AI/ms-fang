"""Deterministic delegation policy for Hermes/OpenFang routing."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import DelegationError


@dataclass
class DelegationConfig:
    enforce_routes: bool
    default_executor: str
    action_routes: dict[str, str]
    command_routes: dict[str, str]
    default_openfang_profile: str
    allowed_executors: set[str]

    @classmethod
    def defaults(cls) -> "DelegationConfig":
        return cls(
            enforce_routes=True,
            default_executor="openfang",
            action_routes={
                "code_change": "openfang",
                "test_run": "openfang",
                "upgrade_apply": "openfang",
                "config_change": "hermes",
                "os_change": "hermes",
                "package_change": "hermes",
                "service_change": "hermes",
                "credential_change": "hermes",
            },
            command_routes={
                "preflight": "hermes",
                "plan": "hermes",
                "execute": "openfang",
                "delegate": "openfang",
                "accept": "hermes",
                "undo": "hermes",
                "prompt": "hermes",
            },
            default_openfang_profile="codex_cli",
            allowed_executors={"hermes", "openfang"},
        )


class DelegationEngine:
    def __init__(self, config: DelegationConfig):
        self.config = config

    @classmethod
    def from_file(cls, path: Path) -> "DelegationEngine":
        if not path.exists():
            return cls(DelegationConfig.defaults())

        data = _parse_yaml_or_json(path.read_text(encoding="utf-8"))
        defaults = DelegationConfig.defaults()
        return cls(
            DelegationConfig(
                enforce_routes=bool(data.get("enforce_routes", defaults.enforce_routes)),
                default_executor=str(data.get("default_executor", defaults.default_executor)),
                action_routes=dict(data.get("action_routes", defaults.action_routes)),
                command_routes=dict(data.get("command_routes", defaults.command_routes)),
                default_openfang_profile=str(data.get("default_openfang_profile", defaults.default_openfang_profile)),
                allowed_executors=set(data.get("allowed_executors", sorted(defaults.allowed_executors))),
            )
        )

    def route_action(self, action_type: str, requested_executor: str | None = None) -> str:
        configured = self.config.action_routes.get(action_type, self.config.default_executor)
        return self._finalize(
            route_key=f"action:{action_type}",
            configured_executor=configured,
            requested_executor=requested_executor,
        )

    def route_command(self, command_name: str, requested_executor: str | None = None) -> str:
        configured = self.config.command_routes.get(command_name, self.config.default_executor)
        return self._finalize(
            route_key=f"command:{command_name}",
            configured_executor=configured,
            requested_executor=requested_executor,
        )

    def resolve_profile(self, requested_profile: str | None = None) -> str:
        profile = (requested_profile or "").strip()
        if profile:
            return profile
        return self.config.default_openfang_profile

    def _finalize(self, *, route_key: str, configured_executor: str, requested_executor: str | None) -> str:
        chosen = configured_executor
        requested = (requested_executor or "").strip().lower()
        if requested:
            if requested not in self.config.allowed_executors:
                raise DelegationError(f"Unsupported executor '{requested}' for {route_key}")
            if self.config.enforce_routes and requested != configured_executor:
                raise DelegationError(
                    f"Delegation override blocked for {route_key}: "
                    f"configured='{configured_executor}' requested='{requested}'"
                )
            chosen = requested

        if chosen not in self.config.allowed_executors:
            raise DelegationError(f"Configured executor '{chosen}' is not allowed for {route_key}")
        return chosen


def _parse_yaml_or_json(text: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore

        parsed = yaml.safe_load(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
