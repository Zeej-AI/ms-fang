"""jcodemunch adapter via isolated Python interpreter tool calls."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class JCodeMunchAdapterConfig:
    python_bin: Path = Path("/Users/claw/.msfang/jcodemunch/venv/bin/python")
    timeout_seconds: int = 180


class JCodeMunchAdapter:
    def __init__(self, config: JCodeMunchAdapterConfig | None = None):
        self.config = config or JCodeMunchAdapterConfig()

    def _call(self, module: str, func: str, kwargs: dict[str, Any]) -> dict:
        bridge = (
            "import json,sys;"
            "m=sys.argv[1];f=sys.argv[2];"
            "kw=json.loads(sys.stdin.read() or '{}');"
            "mod=__import__(m,fromlist=[f]);"
            "fn=getattr(mod,f);"
            "res=fn(**kw);"
            "print(json.dumps(res))"
        )

        proc = subprocess.run(
            [str(self.config.python_bin), "-c", bridge, module, func],
            input=json.dumps(kwargs),
            capture_output=True,
            text=True,
            timeout=self.config.timeout_seconds,
        )

        if proc.returncode != 0:
            return {
                "success": False,
                "error": proc.stderr.strip() or proc.stdout.strip() or "jcodemunch call failed",
            }

        try:
            data = json.loads(proc.stdout.strip() or "{}")
            if isinstance(data, dict):
                return data
            return {"success": True, "data": data}
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "invalid JSON response from jcodemunch",
                "raw": proc.stdout.strip(),
            }

    def index_folder(self, path: str, use_ai_summaries: bool = False) -> dict:
        return self._call(
            "jcodemunch_mcp.tools.index_folder",
            "index_folder",
            {"path": path, "use_ai_summaries": use_ai_summaries},
        )

    def search_symbols(self, repo: str, query: str, max_results: int = 10) -> dict:
        return self._call(
            "jcodemunch_mcp.tools.search_symbols",
            "search_symbols",
            {"repo": repo, "query": query, "max_results": max_results},
        )

    def get_symbol(self, repo: str, symbol_id: str, verify: bool = False, context_lines: int = 0) -> dict:
        return self._call(
            "jcodemunch_mcp.tools.get_symbol",
            "get_symbol",
            {
                "repo": repo,
                "symbol_id": symbol_id,
                "verify": verify,
                "context_lines": context_lines,
            },
        )
