"""Shared text utilities for retrieval: tokenize and keyword score_section."""
import re
from pathlib import Path
from collections import Counter
from typing import Dict, List


def tokenize(text: str) -> List[str]:
    """Simple tokenization: lowercase, split on whitespace and punctuation."""
    text = re.sub(r"[*_`#\[\]()]", " ", text)
    tokens = re.findall(r"\b\w+\b", text.lower())
    return tokens


def section_to_text_for_scoring(section: Dict) -> str:
    """Same text field as embeddings: heading + filename + content."""
    heading = section.get("heading", "")
    filename = Path(section.get("doc_path", "")).name if section.get("doc_path") else ""
    content = section.get("content", "")
    return f"{heading} {filename} {content}".strip()


def score_section(section: Dict, issue_tokens: List[str]) -> float:
    """Score section vs issue using TF overlap on heading+filename+content + small heading bonus."""
    issue_counter = Counter(issue_tokens)
    body_tokens = tokenize(section_to_text_for_scoring(section))
    head_tokens = tokenize(
        section.get("heading", "") + " " + Path(section.get("doc_path", "")).name
    )
    body_c = Counter(body_tokens)
    head_c = Counter(head_tokens)
    score = 0.0
    for t, w in issue_counter.items():
        score += w * body_c.get(t, 0)
    HEAD_WEIGHT = 0.5
    for t, w in issue_counter.items():
        if head_c.get(t, 0) > 0:
            score += HEAD_WEIGHT * w * 1.0
    return score
