from pathlib import Path
import tempfile
import unittest

from msfang.delegation import DelegationEngine
from msfang.exceptions import DelegationError


class DelegationTests(unittest.TestCase):
    def test_enforced_routes_block_override(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "delegation.yaml"
            cfg.write_text(
                (
                    '{"enforce_routes":true,"default_executor":"openfang","default_openfang_profile":"codex_cli",'
                    '"allowed_executors":["hermes","openfang"],'
                    '"action_routes":{"code_change":"openfang"},"command_routes":{"execute":"openfang"}}'
                ),
                encoding="utf-8",
            )
            d = DelegationEngine.from_file(cfg)
            self.assertEqual(d.route_action("code_change"), "openfang")
            self.assertEqual(d.route_command("execute"), "openfang")
            with self.assertRaises(DelegationError):
                d.route_action("code_change", requested_executor="hermes")

    def test_non_enforced_routes_allow_override(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "delegation.yaml"
            cfg.write_text(
                (
                    '{"enforce_routes":false,"default_executor":"openfang","default_openfang_profile":"codex_cli",'
                    '"allowed_executors":["hermes","openfang"],'
                    '"action_routes":{"code_change":"openfang"},"command_routes":{"execute":"openfang"}}'
                ),
                encoding="utf-8",
            )
            d = DelegationEngine.from_file(cfg)
            self.assertEqual(d.route_action("code_change", requested_executor="hermes"), "hermes")


if __name__ == "__main__":
    unittest.main()
