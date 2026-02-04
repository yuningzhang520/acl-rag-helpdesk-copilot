# Runbook: Device Health Check (Basic troubleshooting before escalating)

## Summary (TL;DR)
**What this fixes:** Common device performance and connectivity issues using low-risk, user-side checks.  
**Best next action:** Restart → check updates → verify storage and network → confirm the issue persists → open a ticket with evidence.  
**If you only have 2 minutes:** Restart the device → check Wi‑Fi/internet → retry the problem → capture exact error text and time.

---

## Purpose
Provide a safe, repeatable device health checklist that helps employees resolve common issues and creates high-quality tickets when escalation is needed.

**Use this runbook when:**
- [ ] Your device is slow, apps crash, or network is unreliable
- [ ] You are troubleshooting before opening an IT ticket

**Do NOT use this runbook when:**
- [ ] You suspect malware/phishing or see suspicious pop-ups (go to Escalation)
- [ ] You smell smoke/see swelling battery or overheating (stop using device; escalate immediately)

---

## Scope
- **Systems covered:** End-user device (laptop/desktop) basic health checks.
- **Scenarios included:** Reboot, updates, storage, basic connectivity, safe evidence capture.
- **Scenarios excluded:** Admin-only repairs, disk encryption keys, device re-imaging (handled by IT).

---

## Access & Data Classification (for ACL + governance)
- **Readable by (who may cite):** Employee / Engineer / IT Admin  
- **Executable by (who may perform steps):** Employees (self-checks) + Helpdesk (triage)  
- **Note:** The ACL **permission tier** controls what content may be retrieved/cited. Execution permission is separate and enforced by tools/approvals.  
- **Permission tier:** public  
- **Sensitive data involved:** Possibly (screenshots/logs). Avoid sharing sensitive content.  
- **Logging rule:** Never log secrets, tokens, passwords, or full PII. Redact before sharing.
- **Redaction notes (if any):** Do not screenshot confidential documents; blur emails, names, and any identifiers.

---

## Intake Fields Needed (maps to ticket intake / issue template)
- **Ticket/Request ID:** (if opening/updating a ticket)  
- **Request type:** Other  
- **Urgency:** Low / Medium / High / Critical  
- **Requester identity:** (your work email / username)  
- **Requester role (claimed):** Employee / Engineer / IT Admin  
- **Environment:** home / office / travel / unknown (optional)  
- **Error message(s):** (copy exact text)  
- **Time started (timestamp):**  
- **What changed recently?** (updates installed, new software, travel, new peripherals)  
- **What has been tried already?** (restart, network change)

---

## Preconditions / Prerequisites
- **Tools required:** None (standard device settings).
- **Credentials required:** Your standard device login.
- **Network requirements:** VPN required? (No)
- **Dependencies healthy:** Not required (self-checks only)

---

## Safety Notes (human-in-loop triggers)
**Stop and escalate if:**
- [ ] Device is overheating, smoking, or battery is swollen (safety risk)
- [ ] You suspect malware/phishing or see repeated unexpected security prompts
- [ ] The issue affects many people at once (possible outage)

**Approval required for:**
- [ ] Any action that requires admin privileges or installs unmanaged software (handled by IT)

---

## Steps

### Step 1: Reproduce and describe the symptom clearly
**Objective:** Make the issue measurable and repeatable.  
**Risk level:** Low  
**Action type:** Read-only / Write (Approval required? No)

1. Identify the primary symptom:
   - slow performance, app crash, internet drops, audio/video issues, etc.
2. Note:
   - what app/service is involved
   - exact error text
   - when it started
3. Try to reproduce once.

**Expected result:** Clear symptom definition and reproducible steps (if possible).  
**Verification (evidence to capture):**
- [ ] Exact error text captured (redacted)
- [ ] Timestamp recorded

**If this fails, go to:** Escalation (if urgent) or Step 2

---

