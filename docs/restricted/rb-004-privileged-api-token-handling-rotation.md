# Runbook: Privileged API Token Handling & Rotation (Creation, Storage, Rotation, Revocation; Logging)

## Summary (TL;DR)
**What this fixes:** Secure lifecycle management of privileged API tokens (creation, secure storage, rotation, revocation) with full audit logging.  
**Best next action:** Verify need → obtain approvals → create token → store securely → document rotation schedule → rotate per policy → revoke when expired/compromised.  
**If you only have 2 minutes:** Verify business need + approvals → create token → store in approved secret manager → set rotation schedule → log creation.

---

## Purpose
Provide a controlled, auditable process for managing privileged API tokens throughout their lifecycle (creation, storage, rotation, revocation) with security controls and compliance logging.

**Use this runbook when:**
- [ ] New privileged API token is needed for system integration
- [ ] Existing token requires rotation per policy
- [ ] Token is compromised or suspected compromised (revocation)
- [ ] Token is no longer needed (revocation)

**Do NOT use this runbook when:**
- [ ] Standard user API keys (use standard access request process)
- [ ] Service account provisioning (separate process)
- [ ] Token creation lacks business justification or approvals

---

## Scope
- **Systems covered:** API token management system, secret management/vault, audit logging, service integration platforms.
- **Scenarios included:** Token creation, secure storage, scheduled rotation, emergency rotation, revocation.
- **Scenarios excluded:** User API keys, OAuth tokens (separate process), bulk token operations (change management).

---

## Access & Data Classification (for ACL + governance)
- **Readable by (who may cite):** Employee / Engineer / IT Admin  
- **Executable by (who may perform steps):** Helpdesk (read-only) + Engineer / IT Admin (write/privileged)  
- **Note:** The ACL **permission tier** controls what content may be retrieved/cited. Execution permission is separate and enforced by tools/approvals.  
- **Permission tier:** restricted  
- **Sensitive data involved:** Yes (API tokens, service credentials, integration endpoints). Never log token values, secrets, or full credentials.  
- **Logging rule:** Never log secrets, tokens, passwords, or full PII. Redact before sharing.
- **Redaction notes (if any):** Never log token values; log only token identifiers, creation/rotation timestamps, and metadata (service, scope, expiration).

---

## Intake Fields Needed (maps to ticket intake / issue template)
- **Ticket/Request ID:**  
- **Request type:** Other  
- **Urgency:** Low / Medium / High / Critical  
- **Requester identity:**  
- **Requester role (claimed):** Engineer / IT Admin  
- **Target system:** prod / staging / internal tooling (optional)  
- **Error message(s):** (if token-related error)  
- **Time started (timestamp):**  
- **What changed recently?** (new integration, service change, rotation due)  
- **What has been tried already?** (existing token check, service status)

Additionally required:
- **Service/integration name:**  
- **Token scope/permissions:** (read / write / admin)  
- **Business justification:**  
- **Rotation schedule:** (30 days / 90 days / per policy)  
- **Approver(s):** manager / service owner / Security  
- **Token identifier (if rotation/revocation):**

---

## Preconditions / Prerequisites
- **Tools required:** API token management system, secret management/vault, audit logging system, ticketing system.
- **Credentials required:** Token admin role (privileged) for creation/rotation/revocation; read-only for triage.
- **Network requirements:** VPN required? (Yes for admin consoles)
- **Dependencies healthy:** Token management system operational; secret vault accessible.

**Change window (if applicable):**
- Token creation: business hours preferred; no change window required.
- Token rotation: schedule during low-traffic window if possible; coordinate with service owner.
- Emergency revocation: immediate execution; no change window.

---

## Safety Notes (human-in-loop triggers)
**Stop and escalate if:**
- [ ] Business justification is unclear or insufficient
- [ ] Approvals are missing (manager + service owner + Security for privileged tokens)
- [ ] Token scope exceeds business need (over-privileged)
- [ ] Token is suspected compromised (immediate revocation required)

