# Runbook: [Title]

## Summary (TL;DR)
**What this fixes:**  
**Best next action:**  
**If you only have 2 minutes:** Do Step 1 → Verify → If fails, Escalate.

---

## Purpose
Brief description of what this runbook addresses and when it should be used.

**Use this runbook when:**
- [ ] Condition 1
- [ ] Condition 2

**Do NOT use this runbook when:**
- [ ] Condition A (link to alternative runbook)

---

## Scope
Define the boundaries of this runbook.

- **Systems covered:**  
- **Scenarios included:**  
- **Scenarios excluded:**  

---

## Access & Data Classification (for ACL + governance)
- **Required role:** Employee / Engineer / IT Admin  
- **Permission tier:** public / internal / restricted  
- **Sensitive data involved:** PII / credentials / tokens / secrets? (Yes/No)  
- **Logging rule:** Never log secrets, tokens, passwords, or full PII. Redact before sharing.
- **Redaction notes (if any):** What must be masked in responses/logs (e.g., user emails, device IDs, IPs).

---

## Intake Fields Needed (maps to ticket intake / issue template)
- **Ticket/Request ID:**  
- **Request type:** VPN / MFA / Access / Onboarding / Other  
- **Urgency:** Low / Medium / High / Critical  
- **Requester identity:** (user id / email / GitHub username)  
- **Requester role (claimed):** Employee / Engineer / IT Admin  
- **Environment:** prod / staging / internal  
- **Error message(s):**  
- **Time started (timestamp):**  
- **What changed recently?** (optional)  
- **What has been tried already?** (optional)  

---

## Preconditions / Prerequisites
Things that must be in place before executing this runbook:

- **Tools required:**  
- **Credentials required:**  
- **Network requirements:** VPN required? (Yes/No)  
- **Dependencies healthy:** (Yes/No)  

---

## Safety Notes (human-in-loop triggers)
**Stop and escalate if:**
- [ ] The action is irreversible or destructive
- [ ] The action changes access/permissions (IAM, groups, roles)
- [ ] The action impacts production availability or security posture
- [ ] The requester’s identity cannot be verified
- [ ] You suspect a security incident

**Approval required for:**
- [ ] Any write action affecting production systems
- [ ] Granting access / role changes / privileged operations
- [ ] Any action involving restricted systems or restricted data

---

## Steps

### Step 1: [Action Name]
**Objective:** What this step accomplishes  
**Risk level:** Low / Medium / High  
**Action type:** Read-only / Write (Approval required? Yes/No)

1. Action item 1  
2. Action item 2  
3. Action item 3  

**Expected result:** What you should see if this step succeeds

**Verification (evidence to capture):**
- [ ] Status check result / screenshot / log snippet
- [ ] Before/after comparison (if applicable)

**If this fails, go to:** Step 2 / Troubleshooting / Escalation

---

## Expected Citations (for RAG + evaluation)
List the sections or keywords that should be cited when answering questions with this runbook:
- [ ] Section: “...” (e.g., Scope / Preconditions / Step 1)
- [ ] Keyword anchors: “...”

---

## Troubleshooting

### Common Issues

#### Issue: [Error Message / Symptom]
**Symptoms:**
- What you observe

**Likely causes:**
- Cause 1
- Cause 2

**Resolution:**
1. Check X
2. Verify Y
3. Execute Z

**If unresolved:** Escalate (see Escalation section)

---

### Diagnostics (copy/paste friendly)
```bash
# Useful commands for troubleshooting (optional)
# 1) Check status
# 2) View logs
# 3) Verify configuration
```

---

# Escalation

## Severity guidance: P0 / P1 / P2

**Escalate immediately if:**
- Production outage or widespread service degradation
- Security incident suspected (credentials, phishing, unusual access)
- Data loss or corruption risk
- SLA breach imminent

## Escalation path:

**Level 1:** [Team/Contact] — [Slack/Email] — [Response SLA]

**Level 2:** [Team/Contact] — [Slack/Email] — [Response SLA]

**On-call:** [PagerDuty/OpsGenie] — [Rotation link]

## Information to provide when escalating:

- Ticket/incident ID
- Steps attempted + outcomes
- Exact error messages and relevant logs (redacted)
- Impact assessment (users affected, severity)
- Timeline of events

---

# Related Knowledge

## Related runbooks:
- [Link to related runbook 1]
- [Link to related runbook 2]

## Policies / docs:
- [Link to policy]

## Tools & dashboards:
- [Link to dashboard/admin console]

## KB articles:
- [Link to KB article]

---

# Owner & Review

**Primary owner:** [Name/Team]

**Backup owner:** [Name/Team]

**Review cycle:** Monthly / Quarterly

**Last updated:** YYYY-MM-DD

**Updated by:** [Name]

**Change summary:** [Brief description]