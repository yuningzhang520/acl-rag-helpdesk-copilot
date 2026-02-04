# Runbook: Offboarding & Access Revocation (Termination; Device Return; Account Disable; Data Retention; Audit)

## Summary (TL;DR)
**What this fixes:** Complete, auditable offboarding process that revokes all access, secures devices, preserves data per retention policy, and maintains full audit trail.  
**Best next action:** Verify termination → revoke all access → secure/return devices → preserve data per retention → disable accounts → audit log → close ticket.  
**If you only have 2 minutes:** Verify termination authorization → revoke active sessions → disable account → mark device for return → escalate to Security for access audit.

---

## Purpose
Provide a controlled, auditable offboarding process that ensures complete access revocation, device security, data retention compliance, and full auditability for terminated employees, contractors, and role changes.

**Use this runbook when:**
- [ ] Employee termination (voluntary or involuntary)
- [ ] Contractor end date reached or terminated
- [ ] Role change requiring access revocation (lateral move, demotion)
- [ ] Long-term leave requiring access suspension

**Do NOT use this runbook when:**
- [ ] Temporary access suspension (use access revocation only, not full offboarding)
- [ ] Account compromise (use security incident runbook)
- [ ] Identity cannot be verified (escalate to Security)

---

## Scope
- **Systems covered:** IAM/IdP, endpoint management/MDM, email, access control systems, data retention systems, audit logging.
- **Scenarios included:** Termination offboarding, contractor offboarding, role-change access revocation, long-term leave suspension.
- **Scenarios excluded:** Temporary access suspension, account compromise (separate process), bulk offboarding (change management).

---

## Access & Data Classification (for ACL + governance)
- **Readable by (who may cite):** Employee / Engineer / IT Admin  
- **Executable by (who may perform steps):** Helpdesk (read-only) + Engineer / IT Admin (write/privileged)  
- **Note:** The ACL **permission tier** controls what content may be retrieved/cited. Execution permission is separate and enforced by tools/approvals.  
- **Permission tier:** restricted  
- **Sensitive data involved:** Yes (PII, termination details, access history, device identifiers). Never log passwords, tokens, or full PII.  
- **Logging rule:** Never log secrets, tokens, passwords, or full PII. Redact before sharing.
- **Redaction notes (if any):** Mask user email (e.g., `a***@corp`), device serials, termination details, and any HR-sensitive information.

---

## Intake Fields Needed (maps to ticket intake / issue template)
- **Ticket/Request ID:**  
- **Request type:** Onboarding / Other  
- **Urgency:** Low / Medium / High / Critical  
- **Requester identity:** (HR/Manager)  
- **Requester role (claimed):** Employee / Engineer / IT Admin  
- **Environment:** N/A (offboarding)  
- **Error message(s):** (if applicable)  
- **Time started (timestamp):**  
- **What changed recently?** (termination date, role change, contractor end date)  
- **What has been tried already?** (HR notification, manager confirmation)

Additionally required:
- **Offboarding type:** termination / contractor end / role change / long-term leave  
- **Effective date/time:**  
- **Termination reason (if applicable):** (voluntary / involuntary / other — high-level only)  
- **Manager/HR approver:**  
- **Data retention requirements:** (per policy / legal hold / standard retention)

---

## Preconditions / Prerequisites
- **Tools required:** IAM admin console, endpoint management/MDM, email admin, access audit system, data retention system, ticketing system.
- **Credentials required:** Offboarding operator role (privileged) for revocation actions; read-only for triage.
- **Network requirements:** VPN required? (Yes for admin consoles)
- **Dependencies healthy:** IAM/IdP operational; endpoint management accessible; HR system synchronized.

**Change window (if applicable):**
- Standard offboarding: execute on effective date/time; no change window required.
- Emergency termination: immediate execution; coordinate with Security.

---

## Safety Notes (human-in-loop triggers)
**Stop and escalate if:**
- [ ] Termination authorization cannot be verified (HR/manager confirmation missing)
- [ ] Offboarding involves executive/VIP (additional approvals required)
- [ ] Legal hold is indicated (involve Legal; do not delete data)
- [ ] Device cannot be located or secured (escalate to Security)

**Approval required for:**
- [ ] Any offboarding action (HR + manager approval)
- [ ] Data deletion (Legal approval if legal hold; otherwise per retention policy)
- [ ] Executive/VIP offboarding (additional Security + Legal approval)
- [ ] Emergency termination (Security approval)

**Two-person rule:**
- [ ] Requester cannot self-approve; executor cannot be the approver; offboarding actions require dual control.

