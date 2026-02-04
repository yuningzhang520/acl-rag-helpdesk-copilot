# Runbook: Corporate Laptop Replacement + Secure Wipe (Lost/Damaged/Refresh)

## Summary (TL;DR)
**What this fixes:** Replace a corporate laptop and ensure data protection via secure wipe and access revocation.  
**Best next action:** Classify scenario (lost vs damaged vs refresh) → revoke sessions/access if needed → initiate replacement → enroll new device → wipe/retire old device → verify user productivity.  
**If you only have 2 minutes:** If **lost/stolen**: revoke sessions + mark device lost + escalate to Security. If **damaged**: start replacement workflow and preserve data if possible.

---

## Purpose
Provide an operational, security-aligned procedure for laptop replacement, including secure wipe and audit evidence.

**Use this runbook when:**
- [ ] Laptop is lost or stolen
- [ ] Laptop is damaged and cannot be used
- [ ] Scheduled refresh/replacement is approved

**Do NOT use this runbook when:**
- [ ] A suspected targeted theft or broader security incident is ongoing (escalate to Security; follow incident response)
- [ ] The “device” is a personally owned device (follow BYOD policy)

---

## Scope
- **Systems covered:** Asset inventory, MDM/endpoint management, IdP sessions, disk encryption recovery process, ticketing.
- **Scenarios included:** Lost/stolen, damaged, scheduled refresh.
- **Scenarios excluded:** Forensics workflows (Security-led), legal holds (Legal-led).

---

## Access & Data Classification (for ACL + governance)
- **Readable by (who may cite):** Employee / Engineer / IT Admin  
- **Executable by (who may perform steps):** Helpdesk (intake/routing) + IT Admin (Endpoint admin) (write/privileged)  
- **Note:** The ACL **permission tier** controls what content may be retrieved/cited. Execution permission is separate and enforced by tools/approvals.  
- **Permission tier:** restricted  
- **Sensitive data involved:** Yes (device identifiers, location signals, user identity; potential incident data)  
- **Logging rule:** Never log secrets, tokens, passwords, or full PII. Redact before sharing.
- **Redaction notes (if any):** Mask serial numbers/asset tags in public channels; do not include device location data in tickets beyond need-to-know.

---

## Intake Fields Needed (maps to ticket intake / issue template)
- **Ticket/Request ID:**  
- **Request type:** Other / Onboarding (Refresh)  
- **Urgency:** Low / Medium / High / Critical  
- **Requester identity:**  
- **Requester role (claimed):** Employee / Engineer / IT Admin  
- **Environment:** internal  
- **Time started (timestamp):**  
- **What changed recently?** (travel, incident, OS update)  
- **What has been tried already?** (safe mode, repair)

Additionally required:
- **Scenario:** lost / stolen / damaged / refresh  
- **Last known date/time device seen:**  
- **Last known location (high-level):** (city/office; avoid exact address)  
- **Whether sensitive data may be on device:** Yes/No/Unknown  
- **Replacement shipping/pickup details:** (use secure channel for addresses)  
- **Manager approval (for refresh):**

---

## Preconditions / Prerequisites
- **Tools required:** MDM console, IdP session management, asset inventory, shipping workflow, backup/restore tooling.
- **Credentials required:** Endpoint admin + identity admin (as needed).
- **Network requirements:** VPN required? (Yes for admin consoles, if applicable)
- **Dependencies healthy:** MDM and IdP operational.

---

## Safety Notes (human-in-loop triggers)
**Stop and escalate if:**
- [ ] Device is lost/stolen and may contain sensitive data (Security involvement required)
- [ ] There is evidence of compromise or suspicious activity on the account
- [ ] Legal hold is indicated (Legal + Security)

**Approval required for:**
- [ ] Remote wipe of a device (especially if potential personal data impact)
- [ ] Issuing a new device outside standard refresh cycle

---

## Steps

### Step 1: Classify the scenario and assess security risk
**Objective:** Determine the correct workflow and escalation needs.  
**Risk level:** High  
**Action type:** Read-only / Write (Approval required? Yes)

1. Confirm scenario: lost vs stolen vs damaged vs refresh.
2. For lost/stolen:
   - capture last known time/location (high-level)
   - assess if device had restricted data access
3. Check account sign-in logs for anomalies since last known time.

**Expected result:** Clear scenario classification and risk assessment.  
**Verification (evidence to capture):**
- [ ] Ticket notes include classification + risk assessment (redacted)

**If this fails, go to:** Escalation

---

### Decision points (routing mini-rail)
- **If lost/stolen with possible sensitive data exposure or anomalous sign-ins:** Escalate to **Security** immediately (treat as **P0/P1** based on impact).
- **If damaged/refresh with no security indicators:** Proceed with **replacement provisioning**; wipe/retire old device upon return.
- **If remote wipe cannot be confirmed and device remains offline:** Escalate to **Endpoint + Security** for risk assessment and compensating controls.

---

### Step 2: Containment (lost/stolen or suspected compromise)
**Objective:** Reduce risk by revoking access and preventing further use.  
**Risk level:** High  
**Action type:** Write (Approval required? Yes)

1. Revoke active IdP sessions for the user.
2. Mark device as lost/stolen in MDM (if applicable) and enable lock mode.
3. If policy permits, issue remote wipe command (requires approval).
4. Trigger credential reset workflow if compromise suspected (password reset + MFA review).

