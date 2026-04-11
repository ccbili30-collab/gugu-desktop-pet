"""Shared runtime data models for gugupet_v2.

These are plain Python dataclasses that mirror the JSON schemas
written to / read from the runtime directory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuntimeState:
    """Full shared state written to state.json every brain tick."""

    status: str = "idle"  # idle | sleep | busy_think | busy_act
    bubble_text: str = ""
    bubble_ts: float = 0.0
    chat_text: str = ""
    chat_ts: float = 0.0
    pet_text: str = ""
    pet_ts: float = 0.0
    brain_ts: float = 0.0
    active_dialog_event_id: int = 0
    brain_agent: str = "built_in"
    pet_name: str = "咕咕"
    pet_color: str = ""
    drives: dict[str, float] = field(
        default_factory=lambda: {
            "energy": 0.72,
            "social": 0.56,
            "curiosity": 0.68,
            "comfort": 0.74,
        }
    )
    dominant_drive: str = "curiosity"
    last_drive_update_ts: float = 0.0
    last_owner_attention_ts: float = 0.0
    last_autonomy_ts: float = 0.0
    next_autonomy_after: float = 16.0
    peek_trigger: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        import dataclasses

        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RuntimeState":
        valid = {f.name for f in __import__("dataclasses").fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in valid})


@dataclass
class RuntimeStatus:
    """Body status written to pet_action_status.json by the body every tick."""

    window_x: float = 0.0
    window_y: float = 0.0
    floor_y: float = 900.0
    screen_width: float = 1920.0
    screen_height: float = 1080.0
    work_left: float = 0.0
    work_top: float = 0.0
    work_right: float = 1920.0
    work_bottom: float = 1080.0
    direction: int = 1
    pet_state: str = "stand"
    mood: str = "alert"
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    airborne: bool = False

    def to_dict(self) -> dict[str, Any]:
        import dataclasses

        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RuntimeStatus":
        valid = {f.name for f in __import__("dataclasses").fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in valid})


@dataclass
class RuntimeCommand:
    """One command written to pet_action_command.json by the brain."""

    seq: int = 0
    action: str = "none"
    params: dict[str, Any] = field(default_factory=dict)
    source: str = "brain"
    issued_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        import dataclasses

        return dataclasses.asdict(self)


@dataclass
class RuntimeEventLog:
    """pet_action_events.json schema."""

    next_event_id: int = 1
    events: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RuntimeBridgeState:
    """pet_event_bridge_state.json schema."""

    agent_id: str = "built_in"
    last_event_id: int = 0
