# Runbook: Admin-only Account Reset Procedure (No Bypass; Identity Proof; Temporary Credentials; Forced Rotation)

## Summary (TL;DR)
**What this fixes:** Admin/privileged account resets requiring strict identity verification, no security bypasses, temporary credentials, and forced credential rotation.  
**Best next action:** Verify identity (multi-factor) → confirm account type → obtain approvals → reset with temporary credentials → force rotation → audit log.  
**If you only have 2 minutes:** Verify identity via approved methods → confirm privileged account type → if approvals missing, pause and escalate.

---

## Purpose
Provide a controlled, auditable procedure for resetting admin/privileged accounts that enforces identity verification, requires approvals, uses temporary credentials, and forces immediate rotation.

**Use this runbook when:**
- [ ] Admin/privileged account password reset is required
- [ ] Admin account is locked and needs unlock with credential reset
- [ ] Privileged account MFA reset is needed (with identity verification)

**Do NOT use this runbook when:**
- [ ] Standard user account reset (use standard MFA reset runbook)
- [ ] Service account reset (separate process)
- [ ] Identity cannot be verified (escalate to Security)

---

## Scope
- **Systems covered:** IdP admin console, privileged access management (PAM), audit logging, temporary credential system.
- **Scenarios included:** Admin account password reset, privileged account unlock, admin MFA reset.
- **Scenarios excluded:** Service account provisioning, bulk admin resets (change management), permanent credential bypass (not permitted).

---

## Access & Data Classification (for ACL + governance)
- **Readable by (who may cite):** Employee / Engineer / IT Admin  
- **Executable by (who may perform steps):** Helpdesk (read-only) + Engineer / IT Admin (write/privileged)  
- **Note:** The ACL **permission tier** controls what content may be retrieved/cited. Execution permission is separate and enforced by tools/approvals.  
- **Permission tier:** restricted  
- **Sensitive data involved:** Yes (privileged account identities, temporary credentials, PII). Never log passwords, temporary credentials, or full PII.  
- **Logging rule:** Never log secrets, tokens, passwords, or full PII. Redact before sharing.
- **Redaction notes (if any):** Mask admin account identifiers (e.g., `admin-***`), temporary credential references, and any privileged system details.

---

## Intake Fields Needed (maps to ticket intake / issue template)
- **Ticket/Request ID:**  
- **Request type:** MFA / Other  
- **Urgency:** Low / Medium / High / Critical  
- **Requester identity:**  
- **Requester role (claimed):** IT Admin  
- **Environment:** N/A (admin account reset)  
- **Error message(s):** (if applicable)  
- **Time started (timestamp):**  
- **What changed recently?** (password change, MFA device change, account lockout)  
- **What has been tried already?** (standard reset flow, backup MFA)

Additionally required:
- **Admin account identifier:** (redacted format)  
- **Account type:** IT Admin / Security Admin / System Admin / Other privileged  
- **Reset reason:** password forgotten / account locked / MFA device lost  
- **Manager/Security approver:**  
- **Incident ticket (if security-related):**

---

## Preconditions / Prerequisites
- **Tools required:** IdP admin console, PAM system (if applicable), temporary credential generator, audit logging system, ticketing system.
- **Credentials required:** Identity admin role (privileged) for reset actions; read-only for triage.
- **Network requirements:** VPN required? (Yes for admin consoles)
- **Dependencies healthy:** IdP operational; PAM system accessible (if applicable).

**Change window (if applicable):**
- Standard reset: business hours preferred; no change window required.
- Emergency reset: immediate execution; post-action approval within 24 hours.

---

## Safety Notes (human-in-loop triggers)
**Stop and escalate if:**
- [ ] Requester identity cannot be verified via approved methods
- [ ] Approvals are missing (manager + Security for privileged accounts)
- [ ] Account shows signs of compromise (unusual activity, suspicious lockouts)
- [ ] Request comes from unverified channel