**Expected result:** Sessions revoked and device controlled/wiped per policy.  
**Verification (evidence to capture):**
- [ ] IdP session revoke event reference
- [ ] MDM device status (lost/lock/wipe initiated) reference

**If this fails, go to:** Escalation (Security/Endpoint)

---

### Step 3: Replacement device provisioning
**Objective:** Provide a compliant replacement device quickly.  
**Risk level:** Medium  
**Action type:** Write (Approval required? Yes)

1. Allocate device from inventory or initiate purchase request.
2. Enroll in MDM and apply baseline security posture:
   - disk encryption enabled
   - EDR/AV installed
   - OS baseline and patch level
3. Arrange shipping/pickup. Use secure channel for addresses.

**Expected result:** New device assigned, enrolled, compliant.  
**Verification (evidence to capture):**
- [ ] New asset assigned (asset tag redacted)
- [ ] Compliance status evidence

**If this fails, go to:** Troubleshooting / Escalation

---

### Step 4: Data restore and user validation
**Objective:** Restore productivity while maintaining security posture.  
**Risk level:** Medium  
**Action type:** Read-only / Write (Approval required? No)

1. Restore approved data sources (cloud drive, approved backups).
2. Confirm user can sign in, enroll MFA if needed, and access baseline apps.
3. Provide reminders:
   - report suspicious activity
   - avoid storing restricted data locally where possible

**Expected result:** User can work normally on replacement device.  
**Verification (evidence to capture):**
- [ ] User confirmation + timestamp

**If this fails, go to:** Troubleshooting

---

### Step 5: Retire old device (damaged/refresh) and ensure wipe
**Objective:** Ensure old device is securely wiped and removed from service.  
**Risk level:** High  
**Action type:** Write (Approval required? Yes)

1. For damaged/refresh returns:
   - receive device and verify asset tag
2. Initiate secure wipe per endpoint policy (MDM wipe + verification).
3. Remove device from active inventory, mark as retired, and process disposal.

**Expected result:** Old device wiped and retired with audit trail.  
**Verification (evidence to capture):**
- [ ] Wipe completion evidence
- [ ] Inventory status updated

**If this fails, go to:** Escalation (Endpoint)

---

## Expected Citations (for RAG + evaluation)
- [ ] Section: “Step 2: Containment (lost/stolen or suspected compromise)”
- [ ] Section: “Safety Notes (human-in-loop triggers)”
- [ ] Keyword anchors: “remote wipe”, “session revoke”, “lost/stolen”

---

## Troubleshooting

### Common Issues

#### Issue: Remote wipe command does not complete
**Symptoms:**
- Wipe pending indefinitely; device offline.

**Likely causes:**
- Device not connected to the internet; MDM agent disabled

**Resolution:**
1. Confirm last check-in time.
2. If device is online later, wipe should execute automatically.
3. Escalate to Security for risk assessment if device remains offline.

**If unresolved:** Escalate to Endpoint + Security.

---

#### Issue: Replacement device fails compliance checks
**Symptoms:**
- MDM shows non-compliant; encryption/EDR missing.

**Likely causes:**
- Enrollment profile mismatch, OS version unsupported, policy conflict

**Resolution:**
1. Re-enroll device with correct profile.
2. Apply baseline package; verify encryption and EDR.
3. Re-image if necessary (per policy).

**If unresolved:** Escalate to Endpoint.

---

### Diagnostics (copy/paste friendly)
**Redact:** full serials/asset tags, location data, IP/MAC/hostnames, and any identifiers not required for troubleshooting before pasting into tickets/logs.
```bash
# Keep evidence redacted:
# - device last check-in timestamp
# - compliance status flags
# - wipe command state (pending/complete)
```

---

## Escalation

## Severity guidance: P0 / P1 / P2
- **P0:** Lost/stolen device with suspected sensitive data exposure or active compromise
- **P1:** VIP/critical user blocked without replacement; suspected risk
- **P2:** Standard refresh or damaged device replacement

**Escalate immediately if:**
- Security incident suspected
- Lost/stolen device with restricted data access
- Anomalous sign-in activity after loss

## Escalation path:
**Level 1:** Endpoint Management — `#endpoint` — 30 min  
**Level 2:** Security Operations — `#sec-ops` — 15 min  
**On-call:** Security On-Call — PagerDuty “SECOPS” — (link redacted)

## Information to provide when escalating:
- Ticket ID + scenario classification
- Last known device check-in (redacted)
- Actions taken: session revoke, lock, wipe initiated (event references)
- Sign-in anomaly notes (redacted)

---

## Related Knowledge

## Related runbooks:
- `rb-002-mfa-reset-sop.md`
- `rb-003-employee-onboarding-checklist.md`

## Policies / docs:
- Endpoint Management Policy — (internal link redacted)
- Lost/Stolen Device Policy — (restricted link redacted)

## Tools & dashboards:
- MDM console — (restricted link redacted)
- IdP sign-in logs — (restricted link redacted)

## KB articles:
- “How to set up a replacement laptop” — (internal link redacted)

---

## Owner & Review

**Primary owner:** Endpoint Management  
**Backup owner:** Security Operations (SECOPS)  
**Review cycle:** Quarterly  
**Last updated:** 2026-01-28  
**Updated by:** Copilot Scaffold Generator  
**Change summary:** Initial laptop replacement and secure wipe runbook creation.

