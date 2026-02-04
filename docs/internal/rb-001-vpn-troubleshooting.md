# Runbook: VPN Connectivity Troubleshooting (Employee/Engineer)

## Summary (TL;DR)
**What this fixes:** Common VPN connection failures (auth errors, no traffic, DNS issues, split-tunnel problems).  
**Best next action:** Confirm identity → collect client + network details → validate account status → test connectivity → remediate DNS/routes.  
**If you only have 2 minutes:** Verify user identity → check service status → have user sign out/in + reboot VPN client → capture logs → escalate if multiple users impacted.

---

## Purpose
Restore VPN connectivity for internal users while preserving security controls and ensuring changes are auditable.

**Use this runbook when:**
- [ ] User cannot connect to VPN (authentication/handshake failures)
- [ ] VPN connects but internal resources are unreachable
- [ ] VPN connects but DNS resolution fails for internal domains

**Do NOT use this runbook when:**
- [ ] The request is to grant new VPN entitlement (use access request workflow and approvals)
- [ ] A security incident is suspected (escalate to Security immediately)

---

## Scope
- **Systems covered:** Corporate VPN client, VPN gateway/service, internal DNS over VPN.
- **Scenarios included:** User-facing troubleshooting, account validation, non-destructive client remediation.
- **Scenarios excluded:** Gateway configuration changes, firewall rule changes (IT Admin only; change-managed).

---

## Access & Data Classification (for ACL + governance)
- **Readable by (who may cite):** Employee / Engineer / IT Admin  
- **Executable by (who may perform steps):** Helpdesk (read-only) + Engineer / IT Admin (write/privileged)  
- **Note:** The ACL **permission tier** controls what content may be retrieved/cited. Execution permission is separate and enforced by tools/approvals.  
- **Permission tier:** internal  
- **Sensitive data involved:** Yes (PII, device identifiers, network info; never collect passwords/OTP)  
- **Logging rule:** Never log secrets, tokens, passwords, or full PII. Redact before sharing.
- **Redaction notes (if any):** Mask user email (e.g., `a***@corp`), device serials, IPs, log lines containing tokens.

---

## Intake Fields Needed (maps to ticket intake / issue template)
- **Ticket/Request ID:**  
- **Request type:** VPN  
- **Urgency:** Low / Medium / High / Critical  
- **Requester identity:**  
- **Requester role (claimed):** Employee / Engineer / IT Admin  
- **Environment:** internal  
- **Error message(s):** (copy exact message)  
- **Time started (timestamp):**  
- **What changed recently?** (new device, password reset, travel, hotel Wi‑Fi, OS update)  
- **What has been tried already?** (reboot, reinstall, different network)

---

## Preconditions / Prerequisites
- **Tools required:** VPN admin console (read-only), status page, endpoint management (read-only), ticketing system.
- **Credentials required:** Helpdesk read-only; elevated changes only via IT Admin.
- **Network requirements:** VPN required? (No—this is about VPN access)
- **Dependencies healthy:** Check VPN gateway status + identity provider status.

---

## Safety Notes (human-in-loop triggers)
**Stop and escalate if:**
- [ ] Multiple users report failures (possible outage)
- [ ] Signs of account compromise (unexpected MFA prompts, unusual geo, repeated lockouts)

**Approval required for:**
- [ ] Resetting VPN entitlement / adding to VPN access group
- [ ] Changing gateway policies, routes, DNS settings

---

## Steps

### Step 1: Triage and identity verification
**Objective:** Confirm request legitimacy and gather minimum viable diagnostics.  
**Risk level:** Low  
**Action type:** Read-only / Write (Approval required? No)

1. Verify requester identity per support policy (SSO profile, ticket channel, callback if needed).
2. Confirm impact scope: single user vs multiple users vs region-specific.
3. Collect:
   - VPN client name/version
   - OS + version
   - Network type (home/corp/coffee shop/hotel/mobile hotspot)
   - Exact error text + timestamp
4. Check service status dashboard for VPN + IdP.

**Expected result:** Clear classification: auth issue vs network/DNS vs outage.  
**Verification (evidence to capture):**
- [ ] Screenshot or text of error message
- [ ] Status page snapshot

**If this fails, go to:** Escalation

---

### Decision points (routing mini-rail)
- **If status page shows an outage:** Escalate as **P0** (see Escalation).
- **If auth reason codes show locked/disabled:** Follow **Identity path** (Troubleshooting → Auth issues; escalate to Identity).
- **If VPN connects but no internal access:** Follow **DNS/routes path** (Step 4; Troubleshooting → DNS/route issues).

---

### Step 2: Authentication and account status checks
**Objective:** Determine whether the failure is identity/entitlement related.  
**Risk level:** Low  
**Action type:** Read-only / Write (Approval required? No)

1. Confirm the user can sign in to SSO (separate from VPN).
2. In VPN admin console, check:
   - account enabled/not locked
   - assigned VPN entitlement (group/role)
   - recent auth failures (reason codes)
