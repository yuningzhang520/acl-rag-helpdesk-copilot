# Runbook: MFA Reset SOP (Identity Verification + Approval Gate)

## Summary (TL;DR)
**What this fixes:** Users locked out due to lost device, broken authenticator app, or invalid MFA state.  
**Best next action:** Verify identity → confirm eligibility → obtain approval (if required) → perform reset → validate login → document evidence.  
**If you only have 2 minutes:** Verify identity and urgency → check for security red flags → route to Identity queue if high risk.

---

## Purpose
Provide a controlled, auditable procedure to reset MFA while minimizing account takeover risk.

**Use this runbook when:**
- [ ] User cannot complete MFA due to lost/replaced phone
- [ ] Authenticator app is corrupted and codes do not work
- [ ] MFA enrollment is stuck after a device migration

**Do NOT use this runbook when:**
- [ ] The user is receiving unexpected MFA prompts (potential compromise) — escalate to Security
- [ ] The request comes from an unverified channel — verify identity first

---

## Scope
- **Systems covered:** SSO/IdP MFA enrollment, helpdesk ticketing system.
- **Scenarios included:** User-driven MFA reset with identity verification and approvals.
- **Scenarios excluded:** Disabling MFA permanently (requires Security exception process).

---

## Access & Data Classification (for ACL + governance)
- **Readable by (who may cite):** Employee / Engineer / IT Admin  
- **Executable by (who may perform steps):** Helpdesk (triage/read-only) + IT Admin (write/privileged)  
- **Note:** The ACL **permission tier** controls what content may be retrieved/cited. Execution permission is separate and enforced by tools/approvals.  
- **Permission tier:** restricted  
- **Sensitive data involved:** Yes (PII, authentication state; never request passwords/OTP)  
- **Logging rule:** Never log secrets, tokens, passwords, or full PII. Redact before sharing.
- **Redaction notes (if any):** Mask email/phone, avoid storing screenshots that display QR codes or recovery codes.

---

## Intake Fields Needed (maps to ticket intake / issue template)
- **Ticket/Request ID:**  
- **Request type:** MFA  
- **Urgency:** Low / Medium / High / Critical  
- **Requester identity:**  
- **Requester role (claimed):** Employee / Engineer / IT Admin  
- **Environment:** internal  
- **Error message(s):**  
- **Time started (timestamp):**  
- **What changed recently?** (new phone, travel, password reset)  
- **What has been tried already?** (backup codes, alternate factor)

---

## Preconditions / Prerequisites
- **Tools required:** IdP admin console, ticketing system, identity verification playbook.
- **Credentials required:** IT Admin privileges to reset MFA.
- **Network requirements:** VPN required? (Yes for admin console, if applicable)
- **Dependencies healthy:** IdP operational.

---

## Safety Notes (human-in-loop triggers)
**Stop and escalate if:**
- [ ] Requester cannot pass identity verification
- [ ] There are indicators of compromise (impossible travel, suspicious sign-ins, repeated reset attempts)
- [ ] VIP/privileged account (additional approval required)

**Approval required for:**
- [ ] MFA reset for privileged accounts (IT Admin, Finance, Security)
- [ ] Any change that reduces authentication strength (temporary bypass)

---

## Steps

### Step 1: Identity verification and fraud checks
**Objective:** Confirm the requester is the legitimate account owner.  
**Risk level:** High  
**Action type:** Read-only / Write (Approval required? Yes)

1. Verify the request source:
   - Use approved ticket channel; if email-based, verify sender domain and ticket provenance.
2. Perform identity verification per policy (choose two):
   - Manager confirmation via internal directory
   - Verified callback to number on file
   - Recent HR identifiers (per policy; do not collect SSN)
3. Check IdP sign-in logs for anomalies around the request time (geo/IP patterns).

**Expected result:** Identity verified and no security red flags.  
**Verification (evidence to capture):**
- [ ] Verification method(s) recorded in ticket (no sensitive IDs)
- [ ] Note: “No anomalous sign-ins observed” (or details escalated)

**If this fails, go to:** Escalation (Security)

---

### Decision points (routing mini-rail)
- **If identity cannot be verified or sign-ins look suspicious:** Escalate to **Security** immediately (potential compromise).
- **If the account is privileged (IT Admin/Finance/Security) or VIP:** Require **manager + Security approval** before any reset (Step 2).
- **If IdP/MFA services show outage:** Escalate as **P0/P1** depending on impact and pause resets.

---

### Step 2: Confirm reset eligibility and approvals
**Objective:** Ensure correct approvals before changing authentication state.  
**Risk level:** High  
**Action type:** Read-only / Write (Approval required? Yes)

1. Determine account type:
   - Standard user vs privileged vs service account
2. If privileged:
   - Require manager + Security approval (per policy)
