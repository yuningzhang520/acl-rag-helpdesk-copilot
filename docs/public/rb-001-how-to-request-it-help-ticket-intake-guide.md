# Runbook: How to Request IT Help (Ticket Intake Guide)

## Summary (TL;DR)
**What this fixes:** Faster, safer support by standardizing ticket intake.  
**Best next action:** Submit a ticket with correct type/urgency + required fields + redacted evidence.  
**If you only have 2 minutes:** Impact, timestamp, exact error text, what you tried, one redacted screenshot.

---

## Purpose
Standardize IT requests for consistent triage and auditability.

**Use this runbook when:**
- You need IT help
- You suspect an outage (many users affected)

**Do NOT use this runbook when:**
- You suspect account compromise/phishing (go to Escalation)

---

## Scope
- **Systems covered:** Ticket submission + safe evidence capture.
- **Scenarios included:** New requests, updates, escalation.
- **Scenarios excluded:** Admin/privileged fixes (IT-only).

---

## Access & Data Classification (for ACL + governance)
- **Readable by (who may cite):** Employee / Engineer / IT Admin  
- **Executable by (who may perform steps):** Employees (submit/update tickets; basic self-checks) + Helpdesk (triage)  
- **Note:** The ACL **permission tier** controls what content may be retrieved/cited. Execution permission is separate and enforced by tools/approvals.  
- **Permission tier:** public  
- **Sensitive data involved:** Yes (may include PII/screenshots). Never share passwords, MFA codes, tokens, or secrets.  
- **Logging rule:** Never log secrets, tokens, passwords, or full PII. Redact before sharing.
- **Redaction notes (if any):** Redact emails/phones, device IDs, IP/MAC/hostnames, tokens, QR/recovery codes.

---

## Intake Fields Needed (maps to ticket intake / issue template)
- **Ticket/Request ID:** (if updating)  
- **Request type:** VPN / MFA / Access / Onboarding / Other  
- **Urgency:** Low / Medium / High / Critical  
- **Requester identity:** (work username)  
- **Requester role (claimed):** Employee / Engineer / IT Admin  
- **Environment:** home / office / travel / unknown (optional)  
- **Error message(s):** (exact text)  
- **Time started (timestamp):**  
- **What changed recently?** (optional)  
- **What has been tried already?** (optional)

---

## Preconditions / Prerequisites
- **Tools required:** Ticketing portal or approved support channel.
- **Credentials required:** Your standard work login.
- **Network requirements:** VPN required? (No)
- **Dependencies healthy:** Not required (request intake only)

---

## Safety Notes (human-in-loop triggers)
**Stop and escalate if:**
- You suspect phishing/malware/account takeover
- Many users are impacted (possible outage)
- Anyone asks for passwords/MFA codes/tokens

**Approval required for:**
- Any access grants or permission changes
- Any action involving restricted systems or restricted data

---

## Steps

### Step 1: Choose the right request type and urgency
**Objective:** Route your request to the correct team and response time.  
**Risk level:** Low  
**Action type:** Read-only / Write (Approval required? No)

1. Select the closest **Request type**.
2. Set **Urgency** by impact (Critical only for outage/security concerns).

**Expected result:** Ticket is correctly categorized and prioritized.  
**Verification (evidence to capture):**
- [ ] Ticket shows correct request type and urgency

**If this fails, go to:** Escalation

---

### Decision points (routing mini-rail)
- **If many users are impacted:** Set **Critical** → Escalation (**P0**).
- **If compromise suspected:** Escalation immediately.

---

### Step 2: Write a clear description (the “minimum viable ticket”)
**Objective:** Provide enough context for first-touch resolution.  
**Risk level:** Low  
**Action type:** Write (Approval required? No)

1. Outcome + impact + app/service + device.
2. Exact error text + timestamp.
3. What you tried (1–3 bullets).

**Expected result:** The request is actionable without follow-up questions.  
**Verification (evidence to capture):**
- [ ] Ticket includes impact + app/service + error + timestamp + attempted steps

**If this fails, go to:** Step 3

---

### Step 3: Attach safe evidence (screenshots/logs)
**Objective:** Provide diagnostic evidence without leaking sensitive data.  
**Risk level:** Medium  
**Action type:** Write (Approval required? No)

1. Attach one screenshot (or paste error text).
2. Redact passwords/MFA codes, QR/recovery codes, tokens, full IP/MAC/hostnames.

**Expected result:** Evidence is useful and safe to store in ticketing.  
**Verification (evidence to capture):**
- [ ] Redaction applied where needed
- [ ] Evidence referenced in the ticket description

**If this fails, go to:** Troubleshooting / Escalation

---

## Expected Citations (for RAG + evaluation)
- [ ] Section: “Intake Fields Needed”
- [ ] Section: “Safety Notes (human-in-loop triggers)”
- [ ] Keyword anchors: “minimum viable ticket”, “redact”

---

## Troubleshooting

### Common Issues

#### Issue: Unsure which request type to pick
**Symptoms:**
- Not sure if VPN vs MFA vs Access vs Other.

**Likely causes:**
- Overlapping symptoms.

**Resolution:**
1. Choose the closest category and include exact error + timestamp.

**If unresolved:** Helpdesk will re-route; no action required.

---

#### Issue: Ticket stalls due to missing information
**Symptoms:**
- You get follow-up questions for missing details.

**Likely causes:**
- Missing impact/error/timestamp/what you tried.

**Resolution:**
1. Update the ticket with missing fields and attach one redacted screenshot.

**If unresolved:** Escalate (see Escalation).

---

### Diagnostics (copy/paste friendly)
```bash
# No commands required.
# Provide: error + timestamp + app/service + device + what you tried.
```

---

## Escalation

## Severity guidance: P0 / P1 / P2
- **P0:** Widespread outage or severe security incident
- **P1:** Business-critical work blocked with near-term deadline
- **P2:** Single-user issue

**Escalate immediately if:**
- Many users are impacted (suspected outage)
- Security incident suspected (phishing, malware, account takeover)
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
- Impact assessment (who/what is blocked)
- Exact error messages (redacted) + timestamps
- Steps attempted + outcomes

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
**Backup owner:** IT Operations  
**Review cycle:** Quarterly  
**Last updated:** 2026-01-28  
**Updated by:** Copilot Scaffold Generator  
**Change summary:** Initial public ticket intake guide runbook creation.

