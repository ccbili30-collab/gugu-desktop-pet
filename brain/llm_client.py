"""OpenAI-compatible LLM client for gugupet_v2.

Transport only — no prompt logic here.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from config import loader as cfg


def _normalize_base_url(base_url: str) -> str:
    cleaned = str(base_url or "").strip().rstrip("/")
    if cleaned.endswith("/chat/completions"):
        return cleaned[: -len("/chat/completions")]
    if not cleaned.endswith("/v1"):
        cleaned = cleaned + "/v1"
    return cleaned


def chat_completion(
    messages: list[dict[str, str]],
    max_tokens: int = 220,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call /v1/chat/completions.  Returns dict with keys: ok, text, error."""
    llm = config or cfg.llm()
    if not cfg.llm_enabled({"llm": llm} if config else None):
        return {"ok": False, "error": "llm_disabled", "text": ""}

    api_key = str(llm.get("api_key", "")).strip()
    base_url = _normalize_base_url(
        str(llm.get("base_url", "https://api.openai.com/v1"))
    )
    model = str(llm.get("model", "gpt-4o-mini")).strip() or "gpt-4o-mini"
    timeout = float(llm.get("timeout", 25) or 25)
    temperature = float(llm.get("temperature", 0.8) or 0.8)

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    request = urllib.request.Request(
        url=base_url + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return {"ok": False, "error": f"http_{exc.code}", "text": "", "body": body}
    except urllib.error.URLError as exc:
        return {"ok": False, "error": f"url_error:{exc.reason}", "text": ""}
    except Exception as exc:
        return {"ok": False, "error": f"request_failed:{exc}", "text": ""}

    try:
        data = json.loads(raw)
    except Exception:
        return {"ok": False, "error": "invalid_json", "text": "", "body": raw}

    try:
        text = str(data["choices"][0]["message"]["content"]).strip()
    except Exception:
        text = ""
    return {"ok": bool(text), "error": "", "text": text, "raw": data}
