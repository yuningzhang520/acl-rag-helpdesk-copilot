# Runbook: Access Request — Shared Drive / Application Group (Approval-Gated)

## Summary (TL;DR)
**What this fixes:** Users unable to access a shared drive or internal app due to missing group membership.  
**Best next action:** Validate identity + business justification → confirm correct group → obtain approval → grant access → verify → document + audit.  
**If you only have 2 minutes:** Confirm requested resource + manager → route for approval (do not grant ad hoc).

---

## Purpose
Grant access to shared drives and internal applications in a controlled, auditable way aligned to least privilege.

**Use this runbook when:**
- [ ] User requests access to a shared drive (SMB/SharePoint/Drive)
- [ ] User requests access to an internal application protected by group membership

**Do NOT use this runbook when:**
- [ ] The requester cannot be verified
- [ ] The requested access is privileged/restricted without approvals (escalate)
- [ ] The request is urgent due to an incident requiring break-glass (use incident access process)

---

## Scope
- **Systems covered:** Directory groups (IdP/IAM), shared drive permissions, application access groups, ticketing.
- **Scenarios included:** Standard access request flows with approvals and verification.
- **Scenarios excluded:** Emergency break-glass access, production admin access (separate process).

---

## Access & Data Classification (for ACL + governance)
- **Readable by (who may cite):** Employee / Engineer / IT Admin  
- **Executable by (who may perform steps):** Helpdesk (intake/routing) + IT Admin (or delegated access admin) (write/privileged)  
- **Note:** The ACL **permission tier** controls what content may be retrieved/cited. Execution permission is separate and enforced by tools/approvals.  
- **Permission tier:** restricted  
- **Sensitive data involved:** Yes (PII, access controls, potentially restricted resource names)  
- **Logging rule:** Never log secrets, tokens, passwords, or full PII. Redact before sharing.
- **Redaction notes (if any):** Avoid listing sensitive group names for restricted programs in public channels.

---

## Intake Fields Needed (maps to ticket intake / issue template)
- **Ticket/Request ID:**  
- **Request type:** Access  
- **Urgency:** Low / Medium / High / Critical  
- **Requester identity:**  
- **Requester role (claimed):** Employee / Engineer / IT Admin  
- **Environment:** internal  
- **Time started (timestamp):**  
- **What changed recently?** (new team, new project, role change)  
- **What has been tried already?** (access request portal, manager ping)

Additionally required:
- **Resource requested:** (drive/app name + link/path)  
- **Access level requested:** read / write / admin  
- **Business justification:**  
- **Manager/owner approver:**  
- **Duration:** permanent / time-bounded (end date)

---

## Preconditions / Prerequisites
- **Tools required:** Access request portal (preferred), IdP/IAM admin, file/app permission admin, ticketing.
- **Credentials required:** Delegated access admin role.
- **Network requirements:** VPN required? (Yes for some admin consoles)
- **Dependencies healthy:** IAM/IdP operational.

---

## Safety Notes (human-in-loop triggers)
**Stop and escalate if:**
- [ ] The resource is marked restricted and approvals are missing
- [ ] The user requests broad access (“all drives”, “all apps”) without justification
- [ ] The request appears inconsistent with job role (possible compromise)

**Approval required for:**
- [ ] Any access grant (write/admin always requires approval)
- [ ] Any restricted tier resource
- [ ] Time-bounded access exceptions

---

## Steps

### Step 1: Validate request and route to the right approver
**Objective:** Ensure the correct owner approves the correct access level.  
**Risk level:** High  
**Action type:** Read-only / Write (Approval required? Yes)

1. Verify requester identity and employment status.
2. Identify the system of record for access:
   - preferred: access request portal
   - fallback: ticket workflow with explicit approval comment
3. Determine the correct approver:
   - resource owner / data steward
   - manager (as required by policy)
4. Confirm requested access level (read vs write vs admin).

**Expected result:** Request is properly scoped and routed for approval.  
**Verification (evidence to capture):**
- [ ] Approver identified + approval request created

**If this fails, go to:** Escalation

---

### Decision points (routing mini-rail)
- **If approvals are missing or approver is unknown:** Route to **resource owner / data steward** and pause (do not grant).
- **If resource is `restricted`:** Require **additional approvals** (e.g., Security/program owner) and prefer **time-bounded** access.
- **If request pattern is suspicious or inconsistent with role:** Escalate to **Security** (possible compromise).

---

### Step 2: Confirm resource classification and tier
**Objective:** Ensure access aligns with ACL tier policy.  
**Risk level:** High  
**Action type:** Read-only / Write (Approval required? Yes)

