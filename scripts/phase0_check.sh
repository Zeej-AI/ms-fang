#!/usr/bin/env bash
set -euo pipefail

echo "== Phase 0 environment check =="

if command -v gh >/dev/null 2>&1; then
  echo "gh: $(gh --version | head -n 1)"
  gh auth status >/dev/null 2>&1 && echo "gh auth: ok" || echo "gh auth: missing"
else
  echo "gh: missing"
fi

for c in hermes openfang jcodemunch-mcp; do
  if command -v "$c" >/dev/null 2>&1; then
    echo "$c: installed"
  else
    echo "$c: missing"
  fi
done

if [ -x "$HOME/.lmstudio/bin/lms" ]; then
  "$HOME/.lmstudio/bin/lms" server status || true
fi

if curl -sS -m 2 http://127.0.0.1:1234/v1/models >/dev/null; then
  echo "LM Studio API: up"
else
  echo "LM Studio API: down"
fi
