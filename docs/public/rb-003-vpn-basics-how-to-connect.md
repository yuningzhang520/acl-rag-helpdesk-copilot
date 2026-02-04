# Runbook: VPN Basics (How to connect + common user-side checks)

## Summary (TL;DR)
**What this fixes:** Basic VPN connection issues and “connected but can’t access work resources” symptoms.  
**Best next action:** Confirm you’re on a stable network → sign in to VPN → retry after restart → collect error text and open a ticket if needed.  
**If you only have 2 minutes:** Switch networks if possible → restart VPN app → sign in again → if still failing, submit ticket with exact error.

---

## Purpose
Enable employees to connect to VPN using safe, user-side steps and to provide the right evidence when escalation is needed.

**Use this runbook when:**
- [ ] You need VPN to access work resources from outside the office
- [ ] VPN fails to connect or disconnects frequently

**Do NOT use this runbook when:**
- [ ] You are asked to disable security controls (firewall/antivirus) beyond standard user settings
- [ ] You suspect your account is compromised (go to Escalation)

---

## Scope
- **Systems covered:** VPN client application (user-side), network connectivity basics.
- **Scenarios included:** Connecting, reconnecting, verifying basic network, collecting safe evidence.
- **Scenarios excluded:** VPN entitlement/access grants, gateway/network changes (handled by IT).

---

## Access & Data Classification (for ACL + governance)
- **Readable by (who may cite):** Employee / Engineer / IT Admin  
- **Executable by (who may perform steps):** Employees (user-side checks) + Helpdesk (triage)  
- **Note:** The ACL **permission tier** controls what content may be retrieved/cited. Execution permission is separate and enforced by tools/approvals.  
- **Permission tier:** public  
- **Sensitive data involved:** Yes (network identifiers may appear). Do not share secrets.  
- **Logging rule:** Never log secrets, tokens, passwords, or full PII. Redact before sharing.
- **Redaction notes (if any):** Redact IP addresses, Wi‑Fi SSIDs, device names, and any tokens shown in logs.

---

## Intake Fields Needed (maps to ticket intake / issue template)
- **Ticket/Request ID:** (if opening/updating a ticket)  
- **Request type:** VPN  
- **Urgency:** Low / Medium / High / Critical  
- **Requester identity:** (your work email / username)  
- **Requester role (claimed):** Employee / Engineer / IT Admin  
- **Environment:** home / office / travel / unknown (optional)  
- **Error message(s):** (copy exact text)  
- **Time started (timestamp):**  
- **What changed recently?** (new network, travel, OS update, password change)  
- **What has been tried already?** (restart app, reboot, different network)

---

## Preconditions / Prerequisites
- **Tools required:** VPN client installed and approved for use.
- **Credentials required:** Your standard work login + MFA.
- **Network requirements:** VPN required? (This runbook is for VPN access)
- **Dependencies healthy:** Not required (user-side checks only)

---

## Safety Notes (human-in-loop triggers)
**Stop and escalate if:**
- [ ] You suspect phishing/account takeover (unexpected MFA prompts, unknown device logins)
- [ ] Many people are unable to connect (possible outage)
- [ ] You are asked to share your password, MFA code, or recovery codes

**Approval required for:**
- [ ] VPN entitlement/access changes (handled by IT with approvals)

---

## Steps

### Step 1: Confirm basic connectivity and time sync
**Objective:** Ensure the device can reach the internet and authentication won’t fail due to clock issues.  
**Risk level:** Low  
**Action type:** Read-only / Write (Approval required? No)

1. Confirm the internet works (open a public website).
2. If on Wi‑Fi, ensure signal is stable; if possible, try another network (e.g., hotspot).
3. Ensure your device time/date is set automatically (recommended).

**Expected result:** Stable connectivity and correct system time.  
**Verification (evidence to capture):**
- [ ] “Internet OK” confirmed
- [ ] Time set to automatic (Yes/No)

**If this fails, go to:** Troubleshooting

---