3. If the user requests a temporary bypass:
   - Require Security approval and set a short expiration window

**Expected result:** Required approvals obtained and documented.  
**Verification (evidence to capture):**
- [ ] Approver name/team and timestamp in ticket

**If this fails, go to:** Escalation

---

### Step 3: Perform MFA reset (IdP)
**Objective:** Reset the user’s MFA enrollment so they can re-enroll.  
**Risk level:** High  
**Action type:** Write (Approval required? Yes)

1. In IdP admin console, locate the user account.
2. Revoke existing MFA factors / reset enrollment (per vendor procedure).
3. If policy allows, force re-enrollment at next login.
4. Do **not** disable MFA as a “shortcut” unless explicitly approved and time-bounded.

**Expected result:** User is prompted to re-enroll MFA on next sign-in.  
**Verification (evidence to capture):**
- [ ] Admin console event ID / audit entry reference (no screenshots of QR codes)

**If this fails, go to:** Troubleshooting / Escalation (Identity)

---

### Step 4: Validate user login and close the loop
**Objective:** Confirm the user can authenticate and record completion.  
**Risk level:** Medium  
**Action type:** Read-only / Write (Approval required? No)

1. Ask user to sign in and re-enroll with approved factor(s).
2. Confirm successful authentication and that backup methods are configured (if required).
3. Update ticket with:
   - what was changed
   - how the user validated success
   - any follow-ups (e.g., security awareness reminder)

**Expected result:** User can sign in with MFA successfully.  
**Verification (evidence to capture):**
- [ ] User confirmation + timestamp
- [ ] IdP sign-in success log reference (optional)

**If this fails, go to:** Troubleshooting

---

## Expected Citations (for RAG + evaluation)
- [ ] Section: “Safety Notes (human-in-loop triggers)”
- [ ] Section: “Step 1: Identity verification and fraud checks”
- [ ] Keyword anchors: “privileged account”, “temporary bypass”, “re-enrollment”

---

## Troubleshooting

### Common Issues

#### Issue: User still prompted for old factor after reset
**Symptoms:**
- User sees the old device or factor during sign-in.

**Likely causes:**
- Cached session, factor not revoked correctly, multiple factors still active

**Resolution:**
1. Ensure all old factors are revoked; force sign-out of all sessions.
2. Have user clear browser cookies for SSO domain or use private window.
3. Retry enrollment.

**If unresolved:** Escalate to Identity.

---

#### Issue: User cannot enroll new MFA due to device restrictions
**Symptoms:**
- Enrollment fails on corporate device due to MDM restrictions or blocked app install.

**Likely causes:**
- Mobile management policy, app store restrictions

**Resolution:**
1. Confirm device compliance status.
2. Route to endpoint/MDM support for remediation.

**If unresolved:** Escalate to Endpoint team.

---

### Diagnostics (copy/paste friendly)
**Redact:** full IPs, device identifiers, hostnames, and any authenticator artifacts (QR codes/recovery codes) before pasting into tickets/logs.
```bash
# Capture high-level evidence only; do not paste secrets/QR codes.
# Useful items:
# - IdP audit event ID
# - Sign-in timestamp and result codes
```

---

## Escalation

## Severity guidance: P0 / P1 / P2
- **P0:** Widespread IdP/MFA outage blocking many users
- **P1:** Privileged user blocked; business-critical impact
- **P2:** Single standard user blocked

**Escalate immediately if:**
- Security incident suspected
- VIP/privileged account without approvals
- Repeated reset attempts suggesting fraud

## Escalation path:
**Level 1:** Identity Operations — `#identity-ops` — 30 min  
**Level 2:** Security Operations — `#sec-ops` — 15 min  
**On-call:** Security On-Call — PagerDuty “SECOPS” — (link redacted)

## Information to provide when escalating:
- Ticket ID + requester (redacted)
- Verification method used
- Approval details (if any)
- IdP event IDs and sign-in anomaly notes (redacted)

---

## Related Knowledge

## Related runbooks:
- `rb-001-vpn-troubleshooting.md`

## Policies / docs:
- MFA Reset Policy — (restricted link redacted)
- Identity Verification Policy — (restricted link redacted)

## Tools & dashboards:
- IdP admin console — (restricted link redacted)
- IdP status dashboard — (internal link redacted)

## KB articles:
- “How to re-enroll MFA after phone upgrade” — (internal link redacted)

---

## Owner & Review

**Primary owner:** Identity Operations (IDOPS)  
**Backup owner:** Security Operations (SECOPS)  
**Review cycle:** Quarterly  
**Last updated:** 2026-01-28  
**Updated by:** Copilot Scaffold Generator  
**Change summary:** Initial MFA reset SOP runbook creation with approval gating.

