# Approval Gate for GitHub Write-Back

This document describes the **risk-based approval gate** and **allowlisted GitHub write-back** used when running the pipeline with `--mode github`.

The intent is enterprise-safe behavior:
- **Propose ≠ Execute** (safe-by-default)
- **Risk-based approval** (least privilege)
- **Allowlisted mutations only**
- **Auditability** (append-only logs)

---

## Propose vs Execute

### Propose (always)
The system **always** posts a **Proposed Plan (PENDING APPROVAL)** comment on the GitHub issue. This comment includes:
- `triage` (with `method="keyword"`)
- `retrieval_confidence` (retrieval match strength indicator)
- `answer` with citations (doc + section anchor)
- `proposed_actions_struct` (risk level, required approver role, labels/assignees, summary)

**Important:** Posting the proposed plan comment is the only write-back that may occur **before** approval.

### Execute (only after valid approval)
Allowlisted actions (adding labels, adding assignees) are executed **only** after:
1) a valid **APPROVE** comment is found, and  
2) the commenter’s role satisfies the required approval role for the case’s risk level, and  
3) the approval comment is **newer** than the most recent Proposed Plan comment.

If any check fails, **no execution occurs**.

---

## Risk Levels and Approval Roles

Risk level is an **action risk** concept (not ticket severity). It determines **who can approve execution**.

### L2 — Privileged / Sensitive intent (Admin approval required)
**Triggered when:**
- `triage.category == "Access"`, **or**
- (`triage.priority` is `"High"` or `"Critical"` **and** `proposed_actions_struct` contains write-back actions beyond the proposed-plan comment)

**Approval role:** **IT Admin** only.

**Notes:**
- Engineer approval is **not sufficient** for L2.
- In this demo, L2 does not require actually granting access in external systems; it only changes the approval requirements for write-back actions.

### L1 — Low-risk operational write-back (Agent approval sufficient)
**Triggered when:**
- Write-back actions are planned (labels/assignees), and the case is **not** L2.

**Approval role:** **Engineer** or **IT Admin**.

### No executable write-back actions
If `proposed_actions_struct` contains **no** write-back actions (no labels/assignees), execution is skipped regardless of approval. The system only posts the Proposed Plan comment.

---

## Approval Keyword

### Keyword
The system looks for an issue comment whose body, when **trimmed** and compared **case-insensitively**, equals:

- **`APPROVE`**

Only the **latest** such comment is considered, subject to the timing constraint below.

### Timing constraint (prevents stale approvals)
To avoid reusing stale approvals:
- Only consider `APPROVE` comments **posted after** the most recent **Proposed Plan (PENDING APPROVAL)** comment.

### Approver validation (directory-backed)
The approval comment author’s GitHub `login` is resolved against `workflows/directory.csv` via the `github_username` column to determine their role.

- If the commenter is **not present** in the directory:
  - approval is treated as invalid (`approval_status="rejected_unverified"`)
  - no execution occurs

Employee approvals are **never** valid.

---

## Execution Rules

### Valid approval matrix
| Risk level | Required role | Valid approvers |
|-----------|----------------|-----------------|
| L1        | Engineer       | Engineer, IT Admin |
| L2        | IT Admin       | IT Admin only |

### Invalid approval behavior
If an `APPROVE` comment exists but is not valid (wrong role or unverified):
- `approval_status = "rejected"` (or `"rejected_unverified"`)
- **no write-back actions are executed**
- The system may optionally post a comment such as:
  - `Approval rejected: L2 actions require IT Admin approval.`
  - `Approval rejected: approver is not in directory (unverified).`

---

## Allowlisted Actions

Only the following operations are performed as write-back (and only after valid approval):

1) **Post comment**
   - Post the **Proposed Plan (PENDING APPROVAL)** comment (always).
   - After valid approval and execution, post an **Executed actions** comment summarizing what was done.

2) **Add labels**
   - Add the suggested `labels_to_add` from `proposed_actions_struct`.
   - This is treated as **idempotent** (duplicates ignored by GitHub).

3) **Add assignees**
   - Add the suggested `assignees` from `proposed_actions_struct`.

**Explicitly NOT allowed:**
- closing issues
- editing issue title/body
- deleting comments
- modifying milestones/projects
- any repo-level mutations

This allowlist is intentional to keep the demo safe-by-default and enterprise-aligned.

---

## Proposed Actions Structure

When `--mode github` is enabled, the pipeline produces a structured action proposal:

```json
{
  "risk_level": "L1",
  "approval_role_required": "Engineer",
  "labels_to_add": ["cat:VPN", "prio:Medium", "status:pending-approval"],
  "assignees": [],
  "comment_summary": "Triaged as VPN issue; recommend following VPN runbook steps and collecting client logs if unresolved."
}