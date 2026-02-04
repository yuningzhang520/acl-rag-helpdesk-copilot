# Runbook: Access Request Basics (How to request access, approval expectations, SLA)

## Summary (TL;DR)
**What this fixes:** Sets expectations for requesting access safely (who approves, what info is needed, and typical timelines).  
**Best next action:** Submit an access request with business justification, correct resource, and approver; avoid urgent “just add me” messages.  
**If you only have 2 minutes:** Provide resource + access level + business reason + manager/owner approver + deadline.

---

## Purpose
Help employees request access to tools and resources in a consistent, auditable way aligned to least privilege and approvals.

**Use this runbook when:**
- [ ] You need access to an application, shared folder, repository, or mailing list
- [ ] You need access changes due to role change or new project

**Do NOT use this runbook when:**
- [ ] You suspect an access issue due to compromise (escalate to Security)
- [ ] You need emergency “break-glass” access for an incident (follow incident process via IT)

---

## Scope
- **Systems covered:** Access request process and information requirements.
- **Scenarios included:** New access, access removal, time-bounded access requests, setting expectations for approvals/SLA.
- **Scenarios excluded:** Performing access grants directly (handled by IT/resource owners).

---

## Access & Data Classification (for ACL + governance)
- **Readable by (who may cite):** Employee / Engineer / IT Admin  
- **Executable by (who may perform steps):** Employees (submit requests) + Helpdesk (route/triage)  
- **Note:** The ACL **permission tier** controls what content may be retrieved/cited. Execution permission is separate and enforced by tools/approvals.  
- **Permission tier:** public  
- **Sensitive data involved:** Yes (access controls, potentially confidential resource names).  
- **Logging rule:** Never log secrets, tokens, passwords, or full PII. Redact before sharing.
- **Redaction notes (if any):** Avoid posting sensitive resource names or screenshots in public channels; use the ticketing system.

---

## Intake Fields Needed (maps to ticket intake / issue template)
- **Ticket/Request ID:** (if opening/updating a ticket)  
- **Request type:** Access  
- **Urgency:** Low / Medium / High / Critical  
- **Requester identity:** (your work email / username)  
- **Requester role (claimed):** Employee / Engineer / IT Admin  
- **Environment:** home / office / travel / unknown (optional)  
- **Error message(s):** (if this is an “access denied” issue)  
- **Time started (timestamp):**  
- **What changed recently?** (new team/project, role change)  
- **What has been tried already?** (request portal, manager approval)

Additionally required access request details:
- **Resource requested:** (app name / group name / folder name — keep high-level if sensitive)
- **Access level requested:** read / write / admin (choose the minimum)
- **Business justification:** what work requires this access
- **Approver:** manager and/or resource owner (who can approve)
- **Duration:** permanent / time-bounded (end date if time-bounded)
- **Deadline:** if time-sensitive, include date/time and rationale

---

## Preconditions / Prerequisites
- **Tools required:** Access request portal or IT ticketing system.
- **Credentials required:** Your standard work login.
- **Network requirements:** VPN required? (No)
- **Dependencies healthy:** Not required (request submission only)

---

## Safety Notes (human-in-loop triggers)
**Stop and escalate if:**
- [ ] The request seems suspicious or unrelated to job role
- [ ] You are pressured to bypass approvals (“just add me now”)
- [ ] You suspect compromised credentials or unauthorized access attempts

**Approval required for:**
- [ ] Any access grant (handled by resource owners/IT with approvals)
- [ ] Any elevated permissions (write/admin) or time-bounded exceptions

---

## Steps

### Step 1: Identify the resource and minimum access needed
**Objective:** Request least-privilege access to the correct resource.  
**Risk level:** Low  
**Action type:** Read-only / Write (Approval required? No)

1. Confirm the exact resource (app/folder/group) you need.
2. Choose the minimum access level that meets your needs:
   - read if you only need to view
   - write if you need to edit/upload
   - admin only when explicitly required (rare)
3. Determine who owns/approves the resource (manager or resource owner).

