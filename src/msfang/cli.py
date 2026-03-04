"""CLI for MsFang control-plane actions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapters.hermes_adapter import HermesAdapter
from .adapters.jcodemunch_adapter import JCodeMunchAdapter
from .code_intel import CodeIntelService
from .models import OwnerIdentities
from .policy import PolicyEngine
from .runtime import run_phase0_checks
from .service import MsFangService
from .storage import TicketStore


def _build_service(root: Path) -> tuple[MsFangService, PolicyEngine]:
    policy = PolicyEngine.from_file(root / "config" / "policies.yaml")
    store = TicketStore(root)
    return MsFangService(store, policy), policy


def _print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


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

    p_hermes = sub.add_parser("hermes-command")
    p_hermes.add_argument("ticket_id")
    p_hermes.add_argument("--text", required=True, help="slash command, e.g. '/execute run tests'")
    p_hermes.add_argument("--actor", required=True)
    p_hermes.add_argument("--channel", choices=["slack", "cli"], default="cli")

    p_doc = sub.add_parser("doctor")

    p_ci_index = sub.add_parser("code-index")
    p_ci_index.add_argument("--path", required=True)
    p_ci_index.add_argument("--use-ai-summaries", action="store_true")

    p_ci_search = sub.add_parser("code-search")
    p_ci_search.add_argument("--repo", required=True)
    p_ci_search.add_argument("--query", required=True)
    p_ci_search.add_argument("--max-results", type=int, default=10)

    p_ci_symbol = sub.add_parser("code-symbol")
    p_ci_symbol.add_argument("--repo", required=True)
    p_ci_symbol.add_argument("--symbol-id", required=True)
    p_ci_symbol.add_argument("--verify", action="store_true")
    p_ci_symbol.add_argument("--context-lines", type=int, default=0)

    args = parser.parse_args()
    root = args.root
    svc, policy = _build_service(root)

    if args.cmd == "preflight":
        out = svc.preflight(
            args.ticket_id,
            success_criteria=args.criteria,
            owner=OwnerIdentities(slack_user_ids=args.slack_id, cli_os_users=args.cli_user),
        )
        _print_json(out.to_dict(include_history=True))
        return

    if args.cmd == "plan":
        out = svc.plan(args.ticket_id)
        _print_json(out.to_dict(include_history=True))
        return

    if args.cmd == "execute":
        out = svc.execute(args.ticket_id, loop_notes=args.notes)
        _print_json(out.to_dict(include_history=True))
        return

    if args.cmd == "critic":
        out = svc.critic(
            args.ticket_id,
            success=args.success,
            needs_input=args.needs_input,
            failed=args.failed,
            strikes_increment=args.strikes,
        )
        _print_json(out.to_dict(include_history=True))
        return

    if args.cmd == "request-approval":
        out = svc.request_approval(args.ticket_id, action_type=args.action, context=args.context)
        _print_json(out.to_dict(include_history=True))
        return

    if args.cmd == "accept":
        out = svc.accept(args.ticket_id, args.approval_id)
        _print_json(out.to_dict(include_history=True))
        return

    if args.cmd == "undo":
        out = svc.undo(args.ticket_id)
        _print_json(out.to_dict(include_history=True))
        return

    if args.cmd == "prompt":
        out = svc.set_prompt(args.ticket_id, args.text)
        _print_json(out.to_dict(include_history=True))
        return

    if args.cmd == "janitor":
        out = svc.janitor(args.ticket_id)
        _print_json(out.to_dict(include_history=True))
        return

    if args.cmd == "show":
        out = svc.show(args.ticket_id)
        _print_json(out.to_dict(include_history=True))
        return

    if args.cmd == "hermes-command":
        adapter = HermesAdapter()
        cmd = adapter.parse_text(
            text=args.text,
            ticket_id=args.ticket_id,
            actor=args.actor,
            channel=args.channel,
        )
        out = svc.handle_hermes_command(cmd)
        _print_json(out.to_dict(include_history=True))
        return

    if args.cmd == "doctor":
        _print_json(run_phase0_checks(root))
        return

    # Code intelligence commands are policy-enforced and jcodemunch-first.
    code = CodeIntelService(policy=policy, adapter=JCodeMunchAdapter())

    if args.cmd == "code-index":
        _print_json(code.index_folder(path=args.path, use_ai_summaries=args.use_ai_summaries))
        return

    if args.cmd == "code-search":
        _print_json(code.search_symbols(repo=args.repo, query=args.query, max_results=args.max_results))
        return

    if args.cmd == "code-symbol":
        _print_json(
            code.get_symbol(
                repo=args.repo,
                symbol_id=args.symbol_id,
                verify=args.verify,
                context_lines=args.context_lines,
            )
        )
        return


if __name__ == "__main__":
    main()
