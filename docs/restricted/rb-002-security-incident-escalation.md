# Runbook: Security Incident Escalation (Suspected Compromise; Containment; Evidence Collection; Comms)

## Summary (TL;DR)
**What this fixes:** Suspected security incidents (compromise, phishing, unauthorized access) requiring immediate containment, evidence collection, and coordinated response.  
**Best next action:** Verify incident → contain affected systems → collect evidence (preserve chain of custody) → escalate to Security → coordinate communications.  
**If you only have 2 minutes:** Verify incident indicators → isolate affected account/system → collect timestamped evidence → escalate to Security On-Call immediately.

---

## Purpose
Provide a controlled, auditable process for escalating suspected security incidents with immediate containment, evidence preservation, and coordinated response.

**Use this runbook when:**
- [ ] Suspected account compromise (unexpected sign-ins, unusual geo, credential theft)
- [ ] Phishing/malware indicators detected
- [ ] Unauthorized access to restricted systems/data
- [ ] Suspicious privilege escalation or access pattern

**Do NOT use this runbook when:**
- [ ] Confirmed false positive (no actual security risk)
- [ ] Standard access request (use access grant runbook)
- [ ] Non-security IT issue (use standard troubleshooting)

---

## Scope
- **Systems covered:** Identity systems, endpoint management, network monitoring, audit logs, incident response platform.
- **Scenarios included:** Account compromise, phishing, malware, unauthorized access, privilege escalation.
- **Scenarios excluded:** Physical security incidents (Security team), legal/compliance matters (Legal), confirmed breaches (incident response team).

---

## Access & Data Classification (for ACL + governance)
- **Readable by (who may cite):** Employee / Engineer / IT Admin  
- **Executable by (who may perform steps):** Helpdesk (read-only) + Engineer / IT Admin (write/privileged)  
- **Note:** The ACL **permission tier** controls what content may be retrieved/cited. Execution permission is separate and enforced by tools/approvals.  
- **Permission tier:** restricted  
- **Sensitive data involved:** Yes (incident data, PII, compromised credentials, investigation details). Never log passwords, tokens, or full PII.  
- **Logging rule:** Never log secrets, tokens, passwords, or full PII. Redact before sharing.
- **Redaction notes (if any):** Mask user email (e.g., `a***@corp`), IP addresses, device identifiers, and any investigation-sensitive details in non-Security channels.

---

## Intake Fields Needed (maps to ticket intake / issue template)
- **Ticket/Request ID:**  
- **Request type:** Other / Security  
- **Urgency:** Critical  
- **Requester identity:**  
- **Requester role (claimed):** Employee / Engineer / IT Admin  
- **Environment:** N/A (incident response)  
- **Error message(s):** (if applicable)  
- **Time started (timestamp):**  
- **What changed recently?** (unexpected prompts, unknown devices, suspicious activity)  
- **What has been tried already?** (initial checks, evidence collection)

Additionally required:
- **Incident type:** account compromise / phishing / malware / unauthorized access / other  
- **Indicators observed:** (unexpected sign-ins, unusual geo, suspicious emails, etc.)  
- **Affected systems/users:**  
- **Time first observed:**  
- **Impact assessment:** (data at risk, systems affected, user count)

---

## Preconditions / Prerequisites
- **Tools required:** Incident response platform, IAM admin console (read-only), endpoint management, audit log system, ticketing system.
- **Credentials required:** Security incident responder role for containment actions; read-only for triage.
- **Network requirements:** VPN required? (Yes for admin consoles)
- **Dependencies healthy:** Incident response platform operational; audit logs accessible.

**Change window (if applicable):**
- Containment actions: immediate execution; no change window.
- Evidence collection: preserve chain of custody; timestamp all actions.

---

## Safety Notes (human-in-loop triggers)
**Stop and escalate if:**
- [ ] Incident involves executive/VIP accounts (additional approval required)
- [ ] Incident may involve legal/compliance matters (involve Legal)
- [ ] Containment action would cause production outage (coordinate with Operations)
- [ ] Evidence collection requires forensic imaging (involve Security forensics team)

