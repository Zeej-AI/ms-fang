"""Reflector role: bounded rolling summary writer."""

from __future__ import annotations

import hashlib


def summarize(loop_notes: str) -> tuple[str, str]:
    summary = loop_notes.strip()
    digest = hashlib.sha256(summary.encode("utf-8")).hexdigest()
    return summary, digest
