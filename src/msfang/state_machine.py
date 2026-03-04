"""Deterministic ticket state transitions."""

from __future__ import annotations

from dataclasses import replace

from .exceptions import ApprovalError, StateTransitionError
from .models import Gate, PendingApproval, TicketPhase, TicketState, TicketStatus


class TicketStateMachine:
    """Pure transition operations for TicketState."""

    def __init__(self, max_history: int = 50, strike_threshold_red: int = 3):
        self.max_history = max_history
        self.strike_threshold_red = strike_threshold_red

    def _checkpoint(self, state: TicketState) -> None:
        state.push_history(max_history=self.max_history)

    def preflight(self, state: TicketState) -> TicketState:
        self._checkpoint(state)
        state.phase = TicketPhase.PREFLIGHT
        state.status = TicketStatus.ACTIVE
        state.gate = Gate.AMBER
        state.touch()
        return state

    def plan(self, state: TicketState) -> TicketState:
        if state.phase not in {TicketPhase.PREFLIGHT, TicketPhase.PLAN, TicketPhase.EXECUTE}:
            raise StateTransitionError(f"Cannot enter plan from phase={state.phase}")
        self._checkpoint(state)
        state.phase = TicketPhase.PLAN
        state.status = TicketStatus.ACTIVE
        state.touch()
        return state

    def execute(self, state: TicketState) -> TicketState:
        if state.phase not in {TicketPhase.PLAN, TicketPhase.EXECUTE, TicketPhase.CRITIC}:
            raise StateTransitionError(f"Cannot execute from phase={state.phase}")
        if state.pending_approval is not None:
            raise StateTransitionError("Cannot execute while approval is pending")
        self._checkpoint(state)
        state.phase = TicketPhase.EXECUTE
        state.status = TicketStatus.ACTIVE
        state.touch()
        return state

    def critic(self, state: TicketState, gate: Gate, strikes_increment: int = 0) -> TicketState:
        if state.phase not in {TicketPhase.EXECUTE, TicketPhase.CRITIC, TicketPhase.PLAN}:
            raise StateTransitionError(f"Cannot run critic from phase={state.phase}")
        self._checkpoint(state)
        state.phase = TicketPhase.CRITIC
        state.gate = gate
        state.strike_count += max(0, strikes_increment)

        if state.strike_count >= self.strike_threshold_red:
            state.gate = Gate.RED

        if state.gate is Gate.GREEN:
            state.status = TicketStatus.ACTIVE
        elif state.gate is Gate.AMBER:
            state.status = TicketStatus.SUSPENDED
        else:
            state.status = TicketStatus.BLOCKED

        state.touch()
        return state

    def request_approval(self, state: TicketState, approval: PendingApproval) -> TicketState:
        self._checkpoint(state)
        state.pending_approval = approval
        state.touch()
        return state

    def approve(self, state: TicketState, approval_id: str) -> TicketState:
        if state.pending_approval is None:
            raise ApprovalError("No pending approval on this ticket")
        if state.pending_approval.id != approval_id:
            raise ApprovalError("Approval id mismatch")

        self._checkpoint(state)
        state.pending_approval = None

        if state.gate is Gate.RED:
            state.gate = Gate.AMBER
            state.status = TicketStatus.SUSPENDED
        elif state.gate is Gate.AMBER:
            state.status = TicketStatus.ACTIVE
        else:
            state.status = TicketStatus.ACTIVE

        state.touch()
        return state

    def janitor(self, state: TicketState, janitor_commit_id: str) -> TicketState:
        if state.gate is not Gate.GREEN:
            raise StateTransitionError("Janitor can only run on Green gate")
        self._checkpoint(state)
        state.phase = TicketPhase.JANITOR
        state.artifacts = replace(state.artifacts, janitor_commit_id=janitor_commit_id)
        state.status = TicketStatus.ACTIVE
        state.touch()
        return state

    def close(self, state: TicketState) -> TicketState:
        if state.phase not in {TicketPhase.JANITOR, TicketPhase.CRITIC}:
            raise StateTransitionError(f"Cannot close from phase={state.phase}")
        if state.gate is not Gate.GREEN:
            raise StateTransitionError("Cannot close without Green gate")
        self._checkpoint(state)
        state.phase = TicketPhase.CLOSED
        state.status = TicketStatus.COMPLETE
        state.pending_approval = None
        state.touch()
        return state

    def undo(self, state: TicketState) -> TicketState:
        if not state.history:
            raise StateTransitionError("No history available for undo")
        previous = state.history.pop()
        restored = TicketState.from_dict(previous)
        restored.history = state.history
        restored.touch()
        return restored
