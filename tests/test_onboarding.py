from pathlib import Path
import tempfile
import unittest

from msfang.onboarding import InitOptions, run_init


class OnboardingTests(unittest.TestCase):
    def test_init_writes_expected_config_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = run_init(
                root,
                InitOptions(
                    yes=True,
                    owner_cli_user="claw",
                    owner_slack_id="U123",
                    channels_csv="cli,slack",
                    default_executor="openfang",
                    default_profile="codex_cli",
                ),
            )
            self.assertTrue(out["ok"])
            self.assertTrue((root / "config" / "identities.yaml").exists())
            self.assertTrue((root / "config" / "policies.yaml").exists())
            self.assertTrue((root / "config" / "delegation.yaml").exists())
            self.assertTrue((root / "config" / "openfang_profiles.yaml").exists())

    def test_init_without_force_keeps_existing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_init(root, InitOptions(yes=True, owner_cli_user="claw"))
            out = run_init(root, InitOptions(yes=True, owner_cli_user="other", force=False))
            kept = [x for x in out["writes"] if x["status"] == "kept"]
            self.assertTrue(kept)


if __name__ == "__main__":
    unittest.main()
