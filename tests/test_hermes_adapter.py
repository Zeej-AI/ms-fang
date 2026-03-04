from pathlib import Path
import tempfile
import unittest

from msfang.adapters.hermes_adapter import HermesAdapter
from msfang.models import OwnerIdentities
from msfang.policy import PolicyEngine
from msfang.service import MsFangService
from msfang.storage import TicketStore


class HermesAdapterTests(unittest.TestCase):
    def test_parse_execute_payload(self):
        adapter = HermesAdapter()
        cmd = adapter.parse_text(
            text="/execute run tests for current ticket",
            ticket_id="t1",
            actor="claw",
            channel="cli",
        )
        self.assertEqual(cmd.name, "execute")
        self.assertEqual(cmd.payload["notes"], "run tests for current ticket")
        self.assertEqual(cmd.payload["action_type"], "code_change")

    def test_parse_execute_with_explicit_action(self):
        adapter = HermesAdapter()
        cmd = adapter.parse_text(
            text="/execute test_run :: run unit tests",
            ticket_id="t1",
            actor="claw",
            channel="cli",
        )
        self.assertEqual(cmd.payload["action_type"], "test_run")
        self.assertEqual(cmd.payload["notes"], "run unit tests")

    def test_service_routes_hermes_commands(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "config").mkdir(parents=True, exist_ok=True)
            (root / "config" / "policies.yaml").write_text(
                '{"action_risk_map":{"code_change":"green"},"approval_required_for":["red"],"strike_threshold_red":3,"max_history":50}',
                encoding="utf-8",
            )

            svc = MsFangService(TicketStore(root), PolicyEngine.from_file(root / "config" / "policies.yaml"))
            svc.preflight("demo", ["ok"], OwnerIdentities(cli_os_users=["claw"]))

            adapter = HermesAdapter()
            plan_cmd = adapter.parse_text(text="/plan", ticket_id="demo", actor="claw", channel="cli")
            state = svc.handle_hermes_command(plan_cmd)
            self.assertEqual(state.phase.value, "plan")

            exec_cmd = adapter.parse_text(text="/execute draft implementation", ticket_id="demo", actor="claw", channel="cli")
            state = svc.handle_hermes_command(exec_cmd)
            self.assertEqual(state.phase.value, "execute")


if __name__ == "__main__":
    unittest.main()
