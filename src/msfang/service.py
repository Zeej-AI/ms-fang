"""Core orchestration service for MsFang."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from .adapters.hermes_adapter import HermesCommand
from .models import (
    Gate,
    OwnerIdentities,
    PendingApproval,
    TicketArtifacts,
    TicketPhase,
    TicketState,
    TicketStatus,
    utc_now_iso,
)
from .policy import PolicyEngine
from .roles import critic as critic_role
from .roles import janitor as janitor_role
from .roles import reflector as reflector_role
from .state_machine import TicketStateMachine
from .storage import TicketStore


class MsFangService:
    def __init__(self, store: TicketStore, policy: PolicyEngine):
        self.store = store
        self.policy = policy
        self.machine = TicketStateMachine(
            max_history=self.policy.config.max_history,
            strike_threshold_red=self.policy.config.strike_threshold_red,
        )

    def preflight(self, ticket_id: str, success_criteria: list[str], owner: OwnerIdentities) -> TicketState:
        self.store.ensure_ticket(ticket_id)
        try:
            state = self.store.load_state(ticket_id)
            state.success_criteria = success_criteria or state.success_criteria
            state.owner_identities = owner
        except Exception:
            state = TicketState(
                ticket_id=ticket_id,
                status=TicketStatus.ACTIVE,
                phase=TicketPhase.PREFLIGHT,
                gate=Gate.AMBER,
                strike_count=0,
                success_criteria=success_criteria,
                owner_identities=owner,
                artifacts=TicketArtifacts(),
            )
        state = self.machine.preflight(state)
        self.store.save_state(state)
        self.store.append_audit(ticket_id, f"{utc_now_iso()} preflight")
        return state

    def plan(self, ticket_id: str) -> TicketState:
        state = self.store.load_state(ticket_id)
        state = self.machine.plan(state)
        self.store.save_state(state)
        self.store.append_audit(ticket_id, f"{utc_now_iso()} plan")
        return state

    def execute(self, ticket_id: str, loop_notes: str) -> TicketState:
        state = self.store.load_state(ticket_id)
        state = self.machine.execute(state)
        summary, digest = reflector_role.summarize(loop_notes)
        self.store.write_working_summary(ticket_id, summary)
        state.artifacts.last_reflector_summary_hash = digest
        self.store.save_state(state)
        self.store.append_audit(ticket_id, f"{utc_now_iso()} execute")
        return state

    def critic(
        self,
        ticket_id: str,
        *,
        success: bool,
        needs_input: bool,
        failed: bool,
        strikes_increment: int = 0,
    ) -> TicketState:
        state = self.store.load_state(ticket_id)
        gate = critic_role.evaluate(
            success=success,
            needs_input=needs_input,
            failed=failed,
            strikes=state.strike_count + max(0, strikes_increment),
            strike_threshold_red=self.policy.config.strike_threshold_red,
        )
        state = self.machine.critic(state, gate=gate, strikes_increment=strikes_increment)
        self.store.save_state(state)
        self.store.append_audit(ticket_id, f"{utc_now_iso()} critic gate={state.gate.value}")
        return state

    def request_approval(self, ticket_id: str, action_type: str, context: str, ttl_minutes: int = 120) -> TicketState:
        state = self.store.load_state(ticket_id)
        risk = self.policy.classify(action_type)
        now = datetime.now(timezone.utc)
        approval = PendingApproval(
            id=str(uuid4()),
            action_type=action_type,
            risk=risk,
            requested_at=now.isoformat(),
            expires_at=(now + timedelta(minutes=ttl_minutes)).isoformat(),
            request_context=context,
        )
        state = self.machine.request_approval(state, approval)
        self.store.save_state(state)
        self.store.append_audit(ticket_id, f"{utc_now_iso()} approval_requested action={action_type} risk={risk}")
        return state

    def accept(self, ticket_id: str, approval_id: str) -> TicketState:
        state = self.store.load_state(ticket_id)
        state = self.machine.approve(state, approval_id)
        self.store.save_state(state)
        self.store.append_audit(ticket_id, f"{utc_now_iso()} approval_accepted id={approval_id}")
        return state

    def janitor(self, ticket_id: str) -> TicketState:
        state = self.store.load_state(ticket_id)
        summary_path = self.store.ticket_dir(ticket_id) / "working_summary.md"
        summary = summary_path.read_text(encoding="utf-8") if summary_path.exists() else ""
        delta = janitor_role.build_memory_delta(summary, accepted=True)
        commit_id = janitor_role.generate_commit_id(ticket_id)
        self.store.write_memory_delta(ticket_id, delta)
        state = self.machine.janitor(state, janitor_commit_id=commit_id)
        state = self.machine.close(state)
        self.store.save_state(state)
        self.store.append_audit(ticket_id, f"{utc_now_iso()} janitor commit={commit_id} closed")
        return state

    def undo(self, ticket_id: str) -> TicketState:
        state = self.store.load_state(ticket_id)
        state = self.machine.undo(state)
        self.store.save_state(state)
        self.store.append_audit(ticket_id, f"{utc_now_iso()} undo")
        return state

    def set_prompt(self, ticket_id: str, prompt: str) -> TicketState:
        state = self.store.load_state(ticket_id)
        state.push_history(max_history=self.policy.config.max_history)
        state.prompt = prompt
        state.touch()
        self.store.save_state(state)
        self.store.append_audit(ticket_id, f"{utc_now_iso()} prompt_updated")
        return state

    def show(self, ticket_id: str) -> TicketState:
        return self.store.load_state(ticket_id)

    def handle_hermes_command(self, cmd: HermesCommand) -> TicketState:
        """Apply a validated Hermes slash command to ticket state."""
        if cmd.name == "preflight":
            criteria = cmd.payload.get("criteria", [])
            if isinstance(criteria, str):
                criteria = [criteria]
            return self.preflight(
                cmd.ticket_id,
                success_criteria=list(criteria),
                owner=OwnerIdentities(
                    slack_user_ids=[cmd.actor] if cmd.channel == "slack" else [],
                    cli_os_users=[cmd.actor] if cmd.channel == "cli" else [],
                ),
            )
        if cmd.name == "plan":
            return self.plan(cmd.ticket_id)
        if cmd.name == "execute":
            return self.execute(cmd.ticket_id, loop_notes=cmd.payload.get("notes", ""))
        if cmd.name == "accept":
            return self.accept(cmd.ticket_id, approval_id=cmd.payload.get("approval_id", ""))
        if cmd.name == "undo":
            return self.undo(cmd.ticket_id)
        if cmd.name == "prompt":
            return self.set_prompt(cmd.ticket_id, prompt=cmd.payload.get("text", ""))

        raise ValueError(f"Unsupported Hermes command: {cmd.name}")
