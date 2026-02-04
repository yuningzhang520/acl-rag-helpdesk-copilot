"""
Append-only audit log as JSONL. One JSON object per line.
Path defaults to workflows/audit_log.jsonl (relative to repo root or cwd).
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional


def append_jsonl(
    record: Dict[str, Any],
    path: Optional[Path] = None,
    repo_root: Optional[Path] = None,
) -> None:
    """
    Append a single JSON object as one line to path.
    record is written as one line of JSON (no trailing newline stripped on read).
    """
    if path is None:
        base = repo_root or Path.cwd()
        path = base / "workflows" / "audit_log.jsonl"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
