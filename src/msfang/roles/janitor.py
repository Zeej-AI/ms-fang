"""Janitor role: only durable memory writer contract."""

from __future__ import annotations

from datetime import datetime, timezone


def generate_commit_id(ticket_id: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"janitor-{ticket_id}-{stamp}"


def build_memory_delta(summary: str, accepted: bool = True) -> str:
    status = "accepted" if accepted else "rejected"
    return f"# Memory Delta\n\n- status: {status}\n- summary:\n\n{summary.strip()}\n"
