#!/usr/bin/env bash
# Smoke test for hybrid retriever: 5 fixed queries, PASS/FAIL heuristics.
# Run from repo root. Requires: python -m src.run, jq.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if ! command -v jq &>/dev/null; then
  echo "Error: jq is required. Install with: brew install jq (macOS) or apt-get install jq (Linux)"
  exit 1
fi

RUN_CMD="python -m src.run --mode cli --user_id u001 --retriever hybrid --hybrid_alpha 1.0 --top_k 3"
FAILED=0

# Run one query and output top-3 sections; capture JSON for checks
run_query() {
  local q="$1"
  $RUN_CMD --issue "$q" 2>/dev/null
}

# Heuristic A: non-access queries -> top-3 must NOT contain rb-004-access-request-shared-drive.md
check_non_access() {
  local query="$1"
  local json
  json=$(run_query "$query")
  echo "$json" | jq -r '.debug.retrieved[:3] | .[] | "  \(.section) (\(.doc))"'
  local docs
  docs=$(echo "$json" | jq -r '.debug.retrieved[:3] | .[].doc' | tr '\n' ' ')
  if echo "$docs" | grep -q "rb-004-access-request-shared-drive"; then
    echo "  FAIL (non-access): top-3 must NOT contain rb-004-access-request-shared-drive.md"
    FAILED=1
  else
    echo "  PASS"
  fi
}

# Heuristic B: access queries -> top-3 MUST contain rb-004 or rb-005
check_access() {
  local query="$1"
  local json
  json=$(run_query "$query")
  echo "$json" | jq -r '.debug.retrieved[:3] | .[] | "  \(.section) (\(.doc))"'
  local docs
  docs=$(echo "$json" | jq -r '.debug.retrieved[:3] | .[].doc' | tr '\n' ' ')
  if echo "$docs" | grep -qE "rb-004-access-request-shared-drive|rb-005-access-request-basics-approvals-sla"; then
    echo "  PASS"
  else
    echo "  FAIL (access): top-3 must contain rb-004-access-request-shared-drive.md or rb-005-access-request-basics-approvals-sla.md"
    FAILED=1
  fi
}

echo "=== Smoke: Hybrid retriever (u001, alpha=1.0, top_k=3) ==="
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
