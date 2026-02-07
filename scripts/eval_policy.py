#!/usr/bin/env python3
"""
Policy / system correctness evaluation: ACL, citations, triage, approval gate.

What it measures:
  - ACL: no restricted-tier citations when must_not_cite contains "restricted".
  - Citation: at least one citation matches must_cite (doc name substrings) when set.
  - Triage: category and priority match expected_category, expected_priority.
  - Approval gate: proposed_actions_struct matches expected_approval (e.g. L2_requires_IT_Admin or n/a).

When to use: Run after changing triage keywords, ACL, or approval rules to check
system correctness. Reads golden_set/golden_set.jsonl (expected_category,
expected_priority, expected_approval, must_cite, must_not_cite).
Outputs: workflows/eval_policy_results.csv, workflows/eval_policy_report.md.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.eval import main

if __name__ == "__main__":
    main()
