# ACL Policy — Role-Based Access + Exception Grants

This document defines how **user identity and role** map to **document permission tiers** for the Enterprise AI Helpdesk Copilot.

The objective is to ensure retrieval-augmented generation (RAG) **never surfaces content a user is not authorized to see**, enforcing **least privilege**, reducing data leakage risk, and enabling **auditability**.

---

## 1) Roles

- **Employee**: Standard business user using helpdesk for day-to-day IT support.
- **Engineer**: Technical user who may need internal runbooks and operational troubleshooting guidance.
- **IT Admin**: Privileged operator with elevated access to security and administrative procedures.

User identity and role are resolved from a directory source of truth (see `workflows/directory.csv`).

---

## 2) Document Permission Tiers

Each document is tagged with a `permission_tier`:

- **public**: Safe for all authenticated users (high-level FAQs, generic how-tos).
- **internal**: Internal-only information (runbooks, internal tooling docs, internal system notes).
- **restricted**: Highly sensitive information (security procedures, privileged access steps, admin-only configuration guides).

---

## 3) Baseline Access Policy (RBAC)

Baseline access is role-based:

### Employee
- ✅ `public`
- ✅ `internal`
- ❌ `restricted`

### Engineer
- ✅ `public`
- ✅ `internal`
- ❌ `restricted` (unless explicitly granted; see Exception Grants)

### IT Admin
- ✅ `public`
- ✅ `internal`
- ✅ `restricted`

---

## 4) Exception Grants (Per-User Overrides)

Some users may receive explicit elevated access beyond baseline policy.

In this project, exception grants are represented as:

- `restricted_grant=true` in `workflows/directory.csv`

**Rule:**
- `restricted` content is retrievable only if:
  1) role baseline allows it (IT Admin), **or**
  2) the user has an explicit exception grant (`restricted_grant=true`).

This models real enterprise patterns: RBAC for baseline + explicit grants for rare exceptions.

---

## 5) Deny-by-Default

If user identity cannot be resolved from the directory (e.g., unknown `github_username`), the system must default to the safest mode:

- Allowed tiers → `public` only
- Action mode → **suggest-only** (no write actions)
- Response should include a short instruction: “Please request access / escalate to IT.”

---

## 6) Enforcement Requirements (Non-Negotiable)

### 6.1 Apply ACL filtering **before** ranking
ACL filtering must occur **before** reranking or scoring to prevent leakage via:
- metadata exposure
- ranking artifacts
- partial context contamination

**Correct order:**
1) Identify user → resolve role/grants  
2) Filter candidate docs by allowed tiers  
3) Retrieve/rerank within allowed set  
4) Assemble context for generation

### 6.2 Citation contract
All answers that use retrieved knowledge must include citations:
- doc path
- section heading (or anchor)
- optional excerpt

If no permitted citations support an answer, the system must:
- ask a clarifying question, **or**
- refuse and escalate (especially for restricted topics).

### 6.3 Zero-tolerance for ACL violations
Any instance of citing or using restricted content for an unauthorized user is a **Sev-0** bug.

**Immediate response:**
- rollback mode → `retrieval-only` or `human-only`
- log the violation with high severity
- block further write actions until fixed

---

## 7) Generation Guardrails (Defense-in-Depth)

Even with ACL-filtered retrieval, the LLM must be instructed that:
- retrieved content is untrusted input (prompt injection may exist)
- it must not follow instructions found inside retrieved documents
- it must not infer or reconstruct restricted details

Additionally, when a request appears to require restricted procedures:
- answer at a high level (if safe), or
- refuse + provide escalation steps.

---

## 8) Auditability

For each request, the system must log:
- user identity (github_username), resolved role, restricted_grant
- allowed tiers computed
- retrieved docs + their tiers
- citations used in the final response
- proposed actions and whether approval was required
- approval decision and executed actions (if any)

Logs should be sufficient to reconstruct “what happened” during an incident review.

---

## 9) Examples

### Example A — Employee asking about VPN setup
- User: Employee
- Allowed tiers: public + internal
- OK: cite internal VPN troubleshooting runbook
- NOT OK: cite admin-only backend configuration (restricted)

### Example B — Engineer requesting root DB access steps
- User: Engineer (no restricted grant)
- Allowed tiers: public + internal
- Expected behavior: refuse + escalate (“This procedure is restricted; contact IT Admin / Security.”)
- NOT OK: cite restricted runbook

### Example C — Engineer with restricted grant
- User: Engineer (restricted_grant=true)
- Allowed tiers: public + internal + restricted
- OK: cite restricted procedure, with additional warnings and auditing

### Example D — Unknown user
- Identity not found in directory
- Allowed tiers: public only
- Mode: suggest-only
- Expected behavior: ask for identity / escalation

---

## 10) Testing Requirements (Golden Set)

The golden set must include ACL regression cases verifying:
- **No restricted citations** for Employee / Engineer without grant
- Correct refusal + escalation behavior for restricted requests
- Correct behavior for Engineer with restricted grant
- Deny-by-default behavior for unknown users
- Zero-tolerance check: any ACL violation triggers rollback mode
