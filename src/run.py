#!/usr/bin/env python3
"""
MVP Retrieval + Citations + ACL Pipeline

Demo commands demonstrating ACL enforcement:

Example A (Employee - should NOT see restricted docs):
  python -m src.run --mode cli --user_id u001 --issue "How do I grant access to a shared drive?"

Example B (IT Admin - CAN see restricted docs):
  python -m src.run --mode cli --user_id u005 --issue "How do I grant access to a shared drive?"

Enable LLM intermediate compression (optional):
  python -m src.run --mode cli --llm_intermediate --user_id u001 --issue "How do I grant access to a shared drive?"

GitHub propose:
  python -m src.run --mode github --user_id u005 --repo owner/name --issue_number 12 --issue "How do I grant access to a shared drive?"

GitHub execute:
  python -m src.run --mode github --github_stage execute --user_id u005 --repo owner/name --issue_number 12 --issue "How do I grant access to a shared drive?"
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
from typing import Any

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
    category = triage.get("category", "Other")
    priority = triage.get("priority", "Low")

    # ✅ Only Access requires approval (L2). Everything else is triaged without approval.
    if category == "Access":
        risk_level = "L2"
        approval_role = "IT Admin"
        needs_approval = True
    else:
        risk_level = "L1"
        approval_role = "Engineer"
        needs_approval = False

    labels_to_add = []
    if mode == "github":
        status = "status:pending-approval" if needs_approval else "status:triaged"
        labels_to_add = [f"cat:{category}", f"prio:{priority}", status]

    assignees = []
    comment_summary = "Proposed: " + "; ".join((proposed_actions or [])[:3]) if proposed_actions else "No actions"

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

# ---------------------------
# Intermediate Builder (unified)
# ---------------------------

def build_source_catalog(context_sections: List[Dict]) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, str]]]:
    """
    sources: list for LLM prompt
    source_map: source_id -> {doc_name, anchor, heading}
    """
    sources: List[Dict[str, Any]] = []
    source_map: Dict[str, Dict[str, str]] = {}

    for i, s in enumerate(context_sections, start=1):
        source_id = f"S{i}"
        doc_name = Path(s["doc_path"]).name
        anchor = s.get("anchor", "")
        heading = s.get("heading", "")
        sources.append({
            "source_id": source_id,
            "doc_name": doc_name,
            "anchor": anchor,
            "heading": heading,
            "content": (s.get("content") or "").strip(),
        })
        source_map[source_id] = {"doc_name": doc_name, "anchor": anchor, "heading": heading}

    return sources, source_map

def _deterministic_intermediate(context_sections: List[Dict], issue_text: str) -> Dict[str, Any]:
    if not context_sections:
        return {
            "bullets": [
                {"text": "No accessible runbook sections were retrieved for this request.", "source_id": "N/A"},
                {"text": "Escalate through the official IT support process or provide more details.", "source_id": "N/A"},
            ],
            "clarifying_question": "What system/app and exact error message are you seeing?",
            "confidence_level": "Low",
            "confidence_reason": "No retrieved evidence available in accessible tiers.",
        }

    max_score = max((s.get("score", 0) for s in context_sections), default=0)
    conf_num = confidence_from_max_score(max_score, k=12.0)
    if max_score == 0:
        conf_num = 0.25

    if conf_num >= 0.70:
        conf_level = "High"
    elif conf_num >= 0.45:
        conf_level = "Medium"
    else:
        conf_level = "Low"

    sources, _ = build_source_catalog(context_sections)

    bullets: List[Dict[str, str]] = []
    for src in sources[:5]:
        excerpt = src["content"]
        if len(excerpt) > 180:
            excerpt = excerpt[:180].rstrip() + "..."
        bullets.append({
            "text": f'{src["doc_name"]} — {src["heading"]}: {excerpt}',
            "source_id": src["source_id"],
        })
        if len(bullets) >= 5:
            break

    while len(bullets) < 2:
        bullets.append({"text": "Review the retrieved runbook sections and follow the documented steps.", "source_id": "N/A"})

    issue_lower = issue_text.lower()
    needs_details = any(k in issue_lower for k in ["cannot", "can't", "unable", "not working", "doesn't work", "error"])
    clarifying = ""
    if needs_details:
        clarifying = "Which system/app is this for, and what is the exact error message (copy/paste if possible)?"

    return {
        "bullets": bullets[:5],
        "clarifying_question": clarifying,
        "confidence_level": conf_level,
        "confidence_reason": f"Derived from retrieval max_score={max_score} (confidence={conf_num:.2f}).",
        "_retrieval_confidence_num": conf_num,
    }

def _validate_intermediate(obj: Any, source_map: Dict[str, Dict[str, str]]) -> Tuple[bool, str]:
    if not isinstance(obj, dict):
        return False, "not_a_dict"

    for k in ["bullets", "clarifying_question", "confidence_level", "confidence_reason"]:
        if k not in obj:
            return False, f"missing_field:{k}"

    bullets = obj.get("bullets")
    if not isinstance(bullets, list) or not (2 <= len(bullets) <= 5):
        return False, "bullets_count_out_of_range"

    for b in bullets:
        if not isinstance(b, dict):
            return False, "bullet_not_object"
        text = b.get("text")
        sid = b.get("source_id")
        if not isinstance(text, str) or not text.strip():
            return False, "bullet_text_invalid"
        if not isinstance(sid, str) or not sid.strip():
            return False, "bullet_source_id_invalid"
        if sid != "N/A" and sid not in source_map:
            return False, "bullet_source_id_not_in_sources"

    cq = obj.get("clarifying_question")
    if not isinstance(cq, str):
        return False, "clarifying_question_not_string"
    if cq and len(cq) > 240:
        return False, "clarifying_question_too_long"

    cl = obj.get("confidence_level")
    if cl not in ("High", "Medium", "Low"):
        return False, "invalid_confidence_level"

    cr = obj.get("confidence_reason")
    if not isinstance(cr, str) or not cr.strip():
        return False, "confidence_reason_invalid"

    return True, ""

def _call_openai_intermediate(api_key: str, model: str, issue_text: str, context_sections: List[Dict]) -> Dict[str, Any]:
    sources, _ = build_source_catalog(context_sections)

    compact_sources = []
    for s in sources:
        content = s["content"]
        if len(content) > 700:
            content = content[:700].rstrip() + "..."
        compact_sources.append({
            "source_id": s["source_id"],
            "doc_name": s["doc_name"],
            "anchor": s["anchor"],
            "heading": s["heading"],
            "content": content,
        })

    system_msg = (
        "You are an internal IT helpdesk pipeline component.\n"
        "Return STRICT JSON only (no markdown, no extra text).\n"
        "Use ONLY the provided sources. Do not add any new facts.\n"
        "bullets must be 2-5 items. Each bullet MUST be an object:\n"
        '  {"text": "...", "source_id": "S1"}\n'
        "source_id MUST be one of the provided source_id values.\n"
        "clarifying_question: empty string OR ONE question.\n"
        "confidence_level: High/Medium/Low.\n"
        "confidence_reason: short.\n"
    )

    user_msg = (
        f"User request:\n{issue_text}\n\n"
        f"Sources (JSON):\n{json.dumps(compact_sources, ensure_ascii=False)}\n\n"
        "Return JSON with keys: bullets, clarifying_question, confidence_level, confidence_reason."
    )

    raw = call_openai_chat(
        api_key=api_key,
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=450,
        temperature=0.2,
    )

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            return json.loads(m.group(0))
        raise

def build_intermediate(
    context_sections: List[Dict],
    issue_text: str,
    use_llm: bool,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Unified intermediate builder.
    Returns: (intermediate, meta)
      meta includes: used_llm(bool), fallback_reason(str)
    """
    # Always have deterministic fallback ready
    det = _deterministic_intermediate(context_sections, issue_text)

    if not use_llm:
        # Strip internal helper if present
        det.pop("_retrieval_confidence_num", None)
        return det, {"used_llm": False, "fallback_reason": ""}

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        det.pop("_retrieval_confidence_num", None)
        return det, {"used_llm": False, "fallback_reason": "no_openai_api_key"}

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    _, source_map = build_source_catalog(context_sections)

    try:
        obj = _call_openai_intermediate(api_key, model, issue_text, context_sections)
        ok, reason = _validate_intermediate(obj, source_map)
        if not ok:
            det.pop("_retrieval_confidence_num", None)
            return det, {"used_llm": False, "fallback_reason": f"invalid_intermediate:{reason}"}
        return obj, {"used_llm": True, "fallback_reason": ""}
    except Exception as e:
        det.pop("_retrieval_confidence_num", None)
        return det, {"used_llm": False, "fallback_reason": f"llm_error:{str(e)}"}

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

