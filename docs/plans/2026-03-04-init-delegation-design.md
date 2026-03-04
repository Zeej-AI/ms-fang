# MsFang Init + Delegation + Profiles Design (2026-03-04)

## Goal
Make MsFang operable by a non-technical owner with minimal setup friction, while enforcing deterministic delegation rails across Hermes/OpenFang and preserving future portability.

## Decisions
1. Add `msfang init` as the setup wizard entrypoint.
2. Add `config/delegation.yaml` as hard routing policy for action and command delegation.
3. Add `config/openfang_profiles.yaml` for subagent profile presets (`codex_cli`, `claude_cli`, `critic_fast`).
4. Keep MsFang a thin wrapper: no heavy runtime orchestration duplicated from Hermes/OpenFang.

## Architecture Changes
- New module: `src/msfang/onboarding.py`
  - Creates/updates core config and runtime directories.
  - Supports interactive mode or `--yes` defaults.
- New module: `src/msfang/delegation.py`
  - Loads routing config.
  - Enforces route-locking when `enforce_routes: true`.
- Service layer:
  - New `delegate_execute(...)` method.
  - Hard gate: red-risk action types require accepted approval before execution.
  - Hermes command routing can force `/execute` through OpenFang.
- OpenFang adapter:
  - Added profile-driven execution path using profile config file.

## Why This Path
- Deterministic rails avoid prompt-only delegation behavior.
- Config-based routing keeps upgrades flexible (swap Hermes/OpenFang revisions without rewriting core service logic).
- Profile indirection allows future agent/runtime additions without code churn.

## Tradeoffs
- Hermes executor path is still a structured placeholder for now; direct Hermes runtime bridge remains follow-up work.
- OpenFang runtime availability still depends on daemon state; MsFang surfaces this as explicit `needs_input` output.

## Validation
- New tests for onboarding, delegation policy enforcement, and delegated service execution.
- Full unit suite run after implementation.
