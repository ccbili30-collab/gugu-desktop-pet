"""Pigeon species manifest for gugupet_v2.

Maps standard behavior slots to pigeon frame keys defined in frames.py.
"""

from __future__ import annotations


SPECIES_ID = "pigeon"
PIXEL_SIZE = 6
FRAME_WIDTH = 16
FRAME_HEIGHT = 16

# Colour palette: letter -> hex RGB colour; "." -> transparent
PALETTE: dict[str, str | None] = {
    ".": None,  # transparent
    "B": "#909090",  # body grey
    "D": "#707070",  # dark wing accent
    "H": "#4A4A4A",  # head dark grey
    "G": "#3CB371",  # green (unused in standard frames)
    "E": "#FFFFFF",  # white
    "W": "#000000",  # eye black
    "O": "#FF6600",  # beak orange
    "L": "#FF8C00",  # leg orange
    "T": "#B0B0C0",  # wing tip light grey
}

# Standard behavior slot -> list of frame keys from frames.py
SLOTS: dict[str, list[str]] = {
    "idle": ["idle1", "idle2"],
    "stand": ["stand1", "stand2"],
    "walk_left": ["walk_left1", "walk_left2"],
    "walk_right": ["walk_right1", "walk_right2"],
    "fly_left": ["fly_left1", "fly_left2"],
    "fly_right": ["fly_right1", "fly_right2"],
    "sleep": ["sleep"],
    "sit": ["sit"],
    "peck": ["peck"],
    "hurt": ["idle1"],  # no dedicated hurt frame yet – fallback
    "happy": ["idle1", "idle2"],
    "surprised": ["stand1"],
    "affectionate": ["idle1", "idle2"],
    "wake": ["stand1", "stand2"],
}
