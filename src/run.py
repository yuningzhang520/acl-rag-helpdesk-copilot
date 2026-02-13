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
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Retrieval confidence smoothing (single source of truth for confidence_from_max_score)
CONF_K = 8.0

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


def resolve_user(user_id: str, directory: Dict, role_override: Optional[str] = None) -> Optional[Dict]:
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


def slugify_heading(text: str) -> str:
    """Create a stable markdown-style anchor slug from a heading."""
    s = text.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)          # remove punctuation
    s = re.sub(r"\s+", "-", s)             # spaces to hyphens
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s

def confidence_from_max_score(max_score: float, k: float = CONF_K) -> float:
    """
    Map retrieval score to [0,1) with a simple saturating function:
    conf = max_score / (max_score + k)
    - If max_score is 0 -> 0
    - As max_score grows -> approaches 1
    """
    if max_score <= 0:
        return 0.0
    return float(max_score / (max_score + k))

def triage_issue(issue_text: str, source: str = "cli_arg") -> Dict[str, str]:
    """Simple deterministic triage based on keywords. For github_issue, priority can come from explicit Urgency section."""
    issue_lower = issue_text.lower()

    # Determine category
    category = "Other"
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in issue_lower for kw in keywords):
            category = cat
            break

    # Priority: for GitHub Issue Form, check explicit ### Urgency section first
    priority = "Low"
    if source == "github_issue":
        urgency_heading = re.search(r"###\s*urgency\s*:?\s*\n", issue_text, re.IGNORECASE)
        if urgency_heading:
            after = issue_text[urgency_heading.end():].split("\n")
            for line in after[:5]:
                val = line.strip().strip("- []").strip().lower()
                if val in ("critical", "high", "medium", "low"):
                    priority = val.capitalize()
                    break
    if priority == "Low":
        for prio, keywords in PRIORITY_KEYWORDS.items():
            if any(kw in issue_lower for kw in keywords):
                priority = prio
                break

    return {"category": category, "priority": priority}

def normalize_issue_text(issue_text: str, source: str) -> str:
    """
    For github_issue only: keep title + sections under GitHub Issue Form markdown headings.
    Keeps retrieval-useful sections and Urgency (for triage alignment). Drops Request Type,
    Incident/Request Timestamp, Needed by / Target Resolution Date.
    Non-github sources: return issue_text.strip() unchanged.
    """
    if source != "github_issue":
        return issue_text.strip()

    t = issue_text.strip()
    lines = t.splitlines()

    # Exact Issue Form labels (case-insensitive); only these headings are recognized.
    KEEP_HEADERS = {
        "description",
        "system / app",
        "impact scope",
        "exact error message",
        "steps already tried",
        "access request details",
        "environment",
        "urgency",
    }
    DROP_HEADERS = {
        "request type",
        "incident/request timestamp",
        "needed by / target resolution date",
        "labels",
    }

    def normalized_heading(s: str) -> str:
        return s.strip().lower().rstrip(":").strip()

    keep_lines = []
    keep = False

    for line in lines:
        stripped = line.strip()
        if stripped and not keep_lines:
            keep_lines.append(stripped)
            continue

        m = re.match(r"^###\s*(.+)$", stripped)
        if m:
            h = normalized_heading(m.group(1))
            if h in KEEP_HEADERS:
                keep = True
                keep_lines.append(stripped)
            elif h in DROP_HEADERS:
                keep = False
            else:
                keep = False
            continue

        if keep and stripped and stripped != "- [ ]" and stripped.lower() != "_no response_":
            keep_lines.append(stripped)

    out = "\n".join(keep_lines).strip()
    return out if out else issue_text.strip()

def build_proposed_actions_struct(
    triage: Dict[str, str],
    proposed_actions: List[str],
) -> Dict:
    category = triage.get("category", "Other")
    priority = triage.get("priority", "Low")

    # L2 only for Access (minimal scope). Everything else is L1 (auto-execute).
    if category == "Access":
        risk_level = "L2"
        approval_role_required = "IT Admin"
        needs_approval = True
        auto_execute = False
    else:
        risk_level = "L1"
        approval_role_required = "N/A"  # not applicable; L1 auto-executes (stable string for parseability)
        needs_approval = False
        auto_execute = True

    status = "status:pending-approval" if needs_approval else "status:triaged"
    labels_to_add = [f"cat:{category}", f"prio:{priority}", status]

    assignees = []
    comment_summary = "Proposed: " + "; ".join((proposed_actions or [])[:3]) if proposed_actions else "No actions"

    return {
        "risk_level": risk_level,
        "needs_approval": needs_approval,
        "approval_role_required": approval_role_required,
        "auto_execute": auto_execute,
        "labels_to_add": labels_to_add,
        "assignees": assignees,
        "comment_summary": comment_summary,
    }

def _parse_proposed_plan_struct_from_comment(body: str) -> Optional[Dict]:
    """
    Extract proposed_actions_struct from the fenced code block under
    '### Proposed actions (struct)' in a Proposed Plan comment.
    Accepts ```json, ```JSON, or plain ```; heading may have optional colon.
    Returns None if not found, parse fails, or required keys missing.
    """
    if not body:
        return None
    # Locate heading (optional colon, flexible whitespace)
    heading_re = re.compile(
        r"###\s*Proposed\s+actions\s+\(struct\)\s*:?\s*",
        re.IGNORECASE,
    )
    match = heading_re.search(body)
    if not match:
        return None
    after_heading = body[match.end() :]
    # Find next fenced code block (```json, ```JSON, or ```)
    fence_re = re.compile(r"```\s*(?:json|JSON)?\s*\n([\s\S]*?)```", re.IGNORECASE)
    block = fence_re.search(after_heading)
    if not block:
        return None
    raw = block.group(1).strip()
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(parsed, dict):
        return None
    required = ("risk_level", "needs_approval", "approval_role_required", "labels_to_add")
    if any(k not in parsed for k in required):
        return None
    # Normalize: approval_role_required must be string "IT Admin" (L2) or "N/A" (L1)
    role_req = parsed.get("approval_role_required")
    if not isinstance(role_req, str) or role_req not in ("IT Admin", "N/A"):
        return None
    # labels_to_add must be non-empty list of strings
    labels = parsed.get("labels_to_add")
    if not isinstance(labels, list) or not labels or not all(isinstance(x, str) for x in labels):
        return None
    return parsed


def _plan_title(needs_approval: bool) -> str:
    """Title for the propose-stage GitHub comment: PENDING APPROVAL (L2) or TRIAGED (L1)."""
    return "Proposed Plan (PENDING APPROVAL)" if needs_approval else "Proposed Plan (TRIAGED)"


