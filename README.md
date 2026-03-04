# MsFang

MsFang is a thin control-plane for deterministic personal Agent OS orchestration.

## v1 Scope
- Ticket-centric execution state with mechanical truth in `state.json`
- Traffic-light gating (`green`, `amber`, `red`)
- Modular role contracts (Reflector, Critic, Janitor)
- Policy-driven approvals (minimal prompts, hard red gates)
- Hard delegation rails (Hermes vs OpenFang) via deterministic routing policy
- Upgrade intelligence scaffolding (scout + planner)
- Slack/CLI-ready adapter contracts (implementation starts with CLI)
- jcodemunch-first code intelligence with policy enforcement

## Quick Start
```bash
cd /path/to/MsFang
./scripts/msfang init --yes
./scripts/msfang doctor

./scripts/msfang preflight demo-1 --criteria "state machine works" --cli-user "$USER"
./scripts/msfang plan demo-1
./scripts/msfang delegate demo-1 --action-type code_change --task "Implement feature X" --profile codex_cli
./scripts/msfang critic demo-1 --success
./scripts/msfang janitor demo-1
./scripts/msfang show demo-1

# jcodemunch-backed code intelligence
./scripts/msfang code-index --path .
./scripts/msfang code-search --repo local/control-plane-bootstrap --query "handle_hermes_command"
```

`./scripts/msfang` auto-creates `.venv` and runs MsFang from source, so no global pip install is required.

## Run As Local API Service (`msfangd`)
```bash
cd /path/to/MsFang
./scripts/msfangd --host 127.0.0.1 --port 9387
```

Key endpoints:
- `GET /v1/doctor`
- `POST /v1/init`
- `GET /v1/tickets`
- `POST /v1/tickets`
- `POST /v1/tickets/<id>/preflight|plan|delegate|critic|janitor|undo`
- `POST /v1/tickets/<id>/approval/request|accept`
- `GET /v1/tickets/<id>/events`

Mission Control can proxy this API through `/api/msfang/*` with `MSFANG_API_BASE=http://127.0.0.1:9387`.

## Directory Layout
- `src/msfang/` - control-plane modules
- `config/` - policy/identity/runtime/delegation/profile contracts
- `tickets/` - task state artifacts
- `docs/` - architecture/operator/recovery docs
- `scripts/phase0_check.sh` - environment readiness check

## Design Principles
- Reuse Hermes/OpenFang strengths, add minimal governance glue.
- Keep decisions explicit and machine-checkable.
- Make policy easy to edit without code changes.
- Keep code intelligence deterministic and token-efficient via jcodemunch.