def answer_from_intermediate(intermediate: Dict[str, Any], source_map: Optional[Dict[str, Dict[str, str]]] = None) -> Tuple[str, List[str]]:
    bullets = intermediate.get("bullets") or []
    cq = (intermediate.get("clarifying_question") or "").strip()

    answer_lines = ["Here’s what the runbooks suggest (ACL-filtered):"]
    for b in bullets:
        if isinstance(b, dict):
            text = (b.get("text") or "").strip()
            sid = (b.get("source_id") or "").strip()
            if source_map and sid in source_map:
                meta = source_map[sid]
                cite = f'({meta["doc_name"]}{meta["anchor"]})'
                answer_lines.append(f"- {text} {cite}")
            else:
                answer_lines.append(f"- {text}")
        else:
            answer_lines.append(f"- {str(b)}")

    if cq:
        answer_lines.append("")
        answer_lines.append(f"Clarifying question: {cq}")

    proposed_actions = ["Follow the cited runbook steps"]
    if cq:
        proposed_actions.append("Provide requested details to proceed")

    return "\n".join(answer_lines), proposed_actions

def main():
    parser = argparse.ArgumentParser(description="MVP Retrieval + Citations + ACL Pipeline")
    parser.add_argument("--user_id", required=True, help="User ID from directory.csv")
    parser.add_argument("--issue", help="Issue/question text (optional in --mode github; will read from GitHub issue if omitted)")
    parser.add_argument("--top_k", type=int, default=3, help="Number of sections to retrieve (default: 3)")
    parser.add_argument("--mode", choices=["cli", "github"], default="cli", help="Output channel: cli prints JSON to stdout; github posts to GitHub (default: cli)")
    parser.add_argument("--llm_intermediate", action="store_true", help="Use OpenAI to build intermediate JSON (bullets + optional clarifying question). Default off.")
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
    
    # Determine issue_text
    issue_text = (args.issue or "").strip()
    issue_text_source = "cli_arg" if issue_text else ""

    if args.mode == "github" and not issue_text:
        # Pull from GitHub issue (title + body)
        from . import github_bot
        try:
            gh_issue = github_bot.get_issue(args.repo, args.issue_number)
            title = (gh_issue.get("title") or "").strip()
            body = (gh_issue.get("body") or "").strip()
            issue_text = (title + "\n\n" + body).strip() if body else title
            issue_text_source = "github_issue"
        except Exception as e:
            error_output = {
                "answer": f"Error: --issue is missing and failed to read GitHub issue text: {str(e)}",
                "citations": [],
                "triage": {"category": "Other", "priority": "Low"},
                "retrieval_confidence": 0.0,
                "proposed_actions": [],
                "debug": {"error": "github_issue_fetch_failed"},
            }
            print(json.dumps(error_output, indent=2))
            sys.exit(1)

    if not issue_text:
        error_output = {
            "answer": "Error: --issue is required in --mode cli (or provide --mode github with a valid issue_number).",
            "citations": [],
            "triage": {"category": "Other", "priority": "Low"},
            "retrieval_confidence": 0.0,
            "proposed_actions": [],
            "debug": {"error": "missing_issue_text"},
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
    retrieved = retrieve_top_k(all_sections, issue_text, args.top_k)
    _, source_map = build_source_catalog(retrieved)
    
    # Build citations from retrieved sections (single source of truth)
    citations = []
    for section in retrieved:
        citations.append({
            "doc": section["doc_path"],
            "section": section["heading"],
            "anchor": section.get("anchor", ""),
            "tier": section["tier"],
        })

    # Build intermediate (unified). 
    # Enterprise-safe default: LLM intermediate is opt-in only
    use_llm = bool(args.llm_intermediate)  # opt-in only
    intermediate, intermediate_meta = build_intermediate(retrieved, issue_text, use_llm=use_llm)

    # Final answer comes LINEARLY from intermediate (single truth)
    answer_text, proposed_actions = answer_from_intermediate(intermediate, source_map=source_map)

    # Retrieval confidence for output: prefer intermediate-derived if present, else deterministic helper
    # If you kept det helper _retrieval_confidence_num, it was stripped before returning.
    # So we compute from retrieval score again:
    max_score = max((s.get("score", 0) for s in retrieved), default=0)
    retrieval_conf = confidence_from_max_score(max_score, k=12.0)
    if max_score == 0:
        retrieval_conf = 0.25

    answer_data = {
        "answer": answer_text,
        "citations": citations,
        "confidence": retrieval_conf,  # keep as retrieval_confidence (system gating)
        "proposed_actions": proposed_actions,
        "intermediate": intermediate,
        "intermediate_meta": intermediate_meta,
    }

    # Triage
    triage_data = triage_issue(issue_text)
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
        **({"intermediate": answer_data.get("intermediate", {})} if args.llm_intermediate else {}),
        **({"intermediate_meta": answer_data.get("intermediate_meta", {})} if args.llm_intermediate else {}),
        "triage": triage_data,
        "triage_method": "keyword",
        "retrieval_confidence": answer_data["confidence"],
        "proposed_actions": answer_data["proposed_actions"],
        "proposed_actions_struct": proposed_actions_struct,
        "debug": {
            "user_id": args.user_id,
            "role": role,
            "allowed_tiers": allowed_tiers,
            "issue_text_source": issue_text_source,
            "issue_text_preview": issue_text[:200],
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
        "issue_text_source": issue_text_source,
        "issue_text_len": len(issue_text),
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
                    + "\n\n### Intermediate (evidence summary)\n```json\n"
                    + json.dumps(answer_data.get("intermediate", {}), indent=2)
                    + "\n```\n"
                    + "\n### Intermediate meta\n```json\n"
                    + json.dumps(answer_data.get("intermediate_meta", {}), indent=2)
                    + "\n```\n"
                    + "\n### Proposed actions (struct)\n```json\n"
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
