"""Upgrade scout: compare pinned refs to discovered refs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ComponentRef:
    name: str
    pinned: str
    discovered: str


def build_report(components: list[ComponentRef]) -> dict:
    updates = []
    for comp in components:
        changed = comp.pinned != comp.discovered
        updates.append(
            {
                "component": comp.name,
                "pinned": comp.pinned,
                "discovered": comp.discovered,
                "update_available": changed,
                "change_type": "unknown" if changed else "none",
                "risk": "amber" if changed else "green",
            }
        )
    return {"components": updates}
