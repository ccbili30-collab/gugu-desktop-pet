"""Memory writer for gugupet_v2.

Calls the LLM to decide what (if anything) to store after a conversation turn.
"""

from __future__ import annotations

import json

from brain import llm_client
from brain.memory_store import read_index, store
from brain.prompts import memory_extract_prompt
from config import loader as cfg


def maybe_extract_and_store(user_text: str, pet_reply: str) -> dict | None:
    """Ask the LLM whether to store a memory.  Returns stored candidate or None."""
    if not cfg.llm_enabled():
        return None
    if not user_text.strip():
        return None

    existing_index = read_index()
    system, user = memory_extract_prompt(user_text, pet_reply, existing_index)
    result = llm_client.chat_completion(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=100,
    )
    if not result.get("ok"):
        return None

    raw = str(result.get("text", "") or "").strip()
    try:
        # Strip markdown code fences if present
        raw = raw.strip("`").strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
        data = json.loads(raw)
    except Exception:
        return None

    if not isinstance(data, dict) or not data.get("store"):
        return None

    mem_type = str(data.get("type", "episodes"))
    title = str(data.get("title", ""))
    summary = str(data.get("summary", "")).strip()
    if not summary:
        return None

    store(mem_type, title, summary)
    return {"type": mem_type, "title": title, "summary": summary}