def _find_latest_proposed_plan_and_approve(
    comments: List[Dict],
) -> Tuple[Optional[Dict], Optional[Dict], Optional[Dict]]:
    """
    Find the most recent comment containing a plan title (Proposed Plan (PENDING APPROVAL) or Proposed Plan (TRIAGED)),
    then the latest APPROVE comment posted *after* it.
    Relies on github_bot.list_comments() returning comments in ascending order by creation time.
    Returns (plan_comment, parsed_struct, approve_comment_after_plan).
    """
    plan_comment = None
    plan_index = -1
    for i in range(len(comments) - 1, -1, -1):
        body = comments[i].get("body") or ""
        if "Proposed Plan (PENDING APPROVAL)" in body or "Proposed Plan (TRIAGED)" in body:
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
    source_map: source_id -> {doc_name, anchor, heading, tier}
    """
    sources: List[Dict[str, Any]] = []
    source_map: Dict[str, Dict[str, str]] = {}

    for i, s in enumerate(context_sections, start=1):
        source_id = f"S{i}"
        doc_name = Path(s["doc_path"]).name
        anchor = s.get("anchor", "")
        heading = s.get("heading", "")
        tier = s.get("tier", "")
        sources.append({
            "source_id": source_id,
            "doc_name": doc_name,
            "anchor": anchor,
            "heading": heading,
            "content": (s.get("content") or "").strip(),
        })
        source_map[source_id] = {"doc_name": doc_name, "anchor": anchor, "heading": heading, "tier": tier}

    return sources, source_map

def _pick_best_line(text: str) -> str:
    """
    Pick a short, actionable line from a section.
    Filters out template checklist noise and strips list prefixes.
    """
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    if not lines:
        return ""

    def is_noise(ln: str) -> bool:
        # template checkboxes / boilerplate
        if re.match(r"^\-\s*\[\s*[xX ]\s*\]\s*", ln):
            return True
        if ln.lower().startswith(("use this runbook when", "purpose:", "objective:", "risk level:", "action type:")):
            return True
        return False

    def clean_prefix(ln: str) -> str:
        # remove "- ", "* ", "1. " etc.
        ln = re.sub(r"^(\-|\*|\+)\s+", "", ln)
        ln = re.sub(r"^\d+\.\s+", "", ln)
        return ln.strip()

    # 1) prefer explicit steps / bullets, but skip noise
    for ln in lines:
        if is_noise(ln):
            continue
        if re.match(r"^(\d+\.|\- |\* |\+ )", ln):
            return clean_prefix(ln)

    # 2) heuristic imperative-ish lines
    for ln in lines:
        if is_noise(ln):
            continue
        if re.match(r"^(confirm|ensure|check|retry|restart|open|disconnect|reconnect|verify|sign in|sign-in)\b", ln, flags=re.I):
            return clean_prefix(ln)

    # 3) first non-heading non-noise line
    for ln in lines:
        if is_noise(ln):
            continue
        if not ln.startswith("#"):
            return clean_prefix(ln)

    # final fallback: first non-noise line
    for ln in lines:
        if not is_noise(ln):
            return clean_prefix(ln)

    return ""

def _extract_rationale(text: str) -> str:
    """Derive a short rationale from evidence text without introducing new facts. Max 120 chars."""
    t = (text or "").strip()
    if not t:
        return "Recommended by the cited runbook for this symptom."
    lower = t.lower()
    markers = ("because", "so that", "indicating", "likely", " may ", " can ", "helps")
    for m in markers:
        idx = lower.find(m)
        if idx >= 0:
            tail = t[idx:].strip()
            if tail.lower().startswith(("to the ", "to a ", "to be ")):
                break
            if len(tail) > 120:
                tail = tail[:117].rstrip() + "..."
            return tail if tail else "Recommended by the cited runbook for this symptom."
    return "Recommended by the cited runbook for this symptom."[:120]


def _strip_leading_filler(text: str) -> str:
    """Remove common filler prefixes (case-insensitive), then trim."""
    t = (text or "").strip()
    fillers = (
        "resolution includes",
        "likely causes include",
        "user may experience",
        "steps include",
        "this may be due to",
    )
    for f in fillers:
        if t.lower().startswith(f):
            t = t[len(f):].strip()
            break
    return t.strip()


def _normalize_action_text(text: str) -> str:
    """Lowercase, strip punctuation, collapse spaces for grouping."""
    t = (text or "").lower().strip()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def _leading_verb_key(text: str) -> str:
    """Return leading verb for grouping (or 'other'). Uses filler stripping; verb may be in first ~8 words."""
    t = _strip_leading_filler(text)
    t = _normalize_action_text(t)
    for prefix in ("the ", "a ", "an "):
        if t.startswith(prefix):
            t = t[len(prefix):].strip()
            break
    verbs = ("confirm", "ensure", "check", "retry", "restart", "open", "disconnect", "reconnect", "verify", "sign in", "sign-in")
    for v in verbs:
        if t.startswith(v):
            return v
    words = t.split()[:8]
    for v in verbs:
        if v in ("sign in", "sign-in"):
            if "sign" in words and "in" in words:
                i = words.index("sign")
                if i + 1 < len(words) and words[i + 1] == "in":
                    return "sign in"
        elif v in words:
            return v
    return "other"


# give a schema/structure for the intermediate output (v2: summary_steps + evidence_bullets)
def _deterministic_intermediate(context_sections: List[Dict], issue_text: str) -> Dict[str, Any]:
    if not context_sections:
        return {
            "summary_steps": [
                {"step": "Escalate through official IT support.", "rationale": "No runbook sections were retrieved.", "source_ids": []},
                {"step": "Provide more details or error message.", "rationale": "Helps narrow down the right runbook.", "source_ids": []},
            ],
            "evidence_bullets": [
                {"text": "No accessible runbook sections were retrieved for this request.", "source_id": "N/A"},
                {"text": "Escalate through the official IT support process or provide more details.", "source_id": "N/A"},
            ],
            "clarifying_question": "What system/app and exact error message are you seeing?",
            "confidence_level": "Low",
            "confidence_reason": "No retrieved evidence available in accessible tiers.",
            "_retrieval_confidence_num": 0.25,
        }

    max_score = max((s.get("final_score", s.get("score", 0)) for s in context_sections), default=0)
    conf_num = confidence_from_max_score(max_score)
    if max_score == 0:
        conf_num = 0.25

    if conf_num >= 0.70:
        conf_level = "High"
    elif conf_num >= 0.45:
        conf_level = "Medium"
    else:
        conf_level = "Low"

    sources, _ = build_source_catalog(context_sections)

    # evidence_bullets: best lines from top sources (source-grounded, no merging)
    evidence_bullets: List[Dict[str, str]] = []
    for src in sources[:8]:
        best = _pick_best_line(src.get("content", ""))
        if not best:
            best = f'{src["doc_name"]} — {src["heading"]}'
        if len(best) > 160:
            best = best[:160].rstrip() + "..."
        evidence_bullets.append({"text": best, "source_id": src["source_id"]})

    while len(evidence_bullets) < 2:
        evidence_bullets.append({"text": "Review the retrieved runbook sections and follow the documented steps.", "source_id": "N/A"})

    # summary_steps: group by leading verb, dedupe; step + rationale (<=120) from evidence; source_ids from contributors
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for b in evidence_bullets[:8]:
        text = (b.get("text") or "").strip()
        sid = (b.get("source_id") or "").strip()
        if not text or sid == "N/A":
            continue
        key = _leading_verb_key(text)
        if key not in groups:
            groups[key] = []
        groups[key].append({"text": text, "source_id": sid})

    summary_steps: List[Dict[str, Any]] = []
    for key in ("verify", "check", "confirm", "ensure", "retry", "restart", "reconnect", "disconnect", "open", "sign in", "sign-in", "other"):
        if key not in groups or not groups[key]:
            continue
        items = groups[key]
        raw_text = items[0]["text"]
        step = raw_text[:80].rstrip()
        if len(raw_text) > 80:
            step = step + "..."
        rationale = _extract_rationale(raw_text)
        source_ids = list(dict.fromkeys([x["source_id"] for x in items]))
        summary_steps.append({"step": step, "rationale": rationale, "source_ids": source_ids})
        if len(summary_steps) >= 5:
            break

    fallback_sids = [b["source_id"] for b in evidence_bullets if (b.get("source_id") or "").strip() != "N/A"][:3]
    while len(summary_steps) < 2:
        summary_steps.append({
            "step": "Follow the cited runbook steps.",
            "rationale": "Evidence from retrieved sections.",
            "source_ids": fallback_sids if fallback_sids else [sources[0]["source_id"]] if sources else [],
        })

    issue_lower = issue_text.lower()
    needs_details = any(k in issue_lower for k in ["cannot", "can't", "unable", "not working", "doesn't work", "error"])
    has_explicit_error = ("error:" in issue_lower) or ("authentication failed" in issue_lower) or ('stuck at "connecting"' in issue_lower) or ("stuck at 'connecting'" in issue_lower)
    clarifying = ""
    if needs_details and not has_explicit_error:
        clarifying = "Which system/app is this for, and what is the exact error message (copy/paste if possible)?"

    return {
        "summary_steps": summary_steps[:5],
        "evidence_bullets": evidence_bullets[:8],
        "clarifying_question": clarifying,
        "confidence_level": conf_level,
        "confidence_reason": f"Derived from retrieval max_score={max_score} (confidence={conf_num:.2f}).",
        "_retrieval_confidence_num": conf_num,
    }

# V2 intermediate schema: summary_steps + evidence_bullets (citations from evidence_bullets only)
def _validate_intermediate_v2(obj: Any, source_map: Dict[str, Dict[str, str]]) -> Tuple[bool, str]:
    if not isinstance(obj, dict):
        return False, "not_a_dict"

    for k in ["summary_steps", "evidence_bullets", "clarifying_question", "confidence_level", "confidence_reason"]:
        if k not in obj:
            return False, f"missing_field:{k}"

    # evidence_bullets: 2-8 items; each non-empty text and valid source_id (or N/A only if no sources)
    eb = obj.get("evidence_bullets")
    if not isinstance(eb, list) or not (2 <= len(eb) <= 8):
        return False, "evidence_bullets_count_out_of_range"
    has_sources = len(source_map) > 0
    for b in eb:
        if not isinstance(b, dict):
            return False, "evidence_bullet_not_object"
        text = b.get("text")
        sid = (b.get("source_id") or "").strip()
        if not isinstance(text, str) or not text.strip():
            return False, "evidence_bullet_text_invalid"
        if not sid:
            return False, "evidence_bullet_source_id_invalid"
        if sid == "N/A":
            if has_sources:
                return False, "evidence_bullet_n/a_when_sources"
        elif sid not in source_map:
            return False, "evidence_bullet_source_id_not_in_sources"

    # summary_steps: 2-5 items; each non-empty step, rationale; source_ids may be empty but must be subset of valid ids if present
    ss = obj.get("summary_steps")
    if not isinstance(ss, list) or not (2 <= len(ss) <= 5):
        return False, "summary_steps_count_out_of_range"
    valid_ids = set(source_map.keys())
    step_verb_starts = ("confirm", "ensure", "check", "retry", "restart", "open", "disconnect", "reconnect", "verify", "sign in", "sign-in")
    for s in ss:
        if not isinstance(s, dict):
            return False, "summary_step_not_object"
        step = (s.get("step") or "").strip()
        rationale = (s.get("rationale") or "").strip()
        sids = s.get("source_ids")
        if not step:
            return False, "summary_step_step_empty"
        if not rationale:
            return False, "summary_step_rationale_empty"
        if not isinstance(sids, list):
            return False, "summary_step_source_ids_not_list"
        if not all(isinstance(x, str) for x in sids):
            return False, "summary_step_source_ids_not_strings"
        for x in sids:
            if x not in valid_ids:
                return False, "summary_step_source_id_not_in_sources"
        if has_sources and len(sids) == 0:
            step_lower = step.lower()
            if not any(step_lower.startswith(v) for v in step_verb_starts):
                return False, "summary_step_unattributed_nonverb"

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

# transfer context section as source, limit the content to 700 characters, output llm based only on source
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
        "Output schema (v2):\n"
        "evidence_bullets: array of 2-8 objects, each { \"text\": string, \"source_id\": string }. "
        "source_id MUST be one of the provided source_id values (e.g. S1, S2). One bullet per source quote/fact; do not merge.\n"
        "summary_steps: array of 2-5 objects, each { \"step\": string (short imperative), \"rationale\": string (<=120 chars), \"source_ids\": string[] }. "
        "source_ids MUST be a list; it MAY be empty only if the step truly cannot be attributed, but prefer including at least one valid source_id when possible. Each id must be from provided sources. You may merge/dedupe across sources.\n"
        "clarifying_question: empty string OR one question (max 240 chars).\n"
        "confidence_level: High | Medium | Low.\n"
        "confidence_reason: short string.\n"
    )

    user_msg = (
        f"User request:\n{issue_text}\n\n"
        f"Sources (JSON):\n{json.dumps(compact_sources, ensure_ascii=False)}\n\n"
        "Return JSON with keys: summary_steps, evidence_bullets, clarifying_question, confidence_level, confidence_reason."
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

# 1. det for default, 2. if use_llm=false or openai fail, fall back to det 3. if use_llm, call LLM then _validate_intermediate_v2; if old format (bullets) or invalid, fall back to det
def build_intermediate(
    context_sections: List[Dict],
    issue_text: str,
    use_llm: bool,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Unified intermediate builder (v2 schema: summary_steps + evidence_bullets).
    Returns: (intermediate, meta). meta includes used_llm(bool), fallback_reason(str).
    """
    det = _deterministic_intermediate(context_sections, issue_text)

    if not use_llm:
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
        # Reject old format (bullets) so we always use v2
        if isinstance(obj, dict) and "bullets" in obj and "evidence_bullets" not in obj:
            det.pop("_retrieval_confidence_num", None)
            return det, {"used_llm": False, "fallback_reason": "invalid_intermediate:old_format_bullets"}
        ok, reason = _validate_intermediate_v2(obj, source_map)
        if not ok:
            det.pop("_retrieval_confidence_num", None)
            return det, {"used_llm": False, "fallback_reason": f"invalid_intermediate:{reason}"}
        return obj, {"used_llm": True, "fallback_reason": ""}
    except Exception as e:
        det.pop("_retrieval_confidence_num", None)
        return det, {"used_llm": False, "fallback_reason": f"llm_error:{str(e)}"}

