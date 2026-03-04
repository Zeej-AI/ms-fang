from pathlib import Path
import tempfile
import unittest

from msfang.code_intel import CodeIntelService
from msfang.policy import PolicyEngine


class _StubAdapter:
    def index_folder(self, path: str, use_ai_summaries: bool = False) -> dict:
        return {"ok": True, "op": "index", "path": path, "use_ai_summaries": use_ai_summaries}

    def search_symbols(self, repo: str, query: str, max_results: int = 10) -> dict:
        return {"ok": True, "op": "search", "repo": repo, "query": query, "max_results": max_results}

    def get_symbol(self, repo: str, symbol_id: str, verify: bool = False, context_lines: int = 0) -> dict:
        return {
            "ok": True,
            "op": "get",
            "repo": repo,
            "symbol_id": symbol_id,
            "verify": verify,
            "context_lines": context_lines,
        }


class CodeIntelPolicyTests(unittest.TestCase):
    def test_jcodemunch_enforced_rejects_other_provider(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "policies.yaml"
            cfg.write_text(
                (
                    '{"action_risk_map":{},"approval_required_for":["red"],"strike_threshold_red":3,'
                    '"max_history":50,"code_intel_provider":"other","enforce_jcodemunch_for_code_ops":true}'
                ),
                encoding="utf-8",
            )
            policy = PolicyEngine.from_file(cfg)
            svc = CodeIntelService(policy=policy, adapter=_StubAdapter())  # type: ignore[arg-type]
            with self.assertRaises(ValueError):
                svc.search_symbols(repo="local/demo", query="test")

    def test_non_enforced_policy_allows_calls(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "policies.yaml"
            cfg.write_text(
                (
                    '{"action_risk_map":{},"approval_required_for":["red"],"strike_threshold_red":3,'
                    '"max_history":50,"code_intel_provider":"other","enforce_jcodemunch_for_code_ops":false}'
                ),
                encoding="utf-8",
            )
            policy = PolicyEngine.from_file(cfg)
            svc = CodeIntelService(policy=policy, adapter=_StubAdapter())  # type: ignore[arg-type]
            out = svc.get_symbol(repo="local/demo", symbol_id="x::y#class", verify=True, context_lines=3)
            self.assertTrue(out["ok"])
            self.assertEqual(out["op"], "get")


if __name__ == "__main__":
    unittest.main()