3. If repeated lockouts are present, verify with user for recent password changes and MFA prompts.

**Expected result:** Account is enabled and entitled; auth failures have a known cause.  
**Verification (evidence to capture):**
- [ ] Console event reason code (redacted)

**If this fails, go to:** Troubleshooting → Auth issues / Escalation

---

### Step 3: Client-side remediation (non-destructive)
**Objective:** Fix common client issues without changing permissions.  
**Risk level:** Low  
**Action type:** Read-only / Write (Approval required? No)

1. Ask user to sign out of VPN client, then sign back in.
2. Restart VPN client service (or reboot if permitted).
3. Try alternate network (mobile hotspot) to rule out ISP/Wi‑Fi restrictions.
4. If client is outdated, upgrade to the latest approved version.

**Expected result:** VPN successfully connects and internal resources reachable.  
**Verification (evidence to capture):**
- [ ] “Connected” state screenshot
- [ ] Ping/HTTP check to internal endpoint (no sensitive URLs)

**If this fails, go to:** Step 4

---

### Step 4: Post-connect connectivity (DNS/routes)
**Objective:** Resolve “connected but cannot reach internal” issues.  
**Risk level:** Medium  
**Action type:** Read-only / Write (Approval required? No)

1. Confirm the client received an internal IP and DNS servers.
2. Test internal DNS resolution (e.g., `internal.example`), and a known internal ping target.
3. Check split tunnel configuration indicators (client UI).
4. Capture VPN client logs for the failing session (redact tokens).

**Expected result:** DNS and routes work; traffic flows through VPN as expected.  
**Verification (evidence to capture):**
- [ ] IP/DNS info (redacted)
- [ ] Relevant log snippets (redacted)

**If this fails, go to:** Troubleshooting → DNS/route issues / Escalation

---

## Expected Citations (for RAG + evaluation)
- [ ] Section: “Safety Notes (human-in-loop triggers)”
- [ ] Section: “Step 2: Authentication and account status checks”
- [ ] Keyword anchors: “entitlement”, “reason code”, “split tunnel”, “DNS”

---

## Troubleshooting

### Common Issues

#### Issue: “Authentication failed” / “MFA required” loop
**Symptoms:**
- User sees repeated login prompts or MFA challenges; connection never completes.

**Likely causes:**
- Expired session, password recently changed, device time skew, IdP outage

**Resolution:**
1. Confirm IdP status; ensure device time is set to automatic.
2. Have user sign out/in to SSO in a browser first.
3. Clear VPN client cached session (per vendor guidance) and retry.

**If unresolved:** Escalate to Identity team.

---

#### Issue: “Connected” but internal sites don’t load
**Symptoms:**
- VPN shows connected; internal names don’t resolve or traffic times out.

**Likely causes:**
- DNS not applied, split tunnel conflict, local firewall/EDR interference

**Resolution:**
1. Verify DNS servers pushed by VPN; flush DNS cache; reconnect.
2. Test on alternate network; temporarily disable conflicting VPN/Proxy tools (per policy).
3. Collect logs and route table evidence (redacted) and escalate.

**If unresolved:** Escalate to Network team.

---

### Diagnostics (copy/paste friendly)
**Redact:** full IPs, MAC addresses, and hostnames before pasting into tickets/logs. Capture only the minimum necessary evidence.
```bash
# macOS
scutil --dns | head -n 50
netstat -rn | head -n 50

# Windows (PowerShell)
ipconfig /all
route print
nslookup internal.example
```

---

## Escalation

## Severity guidance: P0 / P1 / P2
- **P0:** VPN outage affecting many users / critical business operations blocked
- **P1:** Multiple users affected in a region or a key team blocked
- **P2:** Single user impacted; workaround available

**Escalate immediately if:**
- Production outage or widespread VPN disruption
- Security incident suspected (phishing, unusual geo, repeated lockouts)

## Escalation path:
**Level 1:** IT Helpdesk Lead — `#it-helpdesk` — 30 min  
**Level 2:** Network Engineering — `#netops` — 30 min  
**On-call:** Network On-Call — PagerDuty “NETOPS” — (link redacted)

## Information to provide when escalating:
- Ticket/incident ID
- User/role (redacted) + region
- Error message + timestamp
- Steps attempted + results
- Evidence: status page, auth reason codes, DNS/route outputs (redacted)

---

## Related Knowledge

## Related runbooks:
- `rb-002-mfa-reset-sop.md`

## Policies / docs:
- VPN Access Policy — (internal link redacted)

## Tools & dashboards:
- VPN status dashboard — (internal link redacted)
- IdP status dashboard — (internal link redacted)

## KB articles:
- “VPN client reinstall procedure” — (internal link redacted)

---

## Owner & Review

**Primary owner:** Network Engineering (NETOPS)  
**Backup owner:** IT Helpdesk Operations  
**Review cycle:** Quarterly  
**Last updated:** 2026-01-28  
**Updated by:** Copilot Scaffold Generator  
**Change summary:** Initial internal runbook creation.