**Approval required for:**
- [ ] Account lockout/revocation (Security approval)
- [ ] Network isolation/quarantine (Security + Operations approval)
- [ ] Public communications (Security + Legal + Comms approval)
- [ ] Forensic actions (Security forensics approval)

**Audit requirements:**
- [ ] Log all containment actions with timestamp, operator identity, reason, affected systems.
- [ ] Log evidence collection with chain of custody (who, what, when, where).
- [ ] Log all escalations and handoffs with Security team.
- [ ] Retain incident logs per compliance policy (e.g., 1–7 years).

**Rollback/containment:**
- [ ] If false positive confirmed, restore access and document in incident log.
- [ ] If containment was premature, coordinate restoration with Security.

---

## Steps

### Step 1: Incident verification and initial assessment
**Objective:** Confirm incident indicators and assess scope/severity.  
**Risk level:** High  
**Action type:** Read-only / Write (Approval required? Yes)

1. Verify incident indicators:
   - unexpected sign-in logs (geo, device, time)
   - suspicious email/phishing reports
   - malware detection alerts
   - unauthorized access attempts
2. Assess scope:
   - single account vs multiple accounts
   - data at risk (PII, restricted data, credentials)
   - systems affected
3. Check for active compromise:
   - current active sessions
   - recent privilege changes
   - data exfiltration indicators

**Expected result:** Incident confirmed and scope assessed.  
**Verification (evidence to capture):**
- [ ] Incident indicators documented (redacted)
- [ ] Scope assessment recorded
- [ ] Severity classification (P0/P1/P2)

**If this fails, go to:** Escalation (Security)

---

### Decision points (routing mini-rail)
- **If confirmed compromise with active sessions:** Immediate containment (Step 2) → Escalation (**P0**).
- **If suspected phishing (no confirmed compromise):** Collect evidence → Escalate to Security for analysis.
- **If false positive (no actual risk):** Document and close; no containment needed.
- **If executive/VIP account involved:** Escalate to Security immediately; additional approvals required.

---

### Step 2: Immediate containment (isolate affected systems)
**Objective:** Prevent further damage by isolating compromised accounts/systems.  
**Risk level:** High  
**Action type:** Write (Approval required? Yes)

1. Revoke active sessions for affected account(s):
   - IdP session revocation
   - VPN session termination
   - application session invalidation
2. Lock/disable affected account(s) if compromise confirmed:
   - set account to disabled state
   - preserve account for investigation (do not delete)
3. Isolate affected endpoints (if malware/compromise detected):
   - network quarantine via endpoint management
   - disable network access
4. Log all containment actions with timestamp and operator identity.

**Expected result:** Affected systems isolated; further damage prevented.  
**Verification (evidence to capture):**
- [ ] Session revocation event IDs
- [ ] Account lock/disable confirmation
- [ ] Network isolation status (if applicable)
- [ ] Containment actions logged

**If this fails, go to:** Escalation (Security + Operations)

---

### Step 3: Evidence collection and chain of custody
**Objective:** Preserve evidence for investigation while maintaining chain of custody.  
**Risk level:** High  
**Action type:** Read-only / Write (Approval required? Yes)

1. Collect timestamped evidence:
   - sign-in logs (geo, IP, device, time)
   - access logs (what was accessed, when)
   - email headers (if phishing)
   - endpoint logs (if malware)
2. Preserve chain of custody:
   - document who collected evidence
   - timestamp all collection actions
   - store in secure, access-controlled location
3. Redact sensitive data before sharing:
   - mask PII, IPs, device identifiers
   - preserve investigation-necessary details only
4. Export evidence to incident response platform.

**Expected result:** Evidence collected and preserved with chain of custody.  
**Verification (evidence to capture):**
- [ ] Evidence collection log (who, what, when)
- [ ] Evidence stored in secure location
- [ ] Chain of custody documented

**If this fails, go to:** Escalation (Security forensics)

---

