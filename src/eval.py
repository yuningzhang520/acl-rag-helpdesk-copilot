#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List


REPO_ROOT = Path(__file__).parent.parent
GOLDEN_PATH = REPO_ROOT / "golden_set" / "golden_set.jsonl"
OUT_CSV = REPO_ROOT / "eval_results.csv"


def run_pipeline(user_id: str, issue_text: str) -> Dict[str, Any]:
    """
    Calls: python -m src.run --mode mock --user_id ... --issue ...
    Returns parsed JSON output.
    """
    cmd = [
        sys.executable, "-m", "src.run",
        "--mode", "mock",
        "--user_id", user_id,
        "--issue", issue_text,
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"run failed: {p.stderr}\nstdout:\n{p.stdout}")
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"invalid JSON output:\n{p.stdout}") from e


def contains_restricted(citations: List[Dict[str, Any]]) -> bool:
    for c in citations or []:
        doc = (c.get("doc") or "")
        if "/restricted/" in doc.replace("\\", "/"):
            return True
    return False


def citation_contains_any(citations: List[Dict[str, Any]], substrs: List[str]) -> bool:
    if not substrs:
        return True
    for c in citations or []:
        doc = (c.get("doc") or "")
        for s in substrs:
            if s and s in doc:
                return True
    return False


def main():
    if not GOLDEN_PATH.exists():
        raise FileNotFoundError(f"golden set not found: {GOLDEN_PATH}")

    rows = []
    total = 0

    acl_violations = 0
    triage_correct = 0
    priority_correct = 0
    approval_gate_correct = 0

    with GOLDEN_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            gs = json.loads(line)
            total += 1

            got = run_pipeline(gs["user_id"], gs["issue_text"])
            triage = got.get("triage") or {}
            citations = got.get("citations") or []
            proposed_struct = got.get("proposed_actions_struct") or {}

            # ---- ACL: must not cite restricted ----
            acl_ok = True
            if "restricted" in (gs.get("must_not_cite") or []):
                if contains_restricted(citations):
                    acl_ok = False
            if not acl_ok:
                acl_violations += 1

            # ---- Citation must include certain doc name substrings (optional) ----
            cite_ok = citation_contains_any(citations, gs.get("must_cite") or [])

            # ---- Triage accuracy ----
            cat_ok = (triage.get("category") == gs.get("expected_category"))
            prio_ok = (triage.get("priority") == gs.get("expected_priority"))
            if cat_ok:
                triage_correct += 1
            if prio_ok:
                priority_correct += 1
            
                        # ---- Debug prints (mismatches) ----
            if not cat_ok:
                print("\n[CATEGORY MISMATCH]")
                print(f"id: {gs.get('id','')}")
                print(f"user_id: {gs['user_id']}")
                print(f"expected: {gs.get('expected_category')} | got: {triage.get('category')}")
                print(f"text: {gs['issue_text']}")

            if not prio_ok:
                print("\n[PRIORITY MISMATCH]")
                print(f"id: {gs.get('id','')}")
                print(f"user_id: {gs['user_id']}")
                print(f"expected: {gs.get('expected_priority')} | got: {triage.get('priority')}")
                print(f"category: {triage.get('category')}")
                print(f"text: {gs['issue_text']}")

            # ---- Approval gate correctness (based on your current logic) ----
            # We judge only the computed struct, not GitHub side effects.
            expected_approval = gs.get("expected_approval", "n/a")
            gate_ok = True
            if expected_approval == "L2_requires_IT_Admin":
                gate_ok = (
                    proposed_struct.get("risk_level") == "L2"
                    and proposed_struct.get("needs_approval") is True
                    and proposed_struct.get("approval_role") == "IT Admin"
                )
            elif expected_approval == "n/a":
                # In your code, non-github mode sets needs_approval False
                gate_ok = (proposed_struct.get("needs_approval") is False)
            if gate_ok:
                approval_gate_correct += 1

                        # ---- pass/fail + reason (for demo readability) ----
            fail_reasons = []
            if not acl_ok:
                fail_reasons.append("acl_violation")
            if not cite_ok:
                fail_reasons.append("citation_mismatch")
            if not cat_ok:
                fail_reasons.append("category_mismatch")
            if not prio_ok:
                fail_reasons.append("priority_mismatch")
            if not gate_ok:
                fail_reasons.append("approval_gate_wrong")

            passed = (len(fail_reasons) == 0)
            fail_reason = "|".join(fail_reasons)


            rows.append({
                "id": gs.get("id", ""),
                "user_id": gs["user_id"],
                "expected_category": gs.get("expected_category", ""),
                "got_category": triage.get("category", ""),
                "expected_priority": gs.get("expected_priority", ""),
                "got_priority": triage.get("priority", ""),
                "acl_ok": acl_ok,
                "cite_ok": cite_ok,
                "approval_gate_ok": gate_ok,
                "passed": passed,
                "fail_reason": fail_reason,
                "retrieval_confidence": got.get("retrieval_confidence", ""),
            })

    # Write CSV
    import csv
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # Print summary
    print("=== Eval Summary ===")
    print(f"cases: {total}")
    print(f"ACL violations: {acl_violations}")
    print(f"triage_accuracy(category): {triage_correct}/{total} = {triage_correct/total:.2%}")
    print(f"triage_accuracy(priority): {priority_correct}/{total} = {priority_correct/total:.2%}")
    print(f"approval_gate_correctness: {approval_gate_correct}/{total} = {approval_gate_correct/total:.2%}")
    print(f"wrote: {OUT_CSV}")


if __name__ == "__main__":
    main()
