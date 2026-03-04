"""Hermes adapter contract for slash-command parsing and routing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HermesCommand:
    name: str
    ticket_id: str
    payload: dict
    actor: str
    channel: str


class HermesAdapter:
    SUPPORTED_COMMANDS = {"preflight", "plan", "execute", "accept", "undo", "prompt"}

    def validate(self, command: HermesCommand) -> None:
        if command.name not in self.SUPPORTED_COMMANDS:
            raise ValueError(f"Unsupported Hermes command: {command.name}")

    def parse_text(self, *, text: str, ticket_id: str, actor: str, channel: str) -> HermesCommand:
        raw = text.strip()
        if not raw.startswith("/"):
            raise ValueError("Hermes command must start with '/'")

        parts = raw[1:].split(maxsplit=1)
        name = parts[0].strip().lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        payload: dict[str, str] = {}
        if name == "execute":
            payload["notes"] = arg
        elif name == "accept":
            payload["approval_id"] = arg
        elif name == "prompt":
            payload["text"] = arg

        cmd = HermesCommand(name=name, ticket_id=ticket_id, payload=payload, actor=actor, channel=channel)
        self.validate(cmd)
        return cmd