# ---------------------------
# Proposal Builder (LLM propose, guarded)
# ---------------------------

def validate_comment_summary(comment_summary: str, issue_text_normalized: str) -> Tuple[bool, str]:
    """
    Validate that LLM-proposed comment_summary does not introduce new facts.
    Returns (ok, reason). reason is empty when ok is True.
    """
    if not isinstance(comment_summary, str) or not comment_summary.strip():
        return True, ""
    cs = comment_summary.strip()
    if len(cs) > 200:
        return False, "comment_summary_too_long"
    issue_lower = (issue_text_normalized or "").lower()

    # (b) No user-ID-like tokens unless present in issue
    for m in re.finditer(r"\bu\d{3,}\b", cs, re.IGNORECASE):
        token = m.group(0).lower()
        if token not in issue_lower:
            return False, "new_facts:user_id"

    # (c) No quoted folder/resource names (double or single quotes) unless in issue
    for m in re.finditer(r'["\']([^"\']+)["\']', cs):
        quoted = m.group(1).strip()
        if len(quoted) > 2 and quoted.lower() not in issue_lower:
            return False, "new_facts:quoted_entity"

    # (d) No duration/time windows unless in issue (e.g. "30 days", "2 weeks")
    duration_pat = re.compile(r"\b(\d+\s*(?:days?|weeks?|months?|hours?))\b", re.IGNORECASE)
    for m in duration_pat.finditer(cs):
        if m.group(0).lower() not in issue_lower:
            return False, "new_facts:duration"

    # (e) No new capitalized multi-word entities (simple: words Cap Cap) unless substring in issue
    cap_phrase = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")
    for m in cap_phrase.finditer(cs):
        phrase = m.group(1)
        if len(phrase) > 3 and phrase.lower() not in issue_lower:
            return False, "new_facts:capitalized_entity"

    return True, ""


