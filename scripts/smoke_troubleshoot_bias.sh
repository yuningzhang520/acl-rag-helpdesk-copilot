#!/usr/bin/env bash
# Smoke test for troubleshooting intent bias (keyword + hybrid).
# Run from repo root. Requires: python -m src.run, jq.
# A) Troubleshoot query + bias ON + alpha=1.0 → "Step 4: Verify access and close ticket" should rank above "Purpose" / "Step 1: Validate request"
# B) Non-troubleshoot query + bias ON → Purpose/Step1 still in top
# C) Same as A with bias OFF → current behavior (no bias)

set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
USER="${1:-u005}"

run_top3() {
  python -m src.run --user_id "$USER" --issue "$1" --retriever hybrid --hybrid_alpha "${2:-1.0}" --top_k 5 "$3" 2>/dev/null | jq -r '.debug.retrieved[:3] | .[] | "\(.section) (score: \(.final_score // .score))"'
}

echo "=== A) Troubleshoot query, bias ON, alpha=1.0 ==="
echo "Query: someone can't see the drive anymore"
run_top3 "someone can't see the drive anymore" "1.0" ""
echo ""

echo "=== B) Non-troubleshoot query, bias ON ==="
echo "Query: give someone access to a team drive"
run_top3 "give someone access to a team drive" "0.7" ""
echo ""

echo "=== C) Troubleshoot query, bias OFF (reproduce current behavior) ==="
echo "Query: someone can't see the drive anymore"
run_top3 "someone can't see the drive anymore" "1.0" "--no_troubleshoot_bias"
echo ""

# Acceptance A: with bias ON, top result should be verify/close-ticket style (Step 4) above Purpose/Step1
echo "=== Acceptance A check: bias ON → top section should be verify/close-ticket style ==="
TOP_SECTION=$(python -m src.run --user_id "$USER" --issue "someone can't see the drive anymore" --retriever hybrid --hybrid_alpha 1.0 --top_k 3 2>/dev/null | jq -r '.debug.retrieved[0].section')
if echo "$TOP_SECTION" | grep -qiE "verify|close ticket|troubleshoot"; then
  echo "PASS: top section is '$TOP_SECTION'"
else
  echo "FAIL: expected top section to contain verify/close ticket/troubleshoot; got '$TOP_SECTION'"
  exit 1
fi
echo "Done."
