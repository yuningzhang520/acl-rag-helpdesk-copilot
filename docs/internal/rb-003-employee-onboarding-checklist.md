# Runbook: Employee Onboarding Checklist (IT Helpdesk)

## Summary (TL;DR)
**What this fixes:** Ensures new hires have the right accounts, devices, and baseline access on Day 1.  
**Best next action:** Validate start date + manager approvals → create accounts → provision device → assign baseline groups → confirm MFA → verify critical apps → close ticket with evidence.  
**If you only have 2 minutes:** Confirm start date + manager → ensure SSO account + email + MFA ready → confirm laptop shipment/pickup → assign baseline access group.

---

## Purpose
Provide a repeatable onboarding process that minimizes Day 1 friction while enforcing access controls and auditability.

**Use this runbook when:**
- [ ] A new employee is starting and needs standard IT setup
- [ ] A contractor requires time-bounded access and device provisioning

**Do NOT use this runbook when:**
- [ ] The request is for elevated/privileged access (follow access request + approvals)
- [ ] The new hire is joining a restricted program requiring special onboarding (use program-specific runbook)

---

## Scope
- **Systems covered:** HR feed/onboarding system, SSO/IdP, email, endpoint management/MDM, ticketing.
- **Scenarios included:** Standard employee onboarding and contractor onboarding (time-bounded).
- **Scenarios excluded:** IT Admin privileges, production access, security tooling access (separate approvals).

---

## Access & Data Classification (for ACL + governance)
- **Readable by (who may cite):** Employee / Engineer / IT Admin  
- **Executable by (who may perform steps):** Helpdesk (standard onboarding actions) + Engineer / IT Admin (privileged/admin actions)  
- **Note:** The ACL **permission tier** controls what content may be retrieved/cited. Execution permission is separate and enforced by tools/approvals.  
- **Permission tier:** internal  
- **Sensitive data involved:** Yes (PII such as name, email, start date, device identifiers)  
- **Logging rule:** Never log secrets, tokens, passwords, or full PII. Redact before sharing.
- **Redaction notes (if any):** Mask personal phone/address; avoid storing passport/ID copies in tickets.

---

## Intake Fields Needed (maps to ticket intake / issue template)
- **Ticket/Request ID:**  
- **Request type:** Onboarding  
- **Urgency:** Low / Medium / High / Critical  
- **Requester identity:** Manager/HR partner  
- **Requester role (claimed):** Employee / Engineer / IT Admin  
- **Environment:** internal  
- **Time started (timestamp):**  
- **What changed recently?** (start date change, location change)  
- **What has been tried already?** (N/A)

Additionally required onboarding data:
- **New hire full name:**  
- **New hire corporate email (if known):**  
- **Start date + timezone:**  
- **Manager:**  
- **Department/team + cost center (if applicable):**  
- **Location (office/remote + country):**  
- **Device preference/requirements:** (Mac/Windows, accessories)  
- **Contract end date (if contractor):**

---

## Preconditions / Prerequisites
- **Tools required:** HR onboarding system, IdP admin (role-based), email admin (role-based), MDM/endpoint console, asset inventory.
- **Credentials required:** Onboarding operator permissions (no privileged admin unless necessary).
- **Network requirements:** VPN required? (Yes for some admin consoles, if applicable)
- **Dependencies healthy:** HR feed current; IdP/email/MDM operational.

---

## Safety Notes (human-in-loop triggers)
**Stop and escalate if:**
- [ ] The requestor identity cannot be verified (e.g., external email)
- [ ] Start date is in the future and the request is for early access without HR approval
- [ ] The request includes privileged access (prod, security, finance) without proper approvals

**Approval required for:**
- [ ] Any access outside baseline onboarding groups
- [ ] Any access to restricted systems or restricted data

---

## Steps

### Step 1: Validate request and approvals
**Objective:** Ensure onboarding is authorized and the data is complete.  
**Risk level:** Medium  
**Action type:** Read-only / Write (Approval required? Yes for non-standard access)

1. Verify requester (manager/HR) via directory and approved channels.
2. Confirm start date, location, and employment type (employee vs contractor).
3. Confirm baseline access package vs non-standard requests.
4. If contractor, confirm end date and time-bounded access requirement.

**Expected result:** Authorized onboarding request with complete data.  
**Verification (evidence to capture):**
- [ ] Ticket contains requester verification note and approvals (if any)

**If this fails, go to:** Escalation

---

### Decision points (routing mini-rail)
- **If start date/manager details don’t match HR system:** Pause and route to **HR/People Ops** for correction.
- **If this includes non-standard or privileged access requests:** Route to **Access Request** process (do not grant ad hoc).
- **If IdP/email/MDM shows platform outage impacting multiple onboardings:** Escalate as **P0/P1** depending on scope.

---

### Step 2: Provision identity and email
**Objective:** Ensure the user can authenticate and communicate on Day 1.  
**Risk level:** High  
**Action type:** Write (Approval required? Yes)

1. Ensure HR record exists and triggers account creation workflow (preferred).
2. If manual creation is required:
   - Create IdP account following naming standards.
   - Provision email mailbox and set baseline security settings.
3. Require MFA enrollment at first login (per policy).

**Expected result:** User has an active IdP account + email ready.  
**Verification (evidence to capture):**
- [ ] Account created/provisioned timestamp (no passwords)
- [ ] MFA required flag set