### Decision points (routing mini-rail)
- **If physical safety issue (overheating/swelling battery/smoke):** Stop using device → Escalation (**P0**) immediately.
- **If many users are affected:** Set urgency to **Critical** → Escalation (**P0**).
- **If issue persists after restart and basic checks:** Escalate with evidence (error text, timestamps, what you tried).

---

### Step 2: Restart and retest
**Objective:** Clear transient state and confirm whether the issue persists.  
**Risk level:** Low  
**Action type:** Write (Approval required? No)

1. Save your work and restart the device.
2. After restart, wait 2–3 minutes for startup tasks to settle.
3. Retry the same action that caused the issue.

**Expected result:** Issue is resolved or clearly persists post-restart.  
**Verification (evidence to capture):**
- [ ] “Resolved after restart” (Yes/No)
- [ ] If No: same error reproduced

**If this fails, go to:** Step 3

---

### Step 3: Check storage, updates, and basic connectivity
**Objective:** Address common root causes: low disk space, missing updates, network instability.  
**Risk level:** Low  
**Action type:** Read-only / Write (Approval required? No)

1. Check available storage:
   - If very low, delete unneeded files or move them to approved cloud storage.
2. Check for pending OS updates and install when appropriate (follow normal update guidance).
3. Check network:
   - toggle Wi‑Fi off/on
   - try a different network if possible
4. Retry the issue.

**Expected result:** Device is reasonably updated, has adequate storage, and has stable network.  
**Verification (evidence to capture):**
- [ ] Storage status (e.g., “Low/OK”)
- [ ] Update status (“Up to date” or “Updates pending”)
- [ ] Network retest outcome

**If this fails, go to:** Troubleshooting / Escalation

---

## Expected Citations (for RAG + evaluation)
- [ ] Section: “Step 2: Restart and retest”
- [ ] Section: “Step 3: Check storage, updates, and basic connectivity”
- [ ] Keyword anchors: “reproduce”, “post-restart”

---

## Troubleshooting

### Common Issues

#### Issue: Device is slow only on one network
**Symptoms:**
- Performance/connectivity is fine elsewhere, but poor on a specific Wi‑Fi network.

**Likely causes:**
- Local Wi‑Fi congestion or ISP issues

**Resolution:**
1. Move closer to the router/access point if possible.
2. Switch to a different network (hotspot) for comparison.
3. If the issue only occurs on one network, note that in the ticket.

**If unresolved:** Escalate (see Escalation).

---

#### Issue: One application crashes repeatedly
**Symptoms:**
- The same app crashes on launch or during a specific action.

**Likely causes:**
- Corrupted local app cache, outdated app version, temporary service issue

**Resolution:**
1. Quit and reopen the app.
2. Check for app updates (if managed, updates may be automatic).
3. If safe and available, “reset app”/clear cache from the app settings (no advanced steps).

**If unresolved:** Escalate (see Escalation).

---

### Diagnostics (copy/paste friendly)
**Redact:** full IPs, MAC addresses, hostnames, device serials, and any identifiers before pasting into tickets/logs.
```bash
# Redact identifiers before pasting into tickets/logs.
# Provide safe evidence:
# - device type (laptop/desktop) and OS version
# - app name and version (if relevant)
# - exact error text
# - timestamp
# - what you tried (restart, updates, network change)
```

---

## Escalation

## Severity guidance: P0 / P1 / P2
- **P0:** Safety risk (battery swelling/overheating) or widespread outage
- **P1:** Business-critical work blocked with deadline
- **P2:** Single-device performance issue

**Escalate immediately if:**
- Physical safety issue (overheating, swelling battery, smoke)
- Security incident suspected
- Many users affected at the same time

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
- Symptoms + timestamps
- Steps attempted + outcomes
- Any error messages (redacted)
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

**Primary owner:** Endpoint Support  
**Backup owner:** IT Service Desk  
**Review cycle:** Quarterly  
**Last updated:** 2026-01-28  
**Updated by:** Copilot Scaffold Generator  
**Change summary:** Normalized to match canonical schema and public escalation style.
