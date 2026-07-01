#!/usr/bin/env bash
# One-time preflight: confirms your environment will run the Agent SDK on your
# Max plan (not the API). Run this FIRST, then `python smoke_test.py`.
#   usage:  bash preflight.sh
set -u
echo "== EdTech3 preflight =="

# 1) No API key. In headless/SDK mode a set ANTHROPIC_API_KEY OVERRIDES your
#    subscription and bills the API (which you don't have). This is the #1 gotcha.
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  echo "FAIL: ANTHROPIC_API_KEY is set — it overrides your Max plan in headless mode."
  echo "      Fix: unset ANTHROPIC_API_KEY   (and remove it from ~/.zshrc / ~/.bashrc)"
  exit 1
fi
echo "OK: ANTHROPIC_API_KEY is not set."

# ANTHROPIC_AUTH_TOKEN also overrides subscription auth (gateway/proxy use).
if [ -n "${ANTHROPIC_AUTH_TOKEN:-}" ]; then
  echo "WARN: ANTHROPIC_AUTH_TOKEN is set; it also overrides subscription auth."
  echo "      Unset it unless you are intentionally routing through a gateway."
fi

# 2) Claude Code present + logged in.
if ! command -v claude >/dev/null 2>&1; then
  echo "FAIL: 'claude' not found. Install Claude Code, run 'claude', log in with Max."
  exit 1
fi
echo "OK: claude CLI found -> $(claude --version 2>/dev/null | head -n1)"

# 3) CLI-level auth smoke test via headless print mode (uses the same auth path
#    as the SDK). Proves your subscription answers a request end to end.
echo "-- CLI smoke test (claude -p) --"
OUT="$(claude -p 'Respond with exactly: SMOKE_OK' 2>&1)"
if echo "$OUT" | grep -q "SMOKE_OK"; then
  echo "OK: CLI returned a response on your subscription."
else
  echo "FAIL: CLI smoke test did not return the expected output."
  echo "      Output was: $OUT"
  echo "      If this mentions auth/login/credit: run 'claude', log in with your Max"
  echo "      plan, type /status to confirm the active method, then re-run."
  exit 1
fi

echo "== CLI preflight PASSED. Next: python smoke_test.py =="