def _deterministic_comment_summary(intermediate: Optional[Dict] = None, proposed_actions: Optional[List[str]] = None) -> str:
    """Build a safe comment_summary from intermediate summary_steps or proposed_actions (no LLM)."""
    if intermediate:
        steps = intermediate.get("summary_steps") or []
        parts = []
        for s in steps[:3]:
            if isinstance(s, dict):
                step = (s.get("step") or "").strip()
                if step:
                    parts.append(step)
        if parts:
            return "Proposed: " + "; ".join(parts)[:300]
    if proposed_actions:
        return "Proposed: " + "; ".join(proposed_actions[:3])[:300] if proposed_actions else "No actions"
    return "Proposed: Follow the cited runbook steps."


def _validate_proposal(obj: Any) -> Tuple[bool, str]:
    """
    Proposal is intentionally narrow and safe.
    Allowed keys: comment_summary(str), assignees(list[str]).
    Everything else will be ignored by guard anyway.
    """
    if not isinstance(obj, dict):
        return False, "not_a_dict"

    # comment_summary is optional but if present must be short
    if "comment_summary" in obj:
        cs = obj.get("comment_summary")
        if not isinstance(cs, str):
            return False, "comment_summary_not_string"
        if len(cs) > 300:
            return False, "comment_summary_too_long"

    # assignees optional
    if "assignees" in obj:
        a = obj.get("assignees")
        if not isinstance(a, list):
            return False, "assignees_not_list"
        if not all(isinstance(x, str) for x in a):
            return False, "assignees_not_strings"
        if len(a) > 10:
            return False, "assignees_too_many"

    return True, ""

def _call_openai_proposal(api_key: str, model: str, issue_text: str, triage: Dict[str, str], intermediate: Dict[str, Any]) -> Dict[str, Any]:
    """
    LLM propose a human-readable comment_summary + optional assignees.
    IMPORTANT:
    - LLM does NOT decide risk/approval/labels.
    - Output JSON only.
    """
    # v2: use summary_steps for plan summary
    summary_steps = intermediate.get("summary_steps") or []
    cq = (intermediate.get("clarifying_question") or "").strip()
    bullets_text = "\n".join([
        f"- {(s.get('step') or '')} — {(s.get('rationale') or '')}" if isinstance(s, dict) else str(s)
        for s in summary_steps[:5]
    ])
    if not bullets_text and intermediate.get("evidence_bullets"):
        bullets_text = "\n".join([
            f"- {(b.get('text','') if isinstance(b, dict) else str(b))}"
            for b in (intermediate.get("evidence_bullets") or [])[:5]
        ])
    cq_text = f"\nClarifying question: {cq}" if cq else ""

    system_msg = (
        "You are an IT helpdesk assistant that writes a short proposed plan summary.\n"
        "Return STRICT JSON only. No markdown.\n"
        "Allowed keys:\n"
        "- comment_summary: a concise summary for a GitHub comment (<= 200 chars preferred)\n"
        "- assignees: optional list of GitHub usernames (strings), usually empty\n"
        "Rules:\n"
        "- Do not invent actions beyond the provided bullets.\n"
        "- Do not include labels/risk/approval in the output.\n"
    )

    user_msg = (
        f"User issue:\n{issue_text}\n\n"
        f"Triage:\ncategory={triage.get('category')} priority={triage.get('priority')}\n\n"
        f"Evidence bullets:\n{bullets_text}{cq_text}\n\n"
        "Return JSON."
    )

    raw = call_openai_chat(
        api_key=api_key,
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=120,
        temperature=0.2,
    )

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            return json.loads(m.group(0))
        raise

