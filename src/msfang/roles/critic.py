"""Critic role: convert evidence flags into gate verdict."""

from __future__ import annotations

from ..models import Gate


def evaluate(*, success: bool, needs_input: bool, failed: bool, strikes: int, strike_threshold_red: int) -> Gate:
    if failed or strikes >= strike_threshold_red:
        return Gate.RED
    if success and not needs_input:
        return Gate.GREEN
    return Gate.AMBER
