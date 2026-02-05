#!/usr/bin/env python3
"""
MVP Retrieval + Citations + ACL Pipeline

Demo commands demonstrating ACL enforcement:

Example A (Employee - should NOT see restricted docs):
  python -m src.run --user_id u001 --issue "How do I grant access to a shared drive?"

Example B (IT Admin - CAN see restricted docs):
  python -m src.run --user_id u005 --issue "How do I grant access to a shared drive?"

The same issue text should retrieve different documents based on user role.
"""

import argparse
import csv
import json
import os
import urllib.request
import urllib.error
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Role → allowed permission tiers mapping
ROLE_TIER_MAP = {
    "Employee": ["public", "internal"],
    "Engineer": ["public", "internal"],
    "IT Admin": ["public", "internal", "restricted"],
}

# Triage category keywords
CATEGORY_KEYWORDS = {
    "VPN": ["vpn"],
    "MFA": ["mfa", "2fa", "multi-factor"],
    # Access: include common enterprise phrasing to reduce cat:Other
    "Onboarding": ["onboarding", "new hire"],
    "Access": ["access", "permission", "grant", "iam", "role", "group", "shared drive", "drive", "folder", "sharepoint", "onedrive", "google drive"],
}

# Priority keywords
PRIORITY_KEYWORDS = {
    "Critical": ["outage", "down", "many users", "widespread"],
    "High": [
        "urgent", "blocked", "critical", "asap", "immediately",
        "cannot sign in", "can't sign in", "unable to sign in",
        "cannot login", "can't login", "unable to login",
        "lost my phone", "lost phone", "mfa reset",
        "looping", "stuck", "locked out",
        "security incident", "incident response", "security investigation",
    ],
    "Medium": [
        "soon", "deadline soon",
        "can't access", "cannot access", "unable to access",
        "no access",
        "doesn't work",
        "no invite", "missing invite",
        "cannot reach", "can't reach",
        "cannot connect", "can't connect", "unable to connect",
        "authentication failed", "auth failed",
        "disconnects", "keeps disconnecting", "reconnecting", "reconnect",
        "time-limited", "temporary", "contractor", "one week"
    ],
}

def load_directory(csv_path: str) -> Tuple[Dict[str, Dict], Dict[str, Dict]]:
    """
    Load user directory. Returns (by_user_id, by_github_username).
    by_github_username[login] = {role, user_id} for approval validation.
    """
    directory = {}
    by_github = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            user_id = row["user_id"]
            role = row["role"]
            github_username = (row.get("github_username") or "").strip()
            restricted_grant = row.get("restricted_grant", "false").lower() == "true"
            allowed_tiers = ROLE_TIER_MAP.get(role, []).copy()
            if restricted_grant and "restricted" not in allowed_tiers:
                allowed_tiers.append("restricted")
            directory[user_id] = {
                "role": role,
                "display_name": row.get("display_name", ""),
                "allowed_tiers": allowed_tiers,
                "github_username": github_username,
            }
            if github_username:
                by_github[github_username.lower()] = {"role": role, "user_id": user_id}
    return directory, by_github


def resolve_user(user_id: str, directory: Dict, role_override: Optional[str] = None) -> Dict:
    """Resolve user_id to role and allowed tiers."""
    if user_id in directory:
        return directory[user_id]
    
    if role_override:
        allowed_tiers = ROLE_TIER_MAP.get(role_override, [])
        return {
            "role": role_override,
            "display_name": "",
            "allowed_tiers": allowed_tiers,
        }
    
    return None


def parse_markdown_sections(file_path: Path, tier: str) -> List[Dict]:
    """Parse markdown file into sections by headings."""
    sections = []
    
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return sections  # Skip files that can't be read
    
    lines = content.split("\n")
    current_heading = None
    current_content = []
    
    for line in lines:
        # Match markdown headings (#, ##, ###)
        heading_match = re.match(r"^(#{1,3})\s+(.+)$", line.strip())
        
        if heading_match:
            # Save previous section if exists
            if current_heading is not None and current_content:
                section_text = "\n".join(current_content).strip()
                if section_text:
                    sections.append({
                        "doc_path": str(file_path),
                        "tier": tier,
                        "heading": current_heading.strip(),
                        "content": section_text,
                        "anchor": f"#{slugify_heading(current_heading)}",
                    })
            
            # Start new section
            current_heading = heading_match.group(2).strip()
            current_content = []
        else:
            # Accumulate content for current section
            if current_heading is not None:
                current_content.append(line)
    
    # Save last section
    if current_heading is not None and current_content:
        section_text = "\n".join(current_content).strip()
        if section_text:
            sections.append({
                "doc_path": str(file_path),
                "tier": tier,
                "heading": current_heading.strip(),
                "content": section_text,
                "anchor": f"#{slugify_heading(current_heading)}",
            })
    
    return sections