def build_proposal(
    issue_text: str,
    triage: Dict[str, str],
    intermediate: Dict[str, Any],
    use_llm: bool,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    Returns: (proposal, meta)
    proposal is optional dict with keys comment_summary/assignees.
    meta includes used_llm and fallback_reason.
    """
    if not use_llm:
        return None, {"used_llm": False, "fallback_reason": ""}

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None, {"used_llm": False, "fallback_reason": "no_openai_api_key"}

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    try:
        obj = _call_openai_proposal(api_key, model, issue_text, triage, intermediate)
        ok, reason = _validate_proposal(obj)
        if not ok:
            return None, {"used_llm": False, "fallback_reason": f"invalid_proposal:{reason}"}
        return obj, {"used_llm": True, "fallback_reason": ""}
    except Exception as e:
        return None, {"used_llm": False, "fallback_reason": f"llm_error:{str(e)}"}

def merge_and_guard_proposed_struct(
    base_struct: Dict[str, Any],
    triage: Dict[str, str],
    mode: str,
    proposal: Optional[Dict[str, Any]] = None,
    issue_text_normalized: str = "",
    proposal_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Guard rail:
    - NEVER trust LLM for risk_level / needs_approval / approval_role_required / labels_to_add.
    - Only allow LLM comment_summary if it passes validate_comment_summary (no new facts).
    - On validation failure, use deterministic comment_summary and set proposal_meta.fallback_reason.
    """
    out = dict(base_struct or {})

    # Deterministic labels override (enterprise safe) — always compute
    cat = triage.get("category", "Other")
    prio = triage.get("priority", "Low")
    status = "status:pending-approval" if out.get("needs_approval") else "status:triaged"
    out["labels_to_add"] = [f"cat:{cat}", f"prio:{prio}", status]

    # LLM-proposed comment summary: only use if validation passes (no invented entities/facts)
    if proposal and isinstance(proposal, dict):
        cs = proposal.get("comment_summary")
        if isinstance(cs, str) and cs.strip():
            ok, reason = validate_comment_summary(cs, issue_text_normalized)
            if ok:
                out["comment_summary"] = cs.strip()[:300]
            else:
                # Keep out["comment_summary"] from base_struct (deterministic); record rejection reason
                if isinstance(proposal_meta, dict):
                    proposal_meta["fallback_reason"] = proposal_meta.get("fallback_reason") or f"invalid_proposal:{reason}"

        # assignees: keep empty unless you explicitly allowlist later
        # If you want allowlist:
        # allowed_assignees = set(["oncall-engineer", "it-admin-1"])
        # a = proposal.get("assignees")
        # if isinstance(a, list):
        #     out["assignees"] = [x for x in a if isinstance(x, str) and x in allowed_assignees][:10]

    return out

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
    summary_steps = intermediate.get("summary_steps") or []
    cq = (intermediate.get("clarifying_question") or "").strip()

    answer_lines = ["Here’s what the runbooks suggest (ACL-filtered):"]
    for s in summary_steps:
        if isinstance(s, dict):
            step = (s.get("step") or "").strip()
            rationale = (s.get("rationale") or "").strip()
            source_ids = s.get("source_ids") or []
            citation_suffix = ""
            if source_map and source_ids:
                cite_parts = []
                for sid in source_ids:
                    if sid in source_map:
                        meta = source_map[sid]
                        tier = meta.get("tier") or ""
                        doc_anchor = (meta.get("doc_name") or "") + (meta.get("anchor") or "")
                        cite_parts.append(f"{tier}:{doc_anchor}" if tier else doc_anchor)
                if cite_parts:
                    citation_suffix = " (" + ", ".join(cite_parts) + ")"
            if step:
                if rationale:
                    answer_lines.append(f"- {step} — {rationale}{citation_suffix}")
                else:
                    answer_lines.append(f"- {step}{citation_suffix}")

    if cq:
        answer_lines.append("")
        answer_lines.append(f"Clarifying question: {cq}")

    # proposed_actions from summary_steps.step (top 3)
    proposed_actions = []
    for s in summary_steps[:3]:
        if isinstance(s, dict):
            step = (s.get("step") or "").strip()
            if step:
                proposed_actions.append(step)

    if not proposed_actions:
        proposed_actions = ["Follow the cited runbook steps"]

    if cq:
        proposed_actions.append("Provide requested details to proceed")

    return "\n".join(answer_lines), proposed_actions


# ---------------------------
# main() helpers
# ---------------------------

def _exit_with_error(
    message: str, debug_error: str, code: int = 1, proposed_actions: Optional[List[str]] = None, **debug_extra: Any
) -> None:
    """Print JSON error payload and exit. Used for CLI/validation failures."""
    payload = {
        "answer": message,
        "citations": [],
        "triage": {"category": "Other", "priority": "Low"},
        "retrieval_confidence": 0.0,
        "proposed_actions": proposed_actions if proposed_actions is not None else [],
        "debug": {"error": debug_error, **debug_extra},
    }
    print(json.dumps(payload, indent=2))
    sys.exit(code)


def _finalize_audit(
    audit_record: Dict,
    audit_path: Path,
    repo_root: Path,
    start_time_perf: float,
) -> None:
    """Set latency_ms and append audit record once."""
    import time as _time
    from . import audit
    latency_ms = round((_time.perf_counter() - start_time_perf) * 1000)
    audit_record["latency_ms"] = latency_ms
    audit.append_jsonl(audit_record, path=audit_path, repo_root=repo_root)


def _maybe_post_rejection_comment(
    github_bot: Any, repo: str, issue_number: int, execution_result: str
) -> None:
    """Post a rejection comment only for these execution_result values."""
    if execution_result in (
        "rejected_employee_approval",
        "rejected_l2_requires_it_admin",
        "rejected_l1_requires_engineer_or_admin",
        "approver_not_in_directory",
        "invalid_plan_format",
        "no_proposed_plan",
    ):
        github_bot.post_comment(repo, issue_number, _rejection_comment_message(execution_result))


def _require_github_args_or_exit(args: Any) -> None:
    if args.mode == "github" and (not args.repo or args.issue_number is None):
        _exit_with_error(
            "Error: --repo and --issue_number are required when --mode github",
            "github_requires_repo_and_issue",
        )


def _get_issue_text_or_exit(args: Any) -> Tuple[str, str, Optional[str]]:
    """Returns (issue_text, issue_text_source, issue_author_login or None). Author login is set when mode=github and issue was fetched from API."""
    issue_text = (args.issue or "").strip()
    issue_text_source = "cli_arg" if issue_text else ""
    issue_author_login: Optional[str] = None
    if args.mode == "github" and not issue_text:
        from . import github_bot
        try:
            gh_issue = github_bot.get_issue(args.repo, args.issue_number)
            title = (gh_issue.get("title") or "").strip()
            body = (gh_issue.get("body") or "").strip()
            issue_text = (title + "\n\n" + body).strip() if body else title
            issue_text_source = "github_issue"
            issue_author_login = (gh_issue.get("user") or {}).get("login") or ""
        except Exception as e:
            _exit_with_error(
                f"Error: --issue is missing and failed to read GitHub issue text: {str(e)}",
                "github_issue_fetch_failed",
            )
    if not issue_text:
        _exit_with_error(
            "Error: --issue is required in --mode cli (or provide --mode github with a valid issue_number).",
            "missing_issue_text",
        )
    return issue_text, issue_text_source, issue_author_login


def _load_directory_or_exit(repo_root: Path) -> Tuple[Dict, Dict]:
    directory_path = repo_root / "workflows" / "directory.csv"
    if not directory_path.exists():
        _exit_with_error(
            f"Error: Directory file not found at {directory_path}",
            "directory_not_found",
            proposed_actions=["Check directory.csv path"],
        )
    return load_directory(str(directory_path))


def _resolve_user_or_exit(
    args: Any, directory: Dict, by_github_username: Dict, issue_author_login: Optional[str] = None
) -> Tuple[str, List[str]]:
    """Resolve role and allowed_tiers. In GitHub mode, if --user_id is missing, resolve from issue author via directory."""
    if args.mode == "github" and not (args.user_id or "").strip():
        if issue_author_login and (issue_author_login.strip().lower() in by_github_username):
            u = by_github_username[issue_author_login.strip().lower()]
            args.user_id = u["user_id"]
            ent = directory.get(args.user_id)
            if ent:
                return ent["role"], ent["allowed_tiers"]
        args.user_id = ""
        setattr(args, "_github_author_unresolved", True)
        return ("Unknown", ["public"])
    if not (args.user_id or "").strip():
        _exit_with_error(
            "Error: --user_id is required in --mode cli.",
            "user_id_required_cli",
            proposed_actions=["Provide --user_id or run in --mode github with issue author in directory"],
        )
    user_info = resolve_user(args.user_id, directory, args.role_override)
    if not user_info:
        _exit_with_error(
            f"Error: User ID '{args.user_id}' not found in directory",
            "user_not_found",
            proposed_actions=["Provide valid user_id or use --role_override"],
            user_id=args.user_id,
        )
    return user_info["role"], user_info["allowed_tiers"]


def _load_sections(repo_root: Path, allowed_tiers: List[str]) -> List[Dict]:
    return load_allowed_documents(allowed_tiers, repo_root / "docs")


def _run_retrieval(
    args: Any, issue_text: str, all_sections: List[Dict], repo_root: Path
) -> Tuple[List[Dict], Dict[str, Any]]:
    from . import retrieval as retrieval_mod
    index_bundle = None
    if args.retriever in ("vector", "hybrid"):
        index_bundle = retrieval_mod.build_or_load_vector_index(
            all_sections, repo_root / "workflows", rebuild=args.rebuild_index
        )
    retrieved, retriever_debug = retrieval_mod.retrieve(
        issue_text,
        all_sections,
        top_k=args.top_k,
        retriever_type=args.retriever,
        candidate_k=args.candidate_k,
        index_bundle=index_bundle,
        hybrid_alpha=args.hybrid_alpha,
        troubleshoot_bias=not args.no_troubleshoot_bias,
    )
    return retrieved, retriever_debug


def _citations_from_intermediate(intermediate: Dict[str, Any], retrieved: List[Dict]) -> List[Dict]:
    """Build citations list from evidence_bullets' source_ids only (order preserved, de-duplicated)."""
    source_id_to_section = {f"S{i}": s for i, s in enumerate(retrieved, start=1)}
    seen: Set[str] = set()
    ordered_ids: List[str] = []
    for b in intermediate.get("evidence_bullets") or []:
        if not isinstance(b, dict):
            continue
        sid = (b.get("source_id") or "").strip()
        if sid and sid != "N/A" and sid not in seen and sid in source_id_to_section:
            seen.add(sid)
            ordered_ids.append(sid)
    citations = []
    for sid in ordered_ids:
        s = source_id_to_section[sid]
        citations.append({
            "doc": s["doc_path"],
            "section": s.get("heading", ""),
            "anchor": s.get("anchor", ""),
            "tier": s.get("tier", ""),
        })
    return citations


def _citations_from_retrieved(retrieved: List[Dict]) -> List[Dict]:
    """Return citations-style list for all retrieved sections (doc, section, anchor, tier), in order."""
    return [
        {"doc": s["doc_path"], "section": s.get("heading", ""), "anchor": s.get("anchor", ""), "tier": s.get("tier", "")}
        for s in retrieved
    ]


def _build_answer_and_actions(
    args: Any, issue_text: str, retrieved: List[Dict], issue_text_source: str = "cli_arg"
) -> Tuple[Dict, Dict, Dict, Optional[Dict], Dict]:
    _, source_map = build_source_catalog(retrieved)
    use_llm = bool(args.llm_intermediate)
    intermediate, intermediate_meta = build_intermediate(retrieved, issue_text, use_llm=use_llm)
    answer_text, proposed_actions = answer_from_intermediate(intermediate, source_map=source_map)
    max_score = max((s.get("final_score", s.get("score", 0)) for s in retrieved), default=0)
    retrieval_conf = confidence_from_max_score(max_score)
    if max_score == 0:
        retrieval_conf = 0.25

    # Align intermediate confidence with retrieval_confidence (single source of truth)
    intermediate["confidence_level"] = (
        "High" if retrieval_conf >= 0.70 else
        "Medium" if retrieval_conf >= 0.45 else
        "Low"
    )
    prefix = f"retrieval_confidence={retrieval_conf:.2f}; "
    existing_reason = intermediate.get("confidence_reason")
    if not isinstance(existing_reason, str):
        existing_reason = "" if existing_reason is None else str(existing_reason)
    existing_reason = existing_reason.strip()
    if not existing_reason.startswith("retrieval_confidence="):
        intermediate["confidence_reason"] = (prefix + existing_reason).strip()
    else:
        intermediate["confidence_reason"] = existing_reason

    answer_data = {
        "answer": answer_text,
        "citations": _citations_from_intermediate(intermediate, retrieved),
        "confidence": retrieval_conf,
        "proposed_actions": proposed_actions,
        "intermediate": intermediate,
        "intermediate_meta": intermediate_meta,
    }
    triage_data = triage_issue(issue_text, source=issue_text_source or "cli_arg")
    proposed_actions_struct = build_proposed_actions_struct(triage_data, answer_data["proposed_actions"])
    proposal, proposal_meta = build_proposal(
        issue_text=issue_text, triage=triage_data, intermediate=intermediate, use_llm=bool(args.llm_propose)
    )
    proposed_actions_struct = merge_and_guard_proposed_struct(
        base_struct=proposed_actions_struct,
        triage=triage_data,
        mode=args.mode,
        proposal=proposal,
        issue_text_normalized=issue_text,
        proposal_meta=proposal_meta,
    )
    return answer_data, triage_data, proposed_actions_struct, proposal, proposal_meta


def _build_output_json(
    args: Any,
    answer_data: Dict,
    triage_data: Dict,
    proposed_actions_struct: Dict,
    proposal: Optional[Dict],
    proposal_meta: Dict,
    role: str,
    allowed_tiers: List[str],
    issue_text_source: str,
    issue_text_raw: str,
    issue_text_normalized: str,
    retrieved: List[Dict],
    retriever_debug: Dict,
) -> Dict:
    debug_retrieved = []
    for s in retrieved:
        entry = {"doc": s["doc_path"], "section": s["heading"], "tier": s["tier"], "score": s.get("score", 0)}
        if "final_score" in s:
            entry["final_score"] = s["final_score"]
        if "keyword_score" in s:
            entry["keyword_score"] = s["keyword_score"]
        if "keyword_norm" in s:
            entry["keyword_norm"] = s["keyword_norm"]
        if "vector_score" in s:
            entry["vector_score"] = s["vector_score"]
        debug_retrieved.append(entry)
    return {
        "answer": answer_data["answer"],
        "citations": answer_data["citations"],
        "retrieved_citations_topk": _citations_from_retrieved(retrieved),
        **({"intermediate": answer_data.get("intermediate", {})} if args.llm_intermediate else {}),
        **({"intermediate_meta": answer_data.get("intermediate_meta", {})} if args.llm_intermediate else {}),
        **({"proposal": proposal} if args.llm_propose else {}),
        **({"proposal_meta": proposal_meta} if args.llm_propose else {}),
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
            "issue_text_preview": issue_text_normalized[:200],
            "issue_text_preview_raw": issue_text_raw[:200],
            "issue_text_normalized": issue_text_normalized,
            "issue_text_raw": issue_text_raw,
            "retrieved": debug_retrieved,
            "llm_propose": bool(args.llm_propose),
             # --- LLM intermediate telemetry (truthy even when LLM falls back) ---
            "llm_intermediate_requested": bool(args.llm_intermediate),
            "llm_intermediate_used": bool((answer_data.get("intermediate_meta") or {}).get("used_llm", False)),
            "llm_intermediate_fallback_reason": (answer_data.get("intermediate_meta") or {}).get("fallback_reason", ""),
            "retriever_type": retriever_debug.get("retriever_type", "keyword"),
            "candidate_k": retriever_debug.get("candidate_k"),
            "vector_index_info": retriever_debug.get("vector_index_info"),
            "hybrid_alpha": retriever_debug.get("hybrid_alpha"),
            "troubleshoot_bias": retriever_debug.get("troubleshoot_bias"),
            "troubleshoot_intent_detected": retriever_debug.get("troubleshoot_intent_detected"),
        },
    }


