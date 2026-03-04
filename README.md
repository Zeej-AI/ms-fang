# MsFang

MsFang is a thin control-plane for deterministic personal Agent OS orchestration.

## v1 Scope
- Ticket-centric execution state with mechanical truth in `state.json`
- Traffic-light gating (`green`, `amber`, `red`)
- Modular role contracts (Reflector, Critic, Janitor)
- Policy-driven approvals (minimal prompts, hard red gates)
- Upgrade intelligence scaffolding (scout + planner)
- Slack/CLI-ready adapter contracts (implementation starts with CLI)

## Quick Start
```bash
cd /path/to/MsFang
python3 -m pip install -e .

msfang --root . preflight demo-1 --criteria "state machine works" --cli-user "$USER"
msfang --root . plan demo-1
msfang --root . execute demo-1 --notes "Executed first loop"
msfang --root . critic demo-1 --success
msfang --root . janitor demo-1
msfang --root . show demo-1
```

## Directory Layout
- `src/msfang/` - control-plane modules
- `config/` - policy/identity/runtime lock contracts
- `tickets/` - task state artifacts
- `docs/` - architecture/operator/recovery docs
- `scripts/phase0_check.sh` - environment readiness check

## Design Principles
- Reuse Hermes/OpenFang strengths, add minimal governance glue.
- Keep decisions explicit and machine-checkable.
- Make policy easy to edit without code changes.