def load_allowed_documents(allowed_tiers: List[str], docs_root: Path) -> List[Dict]:
    """Load and parse all markdown files from allowed tiers."""
    all_sections = []
    
    for tier in allowed_tiers:
        tier_dir = docs_root / tier
        if not tier_dir.exists():
            continue
        
        for md_file in tier_dir.glob("*.md"):
            # Skip README files
            if md_file.name.lower() == "readme.md":
                continue
            
            sections = parse_markdown_sections(md_file, tier)
            all_sections.extend(sections)
    
    return all_sections


def tokenize(text: str) -> List[str]:
    """Simple tokenization: lowercase, split on whitespace and punctuation."""
    # Remove markdown formatting
    text = re.sub(r"[*_`#\[\]()]", " ", text)
    # Split and lowercase
    tokens = re.findall(r"\b\w+\b", text.lower())
    return tokens

def slugify_heading(text: str) -> str:
    """Create a stable markdown-style anchor slug from a heading."""
    s = text.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)          # remove punctuation
    s = re.sub(r"\s+", "-", s)             # spaces to hyphens
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s

def confidence_from_max_score(max_score: float, k: float = 12.0) -> float:
    """
    Map retrieval score to [0,1) with a simple saturating function:
    conf = max_score / (max_score + k)
    - If max_score is 0 -> 0
    - As max_score grows -> approaches 1
    """
    if max_score <= 0:
        return 0.0
    return float(max_score / (max_score + k))

def score_section(section: Dict, issue_tokens: List[str]) -> float:
    """Score section vs issue using TF overlap + heading/filename bonus."""
    issue_counter = Counter(issue_tokens)

    body_tokens = tokenize(section.get("content", ""))
    head_tokens = tokenize(section.get("heading", "") + " " + Path(section.get("doc_path", "")).name)

    body_c = Counter(body_tokens)
    head_c = Counter(head_tokens)

    # Base score:content term-frequency overlap（logic from original code）
    score = 0.0
    for t, w in issue_counter.items():
        score += w * body_c.get(t, 0)

    # Bonus: title/filename hit weighting (small bonus, not replacing content)
    # Key: use min(1, head_c[t]) to prevent score from being inflated by repeated words in title
    HEAD_WEIGHT = 2.0  # 1.5~3.0 is fine; use 2.0 for now
    for t, w in issue_counter.items():
        if head_c.get(t, 0) > 0:
            score += HEAD_WEIGHT * w * 1.0

    return score

def retrieve_top_k(sections: List[Dict], issue_text: str, top_k: int) -> List[Dict]:
    """Retrieve top_k sections based on keyword scoring."""
    issue_tokens = tokenize(issue_text)
    
    # Score all sections
    scored_sections = []
    for section in sections:
        score = score_section(section, issue_tokens)
        scored_sections.append({
            **section,
            "score": score,
        })
    
    # Sort by score descending
    scored_sections.sort(key=lambda x: x["score"], reverse=True)
    
    # Return top_k
    top_sections = scored_sections[:top_k]
    
    # If all scores are zero, use fallback (first sections by doc order)
    if all(s["score"] == 0 for s in top_sections) and len(scored_sections) > top_k:
        # Fallback: return first sections from different docs
        seen_docs = set()
        fallback = []
        for s in scored_sections:
            if len(fallback) >= top_k:
                break
            doc = s["doc_path"]
            if doc not in seen_docs:
                fallback.append(s)
                seen_docs.add(doc)
        if fallback:
            top_sections = fallback
    
    return top_sections