def _rejection_comment_message(execution_result: str) -> str:
    """Human-readable rejection message for execute stage."""
    messages = {
        "rejected_employee_approval": "**Approval rejected.** Employees cannot approve execution. Only an Engineer or IT Admin may comment APPROVE to execute. No actions were performed.",
        "rejected_l2_requires_it_admin": "**Approval rejected.** This plan requires IT Admin approval. Only a user with the IT Admin role in our directory may approve. No actions were performed.",
        "rejected_l1_requires_engineer_or_admin": "**Approval rejected.** This plan requires an Engineer or IT Admin to approve. Your role does not have approval permission. No actions were performed.",
        "approver_not_in_directory": "**Approval rejected.** Your GitHub username is not in our directory, so we could not verify your role. No actions were performed. Please ask an IT Admin or Engineer listed in the directory to comment APPROVE.",
        "invalid_plan_format": "**Invalid plan format.** We could not parse the proposed actions from the latest plan comment. No actions were performed.",
        "no_proposed_plan": "**No proposed plan found.** There is no Proposed Plan comment on this issue. Open the issue so the bot can post a plan, then comment APPROVE to execute (if your role is allowed). No actions were performed.",
    }
    return messages.get(execution_result, "**Approval could not be processed.** No actions were performed.")


def _apply_approved_actions(
    repo: str, issue_number: int, struct_for_execute: Dict, github_bot_module: Any
) -> List[str]:
    """Apply labels and assignees from approved struct; post Executed actions comment. Returns executed_actions list. Idempotent: skips if status:executed already set."""
    current_labels = github_bot_module.get_issue_labels(repo, issue_number) or []
    if "status:executed" in current_labels:
        return []
    base_labels = [lb for lb in (struct_for_execute.get("labels_to_add") or []) if not str(lb).startswith("status:")]
    labels = base_labels + ["status:executed"]
    executed: List[str] = []
    if labels:
        github_bot_module.add_labels(repo, issue_number, labels, remove_prefixes=["status:"])
        executed.append("add_labels")
    if struct_for_execute.get("assignees"):
        github_bot_module.add_assignees(repo, issue_number, struct_for_execute["assignees"])
        executed.append("add_assignees")
    github_bot_module.post_comment(
        repo, issue_number,
        "## Executed actions\n\n" + json.dumps({"executed": executed}, indent=2)
    )
    return executed


