"""File-based memory store for gugupet_v2.

Stores long-term memories as Markdown files under memory/.
"""

from __future__ import annotations

import re
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MEMORY_ROOT = PROJECT_ROOT / "memory"
MEMORY_INDEX = MEMORY_ROOT / "MEMORY.md"
RECENT_FILE = MEMORY_ROOT / "recent_summary.md"

MEMORY_DIRS: dict[str, Path] = {
    "identity": MEMORY_ROOT / "identity",
    "preferences": MEMORY_ROOT / "preferences",
    "episodes": MEMORY_ROOT / "episodes",
    "behavior": MEMORY_ROOT / "behavior",
}

_DEFAULT_FILES: dict[Path, str] = {
    MEMORY_INDEX: "# Memory Index\n\n",
    RECENT_FILE: "# Recent Summary\n\n暂无近期摘要。\n",
    MEMORY_DIRS["identity"]
    / "owner.md": "---\ntype: identity\ndescription: Owner identity.\n---\n\n# Owner\n\n暂无。\n",
    MEMORY_DIRS["identity"]
    / "pet.md": "---\ntype: identity\ndescription: Pet identity.\n---\n\n# Pet\n\n咕咕是一只桌面鸽子宠物。\n",
    MEMORY_DIRS["preferences"]
    / "interaction_preferences.md": "---\ntype: preferences\ndescription: Interaction preferences.\n---\n\n# Interaction Preferences\n\n暂无。\n",
    MEMORY_DIRS["behavior"]
    / "drive_bias.md": "---\ntype: behavior\ndescription: Long-term behavior tendencies.\n---\n\n# Drive Bias\n\n暂无。\n",
}


def ensure() -> None:
    MEMORY_ROOT.mkdir(parents=True, exist_ok=True)
    for d in MEMORY_DIRS.values():
        d.mkdir(parents=True, exist_ok=True)
    for path, content in _DEFAULT_FILES.items():
        if not path.exists():
            path.write_text(content, encoding="utf-8")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", text.strip().lower())
    return re.sub(r"-+", "-", cleaned).strip("-") or f"mem-{int(time.time())}"


def read_index() -> str:
    ensure()
    return _read(MEMORY_INDEX)


def read_recent() -> str:
    ensure()
    return _read(RECENT_FILE)


def write_recent(text: str) -> None:
    ensure()
    RECENT_FILE.write_text(f"# Recent Summary\n\n{text.strip()}\n", encoding="utf-8")


def scan() -> list[dict]:
    ensure()
    items = []
    for mem_type, directory in MEMORY_DIRS.items():
        for path in sorted(directory.glob("*.md")):
            text = _read(path).strip()
            if text:
                items.append(
                    {
                        "type": mem_type,
                        "path": path,
                        "name": path.stem,
                        "text": text,
                        "mtime": path.stat().st_mtime,
                    }
                )
    return items


def store(memory_type: str, title: str, summary: str) -> Path | None:
    ensure()
    memory_type = memory_type if memory_type in MEMORY_DIRS else "episodes"
    summary = str(summary or "").strip()
    title = str(title or "").strip()
    if not summary:
        return None

    if memory_type == "episodes":
        filename = f"{time.strftime('%Y-%m-%d')}-{_slugify(title or summary[:24])}.md"
        path = MEMORY_DIRS[memory_type] / filename
        if not path.exists():
            path.write_text(
                f"---\ntype: {memory_type}\ndescription: {title or summary[:60]}\n---\n\n"
                f"# {title or 'Episode'}\n\n{summary}\n",
                encoding="utf-8",
            )
    else:
        filename = f"{_slugify(title or memory_type)}.md"
        path = MEMORY_DIRS[memory_type] / filename
        existing = {
            line[2:].strip()
            for line in _read(path).splitlines()
            if line.startswith("- ")
        }
        if summary in existing:
            return path
        if not path.exists():
            path.write_text(
                f"---\ntype: {memory_type}\ndescription: {title or memory_type}\n---\n\n"
                f"# {title or memory_type.title()}\n\n- {summary}\n",
                encoding="utf-8",
            )
        else:
            path.write_text(_read(path).rstrip() + f"\n- {summary}\n", encoding="utf-8")

    # Update index
    bullet = (
        f"- [{memory_type}] {title or summary[:40]} -> {path.relative_to(MEMORY_ROOT)}"
    )
    index = _read(MEMORY_INDEX)
    if bullet not in index:
        MEMORY_INDEX.write_text(index.rstrip() + "\n" + bullet + "\n", encoding="utf-8")
    return path
