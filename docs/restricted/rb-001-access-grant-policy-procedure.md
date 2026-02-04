# Runbook: Access Grant Policy & Procedure (IAM Group/Role Changes; Least Privilege; Approvals; Break-Glass)

## Summary (TL;DR)
**What this fixes:** Controlled, auditable access grants for IAM groups/roles with least privilege, approval gates, and break-glass exceptions.  
**Best next action:** Verify identity → confirm least-privilege scope → obtain required approvals → grant access → verify → audit log → monitor.  
**If you only have 2 minutes:** Verify requester identity → confirm resource classification → check approval status → if missing approvals, pause and escalate.

---

## Purpose
Enforce least-privilege access grants through a controlled, auditable process that requires approvals, validates business justification, and supports break-glass exceptions with post-action review.

**Use this runbook when:**
- [ ] Standard access request requires IAM group/role assignment
- [ ] Break-glass access is needed for incident response (with post-action approval)
- [ ] Role changes are required due to job function changes

**Do NOT use this runbook when:**
- [ ] The request lacks business justification or approver identification
- [ ] The requester identity cannot be verified
- [ ] The request appears suspicious or inconsistent with job role

---

## Scope
- **Systems covered:** IAM/IdP directory, group/role management, access request portal, audit logging.
- **Scenarios included:** Standard access grants, time-bounded access, break-glass exceptions, role changes.
- **Scenarios excluded:** Bulk access changes (requires change management), service account provisioning (separate process).

---

## Access & Data Classification (for ACL + governance)
- **Readable by (who may cite):** Employee / Engineer / IT Admin  
- **Executable by (who may perform steps):** Helpdesk (read-only) + Engineer / IT Admin (write/privileged)  
- **Note:** The ACL **permission tier** controls what content may be retrieved/cited. Execution permission is separate and enforced by tools/approvals.  
- **Permission tier:** restricted  
- **Sensitive data involved:** Yes (access controls, PII, privileged resource names, approval chains). Never log passwords, tokens, or full PII.  
- **Logging rule:** Never log secrets, tokens, passwords, or full PII. Redact before sharing.
- **Redaction notes (if any):** Mask user email (e.g., `a***@corp`), resource names for restricted programs, approval comments containing sensitive details.

---

## Intake Fields Needed (maps to ticket intake / issue template)
- **Ticket/Request ID:**  
- **Request type:** Access  
- **Urgency:** Low / Medium / High / Critical  
- **Requester identity:**  
- **Requester role (claimed):** Employee / Engineer / IT Admin  
- **Target system:** prod / staging / internal tooling (optional)  
- **Error message(s):** (if access denied)  
- **Time started (timestamp):**  
- **What changed recently?** (role change, new project, team transfer)  
- **What has been tried already?** (access request portal, manager approval)

Additionally required:
- **Resource/group/role requested:**  
- **Access level requested:** read / write / admin  
- **Business justification:**  
- **Approver(s):** manager / resource owner / data steward  
- **Duration:** permanent / time-bounded (end date)  
- **Break-glass justification (if applicable):**

---

## Preconditions / Prerequisites
- **Tools required:** IAM admin console, access request portal, audit logging system, ticketing system.
- **Credentials required:** IAM admin role (delegated access admin) for write actions; read-only for triage.
- **Network requirements:** VPN required? (Yes for admin consoles)
- **Dependencies healthy:** IAM/IdP operational; access request portal functional.

**Change window (if applicable):**
- Standard grants: business hours preferred; no change window required.
- Break-glass: immediate execution; post-action approval within 24 hours.

---

## Safety Notes (human-in-loop triggers)
**Stop and escalate if:**
- [ ] Requester identity cannot be verified
- [ ] Request appears suspicious or inconsistent with job role
- [ ] Approvals are missing or approver identity is unverified
- [ ] Break-glass request lacks incident ticket or security justification

**Approval required for:**
- [ ] Internal/read access: manager OR resource owner (at least one of)
- [ ] Restricted/read access: manager + resource owner
- [ ] Write/admin access (any tier): manager + resource owner + Security (or equivalent)
- [ ] Break-glass exceptions (post-action approval within 24 hours; Security review required)
- [ ] Time-bounded access extensions (re-approval required)

**Two-person rule:**
- [ ] Requester cannot self-approve; executor cannot be the approver; break-glass/admin grants require dual control.

**Audit requirements:**
- [ ] Log requester identity, approver identity, resource, access level, timestamp, business justification.
- [ ] Log break-glass actions with incident ticket reference and post-action approval timestamp.
- [ ] Retain audit logs per compliance policy (e.g., 1–7 years).

**Rollback/containment:**
- [ ] If access was granted incorrectly, revoke immediately and log revocation reason.
- [ ] If break-glass access is not approved post-action, revoke and notify Security.

---

## Steps

### Step 1: Identity verification and request validation
**Objective:** Confirm requester legitimacy and validate request completeness.  
**Risk level:** Medium  
**Action type:** Read-only / Write (Approval required? Yes)

1. Verify requester identity per support policy (SSO profile, ticket channel, callback if needed).
2. Validate request completeness:
   - resource/group/role clearly identified
   - access level specified (read/write/admin)
   - business justification provided
   - approver(s) identified
3. Check resource classification (public/internal/restricted) in metadata or registry.
4. Verify requester’s current access level and role consistency.

**Expected result:** Request is legitimate, complete, and properly scoped.  
**Verification (evidence to capture):**
- [ ] Requester identity verified (method recorded)
- [ ] Request contains all required fields
- [ ] Resource classification noted

