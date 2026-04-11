"""Bridge command adapter for gugupet_v2.

Translates BrainReaction intents into concrete BodyCommands.
Add new intent handlers in the _INTENT_MAP at the bottom.
"""

from __future__ import annotations

import random
from typing import Any

from bridge.protocol import (
    BodyCommand,
    BodyCommandAction,
    BrainIntentName,
    BrainReaction,
    BodyState,
)


def reaction_to_commands(
    reaction: BrainReaction,
    body_state: BodyState,
) -> list[BodyCommand]:
    """Convert a BrainReaction into one or more BodyCommands."""
    commands: list[BodyCommand] = []

    # Always show bubble if there is a reply
    if reaction.has_reply():
        commands.append(
            BodyCommand(
                action=BodyCommandAction.SHOW_BUBBLE,
                params={"text": reaction.reply, "duration_ms": 4500},
                source="brain",
            )
        )

    # Translate intent to body action
    if reaction.has_action():
        handler = _INTENT_MAP.get(reaction.intent)
        if handler:
            cmd = handler(reaction.params, body_state)
            if cmd and not cmd.is_noop():
                commands.append(cmd)

    return commands


# ---------------------------------------------------------------------------
# Intent handlers
# ---------------------------------------------------------------------------


def _intent_explore_air(params: dict, bs: BodyState) -> BodyCommand:
    margin = 120.0
    tx = random.uniform(bs.work_left + margin, bs.work_right - margin)
    ty = random.uniform(bs.work_top + 60, bs.floor_y - 80)
    return BodyCommand(
        action=BodyCommandAction.FLY_TO,
        params={
            "x": tx,
            "y": ty,
            "hold_seconds": float(params.get("hold_seconds", 1.5)),
        },
        source="brain",
    )


def _intent_seek_attention(params: dict, bs: BodyState) -> BodyCommand:
    # Fly toward horizontal centre of screen
    tx = (bs.work_left + bs.work_right) / 2
    ty = bs.floor_y - 60
    return BodyCommand(
        action=BodyCommandAction.FLY_TO,
        params={"x": tx, "y": ty, "hold_seconds": 2.0},
        source="brain",
    )


def _intent_approach_owner(params: dict, bs: BodyState) -> BodyCommand:
    # Fly toward the cursor position (centre of screen as fallback)
    tx = bs.position_x  # stay near current x, just land on ground
    ty = bs.floor_y
    return BodyCommand(
        action=BodyCommandAction.FLY_TO,
        params={
            "x": tx,
            "y": ty,
            "hold_seconds": float(params.get("hold_seconds", 1.5)),
        },
        source="brain",
    )


def _intent_follow_owner(params: dict, bs: BodyState) -> BodyCommand:
    # Brief cursor follow (max 8s), then stops on its own
    return BodyCommand(
        action=BodyCommandAction.FOLLOW_CURSOR,
        params={
            "duration": min(float(params.get("duration", 6)), 8.0),
            "x_offset": 28,
            "y_offset": -108,
        },
        source="brain",
    )


def _intent_rest(params: dict, bs: BodyState) -> BodyCommand:
    pose = "sleep" if random.random() < 0.4 else "sit"
    return BodyCommand(
        action=BodyCommandAction.SET_POSE,
        params={"pose": pose, "duration": float(params.get("duration", 8))},
        source="brain",
    )


def _intent_settle(params: dict, bs: BodyState) -> BodyCommand:
    return BodyCommand(
        action=BodyCommandAction.SET_POSE,
        params={"pose": "idle", "duration": float(params.get("duration", 5))},
        source="brain",
    )


def _intent_go_sleep(params: dict, bs: BodyState) -> BodyCommand:
    # force_sleep: stay asleep until energy AND comfort are both restored
    return BodyCommand(
        action=BodyCommandAction.FORCE_SLEEP,
        params={},
        source="brain",
    )


def _intent_react_pain(params: dict, bs: BodyState) -> BodyCommand:
    return BodyCommand(
        action=BodyCommandAction.PLAY_BEHAVIOR,
        params={"slot": "hurt", "ticks": 6},
        source="brain",
    )


def _intent_react_joy(params: dict, bs: BodyState) -> BodyCommand:
    return BodyCommand(
        action=BodyCommandAction.EMOTE_HEARTS,
        params={"count": int(params.get("count", 2))},
        source="brain",
    )


def _intent_react_affection(params: dict, bs: BodyState) -> BodyCommand:
    return BodyCommand(
        action=BodyCommandAction.EMOTE_HEARTS,
        params={"count": int(params.get("count", 3))},
        source="brain",
    )


def _intent_show_off(params: dict, bs: BodyState) -> BodyCommand:
    shape = params.get("shape", random.choice(["circle", "heart", "figure8"]))
    return BodyCommand(
        action=BodyCommandAction.FLY_SHAPE,
        params={"shape": shape, "scale": float(params.get("scale", 1.0))},
        source="brain",
    )


def _intent_pose_change(params: dict, bs: BodyState) -> BodyCommand:
    pose = str(params.get("pose", "idle"))
    return BodyCommand(
        action=BodyCommandAction.SET_POSE,
        params={"pose": pose, "duration": float(params.get("duration", 4))},
        source="brain",
    )


def _intent_emit_hearts(params: dict, bs: BodyState) -> BodyCommand:
    return BodyCommand(
        action=BodyCommandAction.EMOTE_HEARTS,
        params={"count": int(params.get("count", 3))},
        source="brain",
    )


# ---------------------------------------------------------------------------
# Registration table — add new intents here
# ---------------------------------------------------------------------------

_INTENT_MAP: dict[str, Any] = {
    BrainIntentName.EXPLORE_AIR: _intent_explore_air,
    BrainIntentName.SEEK_ATTENTION: _intent_seek_attention,
    BrainIntentName.APPROACH_OWNER: _intent_approach_owner,
    BrainIntentName.FOLLOW_OWNER: _intent_follow_owner,
    BrainIntentName.REST: _intent_rest,
    BrainIntentName.SETTLE: _intent_settle,
    BrainIntentName.GO_SLEEP: _intent_go_sleep,
    BrainIntentName.REACT_PAIN: _intent_react_pain,
    BrainIntentName.REACT_JOY: _intent_react_joy,
    BrainIntentName.REACT_AFFECTION: _intent_react_affection,
    BrainIntentName.SHOW_OFF: _intent_show_off,
    BrainIntentName.POSE_CHANGE: _intent_pose_change,
    BrainIntentName.EMIT_HEARTS: _intent_emit_hearts,
}