def triage_issue(issue_text: str) -> Dict[str, str]:
    """Simple deterministic triage based on keywords."""
    issue_lower = issue_text.lower()
    
    # Determine category
    category = "Other"
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in issue_lower for kw in keywords):
            category = cat
            break
    
    # Determine priority
    priority = "Low"
    for prio, keywords in PRIORITY_KEYWORDS.items():
        if any(kw in issue_lower for kw in keywords):
            priority = prio
            break
    
    return {"category": category, "priority": priority}


def build_proposed_actions_struct(
    triage: Dict[str, str],
    proposed_actions: List[str],
    mode: str,
) -> Dict:
    """
    risk_level: L2 only when category == "Access"; High/Critical alone do not trigger L2.
    Else L1 if writeback planned; else needs_approval=false.
    L1 -> approval_role Engineer (or IT Admin). L2 -> approval_role IT Admin.
    Employee approvals are invalid (enforced at validation time).
    """
    category = triage.get("category", "Other")
    priority = triage.get("priority", "Low")
    writeback_planned = mode == "github" and bool(proposed_actions)

    # L2 only when category == "Access"; High/Critical alone do not trigger L2
    if category == "Access":
        risk_level = "L2"
        approval_role = "IT Admin"
        needs_approval = True
    elif writeback_planned:
        risk_level = "L1"
        approval_role = "Engineer"
        needs_approval = True
    else:
        risk_level = "L1"  # placeholder when no approval needed
        approval_role = "Engineer"
        needs_approval = False

    # Enterprise label format: cat:<Category>, prio:<Priority>, status:pending-approval | status:approved
    labels_to_add = []
    if mode == "github":
        labels_to_add = [f"cat:{category}", f"prio:{priority}", "status:pending-approval"]
    assignees = []  # allowlisted; could be config-driven later
    comment_summary = "Proposed: " + "; ".join(proposed_actions[:3]) if proposed_actions else "No actions"

    return {
        "risk_level": risk_level,
        "needs_approval": needs_approval,
        "approval_role": approval_role,
        "labels_to_add": labels_to_add,
        "assignees": assignees,
        "comment_summary": comment_summary,
    }


def _parse_proposed_plan_struct_from_comment(body: str) -> Optional[Dict]:
    """Extract proposed_actions_struct from a Proposed Plan comment body (```json ... ```)."""
    if not body:
        return None
    match = re.search(r"```json\s*([\s\S]*?)```", body)
    if not match:
        return None
    try:
        return json.loads(match.group(1).strip())
    except (json.JSONDecodeError, TypeError):
        return None


def _find_latest_proposed_plan_and_approve(
    comments: List[Dict],
) -> Tuple[Optional[Dict], Optional[Dict], Optional[Dict]]:
    """
    Find the most recent comment containing 'Proposed Plan (PENDING APPROVAL)',
    then the latest APPROVE comment posted *after* it.
    comments are assumed in ascending order (oldest first).
    Returns (plan_comment, parsed_struct, approve_comment_after_plan).
    """
    plan_comment = None
    plan_index = -1
    for i in range(len(comments) - 1, -1, -1):
        if "Proposed Plan (PENDING APPROVAL)" in (comments[i].get("body") or ""):
            plan_comment = comments[i]
            plan_index = i
            break
    if plan_comment is None:
        return None, None, None
    struct = _parse_proposed_plan_struct_from_comment(plan_comment.get("body") or "")
    approve_comment = None
    for i in range(len(comments) - 1, plan_index, -1):
        body = (comments[i].get("body") or "")
        if re.match(r"^\s*APPROVE\s*$", body, flags=re.I):
            approve_comment = comments[i]
            break
    return plan_comment, struct, approve_comment


