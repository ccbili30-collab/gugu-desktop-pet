"""Config schema validation for gugupet_v2.

Validates a loaded config dict against expected types and ranges.
Returns a list of warning strings (empty = valid).
"""

from __future__ import annotations

from typing import Any


def validate(config: dict[str, Any]) -> list[str]:
    """Validate a full config dict.  Returns list of warning strings."""
    warnings: list[str] = []

    llm = config.get("llm", {})
    if not isinstance(llm, dict):
        warnings.append("llm: must be a mapping")
    else:
        if llm.get("enabled") and not str(llm.get("api_key", "")).strip():
            warnings.append("llm.enabled is true but api_key is empty")
        timeout = llm.get("timeout", 25)
        try:
            if float(timeout) <= 0:
                warnings.append("llm.timeout must be > 0")
        except (TypeError, ValueError):
            warnings.append(f"llm.timeout must be a number, got {timeout!r}")
        temp = llm.get("temperature", 0.8)
        try:
            if not (0.0 <= float(temp) <= 2.0):
                warnings.append("llm.temperature should be in [0.0, 2.0]")
        except (TypeError, ValueError):
            warnings.append(f"llm.temperature must be a number, got {temp!r}")

    pet = config.get("pet", {})
    if not isinstance(pet, dict):
        warnings.append("pet: must be a mapping")
    else:
        if not str(pet.get("name", "")).strip():
            warnings.append("pet.name must not be empty")
        if not str(pet.get("species", "")).strip():
            warnings.append("pet.species must not be empty")

    drives = config.get("drives", {})
    if isinstance(drives, dict):
        for key in ("energy", "social", "curiosity", "comfort"):
            val = drives.get(key)
            if val is not None:
                try:
                    if not (0.0 <= float(val) <= 1.0):
                        warnings.append(f"drives.{key} should be in [0.0, 1.0]")
                except (TypeError, ValueError):
                    warnings.append(f"drives.{key} must be a number")

    body = config.get("body", {})
    if isinstance(body, dict):
        for key in ("fall_gravity", "terminal_velocity", "fling_max_speed"):
            val = body.get(key)
            if val is not None:
                try:
                    if float(val) <= 0:
                        warnings.append(f"body.{key} must be > 0")
                except (TypeError, ValueError):
                    warnings.append(f"body.{key} must be a number")

    return warnings


def validate_and_print(config: dict[str, Any]) -> bool:
    """Validate and print warnings.  Returns True if no warnings."""
    issues = validate(config)
    for issue in issues:
        print(f"[config] WARNING: {issue}")
    return len(issues) == 0