**Approval required for:**
- [ ] Any privileged token creation (manager + service owner + Security approval)
- [ ] Token scope changes (re-approval required)
- [ ] Rotation schedule exceptions (Security approval)
- [ ] Emergency revocation (post-action approval if not Security-initiated)

**Two-person rule:**
- [ ] Requester cannot self-approve; executor cannot be the approver; privileged token operations require dual control.

**Audit requirements:**
- [ ] Log token creation: requester identity, approver identities, service name, scope, creation timestamp, expiration, storage location (vault reference).
- [ ] Log token rotation: old token identifier (revoked), new token identifier, rotation timestamp, reason.
- [ ] Log token revocation: token identifier, revocation reason, revocation timestamp, operator identity.
- [ ] Never log token values; log only metadata and identifiers.
- [ ] Retain audit logs per compliance policy (e.g., 1–7 years).

**Rollback/containment:**
- [ ] If token was created incorrectly, revoke immediately and create new token with correct scope.
- [ ] If token is compromised, revoke immediately and rotate all related tokens.

---

## Steps

### Step 1: Business justification and approval verification
**Objective:** Confirm token is needed and required approvals are present.  
**Risk level:** Medium  
**Action type:** Read-only / Write (Approval required? Yes)

1. Verify business justification:
   - service/integration requiring token
   - why token is needed (automation, integration, system access)
   - expected usage pattern
2. Verify required approvals:
   - manager approval (for requester)
   - service owner approval (for service/integration)
   - Security approval (for privileged tokens)
3. Validate least-privilege scope:
   - requested scope matches business need
   - no broader permissions than necessary
   - time-bounded if appropriate

**Expected result:** Business justification confirmed and approvals obtained.  
**Verification (evidence to capture):**
- [ ] Business justification documented
- [ ] Approver identities verified
- [ ] Approval timestamps recorded
- [ ] Scope validated (least privilege)

**If this fails, go to:** Escalation

---

### Decision points (routing mini-rail)
- **If approvals are missing:** Pause and route to approvers; do not create token.
- **If scope exceeds business need:** Request scope reduction; do not create over-privileged token.
- **If token is for rotation:** Verify old token exists and rotation schedule; proceed to rotation step.
- **If token is suspected compromised:** Immediate revocation (Step 4) → Escalation (**P0**).

---

### Step 2: Create token with secure storage
**Objective:** Generate privileged API token and store securely in approved vault.  
**Risk level:** High  
**Action type:** Write (Approval required? Yes)

1. In API token management system, create token:
   - set scope/permissions (least privilege)
   - set expiration (per policy, typically 90 days)
   - set rotation schedule (per policy, typically 30 days)
   - generate token value
2. Store token securely:
   - store in approved secret management/vault system
   - never store in code, config files, or tickets
   - restrict vault access to authorized users only
3. Log token creation:
   - requester identity (redacted)
   - approver identities (redacted)
   - service name
   - scope/permissions
   - creation timestamp
   - expiration date
   - vault storage location (reference only)
   - token identifier (not value)

**Expected result:** Token created and stored securely; audit log entry created.  
**Verification (evidence to capture):**
- [ ] Token creation event ID
- [ ] Token stored in vault (reference)
- [ ] Audit log entry created

**If this fails, go to:** Troubleshooting / Escalation

---

### Step 3: Rotate token per schedule
**Objective:** Rotate token before expiration or per policy schedule.  
**Risk level:** High  
**Action type:** Write (Approval required? Yes)

1. Verify rotation trigger:
   - scheduled rotation due (per policy)
   - token approaching expiration
   - security policy requires rotation
2. Create new token (follow Step 2 creation process).
3. Update service/integration with new token:
   - coordinate with service owner
   - update configuration in approved system
   - verify service continues functioning
4. Revoke old token (follow Step 4 revocation process).
5. Log rotation:
   - old token identifier (revoked)
   - new token identifier
   - rotation timestamp
   - reason (scheduled / expiration / security)

**Expected result:** Token rotated; old token revoked; service updated; audit logged.  
**Verification (evidence to capture):**
- [ ] New token created and stored
- [ ] Old token revoked
- [ ] Service updated and verified
- [ ] Rotation logged