def generate_answer_mock(context_sections: List[Dict], issue_text: str) -> Dict:
    """Generate mock answer with citations (public-safe) based on retrieved sections."""
    if not context_sections:
        return {
            "answer": "I don't have enough information in the accessible runbooks to answer this. Please provide more details or escalate via your organization’s official IT support process.",
            "citations": [],
            "confidence": 0.0,
            "proposed_actions": ["Escalate (see Escalation)"],
        }

    answer_parts = []
    citations = []

    # Use max_score to compute confidence
    max_score = max((s.get("score", 0) for s in context_sections), default=0)
    conf = confidence_from_max_score(max_score, k=12.0)
    if max_score == 0:
        conf = 0.25  # fallback confidence: low but non-zero

    for section in context_sections:
        doc_path = section["doc_path"]
        doc_name = Path(doc_path).name
        heading = section["heading"]
        anchor = section.get("anchor", "")

        # Keep answer concise: short excerpt only
        excerpt = section["content"].strip()
        if len(excerpt) > 220:
            excerpt = excerpt[:220].rstrip() + "..."

        answer_parts.append(f"- From **{doc_name}** {anchor} (**{heading}**): {excerpt}")

        citations.append({
            "doc": doc_path,
            "section": heading,
            "anchor": anchor,
            "tier": section["tier"],
        })

    answer = "Here’s what the runbooks say based on your question:\n" + "\n".join(answer_parts)

    proposed_actions = []
    txt = issue_text.lower()
    if "vpn" in txt:
        proposed_actions.append("Follow the VPN runbook steps")
    if "mfa" in txt or "2fa" in txt:
        proposed_actions.append("Follow the password/MFA guidance runbook")
    if "access" in txt or "permission" in txt or "grant" in txt:
        proposed_actions.append("Use the official access request process and include approvals")

    if not proposed_actions:
        proposed_actions = ["Review the cited sections and follow the steps"]

    return {
        "answer": answer,
        "citations": citations,
        "confidence": conf,
        "proposed_actions": proposed_actions,
    }

