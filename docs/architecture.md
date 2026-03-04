# MsFang Architecture (v1)

## Boundary
- MsFang is the thin control-plane.
- Hermes is executive interface + durable memory backend.
- OpenFang is worker runtime.
- jcodemunch is symbol retrieval layer.
- Policy can enforce jcodemunch as the only code-intel provider.
- Delegation policy can enforce deterministic executor selection.

## Canonical Task State
Each ticket is isolated under `tickets/<ticket_id>/`:
- `Ticket.md`: human-curated task spec
- `state.json`: mechanical truth
- `working_summary.md`: bounded reflector memory
- `memory_delta.md`: janitor durable-memory commit candidate
- `audit.log`: immutable lifecycle trail

## Gate Controller
`Gate` is the deterministic execution signal:
- `green`: success criteria met
- `amber`: needs input or deferred variable
- `red`: failure/policy breach/strike escalation

## Role Hierarchy
- Reflector: summarize each loop
- Critic: assign gate + strike changes
- Janitor: exclusive durable-memory writer

## Policy
Runtime policy is entirely in `config/policies.yaml`.
Defaults keep red gating for os/package/service changes while minimizing prompts for routine work.
Runtime and identity checks are surfaced through `msfang doctor`.

## Delegation
- `config/delegation.yaml` is the mechanical delegation state for action/command routing.
- `enforce_routes: true` means MsFang blocks conflicting manual routing requests.
- Action-level routing is enforced before worker execution.
- Red-risk actions must pass approval gate before delegation.

## OpenFang Subagent Profiles
- `config/openfang_profiles.yaml` stores profile-to-agent mappings and profile instructions.
- MsFang executes profile-selected workers through OpenFang adapter (`delegate` command path).
