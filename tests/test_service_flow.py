from pathlib import Path
import tempfile
import unittest

from msfang.models import OwnerIdentities
from msfang.policy import PolicyEngine
from msfang.service import MsFangService
from msfang.storage import TicketStore


class ServiceFlowTests(unittest.TestCase):
    def test_end_to_end_ticket_lifecycle(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "config").mkdir(parents=True, exist_ok=True)
            (root / "config" / "policies.yaml").write_text(
                '{"action_risk_map":{"os_change":"red","code_change":"green"},"approval_required_for":["red"],"strike_threshold_red":3,"max_history":50}',
                encoding="utf-8",
            )

            svc = MsFangService(TicketStore(root), PolicyEngine.from_file(root / "config" / "policies.yaml"))

            state = svc.preflight("demo", ["criteria"], OwnerIdentities(cli_os_users=["claw"]))
            self.assertEqual(state.phase.value, "preflight")

            state = svc.plan("demo")
            self.assertEqual(state.phase.value, "plan")

            state = svc.execute("demo", "loop notes")
            self.assertEqual(state.phase.value, "execute")
            self.assertTrue((root / "tickets" / "demo" / "working_summary.md").exists())

            state = svc.critic("demo", success=True, needs_input=False, failed=False)
            self.assertEqual(state.gate.value, "green")

            state = svc.janitor("demo")
            self.assertEqual(state.phase.value, "closed")
            self.assertEqual(state.status.value, "complete")


if __name__ == "__main__":
    unittest.main()