**If this fails, go to:** Troubleshooting / Escalation

---

### Step 4: Revoke token (expired, compromised, or no longer needed)
**Objective:** Securely revoke token and update dependent systems.  
**Risk level:** Medium  
**Action type:** Write (Approval required? Yes)

1. Verify revocation reason:
   - token expired
   - token compromised or suspected compromised
   - token no longer needed
   - security policy requires revocation
2. Revoke token in API token management system:
   - set token to revoked state
   - invalidate all active sessions using token
3. Update dependent systems:
   - remove token from service configurations
   - update integrations to use new token (if rotated) or remove integration
4. Log revocation:
   - token identifier
   - revocation reason
   - revocation timestamp
   - operator identity
   - dependent systems updated

**Expected result:** Token revoked; dependent systems updated; audit logged.  
**Verification (evidence to capture):**
- [ ] Token revocation confirmed
- [ ] Dependent systems updated
- [ ] Revocation logged

**If this fails, go to:** Escalation

---

## Expected Citations (for RAG + evaluation)
- [ ] Section: “Safety Notes (human-in-loop triggers)”
- [ ] Section: “Step 2: Create token with secure storage”
- [ ] Keyword anchors: “secure storage”, “rotation schedule”, “audit log”

---

## Troubleshooting

### Common Issues

#### Issue: Token creation fails or token not accessible
**Symptoms:**
- Token creation command fails or token cannot be retrieved from vault.

**Likely causes:**
- Token management system issue, vault access permissions, network connectivity

**Resolution:**
1. Verify token management system status.
2. Verify vault access permissions and connectivity.
3. Retry creation; if still failing, escalate to platform team.

**If unresolved:** Escalate to Platform Engineering + Security.

---

#### Issue: Token rotation breaks service integration
**Symptoms:**
- After rotation, service/integration fails with authentication errors.

**Likely causes:**
- New token not updated in service configuration, old token still cached, scope mismatch

**Resolution:**
1. Verify new token is stored in vault and accessible.
2. Verify service configuration updated with new token.
3. Clear service caches and retry.
4. If scope mismatch, verify new token has correct permissions.

**If unresolved:** Escalate to Service Owner + Platform Engineering.

---

### Diagnostics (copy/paste friendly)
**Redact:** token identifiers, vault references, service endpoints, and any sensitive metadata before pasting into tickets/logs.
```bash
# Read-only diagnostic commands (redact output)
# - Check token expiration status (metadata only)
# - Verify vault connectivity (status only)
# - Query audit logs (event IDs only)
```

---

## Escalation

## Severity guidance: P0 / P1 / P2
- **P0:** Token compromise confirmed or suspected
- **P1:** Critical service integration broken due to token issue
- **P2:** Standard token creation/rotation

**Escalate immediately if:**
- Token compromise suspected or confirmed
- Critical service integration broken
- Token management system outage

## Escalation path:
**Level 1:** Platform Engineering queue — 30 min  
**Level 2:** Security Operations escalation — 15 min  
**On-call:** Security On-Call — (link redacted)

## Information to provide when escalating:
- Ticket/incident ID
- Service/integration name
- Token identifier (redacted)
- Issue description (creation/rotation/revocation failure)
- Error messages (redacted)
- Audit event IDs (redacted)

---

## Related Knowledge

## Related runbooks:
- `rb-001-access-grant-policy-procedure.md`
- `rb-003-admin-account-reset-procedure.md`

## Policies / docs:
- API Token Management Policy — (internal link redacted)
- Secret Management Standard — (internal link redacted)

## Tools & dashboards:
- Token management system — (internal link redacted)
- Secret vault — (internal link redacted)

## KB articles:
- “Secure token storage best practices” — (internal link redacted)

---

## Owner & Review

**Primary owner:** Platform Engineering  
**Backup owner:** Security Operations (SECOPS)  
**Review cycle:** Quarterly  
**Last updated:** 2026-01-28  
**Updated by:** Copilot Scaffold Generator  
**Change summary:** Initial restricted privileged API token handling runbook creation.
