"""Stable protocol contracts between body, bridge, and brain.

This is the long-term seam of the whole system.
No other module should couple body ↔ brain directly.
All communication flows through these dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class BodyEventName(str, Enum):
    """All recognised body event names.

    Add new values here when the body gains new capabilities.
    The string value is what gets serialised into runtime JSON.
    """

    # Interaction
    OWNER_TOUCH = "owner_touch"  # single left-click release, no drag
    OWNER_PET = "owner_pet"  # right-click / long hover over body
    OWNER_PING = "owner_ping"  # double-click "hey"
    USER_MESSAGE = "user_message"  # typed message from control panel

    # Physics
    DRAG_START = "drag_start"
    DRAG_RELEASE = "drag_release"  # mouse released after drag
    WALL_HIT = "wall_hit"
    GROUND_HIT = "ground_hit"  # significant landing impact
    BECAME_AIRBORNE = "became_airborne"
    LANDED = "landed"  # gentle landing, no impact
    SLINGSHOT_LAUNCHED = "slingshot_launched"  # owner used slingshot on the pet

    # Autonomy ticks
    IDLE_TICK = "idle_tick"  # body has been idle for a while
    STATE_TICK = "state_tick"  # periodic body state summary

    # Needs
    NEEDS_UPDATE = "needs_update"  # drive system triggered a need signal


class BrainIntentName(str, Enum):
    """All recognised brain intent names.

    The bridge translates these into concrete BodyCommands.
    Add new values when the brain gains new capabilities.
    """

    NONE = "none"

    # Speech
    REPLY_ONLY = "reply_only"  # just say something, no body action

    # Reactive
    REACT_PAIN = "react_pain"
    REACT_JOY = "react_joy"
    REACT_SURPRISE = "react_surprise"
    REACT_AFFECTION = "react_affection"

    # Locomotion
    EXPLORE_AIR = "explore_air"
    SEEK_ATTENTION = "seek_attention"
    APPROACH_OWNER = "approach_owner"
    FOLLOW_OWNER = "follow_owner"
    REST = "rest"
    SETTLE = "settle"
    GO_SLEEP = "go_sleep"

    # Pose
    POSE_CHANGE = "pose_change"

    # Art / effects
    SHOW_OFF = "show_off"
    EMIT_HEARTS = "emit_hearts"


class BodyCommandAction(str, Enum):
    """All recognised body command actions.

    The body's ActionExecutor dispatches on these.
    Add new values when the body gains new capabilities.
    """

    NONE = "none"
    SHOW_BUBBLE = "show_bubble"
    WALK_BY = "walk_by"
    WALK_TO = "walk_to"
    FLY_TO = "fly_to"
    FLY_SHAPE = "fly_shape"
    FOLLOW_CURSOR = "follow_cursor"
    STOP_FOLLOW = "stop_follow"
    SET_POSE = "set_pose"
    SET_GROUND = "set_ground"
    SET_FLIGHT_PROFILE = "set_flight_profile"
    EMIT_EFFECT = "emit_effect"
    PLAY_BEHAVIOR = "play_behavior"  # play an art-manifest behavior slot
    WRITE_TEXT = "write_text"
    EMOTE_HEARTS = "emote_hearts"
    FORCE_SLEEP = "force_sleep"  # sleep until drives are restored


class EmotionHint(str, Enum):
    """Emotion hints the reflex layer passes to the language brain.

    These shape prompt tone without generating dialogue.
    """

    NEUTRAL = "neutral"
    HAPPY = "happy"
    EXCITED = "excited"
    TIRED = "tired"
    HURT = "hurt"
    SURPRISED = "surprised"
    CURIOUS = "curious"
    LONELY = "lonely"
    AFFECTIONATE = "affectionate"


# ---------------------------------------------------------------------------
# Body State  –  snapshot sent from body to brain
# ---------------------------------------------------------------------------


@dataclass
class BodyState:
    """Current mechanical state of the pet body.

    Always factual: positions, velocities, pose. No personality.
    """

    position_x: float = 0.0
    position_y: float = 0.0
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    floor_y: float = 900.0
    work_left: float = 0.0
    work_top: float = 0.0
    work_right: float = 1920.0
    work_bottom: float = 1080.0
    screen_width: float = 1920.0
    screen_height: float = 1080.0
    facing: int = 1  # +1 right, -1 left
    pose: str = "stand"  # raw locomotion state name
    airborne: bool = False
    on_ground: bool = True
    idle_seconds: float = 0.0
    dragging: bool = False


# ---------------------------------------------------------------------------
# Body Event  –  body reports a fact, no interpretation
# ---------------------------------------------------------------------------


@dataclass
class BodyEvent:
    """A factual event emitted by the body.

    Fields:
        name:    BodyEventName string
        ts:      Unix timestamp of the event
        payload: Free-form dict of factual details
        id:      Monotonically increasing event id (set by EventQueue)
    """

    name: str
    ts: float = 0.0
    payload: dict[str, Any] = field(default_factory=dict)
    id: int = 0

    def is_high_priority(self) -> bool:
        return self.name in {
            BodyEventName.USER_MESSAGE,
            BodyEventName.WALL_HIT,
            BodyEventName.GROUND_HIT,
            BodyEventName.DRAG_RELEASE,
        }


# ---------------------------------------------------------------------------
# Brain Input  –  assembled by bridge, passed to brain
# ---------------------------------------------------------------------------


@dataclass
class BrainInput:
    """Everything the brain needs to make a decision."""

    event: BodyEvent
    body_state: BodyState
    drives: dict[str, float] = field(default_factory=dict)
    emotion_hint: str = EmotionHint.NEUTRAL
    memory_context: str = ""
    pet_name: str = "咕咕"
    species: str = "pigeon"
    user_text: str = ""  # extracted from event.payload for USER_MESSAGE


# ---------------------------------------------------------------------------
# Brain Reaction  –  brain decision, translated by bridge into commands
# ---------------------------------------------------------------------------


@dataclass
class BrainReaction:
    """What the brain decided to do and say.

    intent:       High-level semantic intent (BrainIntentName)
    reply:        Text to display in speech bubble / chat log
    params:       Intent-specific params (e.g. target x/y, pose name)
    memory_candidate: Optional dict suggesting a memory to store
    """

    intent: str = BrainIntentName.NONE
    reply: str = ""
    kaomoji: str = ""  # emoji/kaomoji shown in the pet bubble separately
    params: dict[str, Any] = field(default_factory=dict)
    memory_candidate: dict[str, str] | None = None

    def has_reply(self) -> bool:
        return bool(self.reply.strip())

    def has_action(self) -> bool:
        return self.intent not in (
            BrainIntentName.NONE,
            BrainIntentName.REPLY_ONLY,
            "none",
        )


# ---------------------------------------------------------------------------
# Body Command  –  concrete instruction for the body to execute
# ---------------------------------------------------------------------------


@dataclass
class BodyCommand:
    """A concrete instruction sent from bridge to body.

    action:  BodyCommandAction string
    params:  Action-specific parameters
    source:  Who issued this ('brain', 'brain_autonomy', 'reflex', 'manual')
    seq:     Monotonically increasing command sequence number
    """

    action: str = BodyCommandAction.NONE
    params: dict[str, Any] = field(default_factory=dict)
    source: str = "brain"
    seq: int = 0

    def is_noop(self) -> bool:
        return self.action in (BodyCommandAction.NONE, "none")
