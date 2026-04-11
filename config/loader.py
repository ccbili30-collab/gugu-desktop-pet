"""Configuration loader for gugupet_v2.

Reads config.yaml from the project root, merges with defaults,
and exposes typed accessor helpers.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from config.defaults import DEFAULT_CONFIG


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_FILE = PROJECT_ROOT / "config.yaml"


def _load_yaml() -> object | None:
    try:
        import yaml  # type: ignore

        return yaml
    except Exception:
        return None


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, returning a new dict."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_raw() -> dict[str, Any]:
    """Load config.yaml and merge with defaults.  Always returns a full dict."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    if not CONFIG_FILE.exists():
        return config
    yaml = _load_yaml()
    if yaml is not None:
        try:
            loaded = yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8")) or {}
            if isinstance(loaded, dict):
                config = _deep_merge(config, loaded)
        except Exception:
            pass
    else:
        try:
            loaded = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                config = _deep_merge(config, loaded)
        except Exception:
            pass
    # Environment variable overrides
    for env_key, path in (
        ("GUGU_API_KEY", ("llm", "api_key")),
        ("GUGU_BASE_URL", ("llm", "base_url")),
        ("GUGU_MODEL", ("llm", "model")),
    ):
        val = os.getenv(env_key, "").strip()
        if val:
            node = config
            for part in path[:-1]:
                node = node.setdefault(part, {})
            node[path[-1]] = val
    if str(config.get("llm", {}).get("api_key", "")).strip():
        config.setdefault("llm", {})["enabled"] = True
    return config


# ---------------------------------------------------------------------------
# Typed section accessors
# ---------------------------------------------------------------------------


def llm(config: dict | None = None) -> dict[str, Any]:
    return (config or load_raw()).get("llm", {})


def pet(config: dict | None = None) -> dict[str, Any]:
    return (config or load_raw()).get("pet", {})


def personality(config: dict | None = None) -> dict[str, float]:
    p = pet(config).get("personality", {})
    return {str(k): float(v) for k, v in p.items()}


def drives_defaults(config: dict | None = None) -> dict[str, float]:
    d = (config or load_raw()).get("drives", {})
    return {str(k): float(v) for k, v in d.items()}


def brain(config: dict | None = None) -> dict[str, Any]:
    return (config or load_raw()).get("brain", {})


def body(config: dict | None = None) -> dict[str, Any]:
    return (config or load_raw()).get("body", {})


def memory(config: dict | None = None) -> dict[str, Any]:
    return (config or load_raw()).get("memory", {})


def runtime(config: dict | None = None) -> dict[str, Any]:
    return (config or load_raw()).get("runtime", {})


def llm_enabled(config: dict | None = None) -> bool:
    cfg = llm(config)
    return bool(cfg.get("enabled")) and bool(str(cfg.get("api_key", "")).strip())


def pet_name(config: dict | None = None) -> str:
    return str(pet(config).get("name", "咕咕"))


def species(config: dict | None = None) -> str:
    return str(pet(config).get("species", "pigeon"))


def save(config: dict[str, Any]) -> None:
    """Persist the full config dict back to config.yaml."""
    yaml = _load_yaml()
    if yaml:
        CONFIG_FILE.write_text(
            yaml.safe_dump(config, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
    else:
        CONFIG_FILE.write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def save_llm_section(updates: dict[str, Any]) -> None:
    """Persist llm section updates back to config.yaml."""
    yaml = _load_yaml()
    if not CONFIG_FILE.exists():
        existing: dict = {}
    else:
        try:
            if yaml:
                existing = yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8")) or {}
            else:
                existing = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    if not isinstance(existing, dict):
        existing = {}
    llm_section = existing.get("llm", {})
    if not isinstance(llm_section, dict):
        llm_section = {}
    llm_section.update(updates)
    existing["llm"] = llm_section
    if yaml:
        CONFIG_FILE.write_text(
            yaml.safe_dump(existing, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
    else:
        CONFIG_FILE.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
