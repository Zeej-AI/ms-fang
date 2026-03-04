"""Policy-enforced code intelligence operations."""

from __future__ import annotations

from dataclasses import dataclass

from .adapters.jcodemunch_adapter import JCodeMunchAdapter
from .policy import PolicyEngine


@dataclass
class CodeIntelService:
    policy: PolicyEngine
    adapter: JCodeMunchAdapter

    def _assert_provider(self) -> None:
        if self.policy.config.enforce_jcodemunch_for_code_ops and self.policy.config.code_intel_provider != "jcodemunch":
            raise ValueError(
                "Code intelligence policy enforces jcodemunch, "
                f"but provider is set to '{self.policy.config.code_intel_provider}'"
            )

    def index_folder(self, path: str, use_ai_summaries: bool = False) -> dict:
        self._assert_provider()
        return self.adapter.index_folder(path=path, use_ai_summaries=use_ai_summaries)

    def search_symbols(self, repo: str, query: str, max_results: int = 10) -> dict:
        self._assert_provider()
        return self.adapter.search_symbols(repo=repo, query=query, max_results=max_results)

    def get_symbol(self, repo: str, symbol_id: str, verify: bool = False, context_lines: int = 0) -> dict:
        self._assert_provider()
        return self.adapter.get_symbol(repo=repo, symbol_id=symbol_id, verify=verify, context_lines=context_lines)
