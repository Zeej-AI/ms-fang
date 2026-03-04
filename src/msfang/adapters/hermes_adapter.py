"""Hermes adapter contract for slash-command integration."""

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
