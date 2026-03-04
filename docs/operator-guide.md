# Operator Guide (v1)

## Core Commands
- `msfang preflight <ticket_id> --criteria ...`
- `msfang plan <ticket_id>`
- `msfang execute <ticket_id> --notes "..."`
- `msfang critic <ticket_id> --success|--needs-input|--failed`
- `msfang request-approval <ticket_id> --action <type> --context "..."`
- `msfang accept <ticket_id> <approval_id>`
- `msfang janitor <ticket_id>`
- `msfang undo <ticket_id>`
- `msfang show <ticket_id>`
- `msfang hermes-command <ticket_id> --text "/plan" --actor <id> --channel slack|cli`
- `msfang doctor`
- `msfang code-index --path <repo_path>`
- `msfang code-search --repo <repo> --query "<query>"`
- `msfang code-symbol --repo <repo> --symbol-id "<id>"`

## Recommended Lifecycle
1. Preflight with clear success criteria.
2. Enter plan phase.
3. Execute and write bounded loop notes.
4. Critic assigns gate.
5. If Green, run Janitor and close.
6. If Amber, suspend and await input.
7. If Red, request approval/escalate.

## Code Intel Policy
- `config/policies.yaml` controls code intelligence provider selection.
- Default is `code_intel_provider: "jcodemunch"`.
- If `enforce_jcodemunch_for_code_ops: true`, all code-intel commands fail unless provider is `jcodemunch`.
