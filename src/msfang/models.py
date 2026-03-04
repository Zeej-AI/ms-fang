"""Core state models for MsFang ticket orchestration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class TicketStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BLOCKED = "blocked"
    COMPLETE = "complete"


class TicketPhase(StrEnum):
    PREFLIGHT = "preflight"
    PLAN = "plan"
    EXECUTE = "execute"
    CRITIC = "critic"
    JANITOR = "janitor"
    CLOSED = "closed"


class Gate(StrEnum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PendingApproval:
    id: str
    action_type: str
    risk: str
    requested_at: str
    expires_at: str
    request_context: str


@dataclass
class OwnerIdentities:
    slack_user_ids: list[str] = field(default_factory=list)
    cli_os_users: list[str] = field(default_factory=list)


@dataclass
class TicketArtifacts:
    last_reflector_summary_hash: str = ""
    janitor_commit_id: str | None = None


@dataclass
class TicketTimestamps:
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)


@dataclass
class TicketState:
    ticket_id: str
    status: TicketStatus = TicketStatus.ACTIVE
    phase: TicketPhase = TicketPhase.PREFLIGHT
    gate: Gate = Gate.AMBER
    strike_count: int = 0
    success_criteria: list[str] = field(default_factory=list)
    pending_approval: PendingApproval | None = None
    owner_identities: OwnerIdentities = field(default_factory=OwnerIdentities)
    artifacts: TicketArtifacts = field(default_factory=TicketArtifacts)
    timestamps: TicketTimestamps = field(default_factory=TicketTimestamps)
    prompt: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)

    def touch(self) -> None:
        self.timestamps.updated_at = utc_now_iso()

    def snapshot(self) -> dict[str, Any]:
        snap = self.to_dict(include_history=False)
        return snap

    def push_history(self, max_history: int = 50) -> None:
        self.history.append(self.snapshot())
        if len(self.history) > max_history:
            self.history = self.history[-max_history:]

    def to_dict(self, include_history: bool = True) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["phase"] = self.phase.value
        payload["gate"] = self.gate.value
        if not include_history:
            payload.pop("history", None)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TicketState":
        pending = payload.get("pending_approval")
        pending_obj = PendingApproval(**pending) if pending else None

        identities = OwnerIdentities(**payload.get("owner_identities", {}))
        artifacts = TicketArtifacts(**payload.get("artifacts", {}))
        timestamps = TicketTimestamps(**payload.get("timestamps", {}))

        return cls(
            ticket_id=payload["ticket_id"],
            status=TicketStatus(payload.get("status", TicketStatus.ACTIVE.value)),
            phase=TicketPhase(payload.get("phase", TicketPhase.PREFLIGHT.value)),
            gate=Gate(payload.get("gate", Gate.AMBER.value)),
            strike_count=int(payload.get("strike_count", 0)),
            success_criteria=list(payload.get("success_criteria", [])),
            pending_approval=pending_obj,
            owner_identities=identities,
            artifacts=artifacts,
            timestamps=timestamps,
            prompt=payload.get("prompt", ""),
            history=list(payload.get("history", [])),
        )