**If this fails, go to:** Troubleshooting

---

### Step 3: Device provisioning (laptop + MDM)
**Objective:** Provide a managed device with required security posture.  
**Risk level:** High  
**Action type:** Write (Approval required? Yes)

1. Assign an asset from inventory or trigger purchase request (if none available).
2. Enroll device in MDM/endpoint management.
3. Apply baseline policies:
   - disk encryption
   - screen lock
   - EDR/AV
   - OS update baseline
4. Arrange delivery/pickup and record tracking details (avoid home address in ticket if possible).

**Expected result:** Device is assigned, enrolled, and compliant.  
**Verification (evidence to capture):**
- [ ] Asset tag and enrollment status (redacted)
- [ ] Compliance status screenshot/text

**If this fails, go to:** Troubleshooting / Escalation (Endpoint)

---

### Step 4: Baseline access and application provisioning
**Objective:** Provide standard access required for productivity.  
**Risk level:** Medium  
**Action type:** Write (Approval required? Yes)

1. Assign baseline groups (examples):
   - All-Employees
   - VPN-Users (if standard)
   - Email-Users
2. Provision standard apps (examples):
   - chat/collaboration
   - password manager
   - VPN client
3. For department-specific access, ensure approvals are recorded before assignment.

**Expected result:** User has baseline groups and apps.  
**Verification (evidence to capture):**
- [ ] Group assignment list (redacted)

**If this fails, go to:** Troubleshooting / Escalation (Identity)

---

### Step 5: Day 1 validation and closure
**Objective:** Confirm onboarding success and close the request with evidence.  
**Risk level:** Low  
**Action type:** Read-only / Write (Approval required? No)

1. Confirm user can:
   - sign in to SSO
   - enroll MFA
   - access email and chat
   - connect to VPN (if required)
2. Update ticket with a completion checklist and any remaining follow-ups.

**Expected result:** Onboarding completed; user productive on Day 1.  
**Verification (evidence to capture):**
- [ ] Completion checklist attached in ticket

**If this fails, go to:** Troubleshooting / Escalation

---

## Expected Citations (for RAG + evaluation)
- [ ] Section: “Safety Notes (human-in-loop triggers)”
- [ ] Section: “Step 2: Provision identity and email”
- [ ] Keyword anchors: “baseline groups”, “time-bounded”, “MDM compliant”

---

## Troubleshooting

### Common Issues

#### Issue: Account exists but user cannot sign in
**Symptoms:**
- “Invalid credentials” or “account disabled” at login.

**Likely causes:**
- HR feed not synced, account not activated, password reset needed

**Resolution:**
1. Verify account status in IdP; activate if pending.
2. Trigger password reset process (never set/communicate passwords).
3. Confirm MFA enrollment requirement.

**If unresolved:** Escalate to Identity.

---

#### Issue: Device not enrolling in MDM
**Symptoms:**
- Enrollment fails; device shows non-compliant.

**Likely causes:**
- Network restrictions, wrong enrollment profile, OS mismatch

**Resolution:**
1. Verify enrollment profile and prerequisites.
2. Re-attempt enrollment on a trusted network.
3. Re-image device if required (per endpoint policy).

**If unresolved:** Escalate to Endpoint.

---

### Diagnostics (copy/paste friendly)
**Redact:** full names, personal addresses, device serials/asset tags, and any identifiers not required for troubleshooting before pasting into tickets/logs.
```bash
# Keep diagnostics high-level; avoid exposing device serials or secrets in tickets.
# Useful evidence:
# - IdP account status
# - MDM enrollment state
# - Compliance state
```

---

## Escalation

## Severity guidance: P0 / P1 / P2
- **P0:** Many new hires blocked (systemic onboarding outage)
- **P1:** Executive/VIP onboarding blocked on Day 1
- **P2:** Single onboarding blocked; workaround possible

**Escalate immediately if:**
- Identity system outage blocks onboarding at scale
- Security policy prevents device compliance unexpectedly

## Escalation path:
**Level 1:** IT Helpdesk Ops — `#it-helpdesk` — 30 min  
**Level 2:** Identity Operations — `#identity-ops` — 30 min  
**On-call:** Endpoint On-Call — PagerDuty “ENDPOINT” — (link redacted)

## Information to provide when escalating:
- Ticket ID + start date/timezone
- Account status evidence (redacted)
- Device enrollment/compliance evidence (redacted)
- Approvals for any non-standard access

---

## Related Knowledge

## Related runbooks:
- `rb-001-vpn-troubleshooting.md`
- `rb-002-mfa-reset-sop.md`
- `rb-004-access-request-shared-drive.md`

## Policies / docs:
- New Hire Onboarding Policy — (internal link redacted)
- Device Management Policy — (internal link redacted)

## Tools & dashboards:
- HR onboarding dashboard — (internal link redacted)
- MDM console — (internal link redacted)

## KB articles:
- “First-day setup checklist” — (internal link redacted)

---

## Owner & Review

**Primary owner:** IT Helpdesk Operations  
**Backup owner:** Endpoint Management  
**Review cycle:** Quarterly  
**Last updated:** 2026-01-28  
**Updated by:** Copilot Scaffold Generator  
**Change summary:** Initial onboarding checklist runbook creation.

