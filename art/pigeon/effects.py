"""Pigeon visual effects definitions for gugupet_v2.

Defines particle/effect configurations for the pigeon species.
The body's pet_window reads these when request_effect() is called.
"""

from __future__ import annotations

from typing import Any


# Effect name -> default config
EFFECTS: dict[str, dict[str, Any]] = {
    "hearts": {
        "count": 3,
        "color": "#FF4D6D",
        "size_range": (12, 20),
        "rise_speed": 1.8,
        "drift": 0.6,
        "lifetime": 38,  # ticks
        "symbol": "❤",
    },
    "stars": {
        "count": 4,
        "color": "#FFD700",
        "size_range": (10, 16),
        "rise_speed": 1.4,
        "drift": 0.8,
        "lifetime": 30,
        "symbol": "✦",
    },
    "zzz": {
        "count": 2,
        "color": "#A0C8FF",
        "size_range": (11, 17),
        "rise_speed": 1.0,
        "drift": 0.3,
        "lifetime": 50,
        "symbol": "z",
    },
    "sweat": {
        "count": 2,
        "color": "#7EC8E3",
        "size_range": (9, 13),
        "rise_speed": 1.2,
        "drift": 0.5,
        "lifetime": 24,
        "symbol": "💧",
    },
    "music": {
        "count": 3,
        "color": "#C084FC",
        "size_range": (11, 16),
        "rise_speed": 1.5,
        "drift": 0.7,
        "lifetime": 36,
        "symbol": "♪",
    },
}


def get_effect(name: str) -> dict[str, Any]:
    """Return effect config by name, falling back to 'hearts'."""
    return dict(EFFECTS.get(name, EFFECTS["hearts"]))
