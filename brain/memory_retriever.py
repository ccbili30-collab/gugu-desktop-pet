"""Memory retriever for gugupet_v2.

Finds relevant memory files given a query string.
"""

from __future__ import annotations

import re
import time

from brain.memory_store import read_index, read_recent, scan


def find_relevant(query: str, limit: int = 3) -> list[dict]:
    query_text = str(query or "").strip().lower()
    if not query_text:
        return []
    tokens = {
        t
        for t in re.split(r"\s+|[，。！？,.!?：:；;()\-_/]+", query_text)
        if len(t) >= 2
    }
    scored: list[tuple[float, dict]] = []
    for item in scan():
        haystack = (item["name"] + "\n" + item["text"]).lower()
        score = sum(1.0 for t in tokens if t in haystack)
        if query_text in haystack:
            score += 2.5
        if score <= 0:
            continue
        # Freshness bonus: files modified recently score slightly higher
        age_days = (time.time() - item["mtime"]) / 86400.0
        score += max(0.0, 0.5 - age_days * 0.05)
        scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:limit]]


def format_context(query: str, max_chars: int = 2400) -> str:
    """Build a compact memory context string to inject into prompts."""
    sections: list[str] = []
    index = read_index().strip()
    recent = read_recent().strip()
    if index:
        sections.append("## Memory Index\n" + index)
    if recent:
        sections.append("## Recent Summary\n" + recent)
    for item in find_relevant(query, limit=3):
        text = item["text"].strip()
        name = (
            item["path"].name
            if hasattr(item["path"], "name")
            else str(item.get("name", ""))
        )
        if text:
            sections.append(f"## Memory: {name}\n{text}")
    full = "\n\n".join(sections).strip()
    return full[:max_chars] if len(full) > max_chars else full
