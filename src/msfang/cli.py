"""CLI for MsFang control-plane actions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .models import OwnerIdentities
from .policy import PolicyEngine
from .service import MsFangService
from .storage import TicketStore


def _build_service(root: Path) -> MsFangService:
    policy = PolicyEngine.from_file(root / "config" / "policies.yaml")
    store = TicketStore(root)
    return MsFangService(store, policy)


def main() -> None:
    parser = argparse.ArgumentParser(description="MsFang control-plane CLI")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="MsFang repository root")

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_pre = sub.add_parser("preflight")
    p_pre.add_argument("ticket_id")
    p_pre.add_argument("--criteria", nargs="*", default=[])
    p_pre.add_argument("--slack-id", nargs="*", default=[])
    p_pre.add_argument("--cli-user", nargs="*", default=[])

    p_plan = sub.add_parser("plan")
    p_plan.add_argument("ticket_id")

    p_exec = sub.add_parser("execute")
    p_exec.add_argument("ticket_id")
    p_exec.add_argument("--notes", required=True)

    p_critic = sub.add_parser("critic")
    p_critic.add_argument("ticket_id")
    p_critic.add_argument("--success", action="store_true")
    p_critic.add_argument("--needs-input", action="store_true")
    p_critic.add_argument("--failed", action="store_true")
    p_critic.add_argument("--strikes", type=int, default=0)

    p_req = sub.add_parser("request-approval")
    p_req.add_argument("ticket_id")
    p_req.add_argument("--action", required=True)
    p_req.add_argument("--context", required=True)

    p_acc = sub.add_parser("accept")
    p_acc.add_argument("ticket_id")
    p_acc.add_argument("approval_id")

    p_undo = sub.add_parser("undo")
    p_undo.add_argument("ticket_id")

    p_prompt = sub.add_parser("prompt")
    p_prompt.add_argument("ticket_id")
    p_prompt.add_argument("--text", required=True)

    p_jan = sub.add_parser("janitor")
    p_jan.add_argument("ticket_id")

    p_show = sub.add_parser("show")
    p_show.add_argument("ticket_id")

    args = parser.parse_args()
    svc = _build_service(args.root)

    if args.cmd == "preflight":
        out = svc.preflight(
            args.ticket_id,
            success_criteria=args.criteria,
            owner=OwnerIdentities(slack_user_ids=args.slack_id, cli_os_users=args.cli_user),
        )
    elif args.cmd == "plan":
        out = svc.plan(args.ticket_id)
    elif args.cmd == "execute":
        out = svc.execute(args.ticket_id, loop_notes=args.notes)
    elif args.cmd == "critic":
        out = svc.critic(
            args.ticket_id,
            success=args.success,
            needs_input=args.needs_input,
            failed=args.failed,
            strikes_increment=args.strikes,
        )
    elif args.cmd == "request-approval":
        out = svc.request_approval(args.ticket_id, action_type=args.action, context=args.context)
    elif args.cmd == "accept":
        out = svc.accept(args.ticket_id, args.approval_id)
    elif args.cmd == "undo":
        out = svc.undo(args.ticket_id)
    elif args.cmd == "prompt":
        out = svc.set_prompt(args.ticket_id, args.text)
    elif args.cmd == "janitor":
        out = svc.janitor(args.ticket_id)
    else:
        out = svc.show(args.ticket_id)

    print(json.dumps(out.to_dict(include_history=True), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
