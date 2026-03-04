from pathlib import Path
import tempfile
import unittest

from msfang.policy import PolicyEngine


class PolicyTests(unittest.TestCase):
    def test_defaults(self):
        with tempfile.TemporaryDirectory() as td:
            engine = PolicyEngine.from_file(Path(td) / "missing.yaml")
            self.assertTrue(engine.requires_approval("os_change"))
            self.assertFalse(engine.requires_approval("code_change"))

    def test_file_override(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "policies.yaml"
            p.write_text('{"action_risk_map":{"x":"red"},"approval_required_for":["red"],"strike_threshold_red":4,"max_history":10}', encoding="utf-8")
            engine = PolicyEngine.from_file(p)
            self.assertEqual(engine.classify("x"), "red")
            self.assertEqual(engine.config.strike_threshold_red, 4)
            self.assertEqual(engine.config.max_history, 10)


if __name__ == "__main__":
    unittest.main()
