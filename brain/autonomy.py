"""Autonomous behavior scheduler for gugupet_v2.

Decides when and what the pet does spontaneously,
based on drives, idle time, and cooldowns.
"""

from __future__ import annotations

import random
import time

from brain.drives import dominant_motive
from config import loader as cfg


def should_act(
    last_autonomy_ts: float,
    next_autonomy_after: float,
    status: str,
    active_dialog_event_id: int,
    is_dragging: bool,
) -> bool:
    """Return True if autonomous action should fire this tick."""
    if status not in ("idle",):
        return False
    if active_dialog_event_id:
        return False
    if is_dragging:
        return False
    return (time.time() - last_autonomy_ts) >= next_autonomy_after


def choose_motive(
    drives: dict[str, float],
    last_owner_attention_ts: float,
) -> str:
    """Pick a motive weighted by drives with a small random tie-break.
    When social is high, strongly prefer seek_attention."""
    now = time.time()
    owner_gap = (
        max(0.0, now - last_owner_attention_ts) if last_owner_attention_ts > 0 else 60.0
    )
    base = dominant_motive(drives, owner_gap)

    social = drives.get("social", 0.5)

    # When social is high (>0.7), 60% chance to override with seek_attention
    if social > 0.7 and random.random() < 0.60:
        return "seek_attention"

    # Add light randomness: sometimes pick the second-best motive
    if random.random() < 0.25:
        candidates = ["rest", "seek_attention", "explore_air", "settle"]
        candidates = [c for c in candidates if c != base]
        return random.choice(candidates)
    return base


def next_cooldown(drives: dict[str, float] | None = None) -> float:
    """Return next autonomy cooldown. Shorter when social drive is high."""
    brain_cfg = cfg.brain()
    lo = float(brain_cfg.get("autonomy_cooldown_min", 18.0))
    hi = float(brain_cfg.get("autonomy_cooldown_max", 34.0))
    base = random.uniform(lo, hi)

    if drives:
        social = drives.get("social", 0.5)
        # High social: up to 50% shorter cooldown (more frequent attention-seeking)
        if social > 0.6:
            reduction = (social - 0.6) / 0.4  # 0..1 as social goes 0.6..1.0
            base *= max(0.5, 1.0 - reduction * 0.5)

    return base