**Expected result:** You know what to request and who can approve.  
**Verification (evidence to capture):**
- [ ] Resource identified
- [ ] Access level selected (least privilege)

**If this fails, go to:** Troubleshooting

---

### Decision points (routing mini-rail)
- **If approver is unknown:** Submit request with best-known context and note “approver unknown”; helpdesk can route.
- **If access is denied after approval:** Sign out/in to refresh session; wait propagation window if communicated; if still failing, escalate.
- **If many users are locked out of a core tool:** Set urgency to **Critical** → Escalation (**P0**).

---

### Step 2: Submit the access request with complete details
**Objective:** Create an actionable, auditable request that can be approved quickly.  
**Risk level:** Medium  
**Action type:** Write (Approval required? No)

1. Submit via the approved access request method (portal/ticket).
2. Include:
   - resource
   - access level
   - business justification
   - approver
   - duration (if time-bounded)
   - deadline (if any) and reason
3. Attach safe evidence only (e.g., screenshot of “access denied” with redactions).

**Expected result:** Request is routed to the right approver with sufficient detail.  
**Verification (evidence to capture):**
- [ ] Ticket includes all required fields
- [ ] Approver specified

**If this fails, go to:** Escalation

---

### Step 3: Track approval and set expectations (SLA)
**Objective:** Understand typical timelines and how to follow up appropriately.  
**Risk level:** Low  
**Action type:** Read-only / Write (Approval required? No)

1. Monitor the request status in the portal/ticket.
2. If approval is pending:
   - ensure the approver was correctly identified
   - add clarification in the ticket if requested
3. Avoid requesting bypasses; escalations should be tied to business impact and deadlines.

**Expected result:** Approval progresses or is correctly routed.  
**Verification (evidence to capture):**
- [ ] Status updated or approver engaged

**If this fails, go to:** Escalation

---

## Expected Citations (for RAG + evaluation)
- [ ] Section: “Intake Fields Needed”
- [ ] Section: “Safety Notes (human-in-loop triggers)”
- [ ] Keyword anchors: “least privilege”, “approver”, “SLA”

---

## Troubleshooting

### Common Issues

#### Issue: “I don’t know who the approver is”
**Symptoms:**
- You can’t identify the resource owner or the request keeps being reassigned.

**Likely causes:**
- Resource ownership unclear or not documented

**Resolution:**
1. Ask your manager who owns the resource.
2. Submit the request with best-known context and note “approver unknown”.
3. Helpdesk can route to the correct owner based on resource name.

**If unresolved:** Escalate (see Escalation).

---

#### Issue: “I have access but still see ‘access denied’”
**Symptoms:**
- You were approved but the app/folder still blocks you.

**Likely causes:**
- Propagation delay, cached session, wrong account signed in

**Resolution:**
1. Sign out and back in to refresh your session.
2. Wait a reasonable propagation window (if communicated) and retry.
3. Confirm you are signed in with the correct work account.

**If unresolved:** Update the ticket with the time of approval and the current error.

---

### Diagnostics (copy/paste friendly)
```bash
# Redact identifiers before pasting into tickets/logs.
# Provide safe evidence:
# - resource name (high-level if sensitive)
# - access level requested
# - approval timestamp (if approved)
# - exact “access denied” error text
```

---

## Escalation

## Severity guidance: P0 / P1 / P2
- **P0:** Widespread authorization outage affecting many users
- **P1:** Time-sensitive business-critical access needed with approved justification
- **P2:** Standard access request

**Escalate immediately if:**
- Many users are locked out of a core tool (possible outage)
- Suspicious access patterns suggest compromise
- SLA breach imminent for critical business operations

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
- Resource and access level requested
- Business justification and deadline
- Approver and approval status
- Error messages (redacted) and timestamps

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
**Backup owner:** Access Administration  
**Review cycle:** Quarterly  
**Last updated:** 2026-01-28  
**Updated by:** Copilot Scaffold Generator  
**Change summary:** Normalized to match canonical schema and public escalation style.