**If this fails, go to:** Escalation

---

### Decision points (routing mini-rail)
- **If approvals are missing or approver identity unverified:** Pause and route to approver verification; do not grant.
- **If resource is `restricted`:** Require additional approvals (Security/program owner) and prefer time-bounded access.
- **If break-glass request:** Verify incident ticket reference; grant with post-action approval requirement; notify Security.
- **If request pattern is suspicious:** Escalate to Security (possible compromise).

---

### Step 2: Approval verification and least-privilege validation
**Objective:** Ensure required approvals are present and access level is least-privilege.  
**Risk level:** High  
**Action type:** Read-only / Write (Approval required? Yes)

1. Verify approver identity and authorization:
   - manager approval (for standard requests)
   - resource owner/data steward approval (for resource-specific access)
   - Security approval (for restricted resources or break-glass)
2. Confirm approval timestamps and explicit consent (not inferred).
3. Validate least-privilege:
   - requested access level matches business need
   - no broader role/group than necessary
   - time-bounded if appropriate

**Expected result:** All required approvals obtained and access level is least-privilege.  
**Verification (evidence to capture):**
- [ ] Approver identity verified
- [ ] Approval timestamps recorded
- [ ] Least-privilege validation noted

**If this fails, go to:** Escalation

---

### Step 3: Execute access grant (IAM group/role assignment)
**Objective:** Apply the approved access change with full audit trail.  
**Risk level:** High  
**Action type:** Write (Approval required? Yes)

1. In IAM admin console, locate the user account.
2. Add user to the specified group/role:
   - for time-bounded access, set expiration if supported
   - for break-glass, add temporary group with expiration
3. Verify the assignment completed successfully (check group membership).
4. Log the action:
   - requester identity (redacted)
   - approver identity (redacted)
   - resource/group/role granted
   - access level
   - timestamp
   - business justification (high-level)
   - break-glass incident ticket (if applicable)

**Expected result:** User membership updated and audit log entry created.  
**Verification (evidence to capture):**
- [ ] IAM audit event ID / change record ID
- [ ] Group membership confirmed in console

**If this fails, go to:** Troubleshooting / Escalation

---

### Step 4: Verify access and close ticket
**Objective:** Confirm access is effective and document completion.  
**Risk level:** Medium  
**Action type:** Read-only / Write (Approval required? No)

1. Ask user to retry access (new session) after propagation window.
2. Confirm access level achieved (read vs write).
3. Update ticket with:
   - group/role granted
   - approval references
   - time-bounded end date (if any)
   - audit event ID
4. For break-glass: set reminder for post-action approval within 24 hours.

**Expected result:** User can access the resource as approved; ticket closed with audit trail.  
**Verification (evidence to capture):**
- [ ] User confirmation + timestamp
- [ ] Audit event ID recorded in ticket

**If this fails, go to:** Troubleshooting

---

## Expected Citations (for RAG + evaluation)
- [ ] Section: “Safety Notes (human-in-loop triggers)”
- [ ] Section: “Step 2: Approval verification and least-privilege validation”
- [ ] Keyword anchors: “least privilege”, “approval”, “break-glass”, “audit log”

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
4. If still failing, verify group-to-permission mapping.

**If unresolved:** Escalate to IAM/App owner.

---

#### Issue: Break-glass access not approved post-action
**Symptoms:**
- Break-glass access was granted but post-action approval is denied or missing.

**Likely causes:**
- Incident resolved; approval not obtained; justification insufficient

**Resolution:**
1. Revoke break-glass access immediately.
2. Notify Security and document in audit log.
3. Route to standard access request process if access still needed.

**If unresolved:** Escalate to Security Operations.

---

### Diagnostics (copy/paste friendly)
**Redact:** full group names (for restricted programs), user identifiers, and any sensitive resource paths before pasting into tickets/logs.
```bash
# IAM console queries (read-only; redact output)
# - Check group membership
# - Verify effective permissions
# - Check audit logs (event IDs only)
```

---

## Escalation

## Severity guidance: P0 / P1 / P2
- **P0:** Widespread access control outage affecting many teams
- **P1:** Critical business deadline blocked; approvals present but access not effective
- **P2:** Standard access request

**Escalate immediately if:**
- Suspicious access request pattern (possible compromise)
- Break-glass access granted without incident ticket
- Access control system outage

## Escalation path:
**Level 1:** IT Access Administration queue — 30 min  
**Level 2:** Identity Engineering escalation — 30 min  
**On-call:** Security On-Call — (link redacted)

## Information to provide when escalating:
- Ticket/incident ID
- Requester identity (redacted) + resource
- Approval status and approver details
- IAM audit event IDs (redacted)
- Break-glass incident ticket (if applicable)

---

## Related Knowledge

## Related runbooks:
- `rb-002-security-incident-escalation.md`
- `rb-005-offboarding-access-revocation.md`

## Policies / docs:
- Access Control Policy — (internal link redacted)
- Least Privilege Standard — (internal link redacted)
- Break-Glass Access Procedure — (internal link redacted)

## Tools & dashboards:
- IAM admin console — (internal link redacted)
- Access audit logs — (internal link redacted)

## KB articles:
- “How to verify approver identity” — (internal link redacted)

---

## Owner & Review

**Primary owner:** Identity & Access Management (IAM)  
**Backup owner:** Security Operations (SECOPS)  
**Review cycle:** Quarterly  
**Last updated:** 2026-01-28  
**Updated by:** Copilot Scaffold Generator  
**Change summary:** Initial restricted access grant policy runbook creation.
