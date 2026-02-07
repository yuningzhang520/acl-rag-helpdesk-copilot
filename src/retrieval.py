"""
Local vector index + hybrid retriever (vector recall + optional keyword rerank).
Uses sentence-transformers, sklearn NearestNeighbors, numpy.

Dev notes:
- Sections are ACL-filtered only (caller passes allowed tiers); we never see disallowed docs.
- hybrid = vector recall -> keyword rerank, with vector_score as tie-break (or optional fused score via hybrid_alpha).
- Cache is ACL-scope keyed: filenames include tier_key (e.g. public_internal_restricted), model name, and num_sections
  so different ACL scopes (e.g. Employee vs IT Admin) do not share the same index and risk leaking restricted content.
- Cache is also guarded by a content fingerprint; editing docs invalidates cache without --rebuild_index.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Lazy import to avoid loading model when using keyword-only
_sentence_transformers = None


def _get_model(model_name: str = "all-MiniLM-L6-v2"):
    global _sentence_transformers
    if _sentence_transformers is None:
        try:
            from sentence_transformers import SentenceTransformer
            _sentence_transformers = SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers is required for vector/hybrid retrieval. "
                "Install with: pip install sentence-transformers"
            )
    return _sentence_transformers(model_name)


def _section_to_text(section: Dict) -> str:
    """Concatenate heading + filename + content for embedding."""
    heading = section.get("heading", "")
    doc_path = section.get("doc_path", "")
    filename = Path(doc_path).name if doc_path else ""
    content = section.get("content", "")
    return f"{heading} {filename} {content}".strip()


def _sections_fingerprint(sections: List[Dict]) -> str:
    """Lightweight fingerprint: changes if content changes. Used for cache validation."""
    parts = []
    for s in sections:
        doc_path = str(s.get("doc_path", ""))
        anchor = str(s.get("anchor", ""))
        content = (s.get("content") or "")[:200]
        length = len(s.get("content") or "")
        h = hashlib.sha1(content.encode("utf-8", errors="replace")).hexdigest()
        parts.append(f"{doc_path}|{anchor}|{h}|{length}")
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()


def _acl_cache_key(sections: List[Dict], model_name: str) -> Tuple[str, str, int]:
    """(tier_key, model_sanitized, num_sections) for ACL-scope cache filenames. Prevents cross-scope cache reuse."""
    tiers = sorted(set(s.get("tier") or "" for s in sections if s.get("tier")))
    tier_key = "_".join(tiers) if tiers else "none"
    model_sanitized = (model_name or "").replace("/", "_").replace(" ", "_").strip("_") or "default"
    return tier_key, model_sanitized, len(sections)


def build_or_load_vector_index(
    sections: List[Dict],
    cache_dir: Path,
    rebuild: bool = False,
    model_name: str = "all-MiniLM-L6-v2",
) -> Tuple[Any, List[Dict], Any, Dict[str, Any]]:
    """
    Build or load vector index over ACL-filtered sections.
    Cache files are keyed by ACL scope: tier_key (sorted unique tiers), model name, and num_sections
    so different permission scopes (e.g. Employee vs IT Admin) do not share an index.
    Returns (nn_index, meta, model, info_dict).
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    tier_key, model_sanitized, num_sections = _acl_cache_key(sections, model_name)
    base_name = f"vector_index__{tier_key}__{model_sanitized}__n{num_sections}"
    path_npz = cache_dir / f"{base_name}.npz"
    path_meta = cache_dir / f"vector_meta__{tier_key}__{model_sanitized}__n{num_sections}.json"
    path_info = cache_dir / f"vector_info__{tier_key}__{model_sanitized}__n{num_sections}.json"

    meta = [{"doc_path": s.get("doc_path"), "tier": s.get("tier"), "heading": s.get("heading"), "content": s.get("content"), "anchor": s.get("anchor", "")} for s in sections]
    fingerprint = _sections_fingerprint(sections)

    import numpy as np
    from sklearn.neighbors import NearestNeighbors
    # Only load from ACL-scope keyed paths; old fixed-name cache files are ignored (no cross-scope reuse)
    if not rebuild and path_npz.exists() and path_meta.exists() and path_info.exists():
        try:
            with open(path_info, "r", encoding="utf-8") as f:
                info = json.load(f)
            if (info.get("model_name") == model_name
                    and info.get("num_sections") == num_sections
                    and info.get("fingerprint") == fingerprint):
                data = np.load(path_npz)
                emb = data["embeddings"]
                with open(path_meta, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                if len(meta) == num_sections:
                    model = _get_model(model_name)
                    n_neighbors = min(200, max(1, len(meta)))
                    nn = NearestNeighbors(n_neighbors=n_neighbors, metric="cosine", algorithm="brute")
                    nn.fit(emb)
                    return nn, meta, model, info
        except Exception:
            pass

    if not sections:
        raise ValueError("build_or_load_vector_index requires at least one section")
    model = _get_model(model_name)
    texts = [_section_to_text(s) for s in sections]
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    if isinstance(embeddings, np.ndarray) and embeddings.ndim == 1:
        embeddings = embeddings.reshape(1, -1)
    np.savez_compressed(path_npz, embeddings=embeddings)
    with open(path_meta, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=0)
    info = {
        "model_name": model_name,
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "num_sections": num_sections,
        "fingerprint": fingerprint,
        "tier_key": tier_key,
    }
    with open(path_info, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False)
    n_neighbors = min(200, max(1, len(sections)))
    nn = NearestNeighbors(n_neighbors=n_neighbors, metric="cosine", algorithm="brute")
    nn.fit(embeddings)
    return nn, meta, model, info


def vector_retrieve_candidates(
    issue_text: str,
    nn_index: Any,
    meta: List[Dict],
    model: Any,
    candidate_k: int,
) -> List[Dict]:
    """Return candidate section dicts with vector_distance, vector_score (cosine sim), and score (backwards-compat)."""
    import numpy as np
    if not meta:
        return []
    query_emb = model.encode([issue_text], convert_to_numpy=True)
    if hasattr(query_emb, "ndim") and query_emb.ndim == 1:
        query_emb = query_emb.reshape(1, -1)
    k = min(candidate_k, len(meta))
    distances, indices = nn_index.kneighbors(query_emb, n_neighbors=k)
    candidates = []
    for i, idx in enumerate(indices[0]):
        dist = float(distances[0][i])
        # cosine similarity = 1 - cosine_distance (so higher = more similar)
        vector_score = max(0.0, 1.0 - dist)
        rec = dict(meta[idx])
        rec["vector_distance"] = dist
        rec["vector_score"] = vector_score
        rec["score"] = vector_score  # backwards-compat for vector-only mode
        candidates.append(rec)
    return candidates


# Troubleshooting intent bias: small deterministic boost for verify/troubleshoot-style sections when query suggests trouble.
_TROUBLESHOOT_INTENT_PHRASES = (
    "can't", "cannot", "unable", "not working", "can't see", "missing", "no longer", "anymore", "error"
)
_TROUBLESHOOT_POSITIVE_PHRASES = (
    "verify", "troubleshoot", "fix", "resolve", "common", "steps", "close ticket", "error", "diagnose"
)
_TROUBLESHOOT_NEGATIVE_PHRASES = ("purpose", "overview", "kb articles")
_BIAS_POSITIVE = 0.15
_BIAS_NEGATIVE = -0.10


def _has_troubleshoot_intent(text: str) -> bool:
    """True if query suggests troubleshooting (can't, unable, not working, etc.)."""
    if not text or not text.strip():
        return False
    lower = text.lower().strip()
    return any(p in lower for p in _TROUBLESHOOT_INTENT_PHRASES)


def _section_troubleshoot_bias(section: Dict) -> float:
    """Bias to add to final_score: +0.15 for verify/troubleshoot-style headings, -0.10 for purpose/overview."""
    heading = (section.get("heading") or "").lower()
    doc_path = section.get("doc_path") or ""
    filename = Path(doc_path).name.lower() if doc_path else ""
    combined = f"{heading} {filename}"
    out = 0.0
    if any(p in combined for p in _TROUBLESHOOT_POSITIVE_PHRASES):
        out += _BIAS_POSITIVE
    if any(p in combined for p in _TROUBLESHOOT_NEGATIVE_PHRASES):
        out += _BIAS_NEGATIVE
    return out


def keyword_rerank_candidates(issue_text: str, candidates: List[Dict]) -> List[Dict]:
    """Add keyword_score to each candidate using text_utils (vector_score/score already set)."""
    from . import text_utils
    issue_tokens = text_utils.tokenize(issue_text)
    for c in candidates:
        c["keyword_score"] = text_utils.score_section(c, issue_tokens)
    return candidates


def retrieve(
    issue_text: str,
    all_sections: List[Dict],
    top_k: int,
    retriever_type: str,
    candidate_k: int = 30,
    index_bundle: Optional[Tuple[Any, List[Dict], Any, Dict[str, Any]]] = None,
    hybrid_alpha: float = 0.7,
    troubleshoot_bias: bool = True,
) -> Tuple[List[Dict], Dict[str, Any]]:
    """
    Unified retrieve. Returns (sections, debug_info).
    Each section has doc_path, tier, heading, content, anchor, and scoring fields:
    - keyword_score (float): TF overlap. In hybrid, normalized to [0,1] as keyword_norm = keyword_score / (max(candidates) + 1e-9).
    - vector_score (float in [0,1]): cosine similarity (vector and hybrid).
    - final_score (float): for hybrid, alpha*kw_norm + (1-alpha)*vector_score; used for sort and retrieval_confidence.
    When troubleshoot_bias is True and query suggests troubleshooting intent, a small bias is applied to final_score before sort
    (positive for verify/troubleshoot-style headings, negative for purpose/overview). Disable with --no_troubleshoot_bias.
    To compare rankings by alpha: e.g. --retriever hybrid --hybrid_alpha 0.3 vs --hybrid_alpha 0.9 on same issue (e.g. "give someone access to a team drive").
    """
    troubleshoot_intent = _has_troubleshoot_intent(issue_text)
    debug_info = {
        "retriever_type": retriever_type,
        "candidate_k": candidate_k,
        "vector_index_info": None,
        "hybrid_alpha": hybrid_alpha,
        "troubleshoot_bias": troubleshoot_bias,
        "troubleshoot_intent_detected": troubleshoot_intent if troubleshoot_bias else None,
    }

    if retriever_type == "keyword":
        from . import text_utils
        issue_tokens = text_utils.tokenize(issue_text)
        scored = []
        for s in all_sections:
            sc = text_utils.score_section(s, issue_tokens)
            scored.append({**s, "score": sc, "keyword_score": sc, "final_score": sc})
        if troubleshoot_bias and troubleshoot_intent:
            for s in scored:
                s["final_score"] = s["final_score"] + _section_troubleshoot_bias(s)
        scored.sort(key=lambda x: x["final_score"], reverse=True)
        top = scored[:top_k]
        if all(s["final_score"] == 0 for s in top) and len(scored) > top_k:
            seen = set()
            fallback = []
            for s in scored:
                if len(fallback) >= top_k:
                    break
                if s["doc_path"] not in seen:
                    fallback.append(s)
                    seen.add(s["doc_path"])
            if fallback:
                top = fallback
        return top, debug_info

    if index_bundle is None:
        raise ValueError("index_bundle required for vector or hybrid retriever")
    nn_index, meta, model, info = index_bundle
    debug_info["vector_index_info"] = {"model_name": info.get("model_name"), "num_sections": info.get("num_sections")}
    candidates = vector_retrieve_candidates(issue_text, nn_index, meta, model, candidate_k)
    if not candidates:
        return [], debug_info

    if retriever_type == "vector":
        top = candidates[:top_k]
        return [
            {
                "doc_path": c["doc_path"],
                "tier": c["tier"],
                "heading": c["heading"],
                "content": c["content"],
                "anchor": c.get("anchor", ""),
                "score": c["vector_score"],
                "vector_score": c["vector_score"],
                "final_score": c["vector_score"],
            }
            for c in top
        ], debug_info

    # hybrid: normalize keyword_score to [0,1] then combine with vector_score on same scale
    # keyword_score is TF-overlap (can be 10+); vector_score is cosine sim in [0,1]. Normalize so alpha is meaningful.
    candidates = keyword_rerank_candidates(issue_text, candidates)
    kw_max = max((c.get("keyword_score", 0) for c in candidates), default=0) + 1e-9
    for c in candidates:
        kw = c.get("keyword_score", 0)
        c["keyword_norm"] = kw / kw_max  # [0,1]
        vs = c.get("vector_score", 0)
        c["final_score"] = hybrid_alpha * c["keyword_norm"] + (1.0 - hybrid_alpha) * vs
    if troubleshoot_bias and troubleshoot_intent:
        for c in candidates:
            c["final_score"] = c["final_score"] + _section_troubleshoot_bias(c)
    candidates.sort(key=lambda x: x["final_score"], reverse=True)
    top = candidates[:top_k]
    return [
        {
            "doc_path": c["doc_path"],
            "tier": c["tier"],
            "heading": c["heading"],
            "content": c["content"],
            "anchor": c.get("anchor", ""),
            "score": c["final_score"],
            "keyword_score": c.get("keyword_score"),
            "keyword_norm": c.get("keyword_norm"),
            "vector_score": c.get("vector_score"),
            "final_score": c["final_score"],
        }
        for c in top
    ], debug_info
