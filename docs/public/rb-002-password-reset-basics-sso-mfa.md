# Runbook: Password Reset Basics (SSO + MFA, no account recovery bypass)

## Summary (TL;DR)
**What this fixes:** Standard “forgot password” or password-expired issues using approved self-service flows.  
**Best next action:** Use the official password reset flow → verify MFA → confirm you can sign in.  
**If you only have 2 minutes:** Use password reset link → set a strong new password → sign in again → if MFA is broken, open an IT ticket (do not request bypass).

---

## Purpose
Help employees reset their password safely using approved identity controls (SSO + MFA) without bypassing security.

**Use this runbook when:**
- [ ] You forgot your password or password expired
- [ ] You are locked out due to too many failed attempts (after waiting per policy)

**Do NOT use this runbook when:**
- [ ] You are receiving unexpected MFA prompts or suspect compromise (go to Escalation)
- [ ] You are asked to share a password, MFA code, or recovery codes (stop and escalate)

---

## Scope
- **Systems covered:** SSO sign-in, MFA prompt, official password reset flow.
- **Scenarios included:** Self-service password reset, post-reset sign-in validation, basic browser/app checks.
- **Scenarios excluded:** Permanent MFA disablement or “account recovery bypass” (not permitted).

---

## Access & Data Classification (for ACL + governance)
- **Readable by (who may cite):** Employee / Engineer / IT Admin  
- **Executable by (who may perform steps):** Employees (self-service reset) + Helpdesk (triage)  
- **Note:** The ACL **permission tier** controls what content may be retrieved/cited. Execution permission is separate and enforced by tools/approvals.  
- **Permission tier:** public  
- **Sensitive data involved:** Yes (authentication). Never share passwords, MFA codes, QR codes, or recovery codes.  
- **Logging rule:** Never log secrets, tokens, passwords, or full PII. Redact before sharing.
- **Redaction notes (if any):** Do not paste screenshots showing MFA QR codes, backup codes, or security questions.

---

## Intake Fields Needed (maps to ticket intake / issue template)
- **Ticket/Request ID:** (if opening/updating a ticket)  
- **Request type:** MFA / Other  
- **Urgency:** Low / Medium / High / Critical  
- **Requester identity:** (your work email / username)  
- **Requester role (claimed):** Employee / Engineer / IT Admin  
- **Environment:** home / office / travel / unknown (optional)  
- **Error message(s):** (copy exact text)  
- **Time started (timestamp):**  
- **What changed recently?** (new phone, travel, password change)  
- **What has been tried already?** (reset link, different browser)

---

## Preconditions / Prerequisites
- **Tools required:** Access to the official password reset page; your enrolled MFA method(s).
- **Credentials required:** Your account identifier (email/username).
- **Network requirements:** VPN required? (No)
- **Dependencies healthy:** Not required (self-service reset only)

---

## Safety Notes (human-in-loop triggers)
**Stop and escalate if:**
- [ ] You suspect phishing or account takeover (unexpected prompts, unknown device notifications)
- [ ] You cannot verify the password reset page is official (URL looks wrong, unusual prompts)
- [ ] Someone asks for your password, MFA code, or recovery codes

**Approval required for:**
- [ ] Any request to bypass MFA or reduce authentication strength (not supported via public runbook)
- [ ] Any administrative reset performed by IT (requires identity verification)

---

## Steps

### Step 1: Confirm you are using the official sign-in/reset flow
**Objective:** Prevent credential theft and ensure your reset is processed correctly.  
**Risk level:** Medium  
**Action type:** Read-only / Write (Approval required? No)

1. Navigate only via trusted paths:
   - company portal bookmark, or
   - known official sign-in page from corporate documentation.
2. Do not use links from unsolicited emails/messages.
3. If the page requests unusual information (personal IDs, bank info), stop and escalate.

**Expected result:** You are on the official sign-in/reset flow.  
**Verification (evidence to capture):**
- [ ] You navigated via trusted source (bookmark/portal)
- [ ] No unusual prompts were observed

**If this fails, go to:** Escalation

---

### Decision points (routing mini-rail)
- **If you suspect phishing or account takeover:** Escalation immediately (do not proceed with reset).
- **If reset page shows “Account not found” or “Not eligible”:** Open an IT ticket with exact error text.
- **If MFA prompts fail during reset:** Open an IT ticket (do not request bypass).