**Approval required for:**
- [ ] Any admin account reset (manager + Security approval)
- [ ] Any privileged account unlock (Security approval)
- [ ] Temporary credential issuance (Security approval)
- [ ] Emergency reset (post-action approval within 24 hours)

**Two-person rule:**
- [ ] Requester cannot self-approve; executor cannot be the approver; admin resets require dual control.

**Audit requirements:**
- [ ] Log requester identity, approver identities, account identifier (redacted), reset reason, timestamp, temporary credential issuance (reference only, not value).
- [ ] Log forced rotation requirement and rotation completion timestamp.
- [ ] Retain audit logs per compliance policy (e.g., 1–7 years).

**Rollback/containment:**
- [ ] If reset was performed incorrectly, revoke temporary credentials immediately.
- [ ] If account shows compromise indicators, lock account and escalate to Security.

---

## Steps

### Step 1: Identity verification and account type confirmation
**Objective:** Verify requester identity and confirm account is privileged/admin.  
**Risk level:** Medium  
**Action type:** Read-only / Write (Approval required? Yes)

1. Perform multi-factor identity verification:
   - manager confirmation via internal directory
   - verified callback to number on file
   - recent HR identifiers (per policy; do not collect SSN)
2. Confirm account type in IdP admin console:
   - IT Admin / Security Admin / System Admin / Other privileged
   - verify account has elevated permissions
3. Check account status and recent activity:
   - account enabled/disabled
   - recent sign-in patterns
   - any compromise indicators

**Expected result:** Identity verified and account type confirmed as privileged/admin.  
**Verification (evidence to capture):**
- [ ] Identity verification method(s) recorded (no sensitive IDs)
- [ ] Account type confirmed
- [ ] No compromise indicators observed

**If this fails, go to:** Escalation (Security)

---

### Decision points (routing mini-rail)
- **If identity cannot be verified:** Escalate to Security immediately; do not proceed.
- **If account shows compromise indicators:** Lock account → Escalate to Security (**P0**).
- **If approvals are missing:** Pause and route to approvers; do not reset.
- **If account is not privileged/admin:** Route to standard reset process.

---

### Step 2: Approval verification
**Objective:** Ensure required approvals are present before reset.  
**Risk level:** High  
**Action type:** Read-only / Write (Approval required? Yes)

1. Verify required approvals:
   - manager approval (for IT Admin accounts)
   - Security approval (required for all privileged accounts)
   - incident ticket reference (if security-related)
2. Confirm approval timestamps and explicit consent.
3. For emergency resets, document post-action approval requirement (within 24 hours).

**Expected result:** All required approvals obtained and documented.  
**Verification (evidence to capture):**
- [ ] Approver identities verified
- [ ] Approval timestamps recorded
- [ ] Post-action approval requirement noted (if emergency)

**If this fails, go to:** Escalation

---

### Step 3: Execute reset with temporary credentials
**Objective:** Reset admin account using temporary credentials that force immediate rotation.  
**Risk level:** High  
**Action type:** Write (Approval required? Yes)

1. Generate temporary credentials via approved system:
   - temporary password (strong, random, single-use)
   - or temporary MFA bypass token (time-bounded, single-use)
2. In IdP admin console, reset account:
   - set temporary password (if password reset)
   - reset MFA enrollment (if MFA reset)
   - force password change at next login
   - set temporary credential expiration (24 hours maximum)
3. Log reset action:
   - requester identity (redacted)
   - approver identities (redacted)
   - account identifier (redacted)
   - reset reason
   - temporary credential reference (not value)
   - timestamp
   - forced rotation requirement

**Expected result:** Account reset with temporary credentials; forced rotation enabled.  
**Verification (evidence to capture):**
- [ ] Admin console event ID / audit entry reference
- [ ] Temporary credential issued (reference only)
- [ ] Forced rotation flag set

**If this fails, go to:** Troubleshooting / Escalation (Identity)

