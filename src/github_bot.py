"""
GitHub API client for allowlisted operations only.
Uses stdlib urllib only. Requires GITHUB_TOKEN in environment.
Allowlist: list_comments, post_comment, add_labels, add_assignees.
"""

import json
import os
import urllib.error
import urllib.request
from typing import List, Dict, Any, Optional


def _base_url(repo: str) -> str:
    """repo is owner/name."""
    return f"https://api.github.com/repos/{repo}"


def _auth_headers() -> Dict[str, str]:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is not set")
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _req(
    method: str,
    url: str,
    data: Optional[Dict[str, Any]] = None,
    timeout: float = 30,
) -> Dict[str, Any]:
    headers = _auth_headers()
    headers["Content-Type"] = "application/json"
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    else:
        body = None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def _req_list(method: str, url: str, timeout: float = 30) -> List[Dict[str, Any]]:
    """GET that returns a list."""
    headers = _auth_headers()
    req = urllib.request.Request(url, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else []

def get_issue(repo: str, issue_number: int) -> Dict[str, Any]:
    """
    Get a GitHub issue. Returns {title, body, ...}.
    Allowlisted read operation.
    """
    url = f"{_base_url(repo)}/issues/{issue_number}"
    try:
        return _req("GET", url)
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"GitHub API get_issue failed {e.code}: {err}") from e

def list_comments(repo: str, issue_number: int) -> List[Dict[str, Any]]:
    """
    List comments on an issue, sorted ascending by creation time.
    Returns list of {id, login, user: {login}, body, created_at}; login and body are always str.
    run.py relies on this order and shape for plan/approve detection.
    MVP: per_page=100; issues with more than 100 comments are not paginated (explicit limitation).
    """
    url = f"{_base_url(repo)}/issues/{issue_number}/comments?sort=created&direction=asc&per_page=100"
    try:
        rows = _req_list("GET", url)
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"GitHub API list_comments failed {e.code}: {err}") from e
    out = []
    for r in rows:
        user = r.get("user") or {}
        login = str(user.get("login") or r.get("login") or "")
        out.append({
            "id": r.get("id"),
            "login": login,
            "user": {"login": login},
            "body": str(r.get("body") or ""),
            "created_at": str(r.get("created_at") or ""),
        })
    return out


def post_comment(repo: str, issue_number: int, body: str) -> Dict[str, Any]:
    """Post a comment on an issue. Allowlisted."""
    url = f"{_base_url(repo)}/issues/{issue_number}/comments"
    try:
        return _req("POST", url, data={"body": body})
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"GitHub API post_comment failed {e.code}: {err}") from e

def get_issue_labels(repo: str, issue_number: int) -> List[str]:
    url = f"{_base_url(repo)}/issues/{issue_number}"
    headers = _auth_headers()
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        issue = json.loads(resp.read().decode("utf-8"))
    return [lb.get("name") for lb in issue.get("labels", []) if lb.get("name")]

def add_labels(
    repo: str,
    issue_number: int,
    labels: List[str],
    remove_prefixes: Optional[List[str]] = None,
) -> None:
    """
    Add labels to an issue. Merges with existing labels (GET then PATCH).
    When remove_prefixes is provided, existing labels whose name starts with
    any of those prefixes are removed before merging. Allowlisted.
    """
    if not labels:
        return
    url = f"{_base_url(repo)}/issues/{issue_number}"
    headers = _auth_headers()
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            issue = json.loads(resp.read().decode("utf-8"))
        existing = [lb.get("name") for lb in issue.get("labels", []) if lb.get("name")]
        if remove_prefixes:
            existing = [
                name for name in existing
                if not any(str(name).startswith(p) for p in remove_prefixes)
            ]
        merged = list(dict.fromkeys(existing + labels))
        _req("PATCH", url, data={"labels": merged})
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"GitHub API add_labels failed {e.code}: {err}") from e


def add_assignees(repo: str, issue_number: int, assignees: List[str]) -> None:
    """Add assignees to an issue. Allowlisted."""
    if not assignees:
        return
    url = f"{_base_url(repo)}/issues/{issue_number}/assignees"
    try:
        _req("POST", url, data={"assignees": assignees})
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"GitHub API add_assignees failed {e.code}: {err}") from e
