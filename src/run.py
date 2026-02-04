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
    "Access": ["access", "permission", "grant", "iam", "role", "group"],
    "Onboarding": ["onboarding", "new hire"],
}

# Priority keywords
PRIORITY_KEYWORDS = {
    "Critical": ["outage", "down", "many users", "widespread"],
    "High": ["urgent", "blocked", "deadline", "critical"],
    "Medium": ["soon", "annoying", "inconvenience"],
}


def load_directory(csv_path: str) -> Dict[str, Dict]:
    """Load user directory and return user_id -> user_info mapping."""
    directory = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            user_id = row["user_id"]
            role = row["role"]
            # Handle restricted_grant column if present (for exceptions)
            restricted_grant = row.get("restricted_grant", "false").lower() == "true"
            
            # Determine allowed tiers based on role
            allowed_tiers = ROLE_TIER_MAP.get(role, []).copy()
            
            # If user has explicit restricted grant, add restricted tier
            if restricted_grant and "restricted" not in allowed_tiers:
                allowed_tiers.append("restricted")
            
            directory[user_id] = {
                "role": role,
                "display_name": row.get("display_name", ""),
                "allowed_tiers": allowed_tiers,
            }
    return directory


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
    parser.add_argument("--mode", choices=["mock", "openai"], default="mock", help="Answer generation mode (default: mock)")
    parser.add_argument("--role_override", help="Override role if user_id not found (Employee/Engineer/IT Admin)")
    
    args = parser.parse_args()
    
    # Load directory
    repo_root = Path(__file__).parent.parent
    directory_path = repo_root / "workflows" / "directory.csv"
    
    if not directory_path.exists():
        error_output = {
            "answer": f"Error: Directory file not found at {directory_path}",
            "citations": [],
            "triage": {"category": "Other", "priority": "Low"},
            "confidence": 0.0,
            "proposed_actions": ["Check directory.csv path"],
            "debug": {"error": "directory_not_found"},
        }
        print(json.dumps(error_output, indent=2))
        sys.exit(1)
    
    directory = load_directory(str(directory_path))
    
    # Resolve user
    user_info = resolve_user(args.user_id, directory, args.role_override)
    if not user_info:
        error_output = {
            "answer": f"Error: User ID '{args.user_id}' not found in directory",
            "citations": [],
            "triage": {"category": "Other", "priority": "Low"},
            "confidence": 0.0,
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
    
    # Build final output
    output = {
        "answer": answer_data["answer"],
        "citations": answer_data["citations"],
        "triage": triage_data,
        "confidence": answer_data["confidence"],
        "proposed_actions": answer_data["proposed_actions"],
        "debug": {
            "user_id": args.user_id,
            "role": role,
            "allowed_tiers": allowed_tiers,
            "retrieved": [
                {
                    "doc": s["doc_path"],
                    "section": s["heading"],
                    "tier": s["tier"],
                    "score": s["score"],
                }
                for s in retrieved
            ],
        },
    }
    
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
