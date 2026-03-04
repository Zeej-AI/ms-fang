from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from msfang.http_api import MsFangAPIHandler
from msfang.models import OwnerIdentities
from msfang.onboarding import InitOptions, run_init
from msfang.policy import PolicyEngine
from msfang.service import MsFangService
from msfang.storage import TicketStore


class HttpApiTests(unittest.TestCase):
    def test_handler_reads_ticket_events_and_config(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_init(root, InitOptions(yes=True, owner_cli_user="claw"))

            svc = MsFangService(TicketStore(root), PolicyEngine.from_file(root / "config" / "policies.yaml"))
            svc.preflight("api-demo-1", ["done"], OwnerIdentities(cli_os_users=["claw"]))
            svc.plan("api-demo-1")

            handler = object.__new__(MsFangAPIHandler)
            handler.root = root

            events = handler._read_ticket_events("api-demo-1", limit=50)
            self.assertTrue(events)
            self.assertIn("plan", events[-1]["line"])

            cfg = handler._config_payload()
            self.assertIn("policies.yaml", cfg)
            self.assertIn("delegation.yaml", cfg)

    def test_handler_segments_parser(self):
        handler = object.__new__(MsFangAPIHandler)
        handler.path = "/v1/tickets/demo/events?limit=20&x=y"
        segments, qs = handler._segments()
        self.assertEqual(segments, ["v1", "tickets", "demo", "events"])
        self.assertEqual(qs.get("limit"), ["20"])
        self.assertEqual(qs.get("x"), ["y"])


if __name__ == "__main__":
    unittest.main()