**Audit requirements:**
- [ ] Log all access revocations: account identifier (redacted), access types revoked, revocation timestamp, operator identity.
- [ ] Log device actions: device identifier (redacted), action (returned/wipe/retired), timestamp, operator identity.
- [ ] Log data retention actions: data types preserved, retention period, legal hold status (if applicable).
- [ ] Log account disable: account identifier (redacted), disable timestamp, operator identity, reason (high-level).
- [ ] Retain audit logs per compliance policy (e.g., 1–7 years).

**Rollback/containment:**
- [ ] If offboarding was performed incorrectly, restore access immediately and escalate to Security.
- [ ] If data was deleted incorrectly, attempt recovery from backups; escalate to Legal if legal hold was violated.

---

## Steps

### Step 1: Verify termination authorization and gather offboarding details
**Objective:** Confirm offboarding is authorized and collect complete information.  
**Risk level:** Medium  
**Action type:** Read-only / Write (Approval required? Yes)

1. Verify termination authorization:
   - HR confirmation (via HR system or approved channel)
   - manager confirmation (via internal directory)
   - effective date/time confirmed
2. Gather offboarding details:
   - offboarding type (termination/contractor/role change/leave)
   - current access inventory (groups, roles, applications)
   - device inventory (laptop, phone, other)
   - data retention requirements (per policy, legal hold)
3. Check for special circumstances:
   - executive/VIP (additional approvals)
   - legal hold (involve Legal)
   - security concerns (involve Security)

**Expected result:** Offboarding authorized and details collected.  
**Verification (evidence to capture):**
- [ ] HR/manager authorization verified
- [ ] Access inventory documented
- [ ] Device inventory documented
- [ ] Data retention requirements noted

**If this fails, go to:** Escalation

---

### Decision points (routing mini-rail)
- **If authorization cannot be verified:** Pause and escalate to HR/manager; do not proceed.
- **If executive/VIP:** Require additional Security + Legal approval; proceed with extra caution.
- **If legal hold indicated:** Involve Legal; preserve all data; do not delete.
- **If security concerns:** Involve Security immediately; coordinate containment.

---

### Step 2: Revoke all access (sessions, groups, roles, applications)
**Objective:** Immediately revoke all active access to prevent unauthorized use.  
**Risk level:** High  
**Action type:** Write (Approval required? Yes)

1. Revoke active sessions:
   - IdP session revocation (all devices)
   - VPN session termination
   - application session invalidation
2. Remove from all groups/roles:
   - IAM group removal (all groups)
   - role removal (all roles)
   - application access removal
3. Revoke API tokens and service credentials:
   - API token revocation
   - service account access removal
   - integration credential revocation
4. Log all revocations:
   - account identifier (redacted)
   - access types revoked
   - revocation timestamp
   - operator identity

**Expected result:** All access revoked; audit log entries created.  
**Verification (evidence to capture):**
- [ ] Session revocation confirmed
- [ ] Group/role removal confirmed
- [ ] API token revocation confirmed
- [ ] Revocation actions logged

**If this fails, go to:** Escalation (Security)

---

### Step 3: Secure and return devices
**Objective:** Secure devices, wipe if necessary, and coordinate return.  
**Risk level:** High  
**Action type:** Write (Approval required? Yes)

1. Locate and secure devices:
   - laptop (corporate-issued)
   - phone (corporate-issued)
   - other devices (per inventory)
2. If device is returned:
   - verify device identifier
   - perform secure wipe per endpoint policy
   - mark device as returned in inventory
3. If device is not returned:
   - mark device as lost/stolen in MDM
   - issue remote wipe command (if policy permits)
   - escalate to Security if device contains sensitive data
4. Log device actions:
   - device identifier (redacted)
   - action (returned/wipe/retired/lost)
   - timestamp
   - operator identity

**Expected result:** Devices secured and returned or wiped; inventory updated.  
**Verification (evidence to capture):**
- [ ] Device actions logged
- [ ] Inventory updated
- [ ] Wipe confirmed (if applicable)

**If this fails, go to:** Escalation (Security + Endpoint)

---

### Step 4: Preserve data per retention policy and disable account
**Objective:** Ensure data is preserved per retention policy and account is disabled.  
**Risk level:** High  
**Action type:** Write (Approval required? Yes)

1. Preserve data per retention policy:
   - email (per retention policy, typically 90 days)
   - files/data (per retention policy)
   - audit logs (per compliance policy)
   - legal hold data (if applicable; preserve indefinitely)
2. Disable account in IdP:
   - set account to disabled state
   - preserve account for retention period (do not delete immediately)
   - set account deletion date (per retention policy)
3. Update email (if applicable):
   - set out-of-office message (if policy requires)
   - forward to manager/delegate (if policy requires)
   - preserve mailbox per retention policy
