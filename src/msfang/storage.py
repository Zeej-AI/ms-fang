"""Ticket file persistence and artifact writing."""

from __future__ import annotations

import json
from pathlib import Path

from .exceptions import TicketNotFoundError
from .models import TicketState


class TicketStore:
    def __init__(self, root: Path):
        self.root = root
        self.tickets_dir = root / "tickets"
        self.tickets_dir.mkdir(parents=True, exist_ok=True)

    def ticket_dir(self, ticket_id: str) -> Path:
        return self.tickets_dir / ticket_id

    def state_path(self, ticket_id: str) -> Path:
        return self.ticket_dir(ticket_id) / "state.json"

    def ensure_ticket(self, ticket_id: str, ticket_md: str = "") -> None:
        tdir = self.ticket_dir(ticket_id)
        tdir.mkdir(parents=True, exist_ok=True)
        ticket_file = tdir / "Ticket.md"
        if not ticket_file.exists():
            ticket_file.write_text(ticket_md or f"# Ticket {ticket_id}\n", encoding="utf-8")
        for name in ["working_summary.md", "memory_delta.md", "audit.log"]:
            p = tdir / name
            if not p.exists():
                p.write_text("", encoding="utf-8")

    def save_state(self, state: TicketState) -> None:
        self.ensure_ticket(state.ticket_id)
        payload = state.to_dict(include_history=True)
        self.state_path(state.ticket_id).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def load_state(self, ticket_id: str) -> TicketState:
        p = self.state_path(ticket_id)
        if not p.exists():
            raise TicketNotFoundError(f"Ticket not found: {ticket_id}")
        payload = json.loads(p.read_text(encoding="utf-8"))
        return TicketState.from_dict(payload)

    def append_audit(self, ticket_id: str, line: str) -> None:
        self.ensure_ticket(ticket_id)
        p = self.ticket_dir(ticket_id) / "audit.log"
        with p.open("a", encoding="utf-8") as f:
            f.write(line.rstrip() + "\n")

    def write_working_summary(self, ticket_id: str, summary: str) -> None:
        self.ensure_ticket(ticket_id)
        p = self.ticket_dir(ticket_id) / "working_summary.md"
        p.write_text(summary, encoding="utf-8")

    def write_memory_delta(self, ticket_id: str, delta: str) -> None:
        self.ensure_ticket(ticket_id)
        p = self.ticket_dir(ticket_id) / "memory_delta.md"
        p.write_text(delta, encoding="utf-8")