### Decision points (routing mini-rail)
- **If many users cannot connect:** Set urgency to **Critical** → Escalation (**P0**).
- **If VPN fails with authentication errors:** Confirm you can sign in to your work portal separately; if not, follow password/MFA guidance.
- **If VPN connects but apps don’t work:** Try disconnect/reconnect once; if still failing, escalate with app names and error text.

---

### Step 2: Sign in to VPN and retry a clean reconnect
**Objective:** Clear transient client issues and establish a fresh session.  
**Risk level:** Low  
**Action type:** Write (Approval required? No)

1. Open the VPN client.
2. If it shows “Connected”, disconnect.
3. Close the VPN client completely, reopen it, and connect again.
4. Complete MFA prompts as usual.

**Expected result:** VPN shows “Connected” and stays connected.  
**Verification (evidence to capture):**
- [ ] VPN status shows connected
- [ ] No repeated auth prompts

**If this fails, go to:** Step 3 / Troubleshooting

---

### Step 3: Verify access to work resources (high-level)
**Objective:** Confirm VPN is actually providing access (not just “connected”).  
**Risk level:** Low  
**Action type:** Read-only / Write (Approval required? No)

1. Try to access a standard work application you normally use.
2. If you can connect but apps fail:
   - disconnect and reconnect once
   - try a different network if possible
3. Record what fails (app name, error, time).

**Expected result:** Work apps load as expected while connected.  
**Verification (evidence to capture):**
- [ ] App access succeeded (Yes/No)
- [ ] If No: app name + error text captured

**If this fails, go to:** Troubleshooting / Escalation

---

## Expected Citations (for RAG + evaluation)
- [ ] Section: “Intake Fields Needed”
- [ ] Section: “Step 2: Sign in to VPN and retry a clean reconnect”
- [ ] Keyword anchors: “stable network”, “time sync”

---

## Troubleshooting

### Common Issues

#### Issue: VPN fails with a generic “Authentication failed”
**Symptoms:**
- VPN prompts for sign-in repeatedly or fails after MFA.

**Likely causes:**
- Password recently changed, MFA not completing, device time incorrect, temporary identity service issues

**Resolution:**
1. Confirm you can sign in to your standard work portal (separate from VPN).
2. Ensure device time is automatic and correct.
3. Retry once after restarting the VPN app.

**If unresolved:** Open a ticket with the exact error text and timestamp.

---

#### Issue: VPN connects but work apps still don’t work
**Symptoms:**
- VPN shows “Connected” but work apps time out or cannot load.

**Likely causes:**
- Unstable network, client stuck session, temporary service issue

**Resolution:**
1. Disconnect/reconnect once.
2. Switch networks (if possible) and retry.
3. Restart your device and try again.

**If unresolved:** Escalate (see Escalation).

---

### Diagnostics (copy/paste friendly)
**Redact:** full IPs, MAC addresses, and hostnames before pasting into tickets/logs. Capture only the minimum necessary evidence.
```bash
# Redact any IP/MAC/hostnames before pasting into tickets/logs.
# Safe evidence to provide:
# - VPN client version (from app “About”)
# - exact error message text
# - timestamp
# - network type (Wi‑Fi vs mobile hotspot) without naming SSID
```

---

## Escalation

## Severity guidance: P0 / P1 / P2
- **P0:** Widespread VPN outage affecting many users
- **P1:** You are blocked from business-critical work with deadline
- **P2:** Single-user VPN issue

**Escalate immediately if:**
- Many users cannot connect (possible outage)
- Security incident suspected
- SLA breach imminent for critical work

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
- Exact error message(s) and timestamp (redacted)
- VPN client version + device OS
- What you tried (reconnect, reboot, network change)
- Whether others are affected

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

**Primary owner:** IT Service Desk  
**Backup owner:** Network Support  
**Review cycle:** Quarterly  
**Last updated:** 2026-01-28  
**Updated by:** Copilot Scaffold Generator  
**Change summary:** Normalized to match canonical schema and public escalation style.
