#!/usr/bin/env python3
"""
Policy / system correctness evaluation (run via: python -m src.eval or python scripts/eval_policy.py).

What it measures:
  - ACL: no restricted-tier citations when must_not_cite contains "restricted".
  - Citation: at least one citation matches must_cite (doc name substrings) when set.
  - Triage: category and priority match expected_category, expected_priority.
  - Approval gate: proposed_actions_struct matches expected_approval (e.g. L2_requires_IT_Admin or n/a).

Golden set: golden_set/golden_set.jsonl with expected_category, expected_priority,
expected_approval, must_cite, must_not_cite. Outputs: workflows/eval_policy_results.csv,
workflows/eval_policy_report.md.
"""

import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_PATH = REPO_ROOT / "golden_set" / "golden_set.jsonl"
OUT_CSV = REPO_ROOT / "workflows" / "eval_policy_results.csv"
OUT_MD = REPO_ROOT / "workflows" / "eval_policy_report.md"


def run_pipeline(user_id: str, issue_text: str) -> Dict[str, Any]:
    """Run pipeline with --mode cli; return parsed JSON."""
    cmd = [
        sys.executable, "-m", "src.run",
        "--mode", "cli",
        "--user_id", user_id,
        "--issue", issue_text,
    ]
    p = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"run failed: {p.stderr}\nstdout:\n{p.stdout}")
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"invalid JSON output:\n{p.stdout}") from e


def contains_restricted(citations: List[Dict[str, Any]]) -> bool:
    for c in citations or []:
        if c.get("tier") == "restricted":
            return True
        doc = (c.get("doc") or "")
        if "/restricted/" in doc.replace("\\", "/"):
            return True
    return False

def citation_contains_any(citations: List[Dict[str, Any]], substrs: List[str]) -> bool:
    if not substrs:
        return True
    for c in citations or []:
        doc = (c.get("doc") or "").replace("\\", "/")
        filename = doc.split("/")[-1] if doc else ""
        for s in substrs:
            if not s:
                continue
            if s in filename:
                return True
            if s in doc:
                return True
    return False

def main() -> None:
    if not GOLDEN_PATH.exists():
        raise FileNotFoundError(f"Golden set not found: {GOLDEN_PATH}")
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    total = 0
    acl_violations = 0
    triage_correct = 0
    priority_correct = 0
    approval_gate_correct = 0

    with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
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

            acl_ok = True
            if "restricted" in (gs.get("must_not_cite") or []):
                if contains_restricted(citations):
                    acl_ok = False
            if not acl_ok:
                acl_violations += 1

            cite_ok = citation_contains_any(citations, gs.get("must_cite") or [])

            cat_ok = (triage.get("category") == gs.get("expected_category"))
            prio_ok = (triage.get("priority") == gs.get("expected_priority"))
            if cat_ok:
                triage_correct += 1
            if prio_ok:
                priority_correct += 1

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

            expected_approval = gs.get("expected_approval", "n/a")
            gate_ok = True
            if expected_approval == "L2_requires_IT_Admin":
                gate_ok = (
                    proposed_struct.get("risk_level") == "L2"
                    and proposed_struct.get("needs_approval") is True
                    and (proposed_struct.get("approval_role_required") or proposed_struct.get("approval_role")) == "IT Admin"
                )
            elif expected_approval == "n/a":
                gate_ok = (proposed_struct.get("needs_approval") is False)
            if gate_ok:
                approval_gate_correct += 1

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
                "retrieval_confidence": got.get("retrieval_confidence", got.get("confidence", "")),
            })

    fieldnames = list(rows[0].keys()) if rows else []
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    pct = lambda a, b: f"{a}/{b} = {a/b:.2%}" if b else "-"
    report_lines = [
        "# Policy Eval Report",
        "",
        f"Cases: {total}",
        "",
        "| Metric | Result |",
        "|--------|--------|",
        f"| ACL violations | {acl_violations} |",
        f"| Triage (category) | {pct(triage_correct, total)} |",
        f"| Triage (priority) | {pct(priority_correct, total)} |",
        f"| Approval gate correct | {pct(approval_gate_correct, total)} |",
        "",
        f"Output: `{OUT_CSV}`",
        "",
    ]
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print("=== Policy Eval Summary ===")
    print(f"cases: {total}")
    print(f"ACL violations: {acl_violations}")
    if total:
        print(f"triage_accuracy(category): {triage_correct}/{total} = {triage_correct/total:.2%}")
        print(f"triage_accuracy(priority): {priority_correct}/{total} = {priority_correct/total:.2%}")
        print(f"approval_gate_correctness: {approval_gate_correct}/{total} = {approval_gate_correct/total:.2%}")
    print(f"wrote: {OUT_CSV}")
    print(f"wrote: {OUT_MD}")


if __name__ == "__main__":
    main()