def call_openai_chat(api_key: str, model: str, messages: List[Dict], max_tokens: int = 500, temperature: float = 0.3) -> str:
    """
    Minimal OpenAI Chat Completions call using stdlib urllib (no external deps).
    Returns assistant text.
    """
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            parsed = json.loads(body)
            return parsed["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"OpenAI HTTPError {e.code}: {err}") from e
    except Exception as e:
        raise RuntimeError(f"OpenAI request failed: {str(e)}") from e

def generate_answer_openai(context_sections: List[Dict], issue_text: str) -> Dict:
    """
    If OPENAI_API_KEY is not set:
      - Return retrieval+citations answer (mock) with a clear note (no API call).
    If OPENAI_API_KEY is set:
      - Call OpenAI and return a real LLM-generated answer grounded in retrieved sections.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    base = generate_answer_mock(context_sections, issue_text)

    # No key: still demo retrieval + citations
    if not api_key:
        base["answer"] = (
            "Note: OPENAI_API_KEY is not configured, so no LLM call was made.\n"
            "Answer below is generated from retrieved runbook sections (ACL-filtered) with citations.\n\n"
            + base["answer"]
        )
        return base

    # Key exists: call OpenAI for real
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Build compact context for the LLM
    context_parts = []
    for s in context_sections:
        doc_name = Path(s["doc_path"]).name
        heading = s["heading"]
        anchor = s.get("anchor", "")
        content = (s["content"] or "").strip()
        if len(content) > 600:
            content = content[:600].rstrip() + "..."
        context_parts.append(
            f"Document: {doc_name}\nSection: {heading}\nAnchor: {anchor}\nContent:\n{content}"
        )
    context = "\n\n---\n\n".join(context_parts)

    prompt = (
        "You are an IT helpdesk assistant.\n"
        "Answer the user's question using ONLY the provided runbook context.\n"
        "If the context is insufficient, say so and suggest escalation via official IT support.\n\n"
        "When referencing information, cite the source as (Document + Anchor).\n\n"
        f"Context:\n{context}\n\n"
        f"User question:\n{issue_text}\n"
    )

    try:
        answer_text = call_openai_chat(
            api_key=api_key,
            model=model,
            messages=[
                {"role": "system", "content": "You answer using only provided context and include citations (Document + Anchor)."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            temperature=0.3,
        )

        # Keep citations as the retrieved set (MVP). (Later you can parse and filter.)
        citations = base["citations"]

        # Confidence: combine retrieval confidence + small bump for successful LLM call
        conf = min(1.0, base["confidence"] + 0.10)

        proposed_actions = base["proposed_actions"]
        if "escalat" in answer_text.lower():
            # Keep public-safe wording
            if "Escalate (see Escalation)" not in proposed_actions:
                proposed_actions = proposed_actions + ["Escalate (see Escalation)"]

        return {
            "answer": answer_text,
            "citations": citations,
            "confidence": conf,
            "proposed_actions": proposed_actions,
        }

    except Exception as e:
        # If API fails, fall back to retrieval answer (still useful for demo)
        base["answer"] = (
            f"Note: OPENAI_API_KEY is configured, but the LLM call failed ({str(e)}).\n"
            "Falling back to retrieval+citations answer.\n\n"
            + base["answer"]
        )
        return base

def main():
    parser = argparse.ArgumentParser(description="MVP Retrieval + Citations + ACL Pipeline")
    parser.add_argument("--user_id", required=True, help="User ID from directory.csv")
    parser.add_argument("--issue", required=True, help="Issue/question text")
    parser.add_argument("--top_k", type=int, default=3, help="Number of sections to retrieve (default: 3)")
    parser.add_argument("--mode", choices=["mock", "openai", "github"], default="mock", help="Answer generation mode (default: mock)")
    parser.add_argument("--role_override", help="Override role if user_id not found (Employee/Engineer/IT Admin)")
    parser.add_argument("--repo", help="GitHub repo owner/name (required for --mode github)")
    parser.add_argument("--issue_number", type=int, help="GitHub issue number (required for --mode github)")
    parser.add_argument("--github_stage", choices=["propose", "execute"], default="propose", help="GitHub mode: propose = post plan only; execute = check approval and run allowlisted actions (default: propose)")
    args = parser.parse_args()
    import time as _time
    _start_audit = _time.perf_counter()

    if args.mode == "github" and (not args.repo or args.issue_number is None):
        error_output = {
            "answer": "Error: --repo and --issue_number are required when --mode github",
            "citations": [],
            "triage": {"category": "Other", "priority": "Low"},
            "retrieval_confidence": 0.0,
            "proposed_actions": [],
            "debug": {"error": "github_requires_repo_and_issue"},
        }
        print(json.dumps(error_output, indent=2))
        sys.exit(1)
    
    # Load directory
    repo_root = Path(__file__).parent.parent
    directory_path = repo_root / "workflows" / "directory.csv"
    
    if not directory_path.exists():
        error_output = {
            "answer": f"Error: Directory file not found at {directory_path}",
            "citations": [],
            "triage": {"category": "Other", "priority": "Low"},
            "retrieval_confidence": 0.0,
            "proposed_actions": ["Check directory.csv path"],
            "debug": {"error": "directory_not_found"},
        }
        print(json.dumps(error_output, indent=2))
        sys.exit(1)
    
    directory, by_github_username = load_directory(str(directory_path))

    # Resolve user
    user_info = resolve_user(args.user_id, directory, args.role_override)
    if not user_info:
        error_output = {
            "answer": f"Error: User ID '{args.user_id}' not found in directory",
            "citations": [],
            "triage": {"category": "Other", "priority": "Low"},
            "retrieval_confidence": 0.0,
            "proposed_actions": ["Provide valid user_id or use --role_override"],
            "debug": {"error": "user_not_found", "user_id": args.user_id},
        }
        print(json.dumps(error_output, indent=2))
        sys.exit(1)
    
    allowed_tiers = user_info["allowed_tiers"]
    role = user_info["role"]
    
    # Load allowed documents
    docs_root = repo_root / "docs"
    all_sections = load_allowed_documents(allowed_tiers, docs_root)
    
    # Retrieve top_k sections
    retrieved = retrieve_top_k(all_sections, args.issue, args.top_k)
    
    # Generate answer
    if args.mode == "mock":
        answer_data = generate_answer_mock(retrieved, args.issue)
    else:
        answer_data = generate_answer_openai(retrieved, args.issue)
    
    # Triage
    triage_data = triage_issue(args.issue)
    proposed_actions_struct = build_proposed_actions_struct(
        triage_data, answer_data["proposed_actions"], args.mode
    )

    # Build base output (triage_method=keyword, retrieval_confidence)
    debug_retrieved = [
        {"doc": s["doc_path"], "section": s["heading"], "tier": s["tier"], "score": s["score"]}
        for s in retrieved
    ]
    output = {
        "answer": answer_data["answer"],
        "citations": answer_data["citations"],
        "triage": triage_data,
        "triage_method": "keyword",
        "retrieval_confidence": answer_data["confidence"],
        "proposed_actions": answer_data["proposed_actions"],
        "proposed_actions_struct": proposed_actions_struct,
        "debug": {
            "user_id": args.user_id,
            "role": role,
            "allowed_tiers": allowed_tiers,
            "retrieved": debug_retrieved,
        },
    }

    # Audit log (every run)
    repo_root = Path(__file__).parent.parent
    audit_path = repo_root / "workflows" / "audit_log.jsonl"
    audit_record = {
        "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
        "repo": str(args.repo) if (args.mode == "github" and args.repo) else "",
        "issue_number": int(args.issue_number) if (args.mode == "github" and args.issue_number is not None) else 0,
        "requester_user_id": str(args.user_id),
        "requester_role": str(role),
        "allowed_tiers": list(allowed_tiers),
        "triage": {**triage_data, "method": "keyword"},
        "retrieval_confidence": float(output["retrieval_confidence"]),
        "retrieved": debug_retrieved,
        "citations": output["citations"],
        "proposed_actions_struct": proposed_actions_struct,
        "approval_status": "n/a",
        "approval_actor_login": "",
        "approval_actor_role": "",
        "executed_actions": [],
        "execution_result": "n/a",
        "latency_ms": 0,
        "estimated_cost": 0,
    }
    if args.mode == "github":
        from . import github_bot
        from . import audit
        # Audit: consistent string fields; executed_actions always a list
        audit_record["approval_status"] = "n/a"
        audit_record["approval_actor_login"] = ""
        audit_record["approval_actor_role"] = ""
        audit_record["executed_actions"] = []
        audit_record["execution_result"] = "n/a"
        try:
            stage = getattr(args, "github_stage", "propose") or "propose"
            if stage == "propose":
                # Only post Proposed Plan and exit (no approval checks)
                plan_body = (
                    "## Proposed Plan (PENDING APPROVAL)\n\n"
                    + answer_data["answer"]
                    + "\n\n### Proposed actions (struct)\n```json\n"
                    + json.dumps(proposed_actions_struct, indent=2)
                    + "\n```"
                )
                github_bot.post_comment(args.repo, args.issue_number, plan_body)

                labels = list(proposed_actions_struct.get("labels_to_add") or [])
                if labels:
                    github_bot.add_labels(args.repo, args.issue_number, labels, remove_prefixes=["status:"])

                audit_record["approval_status"] = "n/a"
                audit_record["execution_result"] = "propose_only"
                audit_record["executed_actions"] = []
            else:
                # execute: do NOT post plan; only consider APPROVE comments after latest Proposed Plan
                comments = github_bot.list_comments(args.repo, args.issue_number)
                plan_comment, parsed_struct, approve_comment = _find_latest_proposed_plan_and_approve(comments)
                # Enterprise-safe: only execute actions based on the last Proposed Plan.
                # If plan exists but JSON struct is missing/unparseable, do not execute.
                if plan_comment is not None and not parsed_struct:
                    audit_record["approval_status"] = "rejected"
                    audit_record["execution_result"] = "invalid_plan_format"
                    audit_record["executed_actions"] = []
                    latency_ms = round((_time.perf_counter() - _start_audit) * 1000)
                    audit_record["latency_ms"] = latency_ms
                    audit.append_jsonl(audit_record, path=audit_path, repo_root=repo_root)
                    print(json.dumps(output, indent=2))
                    return

                struct_for_execute = parsed_struct if parsed_struct else proposed_actions_struct
                approval_status = "pending"
                approval_actor_login = ""
                approval_actor_role = ""
                executed_actions = []
                execution_result = "skipped"
                if approve_comment:
                    approval_actor_login = (approve_comment.get("login") or "")
                    login_lower = approval_actor_login.lower()
                    approver_info = by_github_username.get(login_lower)
                    if approver_info:
                        approval_actor_role = approver_info.get("role") or ""
                        if approval_actor_role == "Employee":
                            approval_status = "rejected"
                            execution_result = "rejected_employee_approval"
                        elif struct_for_execute.get("needs_approval"):
                            if struct_for_execute.get("risk_level") == "L2":
                                if approval_actor_role != "IT Admin":
                                    approval_status = "rejected"
                                    execution_result = "rejected_l2_requires_it_admin"
                                else:
                                    approval_status = "approved"
                                    current_labels = github_bot.get_issue_labels(args.repo, args.issue_number)
                                    if "status:approved" in (current_labels or []):
                                        execution_result = "already_approved_skip"
                                        executed_actions = []
                                    else:
                                        base_labels = list(struct_for_execute.get("labels_to_add") or [])

                                        # Keep only non-status labels (e.g., cat:* and prio:*)
                                        labels = [lb for lb in base_labels if not str(lb).startswith("status:")]

                                        # Set final status
                                        labels.append("status:approved")

                                        if labels:
                                            github_bot.add_labels(
                                                args.repo,
                                                args.issue_number,
                                                labels,
                                                remove_prefixes=["status:"],  # remove any existing status:* before adding the new one
                                            )
                                            executed_actions.append("add_labels")

                                        if struct_for_execute.get("assignees"):
                                            github_bot.add_assignees(args.repo, args.issue_number, struct_for_execute["assignees"])
                                            executed_actions.append("add_assignees")
                                        github_bot.post_comment(args.repo, args.issue_number, "## Executed actions\n\n" + json.dumps({"executed": executed_actions}, indent=2))
                                        execution_result = "success"
                            else:
                                if approval_actor_role not in ("Engineer", "IT Admin"):
                                    approval_status = "rejected"
                                    execution_result = "rejected_l1_requires_engineer_or_admin"
                                else:
                                    approval_status = "approved"
                                    current_labels = github_bot.get_issue_labels(args.repo, args.issue_number)
                                    if "status:approved" in (current_labels or []):
                                        execution_result = "already_approved_skip"
                                        executed_actions = []
                                    else:
                                        base_labels = list(struct_for_execute.get("labels_to_add") or [])

                                        # Keep only non-status labels (e.g., cat:* and prio:*)
                                        labels = [lb for lb in base_labels if not str(lb).startswith("status:")]

                                        # Set final status
                                        labels.append("status:approved")

                                        if labels:
                                            github_bot.add_labels(
                                                args.repo,
                                                args.issue_number,
                                                labels,
                                                remove_prefixes=["status:"],  # remove any existing status:* before adding the new one
                                            )
                                            executed_actions.append("add_labels")

                                        if struct_for_execute.get("assignees"):
                                            github_bot.add_assignees(args.repo, args.issue_number, struct_for_execute["assignees"])
                                            executed_actions.append("add_assignees")
                                        github_bot.post_comment(args.repo, args.issue_number, "## Executed actions\n\n" + json.dumps({"executed": executed_actions}, indent=2))
                                        execution_result = "success"
                        else:
                            approval_status = "approved"
                            execution_result = "skipped"
                    else:
                        approval_status = "rejected"
                        execution_result = "approver_not_in_directory"
                else:
                    if plan_comment is None:
                        execution_result = "no_proposed_plan"
                audit_record["approval_status"] = approval_status
                audit_record["approval_actor_login"] = approval_actor_login or ""
                audit_record["approval_actor_role"] = approval_actor_role or ""
                audit_record["executed_actions"] = executed_actions if isinstance(executed_actions, list) else []
                audit_record["execution_result"] = execution_result
        except Exception as e:
            audit_record["execution_result"] = "error"
            audit_record["error"] = str(e)
            audit_record["executed_actions"] = []
            output["debug"]["github_error"] = str(e)
        latency_ms = round((_time.perf_counter() - _start_audit) * 1000)
        audit_record["latency_ms"] = latency_ms
        audit.append_jsonl(audit_record, path=audit_path, repo_root=repo_root)
    else:
        latency_ms = round((_time.perf_counter() - _start_audit) * 1000)
        audit_record["latency_ms"] = latency_ms
        audit_record["approval_status"] = "n/a"
        audit_record["execution_result"] = "n/a"
        from . import audit as _audit
        _audit.append_jsonl(audit_record, path=audit_path, repo_root=repo_root)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