---

### Step 4: Validate rotation and close ticket
**Objective:** Confirm user rotated credentials and document completion.  
**Risk level:** Medium  
**Action type:** Read-only / Write (Approval required? No)

1. Verify temporary credential was used and rotated:
   - check rotation completion timestamp
   - confirm new credential meets policy (strength, MFA)
2. If rotation not completed within expiration window:
   - revoke temporary credential
   - lock account
   - escalate to Security
3. Update ticket with:
   - reset completed timestamp
   - rotation completed timestamp
   - audit event IDs
   - any follow-ups (post-action approval if emergency)

**Expected result:** Credentials rotated; account secure; ticket closed with audit trail.  
**Verification (evidence to capture):**
- [ ] Rotation completion timestamp
- [ ] Audit event IDs recorded

**If this fails, go to:** Escalation (Security)

---

## Expected Citations (for RAG + evaluation)
- [ ] Section: “Safety Notes (human-in-loop triggers)”
- [ ] Section: “Step 1: Identity verification and account type confirmation”
- [ ] Keyword anchors: “temporary credentials”, “forced rotation”, “identity verification”

---

## Troubleshooting

### Common Issues

#### Issue: Temporary credential rotation fails
**Symptoms:**
- User cannot rotate temporary credential or rotation times out.

**Likely causes:**
- Temporary credential expired, policy violation, system issue

**Resolution:**
1. Verify temporary credential expiration status.
2. If expired, revoke and issue new temporary credential (requires re-approval).
3. If policy violation, guide user to meet requirements.

**If unresolved:** Escalate to Identity + Security.

---

#### Issue: Account reset succeeds but user cannot sign in
**Symptoms:**
- Reset completed but user cannot authenticate with temporary credential.

**Likely causes:**
- Temporary credential not communicated securely, typo, system propagation delay

**Resolution:**
1. Verify temporary credential was issued and communicated via secure channel.
2. Check account status (not disabled/locked).
3. Wait propagation window and retry.

**If unresolved:** Escalate to Identity.

---

### Diagnostics (copy/paste friendly)
**Redact:** account identifiers, temporary credential references, and any privileged system details before pasting into tickets/logs.
```bash
# Read-only diagnostic commands (redact output)
# - Check account status (enabled/disabled)
# - Verify rotation completion timestamp
# - Query audit logs (event IDs only)
```

---

## Escalation

## Severity guidance: P0 / P1 / P2
- **P0:** Privileged account compromise suspected or confirmed
- **P1:** Critical admin account blocked; business impact
- **P2:** Standard admin account reset

**Escalate immediately if:**
- Account compromise suspected
- Approvals missing for privileged account
- Temporary credential rotation fails

## Escalation path:
**Level 1:** Identity Operations queue — 30 min  
**Level 2:** Security Operations escalation — 15 min  
**On-call:** Security On-Call — (link redacted)

## Information to provide when escalating:
- Ticket/incident ID
- Account type and identifier (redacted)
- Identity verification status
- Approval status
- Reset action taken (if any)
- Audit event IDs (redacted)

---

## Related Knowledge

## Related runbooks:
- `rb-002-security-incident-escalation.md`
- `rb-001-access-grant-policy-procedure.md`

## Policies / docs:
- Privileged Access Management Policy — (internal link redacted)
- Identity Verification Policy — (internal link redacted)

## Tools & dashboards:
- IdP admin console — (internal link redacted)
- PAM system — (internal link redacted)

## KB articles:
- “Temporary credential security requirements” — (internal link redacted)

---

## Owner & Review

**Primary owner:** Identity Operations (IDOPS)  
**Backup owner:** Security Operations (SECOPS)  
**Review cycle:** Quarterly  
**Last updated:** 2026-01-28  
**Updated by:** Copilot Scaffold Generator  
**Change summary:** Initial restricted admin account reset procedure runbook creation.
