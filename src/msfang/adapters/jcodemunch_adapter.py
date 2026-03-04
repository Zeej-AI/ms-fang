"""jcodemunch MCP adapter contract."""

from __future__ import annotations


class JCodeMunchAdapter:
    def search_symbols(self, repo: str, query: str) -> dict:
        # Thin placeholder contract. Real implementation will call MCP tools.
        return {"repo": repo, "query": query, "results": []}
