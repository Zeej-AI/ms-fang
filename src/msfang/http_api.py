"""HTTP API server for MsFang control-plane orchestration."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .adapters.openfang_adapter import OpenFangAdapter, OpenFangAdapterConfig
from .delegation import DelegationEngine
from .models import OwnerIdentities
from .onboarding import InitOptions, run_init
from .policy import PolicyEngine
from .runtime import run_phase0_checks
from .service import MsFangService
from .storage import TicketStore


def _build_service(root: Path) -> MsFangService:
    policy = PolicyEngine.from_file(root / "config" / "policies.yaml")
    delegation = DelegationEngine.from_file(root / "config" / "delegation.yaml")
    store = TicketStore(root)
    openfang = OpenFangAdapter(
        OpenFangAdapterConfig(
            profiles_path=root / "config" / "openfang_profiles.yaml",
        )
    )
    return MsFangService(
        store,
        policy,
        delegation=delegation,
        openfang=openfang,
        openfang_profiles_path=root / "config" / "openfang_profiles.yaml",
    )


class MsFangAPIHandler(BaseHTTPRequestHandler):
    """Route JSON HTTP requests into MsFang service operations."""

    root: Path = Path.cwd()

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _parse_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        if not raw.strip():
            return {}
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}

    def _service(self) -> MsFangService:
        return _build_service(self.root)

    def _segments(self) -> tuple[list[str], dict[str, list[str]]]:
        parsed = urlparse(self.path)
        segments = [x for x in parsed.path.split("/") if x]
        return segments, parse_qs(parsed.query)

    def _config_payload(self) -> dict[str, Any]:
        config_dir = self.root / "config"
        out: dict[str, Any] = {}
        for name in [
            "identities.yaml",
            "policies.yaml",
            "delegation.yaml",
            "openfang_profiles.yaml",
            "runtime_homes.yaml",
        ]:
            p = config_dir / name
            if p.exists():
                try:
                    out[name] = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    out[name] = p.read_text(encoding="utf-8")
        return out

    def _read_ticket_events(self, ticket_id: str, limit: int = 200) -> list[dict[str, str]]:
        p = self.root / "tickets" / ticket_id / "audit.log"
        if not p.exists():
            return []
        lines = [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
        events = lines[-max(1, min(limit, 500)) :]
        return [{"line": line} for line in events]

    def do_GET(self) -> None:  # noqa: N802
        try:
            segments, qs = self._segments()
            if len(segments) >= 1 and segments[0] != "v1":
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
                return

            svc = self._service()

            if segments == ["v1"] or segments == ["v1", "health"]:
                self._send_json(HTTPStatus.OK, {"ok": True, "root": str(self.root)})
                return

            if segments == ["v1", "doctor"]:
                self._send_json(HTTPStatus.OK, run_phase0_checks(self.root))
                return

            if segments == ["v1", "config"]:
                self._send_json(HTTPStatus.OK, {"ok": True, "config": self._config_payload()})
                return

            if segments == ["v1", "tickets"]:
                tickets_dir = self.root / "tickets"
                tickets: list[dict[str, Any]] = []
                for p in sorted(tickets_dir.iterdir()) if tickets_dir.exists() else []:
                    if not p.is_dir():
                        continue
                    try:
                        state = svc.show(p.name)
                        tickets.append(state.to_dict(include_history=False))
                    except Exception:
                        continue
                self._send_json(HTTPStatus.OK, {"ok": True, "tickets": tickets})
                return

            if len(segments) == 3 and segments[:2] == ["v1", "tickets"]:
                ticket_id = segments[2]
                state = svc.show(ticket_id)
                self._send_json(HTTPStatus.OK, {"ok": True, "ticket": state.to_dict(include_history=True)})
                return

            if len(segments) == 4 and segments[:2] == ["v1", "tickets"] and segments[3] == "events":
                ticket_id = segments[2]
                limit = int((qs.get("limit", ["200"]) or ["200"])[0])
                self._send_json(HTTPStatus.OK, {"ok": True, "events": self._read_ticket_events(ticket_id, limit=limit)})
                return

            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
        except Exception as exc:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        try:
            segments, _ = self._segments()
            if len(segments) < 2 or segments[0] != "v1":
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
                return

            body = self._parse_json_body()
            svc = self._service()

            if segments == ["v1", "init"]:
                payload = run_init(
                    self.root,
                    InitOptions(
                        yes=bool(body.get("yes", True)),
                        force=bool(body.get("force", False)),
                        owner_cli_user=str(body.get("owner_cli_user", "")),
                        owner_slack_id=str(body.get("owner_slack_id", "")),
                        channels_csv=str(body.get("channels_csv", "cli,slack")),
                        default_executor=str(body.get("default_executor", "openfang")),
                        default_profile=str(body.get("default_profile", "codex_cli")),
                    ),
                )
                self._send_json(HTTPStatus.OK, payload)
                return

            if segments == ["v1", "tickets"]:
                ticket_id = str(body.get("ticket_id", "")).strip()
                if not ticket_id:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "ticket_id is required"})
                    return
                criteria = body.get("success_criteria", [])
                if not isinstance(criteria, list):
                    criteria = [str(criteria)]
                owner = OwnerIdentities(
                    slack_user_ids=[str(x) for x in body.get("slack_user_ids", []) if str(x).strip()],
                    cli_os_users=[str(x) for x in body.get("cli_os_users", []) if str(x).strip()],
                )
                state = svc.preflight(ticket_id, success_criteria=[str(x) for x in criteria], owner=owner)
                self._send_json(HTTPStatus.CREATED, {"ok": True, "ticket": state.to_dict(include_history=True)})
                return

            if len(segments) >= 4 and segments[:2] == ["v1", "tickets"]:
                ticket_id = segments[2]
                action = segments[3]

                if action == "preflight":
                    criteria = body.get("criteria", [])
                    if not isinstance(criteria, list):
                        criteria = [str(criteria)]
                    owner = OwnerIdentities(
                        slack_user_ids=[str(x) for x in body.get("slack_user_ids", []) if str(x).strip()],
                        cli_os_users=[str(x) for x in body.get("cli_os_users", []) if str(x).strip()],
                    )
                    state = svc.preflight(ticket_id, success_criteria=[str(x) for x in criteria], owner=owner)
                    self._send_json(HTTPStatus.OK, {"ok": True, "ticket": state.to_dict(include_history=True)})
                    return

                if action == "plan":
                    state = svc.plan(ticket_id)
                    self._send_json(HTTPStatus.OK, {"ok": True, "ticket": state.to_dict(include_history=True)})
                    return

                if action == "execute":
                    notes = str(body.get("notes", ""))
                    state = svc.execute(ticket_id, loop_notes=notes)
                    self._send_json(HTTPStatus.OK, {"ok": True, "ticket": state.to_dict(include_history=True)})
                    return

                if action == "delegate":
                    state, result = svc.delegate_execute(
                        ticket_id,
                        action_type=str(body.get("action_type", "code_change")),
                        task=str(body.get("task", "")),
                        context=str(body.get("context", "")),
                        requested_executor=(str(body.get("executor", "")).strip() or None),
                        profile=(str(body.get("profile", "")).strip() or None),
                    )
                    self._send_json(
                        HTTPStatus.OK,
                        {
                            "ok": True,
                            "ticket": state.to_dict(include_history=True),
                            "delegation": result,
                        },
                    )
                    return

                if action == "critic":
                    state = svc.critic(
                        ticket_id,
                        success=bool(body.get("success", False)),
                        needs_input=bool(body.get("needs_input", False)),
                        failed=bool(body.get("failed", False)),
                        strikes_increment=int(body.get("strikes", 0)),
                    )
                    self._send_json(HTTPStatus.OK, {"ok": True, "ticket": state.to_dict(include_history=True)})
                    return

                if action == "janitor":
                    state = svc.janitor(ticket_id)
                    self._send_json(HTTPStatus.OK, {"ok": True, "ticket": state.to_dict(include_history=True)})
                    return

                if action == "undo":
                    state = svc.undo(ticket_id)
                    self._send_json(HTTPStatus.OK, {"ok": True, "ticket": state.to_dict(include_history=True)})
                    return

                if action == "prompt":
                    state = svc.set_prompt(ticket_id, str(body.get("text", "")))
                    self._send_json(HTTPStatus.OK, {"ok": True, "ticket": state.to_dict(include_history=True)})
                    return

                if action == "approval" and len(segments) >= 5:
                    sub = segments[4]
                    if sub == "request":
                        state = svc.request_approval(
                            ticket_id,
                            action_type=str(body.get("action_type", "config_change")),
                            context=str(body.get("context", "")),
                            ttl_minutes=int(body.get("ttl_minutes", 120)),
                        )
                        self._send_json(HTTPStatus.OK, {"ok": True, "ticket": state.to_dict(include_history=True)})
                        return
                    if sub == "accept":
                        state = svc.accept(ticket_id, approval_id=str(body.get("approval_id", "")))
                        self._send_json(HTTPStatus.OK, {"ok": True, "ticket": state.to_dict(include_history=True)})
                        return

            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
        except Exception as exc:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def do_PUT(self) -> None:  # noqa: N802
        try:
            segments, _ = self._segments()
            if segments == ["v1", "config"]:
                body = self._parse_json_body()
                config = body.get("config")
                if not isinstance(config, dict):
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "config payload is required"})
                    return
                config_dir = self.root / "config"
                config_dir.mkdir(parents=True, exist_ok=True)
                writes: list[dict[str, str]] = []
                for name, payload in config.items():
                    if not isinstance(name, str) or not name.endswith(".yaml"):
                        continue
                    p = config_dir / name
                    p.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                    writes.append({"path": str(p), "status": "written"})
                self._send_json(HTTPStatus.OK, {"ok": True, "writes": writes})
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
        except Exception as exc:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Allow", "GET,POST,PUT,OPTIONS")
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        # Keep API server quiet by default.
        _ = format
        _ = args


def run_server(*, root: Path, host: str = "127.0.0.1", port: int = 9387) -> None:
    handler = MsFangAPIHandler
    handler.root = root
    server = ThreadingHTTPServer((host, port), handler)
    print(
        json.dumps(
            {
                "ok": True,
                "service": "msfangd",
                "host": host,
                "port": port,
                "root": str(root),
            }
        )
    )
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="MsFang HTTP API server")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="MsFang repository root")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9387)
    args = parser.parse_args()
    run_server(root=args.root, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
