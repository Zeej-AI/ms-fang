from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from msfang.adapters.openfang_adapter import WorkerResult
from msfang.delegation import DelegationEngine
from msfang.exceptions import ApprovalError, DelegationError
from msfang.models import OwnerIdentities
from msfang.policy import PolicyEngine
from msfang.service import MsFangService
from msfang.storage import TicketStore


class _StubOpenFang:
    def run_profile(self, profile_name: str, task: str, context: str = "", profiles_path: Path | None = None) -> WorkerResult:
        return WorkerResult(success=True, output=f"profile={profile_name} task={task} context={context}")


class DelegateServiceTests(unittest.TestCase):
    def test_delegate_execute_routes_to_openfang(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "config").mkdir(parents=True, exist_ok=True)
            (root / "config" / "policies.yaml").write_text(
                (
                    '{"action_risk_map":{"code_change":"green","os_change":"red"},'
                    '"approval_required_for":["red"],"strike_threshold_red":3,"max_history":50,'
                    '"code_intel_provider":"jcodemunch","enforce_jcodemunch_for_code_ops":true}'
                ),
                encoding="utf-8",
            )
            (root / "config" / "delegation.yaml").write_text(
                (
                    '{"enforce_routes":true,"default_executor":"openfang","default_openfang_profile":"codex_cli",'
                    '"allowed_executors":["hermes","openfang"],'
                    '"action_routes":{"code_change":"openfang","os_change":"hermes"},'
                    '"command_routes":{"execute":"openfang","delegate":"openfang"}}'
                ),
                encoding="utf-8",
            )
            (root / "config" / "openfang_profiles.yaml").write_text(
                '{"default_profile":"codex_cli","profiles":{"codex_cli":{"agent":"coder","instructions":"x"}}}',
                encoding="utf-8",
            )

            svc = MsFangService(
                TicketStore(root),
                PolicyEngine.from_file(root / "config" / "policies.yaml"),
                delegation=DelegationEngine.from_file(root / "config" / "delegation.yaml"),
                openfang=_StubOpenFang(),  # type: ignore[arg-type]
                openfang_profiles_path=root / "config" / "openfang_profiles.yaml",
            )
            svc.preflight("demo", ["done"], OwnerIdentities(cli_os_users=["claw"]))
            svc.plan("demo")

            state, result = svc.delegate_execute(
                "demo",
                action_type="code_change",
                task="implement test",
                context="ctx",
            )

            self.assertEqual(state.phase.value, "execute")
            self.assertEqual(result["executor"], "openfang")
            self.assertTrue(result["worker"]["success"])

    def test_delegate_execute_blocks_policy_override_and_red_without_approval(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "config").mkdir(parents=True, exist_ok=True)
            (root / "config" / "policies.yaml").write_text(
                (
                    '{"action_risk_map":{"code_change":"green","os_change":"red"},'
                    '"approval_required_for":["red"],"strike_threshold_red":3,"max_history":50,'
                    '"code_intel_provider":"jcodemunch","enforce_jcodemunch_for_code_ops":true}'
                ),
                encoding="utf-8",
            )
            (root / "config" / "delegation.yaml").write_text(
                (
                    '{"enforce_routes":true,"default_executor":"openfang","default_openfang_profile":"codex_cli",'
                    '"allowed_executors":["hermes","openfang"],'
                    '"action_routes":{"code_change":"openfang","os_change":"hermes"},'
                    '"command_routes":{"execute":"openfang","delegate":"openfang"}}'
                ),
                encoding="utf-8",
            )
            (root / "config" / "openfang_profiles.yaml").write_text(
                '{"default_profile":"codex_cli","profiles":{"codex_cli":{"agent":"coder","instructions":"x"}}}',
                encoding="utf-8",
            )

            svc = MsFangService(
                TicketStore(root),
                PolicyEngine.from_file(root / "config" / "policies.yaml"),
                delegation=DelegationEngine.from_file(root / "config" / "delegation.yaml"),
                openfang=_StubOpenFang(),  # type: ignore[arg-type]
                openfang_profiles_path=root / "config" / "openfang_profiles.yaml",
            )
            svc.preflight("demo", ["done"], OwnerIdentities(cli_os_users=["claw"]))
            svc.plan("demo")

            with self.assertRaises(DelegationError):
                svc.delegate_execute(
                    "demo",
                    action_type="code_change",
                    task="should fail route override",
                    requested_executor="hermes",
                )

            with self.assertRaises(ApprovalError):
                svc.delegate_execute(
                    "demo",
                    action_type="os_change",
                    task="sudo apt install",
                )


if __name__ == "__main__":
    unittest.main()
