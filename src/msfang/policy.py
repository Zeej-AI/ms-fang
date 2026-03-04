"""Policy loading and risk classification."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PolicyConfig:
    action_risk_map: dict[str, str]
    approval_required_for: set[str]
    strike_threshold_red: int
    max_history: int

    @classmethod
    def defaults(cls) -> "PolicyConfig":
        return cls(
            action_risk_map={
                "os_change": "red",
                "package_change": "red",
                "service_change": "red",
                "config_change": "amber",
                "code_change": "green",
                "test_run": "green",
                "upgrade_apply": "amber",
            },
            approval_required_for={"red"},
            strike_threshold_red=3,
            max_history=50,
        )


class PolicyEngine:
    def __init__(self, config: PolicyConfig):
        self.config = config

    @classmethod
    def from_file(cls, path: Path) -> "PolicyEngine":
        if not path.exists():
            return cls(PolicyConfig.defaults())

        text = path.read_text(encoding="utf-8")
        data = _parse_yaml_or_json(text)

        defaults = PolicyConfig.defaults()
        return cls(
            PolicyConfig(
                action_risk_map=data.get("action_risk_map", defaults.action_risk_map),
                approval_required_for=set(data.get("approval_required_for", list(defaults.approval_required_for))),
                strike_threshold_red=int(data.get("strike_threshold_red", defaults.strike_threshold_red)),
                max_history=int(data.get("max_history", defaults.max_history)),
            )
        )

    def classify(self, action_type: str) -> str:
        return self.config.action_risk_map.get(action_type, "amber")

    def requires_approval(self, action_type: str) -> bool:
        risk = self.classify(action_type)
        return risk in self.config.approval_required_for


def _parse_yaml_or_json(text: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore

        parsed = yaml.safe_load(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