4. Log data retention and account disable:
   - data types preserved
   - retention period
   - legal hold status (if applicable)
   - account disable timestamp
   - account deletion date (scheduled)

**Expected result:** Data preserved per policy; account disabled; retention scheduled.  
**Verification (evidence to capture):**
- [ ] Data preservation confirmed
- [ ] Account disabled confirmed
- [ ] Retention actions logged

**If this fails, go to:** Escalation (Legal + Security)

---

### Step 5: Final audit and ticket closure
**Objective:** Complete audit verification and close ticket with full audit trail.  
**Risk level:** Medium  
**Action type:** Read-only / Write (Approval required? No)

1. Verify all offboarding actions completed:
   - access revoked (all groups/roles/applications)
   - devices secured/returned
   - data preserved per policy
   - account disabled
2. Generate offboarding audit report:
   - access revocations (summary)
   - device actions (summary)
   - data retention status
   - account disable status
   - audit event IDs
3. Update ticket with:
   - offboarding completion timestamp
   - audit report reference
   - any follow-ups (device return, data deletion schedule)
4. Close ticket.

**Expected result:** Offboarding complete; audit report generated; ticket closed.  
**Verification (evidence to capture):**
- [ ] Audit report generated
- [ ] Ticket closed with audit trail

**If this fails, go to:** Escalation

---

## Expected Citations (for RAG + evaluation)
- [ ] Section: “Safety Notes (human-in-loop triggers)”
- [ ] Section: “Step 2: Revoke all access (sessions, groups, roles, applications)”
- [ ] Keyword anchors: “access revocation”, “data retention”, “audit log”

---

## Troubleshooting

### Common Issues

#### Issue: Access revocation incomplete (some groups/roles remain)
**Symptoms:**
- User still has access to some systems after offboarding.

**Likely causes:**
- Nested groups, propagation delay, manual access grants not documented

**Resolution:**
1. Perform comprehensive access audit (all systems).
2. Revoke any remaining access manually.
3. Verify effective access (test if possible, or query all systems).
4. Document any access that could not be revoked and escalate.

**If unresolved:** Escalate to Security + IAM for comprehensive access audit.

---

#### Issue: Device cannot be located or returned
**Symptoms:**
- Device is not returned and remote wipe cannot be confirmed.

**Likely causes:**
- Device offline, MDM agent disabled, device lost/stolen

**Resolution:**
1. Mark device as lost/stolen in MDM.
2. Issue remote wipe command (if policy permits).
3. If device contains sensitive data, escalate to Security.
4. Document device status in offboarding ticket.

**If unresolved:** Escalate to Security + Endpoint Management.

---

### Diagnostics (copy/paste friendly)
**Redact:** account identifiers, device serials, termination details, and any HR-sensitive information before pasting into tickets/logs.
```bash
# Read-only diagnostic commands (redact output)
# - Check account status (enabled/disabled)
# - Verify group/role membership (summary only)
# - Query audit logs (event IDs only)
```

---

## Escalation

## Severity guidance: P0 / P1 / P2
- **P0:** Emergency termination with security concerns or device compromise risk
- **P1:** Offboarding incomplete (access or device not secured)
- **P2:** Standard offboarding

**Escalate immediately if:**
- Emergency termination with security concerns
- Access revocation incomplete
- Device cannot be secured
- Legal hold violated

## Escalation path:
**Level 1:** IT Operations queue — 30 min  
**Level 2:** Security Operations escalation — 15 min  
**On-call:** Security On-Call — (link redacted)

## Information to provide when escalating:
- Ticket/incident ID
- Offboarding type and effective date
- Access revocation status (complete/incomplete)
- Device status (returned/lost/wipe pending)
- Data retention status
- Audit event IDs (redacted)

---

## Related Knowledge

## Related runbooks:
- `rb-001-access-grant-policy-procedure.md`
- `rb-002-security-incident-escalation.md`

## Policies / docs:
- Offboarding Policy — (internal link redacted)
- Data Retention Policy — (internal link redacted)
- Device Return Procedure — (internal link redacted)

## Tools & dashboards:
- IAM admin console — (internal link redacted)
- Endpoint management — (internal link redacted)
- Access audit system — (internal link redacted)

## KB articles:
- “Complete access revocation checklist” — (internal link redacted)

---

## Owner & Review

**Primary owner:** IT Operations  
**Backup owner:** Security Operations (SECOPS)  
**Review cycle:** Quarterly  
**Last updated:** 2026-01-28  
**Updated by:** Copilot Scaffold Generator  
**Change summary:** Initial restricted offboarding and access revocation runbook creation.
