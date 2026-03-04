# Recovery Runbook

## Ticket Recovery
1. Read `tickets/<ticket_id>/state.json`.
2. Inspect `audit.log` to identify the last successful transition.
3. Use `msfang undo <ticket_id>` only when last transition was invalid.
4. Re-run `msfang show <ticket_id>` and verify:
   - phase is coherent
   - gate aligns with known status
   - pending approval is valid

## Service Recovery
1. Restart Hermes gateway and OpenFang runtime.
2. Validate adapter health before ticket resume.
3. Resume from `amber` or `active` state only.

## Upgrade Recovery
1. Re-pin previous refs in `config/providers.lock.yaml`.
2. Restart runtime services.
3. Re-run smoke checks and compare behavior.
