"""Drive system for gugupet_v2.

Maintains four internal drives that drift over time and are impacted
by body events.  The drives determine what the pet spontaneously wants.
"""

from __future__ import annotations

import time

from bridge.protocol import BodyEventName
from config import loader as cfg


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DRIVE_KEYS = ("energy", "social", "curiosity", "comfort")

_DRIFT: dict[str, dict[str, float]] = {
    # pose -> {drive: delta_per_second}
    # Flying: burns energy + comfort, satisfies curiosity a little
    "fly": {"energy": -0.030, "comfort": -0.010, "curiosity": -0.004, "social": -0.006},
    # Sleep: restores energy + comfort, social slowly drains
    "sleep": {"energy": 0.040, "comfort": 0.025, "social": -0.004},
    # Active dialog: all four drives drain (engaging is tiring)
    "dialog": {
        "energy": -0.018,
        "social": -0.010,
        "curiosity": -0.008,
        "comfort": -0.006,
    },
    "default": {
        "energy": -0.006,
        "curiosity": 0.010,
        "comfort": 0.004,
        "social": -0.004,
    },
    "grounded_bonus": {"comfort": 0.004},  # applied when on ground
}

# Cross-feed rates per second: curiosity feeds social, comfort feeds energy
# Meaningful values: at curiosity=0.8, social gets +0.016/s (noticeable over ~30s)
_CROSS_FEED_RATE = 0.020

_EVENT_IMPACT: dict[str, dict[str, float]] = {
    BodyEventName.USER_MESSAGE: {"social": 0.18, "comfort": 0.03},
    BodyEventName.OWNER_TOUCH: {"social": 0.10, "comfort": 0.05},
    BodyEventName.OWNER_PET: {"social": 0.14, "comfort": 0.08},
    BodyEventName.OWNER_PING: {"social": 0.08},
    BodyEventName.WALL_HIT: {"comfort": -0.12, "curiosity": -0.05},
    BodyEventName.GROUND_HIT: {"comfort": -0.08},
    BodyEventName.NEEDS_UPDATE: {},  # handled separately per need tag
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def _load_defaults() -> dict[str, float]:
    raw = cfg.drives_defaults()
    return {k: _clamp(float(raw.get(k, 0.7))) for k in DRIVE_KEYS}


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def initial_drives() -> dict[str, float]:
    return _load_defaults()


def tick_drift(
    drives: dict[str, float],
    pose: str,
    on_ground: bool,
    last_ts: float,
    now: float,
    in_dialog: bool = False,
) -> dict[str, float]:
    """Apply time-based drift to drives.  Returns updated drives dict."""
    dt = max(0.0, min(5.0, now - last_ts)) if last_ts > 0 else 0.8

    # Active dialog drains all four drives
    effective_pose = "dialog" if in_dialog else pose

    deltas: dict[str, float] = {}
    if effective_pose in ("fly", "sleep", "dialog"):
        # Use pose-specific table only
        deltas = dict(_DRIFT[effective_pose])
    else:
        # Default table (walk/stand/idle/peck etc.)
        deltas = dict(_DRIFT["default"])
    if on_ground and effective_pose not in ("fly",):
        for k, v in _DRIFT["grounded_bonus"].items():
            deltas[k] = deltas.get(k, 0.0) + v

    updated = {
        k: _clamp(drives.get(k, 0.7) + deltas.get(k, 0.0) * dt) for k in DRIVE_KEYS
    }

    # Cross-feed: curiosity converts into social, comfort converts into energy
    # The source drive is consumed (decreases) while the target increases
    # Rate: per second, at full source value transfers ~0.020/s
    curiosity = updated["curiosity"]
    comfort = updated["comfort"]
    cross_dt = dt * _CROSS_FEED_RATE
    curiosity_spend = curiosity * cross_dt  # how much curiosity is consumed
    comfort_spend = comfort * cross_dt  # how much comfort is consumed
    updated["curiosity"] = _clamp(updated["curiosity"] - curiosity_spend)
    updated["social"] = _clamp(updated["social"] + curiosity_spend)
    updated["comfort"] = _clamp(updated["comfort"] - comfort_spend)
    updated["energy"] = _clamp(updated["energy"] + comfort_spend)

    return updated


def apply_event_impact(
    drives: dict[str, float],
    event_name: str,
    payload: dict,
) -> dict[str, float]:
    """Apply a one-time drive impact from a body event."""
    impact = dict(_EVENT_IMPACT.get(event_name, {}))

    if event_name == BodyEventName.WALL_HIT or event_name == BodyEventName.GROUND_HIT:
        try:
            intensity = float(payload.get("intensity", 0.0) or 0.0)
            extra = min(0.20, intensity / 40.0)
            impact["comfort"] = impact.get("comfort", 0.0) - extra
        except Exception:
            pass

    if event_name == BodyEventName.NEEDS_UPDATE:
        need = str(payload.get("need", "")).lower()
        if need == "tired":
            impact["energy"] = -0.12
        elif need == "bored":
            impact["curiosity"] = 0.12

    return {k: _clamp(drives.get(k, 0.7) + impact.get(k, 0.0)) for k in DRIVE_KEYS}


def dominant_motive(drives: dict[str, float], owner_gap_seconds: float) -> str:
    """Return the name of the most pressing motive right now."""
    scored = {
        "rest": (1.0 - drives["energy"]) * 0.85 + (1.0 - drives["comfort"]) * 0.30,
        "seek_attention": drives["social"] * 0.70 + min(0.35, owner_gap_seconds / 90.0),
        "explore_air": drives["curiosity"] * 0.85 + drives["energy"] * 0.20,
        "settle": drives["comfort"] * 0.45 + (1.0 - drives["curiosity"]) * 0.20,
    }
    return max(scored, key=lambda k: scored[k])
