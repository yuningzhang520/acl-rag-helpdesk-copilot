#!/usr/bin/env python3
"""
Retrieval evaluation: compares keyword / vector / hybrid retrievers.

What it measures:
  - Recall@3: whether any of the top-3 citations match expected docs (must_cite).
  - MRR@3: mean reciprocal rank of first expected doc in top-3.
  - ACL pass: no restricted-tier citations when must_not_cite contains "restricted".

When to use: Run after changing retrieval logic or adding runbooks to compare
retriever quality. Reads golden_set/golden_set.jsonl (must_cite, must_not_cite).
Outputs: workflows/eval_retrieval_results.csv, workflows/eval_retrieval_report.md.
"""

import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_PATH = REPO_ROOT / "golden_set" / "golden_set.jsonl"
OUT_CSV = REPO_ROOT / "workflows" / "eval_retrieval_results.csv"
OUT_MD = REPO_ROOT / "workflows" / "eval_retrieval_report.md"
CANDIDATE_K = 30


def run_pipeline(user_id: str, issue_text: str, retriever: str = "keyword", top_k: int = 3) -> Dict[str, Any]:
    """Run pipeline with given retriever; return parsed JSON."""
    cmd = [
        sys.executable, "-m", "src.run",
        "--mode", "cli",
        "--user_id", user_id,
        "--issue", issue_text,
        "--retriever", retriever,
        "--top_k", str(top_k),
    ]
    if retriever in ("vector", "hybrid"):
        cmd.extend(["--candidate_k", str(CANDIDATE_K)])
    p = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"run failed (retriever={retriever}): {p.stderr}\n{p.stdout}")
    return json.loads(p.stdout)

def doc_path_to_filename(doc: str) -> str:
    """Normalize doc path to filename for matching."""
    doc = (doc or "").replace("\\", "/")
    return doc.split("/")[-1] if doc else ""

def recall_at_k(citations: List[Dict], expected_docs: List[str], k: int = 3) -> float:
    """1.0 if any of top-k citations matches any expected_doc (by filename)."""
    if not expected_docs:
        return 0.0
    top = (citations or [])[:k]
    filenames = {doc_path_to_filename(c.get("doc") or "") for c in top}
    for exp in expected_docs:
        exp_name = Path(exp).name if exp else ""
        if exp_name and exp_name in filenames:
            return 1.0
    return 0.0


def mrr_at_k(citations: List[Dict], expected_docs: List[str], k: int = 3) -> float:
    """1/rank of first match (1-indexed), 0 if no match."""
    if not expected_docs:
        return 0.0
    top = (citations or [])[:k]
    exp_names = {Path(exp).name for exp in expected_docs if exp}
    for rank, c in enumerate(top, 1):
        fn = doc_path_to_filename(c.get("doc") or "")
        if fn in exp_names:
            return 1.0 / rank
    return 0.0


def acl_pass(citations: List[Dict], must_not_cite: List[str]) -> bool:
    """True if no citation has tier restricted when must_not_cite contains 'restricted'."""
    if "restricted" not in (must_not_cite or []):
        return True
    for c in citations or []:
        if c.get("tier") == "restricted":
            return False
        doc = (c.get("doc") or "").replace("\\", "/")
        if "/restricted/" in doc:
            return False
    return True


def top_docs_str(citations: List[Dict], k: int = 3) -> str:
    """Comma-separated filenames of top-k citations."""
    top = (citations or [])[:k]
    return ",".join(doc_path_to_filename(c.get("doc") or "") for c in top)


