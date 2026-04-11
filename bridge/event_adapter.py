"""Bridge event adapter for gugupet_v2.

Converts BodyEvent facts into BrainInput objects ready for the brain.
No interpretation happens here — only structural translation.
"""

from __future__ import annotations

from bridge.protocol import (
    BodyEvent,
    BodyEventName,
    BodyState,
    BrainInput,
    EmotionHint,
)
from runtime.state_store import read_status


def body_state_from_runtime() -> BodyState:
    """Read current body position/velocity from runtime status file."""
    s = read_status()
    return BodyState(
        position_x=s.window_x,
        position_y=s.window_y,
        velocity_x=s.velocity_x,
        velocity_y=s.velocity_y,
        floor_y=s.floor_y,
        work_left=s.work_left,
        work_top=s.work_top,
        work_right=s.work_right,
        work_bottom=s.work_bottom,
        facing=s.direction,
        pose=s.pet_state,
        airborne=s.airborne,
        on_ground=not s.airborne,
    )


def event_to_brain_input(
    event: BodyEvent,
    drives: dict[str, float],
    emotion_hint: str,
    memory_context: str,
    pet_name: str,
    species: str,
) -> BrainInput:
    """Assemble a BrainInput from a BodyEvent plus current context."""
    body_state = body_state_from_runtime()
    user_text = ""
    if event.name == BodyEventName.USER_MESSAGE:
        user_text = str(event.payload.get("text", "") or "").strip()

    return BrainInput(
        event=event,
        body_state=body_state,
        drives=drives,
        emotion_hint=emotion_hint,
        memory_context=memory_context,
        pet_name=pet_name,
        species=species,
        user_text=user_text,
    )