### Step 4: Escalate to Security and coordinate response
**Objective:** Hand off to Security team with complete context and coordinate ongoing response.  
**Risk level:** High  
**Action type:** Read-only / Write (Approval required? Yes)

1. Escalate to Security On-Call via approved channel (PagerDuty/incident platform).
2. Provide incident summary:
   - incident type and indicators
   - scope and impact assessment
   - containment actions taken
   - evidence collected (location/reference)
3. Coordinate ongoing response:
   - follow Security team guidance
   - assist with additional containment if needed
   - support user communication (if approved)
4. Update incident ticket with Security team reference and status.

**Expected result:** Security team engaged; coordinated response in progress.  
**Verification (evidence to capture):**
- [ ] Security escalation confirmed (incident ID)
- [ ] Handoff documented in ticket
- [ ] Ongoing coordination status

**If this fails, go to:** Escalation (Security leadership)

---

## Expected Citations (for RAG + evaluation)
- [ ] Section: “Safety Notes (human-in-loop triggers)”
- [ ] Section: “Step 2: Immediate containment (isolate affected systems)”
- [ ] Keyword anchors: “containment”, “evidence collection”, “chain of custody”

---

## Troubleshooting

### Common Issues

#### Issue: Containment action fails (account cannot be locked)
**Symptoms:**
- Account lock/disable command fails or account remains active.

**Likely causes:**
- IAM system issue, account in use by critical process, permission error

**Resolution:**
1. Verify IAM system status.
2. Try alternate containment method (session revocation, network isolation).
3. Escalate to Security + IAM team immediately.

**If unresolved:** Escalate to Security + IAM; consider network-level containment.

---

#### Issue: Evidence collection blocked or logs unavailable
**Symptoms:**
- Required logs are not accessible or have been purged.

**Likely causes:**
- Log retention policy, access permissions, system outage

**Resolution:**
1. Document what evidence is available vs missing.
2. Collect alternative evidence (endpoint logs, network logs).
3. Escalate to Security with evidence gap documentation.

**If unresolved:** Escalate to Security; document evidence limitations.

---

### Diagnostics (copy/paste friendly)
**Redact:** full IPs, user identifiers, device serials, and any investigation-sensitive details before pasting into tickets/logs.
```bash
# Read-only diagnostic commands (redact output)
# - Check active sessions (event IDs only)
# - Query audit logs (timestamp ranges, event types)
# - Verify account status (enabled/disabled)
```

---

## Escalation

## Severity guidance: P0 / P1 / P2
- **P0:** Confirmed active compromise with data exfiltration risk
- **P1:** Suspected compromise with potential impact
- **P2:** Low-confidence indicators requiring investigation

**Escalate immediately if:**
- Confirmed active compromise
- Executive/VIP account involved
- Production systems at risk
- Data exfiltration suspected

## Escalation path:
**Level 1:** Security Operations queue — 15 min  
**Level 2:** Security Incident Response Team escalation — 15 min  
**On-call:** Security On-Call — (link redacted)

## Information to provide when escalating:
- Incident ticket ID
- Incident type and indicators (redacted)
- Scope and impact assessment
- Containment actions taken
- Evidence collected (location/reference)
- Affected systems/users (redacted)

---

## Related Knowledge

## Related runbooks:
- `rb-001-access-grant-policy-procedure.md`
- `rb-003-admin-account-reset-procedure.md`

## Policies / docs:
- Security Incident Response Policy — (internal link redacted)
- Evidence Collection & Chain of Custody — (internal link redacted)

## Tools & dashboards:
- Incident response platform — (internal link redacted)
- Security audit logs — (internal link redacted)

## KB articles:
- “How to preserve evidence chain of custody” — (internal link redacted)

---

## Owner & Review

**Primary owner:** Security Operations (SECOPS)  
**Backup owner:** IT Operations  
**Review cycle:** Quarterly  
**Last updated:** 2026-01-28  
**Updated by:** Copilot Scaffold Generator  
**Change summary:** Initial restricted security incident escalation runbook creation.