def main() -> None:
    if not GOLDEN_PATH.exists():
        raise FileNotFoundError(f"Golden set not found: {GOLDEN_PATH}")
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    cases = []
    with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cases.append(json.loads(line))

    rows: List[Dict[str, Any]] = []
    retrievers = ["keyword", "vector", "hybrid"]
    for gs in cases:
        case_id = gs.get("id", "")
        user_id = gs.get("user_id", "")
        issue = gs.get("issue_text", "")
        expected_doc_list = gs.get("must_cite") or []
        must_not_cite = gs.get("must_not_cite") or []
        for retriever in retrievers:
            has_expected_docs = len(expected_doc_list) > 0
            skipped_in_avg = not has_expected_docs
            try:
                out = run_pipeline(user_id, issue, retriever=retriever, top_k=3)
            except Exception as e:
                rows.append({
                    "case_id": case_id,
                    "retriever": retriever,
                    "recall_at_3": 0.0,
                    "mrr_at_3": 0.0,
                    "acl_pass": False,
                    "top_docs": "",
                    "has_expected_docs": has_expected_docs,
                    "skipped_in_avg": skipped_in_avg,
                    "error": str(e),
                })
                continue
            citations = out.get("citations") or []
            rec = recall_at_k(citations, expected_doc_list, k=3)
            mrr = mrr_at_k(citations, expected_doc_list, k=3)
            acl_ok = acl_pass(citations, must_not_cite)
            rows.append({
                "case_id": case_id,
                "retriever": retriever,
                "recall_at_3": rec,
                "mrr_at_3": mrr,
                "acl_pass": acl_ok,
                "top_docs": top_docs_str(citations, 3),
                "has_expected_docs": has_expected_docs,
                "skipped_in_avg": skipped_in_avg,
            })

    fieldnames = ["case_id", "retriever", "recall_at_3", "mrr_at_3", "acl_pass", "top_docs", "has_expected_docs", "skipped_in_avg"]
    if any("error" in r for r in rows):
        fieldnames.append("error")
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    n_cases = len(cases)
    n_with_expected_docs = sum(1 for gs in cases if (gs.get("must_cite") or []))
    report_lines = [
        "# Retrieval Eval Report",
        "",
        f"N_total cases: {n_cases} | N_with_expected_docs: {n_with_expected_docs} | Retrievers: keyword, vector, hybrid",
        "",
        "## Averages (per retriever)",
        "",
        "Recall@3 and MRR@3 are computed only over rows where has_expected_docs=true and no error. ACL pass % is over all non-error rows.",
        "",
        "| Retriever | N_used_for_recall_mrr | Recall@3 | MRR@3 | ACL pass % |",
        "|-----------|------------------------|----------|-------|------------|",
    ]
    for ret in retrievers:
        non_error = [r for r in rows if r.get("retriever") == ret and "error" not in r]
        used_for_recall_mrr = [r for r in non_error if r.get("has_expected_docs")]
        n_used = len(used_for_recall_mrr)
        if not non_error:
            report_lines.append(f"| {ret} | 0 | - | - | - |")
            continue
        acl_pct = 100.0 * sum(1 for r in non_error if r["acl_pass"]) / len(non_error)
        if n_used == 0:
            report_lines.append(f"| {ret} | 0 | - | - | {acl_pct:.1f}% |")
            continue
        rec_avg = sum(r["recall_at_3"] for r in used_for_recall_mrr) / n_used
        mrr_avg = sum(r["mrr_at_3"] for r in used_for_recall_mrr) / n_used
        report_lines.append(f"| {ret} | {n_used} | {rec_avg:.3f} | {mrr_avg:.3f} | {acl_pct:.1f}% |")
    report_lines.extend(["", "## Output", "", f"- `{OUT_CSV}`", ""])
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"Wrote {OUT_CSV}")
    print(f"Wrote {OUT_MD}")
    for ret in retrievers:
        non_error = [r for r in rows if r.get("retriever") == ret and "error" not in r]
        used = [r for r in non_error if r.get("has_expected_docs")]
        if non_error:
            acl_pct = 100.0 * sum(1 for r in non_error if r["acl_pass"]) / len(non_error)
            if used:
                rec_avg = sum(r["recall_at_3"] for r in used) / len(used)
                mrr_avg = sum(r["mrr_at_3"] for r in used) / len(used)
                print(f"  {ret}: N_used={len(used)} Recall@3={rec_avg:.3f} MRR@3={mrr_avg:.3f} ACL_pass={acl_pct:.1f}%")
            else:
                print(f"  {ret}: N_used=0 Recall@3=- MRR@3=- ACL_pass={acl_pct:.1f}%")


if __name__ == "__main__":
    main()
