"""Cat species manifest skeleton for gugupet_v2.

This is a placeholder showing how to add a second species.
To activate: add real pixel frames in frames.py and
call art.registry.register(cat_manifest) at startup.
"""

from __future__ import annotations

SPECIES_ID = "cat"
PIXEL_SIZE = 6
FRAME_WIDTH = 16
FRAME_HEIGHT = 16

PALETTE: dict[str, str | None] = {
    ".": None,
    "B": "#E8C89A",  # body tan
    "D": "#C8A070",  # dark fur
    "H": "#A07850",  # head dark
    "W": "#000000",  # eye
    "O": "#FF9060",  # nose/paw pad
    "T": "#F0DCC0",  # belly lighter
    "E": "#FFFFFF",  # white highlight
}

# Placeholder slots — populate frames.py with real pixel art to use
SLOTS: dict[str, list[str]] = {
    "idle": ["cat_idle1", "cat_idle2"],
    "stand": ["cat_stand1"],
    "walk_left": ["cat_walk_left1", "cat_walk_left2"],
    "walk_right": ["cat_walk_right1", "cat_walk_right2"],
    "fly_left": ["cat_jump_left"],
    "fly_right": ["cat_jump_right"],
    "sleep": ["cat_sleep"],
    "sit": ["cat_sit"],
    "peck": ["cat_sniff"],
    "hurt": ["cat_idle1"],
    "happy": ["cat_idle1", "cat_idle2"],
}