def _run_execute_stage(
    args: Any,
    repo_root: Path,
    audit_path: Path,
    start_time_perf: float,
    by_github_username: Dict,
) -> Dict[str, Any]:
    """
    Lightweight execute-only path: find latest Proposed Plan + APPROVE comment,
    validate approver role, apply allowlisted actions or post rejection. No retrieval, no docs.
    Writes audit once via _finalize_audit. Returns small output JSON for stdout.
    """
    import time as _time
    from . import github_bot

    audit_record = {
        "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
        "repo": str(args.repo) if (args.mode == "github" and args.repo) else "",
        "issue_number": int(args.issue_number) if (args.mode == "github" and args.issue_number is not None) else 0,
        "requester_user_id": "",
        "requester_role": "",
        "allowed_tiers": ["public"],
        "approval_status": "n/a",
        "approval_actor_login": "",
        "approval_actor_role": "",
        "executed_actions": [],
        "execution_result": "n/a",
        "latency_ms": 0,
        "estimated_cost": 0,
    }

    def _out(approval_status: str, approval_actor_login: str, approval_actor_role: str, executed_actions: List[str], execution_result: str) -> Dict[str, Any]:
        return {
            "execution": {
                "approval_status": approval_status,
                "approval_actor_login": approval_actor_login,
                "approval_actor_role": approval_actor_role,
                "executed_actions": executed_actions,
                "execution_result": execution_result,
            }
        }

    try:
        current_labels = github_bot.get_issue_labels(args.repo, args.issue_number) or []
        if "status:executed" in current_labels:
            audit_record["execution_result"] = "already_executed_noop"
            _finalize_audit(audit_record, audit_path, repo_root, start_time_perf)
            return _out("n/a", "", "", [], "already_executed_noop")

        comments = github_bot.list_comments(args.repo, args.issue_number)
        plan_comment, parsed_struct, approve_comment = _find_latest_proposed_plan_and_approve(comments)

        if plan_comment is None:
            audit_record["execution_result"] = "no_proposed_plan"
            _maybe_post_rejection_comment(github_bot, args.repo, args.issue_number, "no_proposed_plan")
            _finalize_audit(audit_record, audit_path, repo_root, start_time_perf)
            return _out("n/a", "", "", [], "no_proposed_plan")

        if parsed_struct is None:
            audit_record["approval_status"] = "rejected"
            audit_record["execution_result"] = "invalid_plan_format"
            _maybe_post_rejection_comment(github_bot, args.repo, args.issue_number, "invalid_plan_format")
            _finalize_audit(audit_record, audit_path, repo_root, start_time_perf)
            return _out("rejected", "", "", [], "invalid_plan_format")

        struct_for_execute = parsed_struct
        if struct_for_execute.get("needs_approval") is False:
            audit_record["approval_status"] = "n/a"
            audit_record["execution_result"] = "l1_noop"
            audit_record["executed_actions"] = []
            _finalize_audit(audit_record, audit_path, repo_root, start_time_perf)
            return _out("n/a", "", "", [], "l1_noop")

        approval_status = "pending"
        approval_actor_login = ""
        approval_actor_role = ""
        executed_actions: List[str] = []
        execution_result = "no_approval_found"

        if approve_comment:
            approval_actor_login = (
                approve_comment.get("login")
                or (approve_comment.get("user") or {}).get("login")
                or ""
            )
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
                            executed_actions = _apply_approved_actions(args.repo, args.issue_number, struct_for_execute, github_bot)
                            execution_result = "already_approved_skip" if not executed_actions else "success"
                    else:
                        if approval_actor_role not in ("Engineer", "IT Admin"):
                            approval_status = "rejected"
                            execution_result = "rejected_l1_requires_engineer_or_admin"
                        else:
                            approval_status = "approved"
                            executed_actions = _apply_approved_actions(args.repo, args.issue_number, struct_for_execute, github_bot)
                            execution_result = "already_approved_skip" if not executed_actions else "success"
            else:
                approval_status = "rejected"
                execution_result = "approver_not_in_directory"

        _maybe_post_rejection_comment(github_bot, args.repo, args.issue_number, execution_result)
        audit_record["approval_status"] = approval_status
        audit_record["approval_actor_login"] = approval_actor_login or ""
        audit_record["approval_actor_role"] = approval_actor_role
        audit_record["executed_actions"] = executed_actions
        audit_record["execution_result"] = execution_result
        _finalize_audit(audit_record, audit_path, repo_root, start_time_perf)
        return _out(approval_status, approval_actor_login or "", approval_actor_role, executed_actions, execution_result)

    except Exception as e:
        audit_record["execution_result"] = "error"
        audit_record["error"] = str(e)
        audit_record["executed_actions"] = []
        _finalize_audit(audit_record, audit_path, repo_root, start_time_perf)
        return _out("rejected", "", "", [], "error")


