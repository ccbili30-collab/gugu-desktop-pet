"""Reflex layer for gugupet_v2.

Fast non-LLM layer that:
  - detects urgency of body events
  - provides an emotion hint to guide the language brain's tone
  - optionally suggests a high-priority intent (e.g. react_pain)

Does NOT generate dialogue.  Does NOT fake pet replies.
"""

from __future__ import annotations

from bridge.protocol import BodyEvent, BodyEventName, EmotionHint


def analyse(event: BodyEvent, drives: dict[str, float]) -> tuple[str, str | None]:
    """Return (emotion_hint, suggested_intent | None).

    emotion_hint:      feeds into the language brain's prompt tone
    suggested_intent:  if not None, brain should prefer this intent
    """
    name = event.name
    payload = event.payload

    if name == BodyEventName.WALL_HIT:
        intensity = float(payload.get("intensity", 0) or 0)
        hint = EmotionHint.HURT if intensity >= 10 else EmotionHint.SURPRISED
        return hint, "react_pain"

    if name == BodyEventName.GROUND_HIT:
        intensity = float(payload.get("intensity", 0) or 0)
        hint = EmotionHint.HURT if intensity >= 12 else EmotionHint.SURPRISED
        return hint, "react_pain"

    if name == BodyEventName.OWNER_PET:
        return EmotionHint.AFFECTIONATE, None

    if name == BodyEventName.OWNER_TOUCH:
        return EmotionHint.HAPPY, None

    if name == BodyEventName.OWNER_PING:
        return EmotionHint.CURIOUS, None

    if name == BodyEventName.DRAG_RELEASE:
        return EmotionHint.EXCITED, None

    if name == BodyEventName.SLINGSHOT_LAUNCHED:
        return EmotionHint.HURT, "react_pain"

    if name == BodyEventName.NEEDS_UPDATE:
        need = str(payload.get("need", "")).lower()
        if need == "tired":
            return EmotionHint.TIRED, "rest"
        if need == "bored":
            return EmotionHint.CURIOUS, "explore_air"
        return EmotionHint.NEUTRAL, None

    if name == BodyEventName.IDLE_TICK:
        social = drives.get("social", 0.5)
        curiosity = drives.get("curiosity", 0.5)
        if social > 0.7:
            return EmotionHint.LONELY, None
        if curiosity > 0.7:
            return EmotionHint.CURIOUS, None
        return EmotionHint.NEUTRAL, None

    return EmotionHint.NEUTRAL, None