1. Check resource classification (public/internal/restricted) in metadata or registry.
2. If restricted:
   - require additional approvals (e.g., Security, program owner)
   - prefer time-bounded grants
3. Ensure group membership grant is least privilege (specific group, not broad role).

**Expected result:** Access plan meets policy for the resource tier.  
**Verification (evidence to capture):**
- [ ] Classification noted in ticket
- [ ] Any extra approvals noted (for restricted)

**If this fails, go to:** Escalation

---

### Step 3: Grant access (group membership) after approval
**Objective:** Apply the approved permission change.  
**Risk level:** High  
**Action type:** Write (Approval required? Yes)

1. Confirm approval is present (explicit in portal or ticket).
2. Add user to the correct group:
   - for time-bounded access, set expiration if supported
3. If using direct permissions (discouraged), follow change management and document rationale.

**Expected result:** User membership updated and effective.  
**Verification (evidence to capture):**
- [ ] IAM audit event ID / change record ID

**If this fails, go to:** Troubleshooting / Escalation

---

### Step 4: Verify access and close ticket
**Objective:** Confirm the user can access the resource and record completion.  
**Risk level:** Medium  
**Action type:** Read-only / Write (Approval required? No)

1. Ask user to retry access (new session).
2. Confirm access level achieved (read vs write).
3. Update ticket with:
   - group granted
   - approval reference
   - time-bounded end date (if any)

**Expected result:** User can access the resource as approved.  
**Verification (evidence to capture):**
- [ ] User confirmation + timestamp

**If this fails, go to:** Troubleshooting

---

## Expected Citations (for RAG + evaluation)
- [ ] Section: “Safety Notes (human-in-loop triggers)”
- [ ] Section: “Step 2: Confirm resource classification and tier”
- [ ] Keyword anchors: “least privilege”, “time-bounded”, “approver”

---

## Troubleshooting

### Common Issues

#### Issue: User still denied after group grant
**Symptoms:**
- Access denied persists after membership added.

**Likely causes:**
- Propagation delay, cached token, wrong group, nested group issues

**Resolution:**
1. Confirm membership in IAM and effective group evaluation.
2. Have user sign out/in (token refresh).
3. Wait propagation window (per system SLA) and retest.

**If unresolved:** Escalate to IAM/App owner.

---

#### Issue: Wrong access level (read-only vs write)
**Symptoms:**
- User can view but cannot edit/upload.

**Likely causes:**
- Incorrect group, resource-level permissions mismatch

**Resolution:**
1. Verify which group maps to which permission level.
2. Confirm owner approved write access explicitly.
3. Adjust group membership only with correct approval.

**If unresolved:** Escalate to resource owner.

---

### Diagnostics (copy/paste friendly)
**Redact:** full group names (for restricted programs), user identifiers, and any sensitive resource paths before pasting into tickets/logs.
```bash
# Provide only redacted evidence:
# - group membership (yes/no)
# - effective permissions (high-level)
# - propagation window start time
```

---

## Escalation

## Severity guidance: P0 / P1 / P2
- **P0:** Widespread access control outage affecting many teams
- **P1:** Critical business deadline blocked; approvals present
- **P2:** Standard access request

**Escalate immediately if:**
- Restricted resource requested without approvals
- Suspicious access request pattern (possible compromise)

## Escalation path:
**Level 1:** IT Access Administration — `#it-access` — 30 min  
**Level 2:** IAM/Identity Engineering — `#identity-ops` — 30 min  
**On-call:** Security On-Call — PagerDuty “SECOPS” — (link redacted)

## Information to provide when escalating:
- Ticket ID + requester (redacted)
- Resource + classification tier
- Approval references (who/when)
- IAM audit event IDs (redacted)

---

## Related Knowledge

## Related runbooks:
- `rb-003-employee-onboarding-checklist.md`

## Policies / docs:
- Access Control Policy — (restricted link redacted)
- Data Classification Standard — (internal link redacted)

## Tools & dashboards:
- Access request portal — (internal link redacted)
- IAM audit logs — (restricted link redacted)

## KB articles:
- “How to request shared drive access” — (internal link redacted)

---

## Owner & Review

**Primary owner:** IT Access Administration  
**Backup owner:** Identity Operations (IDOPS)  
**Review cycle:** Quarterly  
**Last updated:** 2026-01-28  
**Updated by:** Copilot Scaffold Generator  
**Change summary:** Initial access request runbook creation with approval gate and tier checks.