def _write_audit_and_maybe_github(
    args: Any,
    output: Dict,
    answer_data: Dict,
    triage_data: Dict,
    proposed_actions_struct: Dict,
    proposal: Optional[Dict],
    proposal_meta: Dict,
    retrieved: List[Dict],
    retriever_debug: Dict,
    by_github_username: Dict,
    repo_root: Path,
    audit_path: Path,
    start_time_perf: float,
    issue_text_source: str,
    issue_text_raw: str,
    issue_text_normalized: str,
) -> None:
    import time as _time
    debug_retrieved = output["debug"]["retrieved"]
    audit_record = {
        "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
        "repo": str(args.repo) if (args.mode == "github" and args.repo) else "",
        "issue_number": int(args.issue_number) if (args.mode == "github" and args.issue_number is not None) else 0,
        "requester_user_id": str(args.user_id),
        "requester_role": output["debug"]["role"],
        "allowed_tiers": list(output["debug"]["allowed_tiers"]),
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
        "issue_text_len": len(issue_text_normalized),
        "llm_propose": bool(args.llm_propose),
        "proposal_meta": proposal_meta if args.llm_propose else {},
        "issue_text_len_raw": len(issue_text_raw),
        "retriever_type": retriever_debug.get("retriever_type", "keyword"),
        "candidate_k": retriever_debug.get("candidate_k"),
        "vector_model_name": (retriever_debug.get("vector_index_info") or {}).get("model_name") or "",
    }
    if args.mode == "github":
        if getattr(args, "github_stage", "propose") == "execute":
            raise RuntimeError(
                "Execute stage is handled by _run_execute_stage; _write_audit_and_maybe_github should not be used for execute."
            )
        from . import github_bot
        try:
            if getattr(args, "github_stage", "propose") == "propose":
                plan_title = _plan_title(proposed_actions_struct.get("needs_approval", False))
                short_plan = (
                    "## " + plan_title + "\n\n"
                    + (proposed_actions_struct.get("comment_summary", "").strip() + "\n\n" if proposed_actions_struct.get("comment_summary") else "")
                    + answer_data["answer"]
                )
                _, source_map_plan = build_source_catalog(retrieved)
                def _sources_map_line(sid: str, m: Dict) -> str:
                    tier = m.get("tier") or ""
                    doc_anchor = (m.get("doc_name") or "") + (m.get("anchor") or "")
                    prefix = f"{tier}:" if tier else ""
                    return f"{sid} -> {prefix}{doc_anchor} ({m.get('heading', '')})"

                sources_map_lines = [_sources_map_line(sid, m) for sid, m in sorted(source_map_plan.items())]
                sources_map_block = "### Sources map\n\n" + "\n".join(sources_map_lines) + "\n\n" if sources_map_lines else ""
                details_content = (
                    sources_map_block
                    + "### Intermediate (evidence summary)\n\n```json\n"
                    + json.dumps(answer_data.get("intermediate", {}), indent=2)
                    + "\n```\n\n### Intermediate meta\n\n```json\n"
                    + json.dumps(answer_data.get("intermediate_meta", {}), indent=2)
                    + "\n```\n\n### Proposed actions (struct)\n\n```json\n"
                    + json.dumps(proposed_actions_struct, indent=2)
                    + "\n```\n\n### Proposal meta\n\n```json\n"
                    + json.dumps(proposal_meta if args.llm_propose else {}, indent=2)
                    + "\n```\n\n### Proposal (LLM)\n\n```json\n"
                    + json.dumps(proposal if args.llm_propose else {}, indent=2)
                    + "\n```\n"
                )
                plan_body = short_plan + "\n\n<details><summary>Details (evidence + struct)</summary>" + details_content + "\n</details>\n"
                github_bot.post_comment(args.repo, args.issue_number, plan_body)
                labels = list(proposed_actions_struct.get("labels_to_add") or [])
                if labels:
                    github_bot.add_labels(args.repo, args.issue_number, labels, remove_prefixes=["status:"])
                if not proposed_actions_struct.get("needs_approval"):
                    executed_actions = _apply_approved_actions(args.repo, args.issue_number, proposed_actions_struct, github_bot)
                    audit_record["executed_actions"] = executed_actions
                    audit_record["execution_result"] = "propose_and_execute"
                else:
                    audit_record["execution_result"] = "propose_only"
        except Exception as e:
            audit_record["execution_result"] = "error"
            audit_record["error"] = str(e)
            audit_record["executed_actions"] = []
            output["debug"]["github_error"] = str(e)
    _finalize_audit(audit_record, audit_path, repo_root, start_time_perf)


def main():
    import time as _time
    parser = argparse.ArgumentParser(description="MVP Retrieval + Citations + ACL Pipeline")
    parser.add_argument("--user_id", default=None, help="User ID from directory.csv (required in CLI mode; optional in GitHub mode: resolved from issue author via directory)")
    parser.add_argument("--issue", help="Issue/question text (optional in --mode github; will read from GitHub issue if omitted)")
    parser.add_argument("--top_k", type=int, default=3, help="Number of sections to retrieve (default: 3)")
    parser.add_argument("--mode", choices=["cli", "github"], default="cli", help="Output channel: cli prints JSON to stdout; github posts to GitHub (default: cli)")
    parser.add_argument("--llm_intermediate", action="store_true", help="Use OpenAI to build intermediate JSON (bullets + optional clarifying question). Default off.")
    parser.add_argument("--llm_propose", action="store_true", help="Use OpenAI to propose a plan/summary for GitHub comment (proposal only). Default off.")
    parser.add_argument("--role_override", help="Override role if user_id not found (Employee/Engineer/IT Admin)")
    parser.add_argument("--repo", help="GitHub repo owner/name (required for --mode github)")
    parser.add_argument("--issue_number", type=int, help="GitHub issue number (required for --mode github)")
    parser.add_argument("--github_stage", choices=["propose", "execute"], default="propose", help="GitHub mode: propose = post plan only; execute = check approval and run allowlisted actions (default: propose)")
    parser.add_argument("--retriever", choices=["keyword", "vector", "hybrid"], default="keyword", help="Retrieval method: keyword (default), vector, or hybrid (vector + keyword rerank)")
    parser.add_argument("--candidate_k", type=int, default=30, help="Candidate pool size for vector/hybrid (default: 30)")
    parser.add_argument("--rebuild_index", action="store_true", help="Force rebuild of vector index (workflows/vector_*.npz and .json)")
    parser.add_argument("--hybrid_alpha", type=float, default=0.7, help="Hybrid retriever: final_score = alpha*kw_norm + (1-alpha)*vector_score; kw_norm in [0,1] (default: 0.7)")
    parser.add_argument("--no_troubleshoot_bias", action="store_true", help="Disable troubleshooting intent bias in retrieval (bias ON by default: boosts verify/troubleshoot sections when query suggests trouble)")
    args = parser.parse_args()
    _start_audit = _time.perf_counter()

    _require_github_args_or_exit(args)

    repo_root = Path(__file__).parent.parent
    audit_path = repo_root / "workflows" / "audit_log.jsonl"
    directory, by_github_username = _load_directory_or_exit(repo_root)

    if args.mode == "github" and getattr(args, "github_stage", "propose") == "execute":
        output = _run_execute_stage(args, repo_root, audit_path, _start_audit, by_github_username)
        print(json.dumps(output, indent=2))
        return

    issue_text_raw, issue_text_source, issue_author_login = _get_issue_text_or_exit(args)
    issue_text = normalize_issue_text(issue_text_raw, issue_text_source)
    role, allowed_tiers = _resolve_user_or_exit(args, directory, by_github_username, issue_author_login)

    if getattr(args, "_github_author_unresolved", False):
        from . import github_bot
        github_bot.post_comment(
            args.repo,
            args.issue_number,
            "We could not match the issue author to a user in our directory. Please escalate to IT or an administrator to get access.",
        )
        audit_record = {
            "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
            "repo": str(args.repo),
            "issue_number": int(args.issue_number),
            "requester_user_id": "",
            "requester_role": "Unknown",
            "allowed_tiers": ["public"],
            "triage": {},
            "execution_result": "author_unresolved",
        }
        # Audit: written exactly once per run. This path finalizes here; normal path finalizes in _write_audit_and_maybe_github() via _finalize_audit(). Do not add a second finalize.
        _finalize_audit(audit_record, audit_path, repo_root, _start_audit)
        output = {
            "answer": "Author unresolved; escalation comment posted.",
            "citations": [],
            "debug": {"execution_result": "author_unresolved"},
        }
    else:
        all_sections = _load_sections(repo_root, allowed_tiers)
        retrieved, retriever_debug = _run_retrieval(args, issue_text, all_sections, repo_root)

        answer_data, triage_data, proposed_actions_struct, proposal, proposal_meta = _build_answer_and_actions(
            args, issue_text, retrieved, issue_text_source
        )

        output = _build_output_json(
            args, answer_data, triage_data, proposed_actions_struct, proposal, proposal_meta,
            role, allowed_tiers, issue_text_source, issue_text_raw, issue_text, retrieved, retriever_debug,
        )

        _write_audit_and_maybe_github(
            args, output, answer_data, triage_data, proposed_actions_struct, proposal, proposal_meta,
            retrieved, retriever_debug, by_github_username, repo_root, audit_path, _start_audit,
            issue_text_source, issue_text_raw, issue_text,
        )

    print(json.dumps(output, indent=2))
    if getattr(args, "_github_author_unresolved", False):
        sys.exit(0)


if __name__ == "__main__":
    main()
