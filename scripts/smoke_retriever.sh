#!/usr/bin/env bash
# Smoke test: hybrid retriever (alpha=0.7) + keyword baseline (alpha=1.0). 5 queries, PASS/FAIL on hybrid.
# Run from repo root. Requires: python -m src.run, jq.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if ! command -v jq &>/dev/null; then
  echo "Error: jq is required. Install with: brew install jq (macOS) or apt-get install jq (Linux)"
  exit 1
fi

DEFAULT_ALPHA=0.7
RUN_CMD="python -m src.run --mode cli --user_id u001 --retriever hybrid --hybrid_alpha $DEFAULT_ALPHA --top_k 3"
RUN_CMD_BASELINE="python -m src.run --mode cli --user_id u001 --retriever hybrid --hybrid_alpha 1.0 --top_k 3"
FAILED=0

# Run a command with --issue and emit JSON to stdout (bash -lc avoids word-splitting of cmd)
run_with_issue() {
  local cmd="$1"
  local q="$2"
  local out
  out=$(bash -lc "$cmd --issue \"$q\"" 2>/dev/null || true)
  # basic sanity: must look like JSON
  if [[ -z "$out" ]] || [[ "$out" != \{* ]]; then
    echo "{\"error\":\"pipeline_failed_or_non_json\",\"cmd\":\"$cmd\",\"query\":\"$q\",\"raw\":\"${out:0:200}\"}"
    return 0
  fi
  echo "$out"
}

# Print top-3 sections from pipeline JSON
print_top3() {
  echo "$1" | jq -r '.debug.retrieved[:3] | .[] | "  \(.section) (\(.doc))"'
}

# Heuristic A: non-access -> top-3 must NOT contain rb-004-access-request-shared-drive.md
check_non_access() {
  local query="$1"
  local json
  json=$(run_with_issue "$RUN_CMD" "$query")
  print_top3 "$json"
  local docs
  docs=$(echo "$json" | jq -r '.debug.retrieved[:3] | .[].doc' | tr '\n' ' ')
  if echo "$docs" | grep -q "rb-004-access-request-shared-drive"; then
    echo "  FAIL (non-access): top-3 must NOT contain rb-004-access-request-shared-drive.md"
    FAILED=1
  else
    echo "  PASS"
  fi
  echo "  Keyword baseline (alpha=1.0):"
  print_top3 "$(run_with_issue "$RUN_CMD_BASELINE" "$query")"
}

# Heuristic B: access -> top-3 MUST contain rb-004 or rb-005
check_access() {
  local query="$1"
  local json
  json=$(run_with_issue "$RUN_CMD" "$query")
  print_top3 "$json"
  local docs
  docs=$(echo "$json" | jq -r '.debug.retrieved[:3] | .[].doc' | tr '\n' ' ')
  if echo "$docs" | grep -qE "rb-004-access-request-shared-drive|rb-005-access-request-basics-approvals-sla"; then
    echo "  PASS"
  else
    echo "  FAIL (access): top-3 must contain rb-004-access-request-shared-drive.md or rb-005-access-request-basics-approvals-sla.md"
    FAILED=1
  fi
  echo "  Keyword baseline (alpha=1.0):"
  print_top3 "$(run_with_issue "$RUN_CMD_BASELINE" "$query")"
}

echo "=== Smoke: Hybrid retriever (alpha=$DEFAULT_ALPHA) + keyword baseline (alpha=1.0) ==="
echo ""

echo "--- Access: add a coworker to the shared drive ---"
check_access "add a coworker to the shared drive"
echo ""

echo "--- Access: someone can't see the drive anymore ---"
check_access "someone can't see the drive anymore"
echo ""

echo "--- VPN: vpn keeps disconnecting ---"
check_non_access "vpn keeps disconnecting"
echo ""

echo "--- MFA: mfa reset lost phone ---"
check_non_access "mfa reset lost phone"
echo ""

echo "--- Onboarding: new hire onboarding access ---"
check_non_access "new hire onboarding access"
echo ""

if [[ $FAILED -eq 1 ]]; then
  echo "One or more heuristics failed. Exit 1."
  exit 1
fi
echo "All heuristics passed. Exit 0."
exit 0