---

### Step 2: Perform a standard password reset
**Objective:** Reset your password using approved self-service controls.  
**Risk level:** Medium  
**Action type:** Write (Approval required? No)

1. Select “Forgot password” / “Reset password”.
2. Complete identity checks via your enrolled MFA method.
3. Set a new strong password:
   - long passphrase preferred
   - do not reuse old passwords
4. Save and confirm the reset completes successfully.

**Expected result:** Password reset completes without errors.  
**Verification (evidence to capture):**
- [ ] Confirmation message displayed (no screenshots with sensitive info)

**If this fails, go to:** Troubleshooting

---

### Step 3: Validate sign-in and update saved sessions
**Objective:** Ensure you can access core tools after the reset.  
**Risk level:** Low  
**Action type:** Read-only / Write (Approval required? No)

1. Sign in again using the new password.
2. Approve MFA prompt as usual.
3. If apps keep prompting for old password:
   - sign out of the app
   - close and reopen
   - sign in again

**Expected result:** Successful sign-in across critical apps.  
**Verification (evidence to capture):**
- [ ] You can sign in to at least one core app successfully

**If this fails, go to:** Troubleshooting / Escalation

---

## Expected Citations (for RAG + evaluation)
- [ ] Section: “Safety Notes (human-in-loop triggers)”
- [ ] Section: “Step 2: Perform a standard password reset”
- [ ] Keyword anchors: “no bypass”, “official flow”

---

## Troubleshooting

### Common Issues

#### Issue: Reset page says “Account not found” or “Not eligible”
**Symptoms:**
- Reset flow cannot locate your account or blocks the action.

**Likely causes:**
- Typo in username/email, account not activated, account disabled

**Resolution:**
1. Re-enter your username/email carefully.
2. Try from a different browser or private/incognito window.
3. If still blocked, open an IT ticket and provide the exact error text (redacted).

**If unresolved:** Escalate (see Escalation).

---

#### Issue: MFA prompts fail during reset
**Symptoms:**
- You cannot approve MFA or do not receive prompts.

**Likely causes:**
- Phone offline, notification delays, authenticator app issue

**Resolution:**
1. Confirm your phone has connectivity (Wi‑Fi/cellular).
2. Restart the authenticator app and retry.
3. If you changed phones recently, open an IT ticket (do not request bypass).

**If unresolved:** Escalate (see Escalation).

---

### Diagnostics (copy/paste friendly)
```bash
# No commands required. Provide safe evidence:
# - exact error message
# - timestamp
# - device type (laptop/phone)
# - whether MFA prompt is received
```

---

## Escalation

## Severity guidance: P0 / P1 / P2
- **P0:** Widespread sign-in outage or suspected coordinated compromise
- **P1:** You are blocked from business-critical work with deadline
- **P2:** Single-user password reset issue

**Escalate immediately if:**
- You suspect phishing/account takeover
- Many users report the same sign-in/reset failure
- You observe unusual security prompts or unexpected login notifications

## Escalation path:
**If you have ticket portal access:**
1. Set urgency to **Critical** in the ticket portal.
2. Add an escalation comment explaining why this is urgent (impact, deadline, or security concern).

**If you do not have ticket portal access:**
1. Use the official IT support contact method (phone, email, or chat as provided by your organization).
2. Clearly state that this is an escalation and provide the ticket/incident ID if you have one.

**For suspected compromise or security incidents:**
1. Use the official security incident reporting path (as provided by your organization).
2. Do not wait for normal ticket processing.

## Information to provide when escalating:
- Ticket/incident ID
- Exact error messages (redacted)
- Time started and whether others are affected
- Device type and whether MFA prompt is received
- What you already tried

---

## Related Knowledge

## Related runbooks:
- N/A (public)

## Policies / docs:
- N/A (public)

## Tools & dashboards:
- N/A (public)

## KB articles:
- N/A (public)

---

## Owner & Review

**Primary owner:** Identity Support  
**Backup owner:** IT Service Desk  
**Review cycle:** Quarterly  
**Last updated:** 2026-01-28  
**Updated by:** Copilot Scaffold Generator  
**Change summary:** Normalized to match canonical schema and public escalation style.
