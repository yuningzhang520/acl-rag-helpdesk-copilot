#!/usr/bin/env bash
# Smoke test for troubleshooting intent bias (hybrid).
# Run from repo root. Requires: python -m src.run, jq.
# A) Troubleshoot query + bias ON + alpha=1.0 → "Step 4: Verify access and close ticket" should rank above "Purpose"/"Step 1"
# B) Non-troubleshoot query + bias ON → "Purpose"/"Step 1" should remain in top-3
# C) Troubleshoot query + bias OFF → compare behavior

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if ! command -v jq &>/dev/null; then
  echo "Error: jq is required. Install with: brew install jq (macOS) or apt-get install jq (Linux)"
  exit 1
fi

USER="${1:-u005}"

run_top3() {
  local query="$1"
  local alpha="${2:-1.0}"
  local extra="${3:-}"
  python -m src.run \
    --mode cli \
    --user_id "$USER" \
    --issue "$query" \
    --retriever hybrid \
    --hybrid_alpha "$alpha" \
    --top_k 5 \
    $extra 2>/dev/null \
    | jq -r '.debug.retrieved[:3] | .[] | "\(.section) (score: \(.final_score // .score))"'
}

echo "=== A) Troubleshoot query, bias ON, alpha=1.0 ==="
echo "Query: someone can't see the drive anymore"
run_top3 "someone can't see the drive anymore" "1.0" ""
echo ""

echo "=== B) Non-troubleshoot query, bias ON ==="
echo "Query: give someone access to a team drive"
run_top3 "give someone access to a team drive" "0.7" ""
echo ""

echo "=== C) Troubleshoot query, bias OFF ==="
echo "Query: someone can't see the drive anymore"
run_top3 "someone can't see the drive anymore" "1.0" "--no_troubleshoot_bias"
echo ""

echo "=== Acceptance A check: bias ON → top section should be verify/close-ticket style ==="
TOP_SECTION=$(
  python -m src.run --mode cli --user_id "$USER" --issue "someone can't see the drive anymore" \
    --retriever hybrid --hybrid_alpha 1.0 --top_k 3 2>/dev/null \
    | jq -r '.debug.retrieved[0].section'
)

if echo "$TOP_SECTION" | grep -qiE "verify|close ticket|troubleshoot"; then
  echo "PASS: top section is '$TOP_SECTION'"
else
  echo "FAIL: expected top section to contain verify/close ticket/troubleshoot; got '$TOP_SECTION'"
  exit 1
fi

echo "Done."
