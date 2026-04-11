"""Art behavior slot manifest interface for gugupet_v2.

Every species must provide a manifest that maps standard behavior slot names
to lists of frame keys defined in its frames.py.

The body layer never knows species-specific frame names.
It only ever asks for a slot like "walk_left" or "hurt".
The registry resolves the actual frames.
"""

from __future__ import annotations

from typing import Protocol


# ---------------------------------------------------------------------------
# Standard slot names
# Every species manifest MUST provide all required slots.
# ---------------------------------------------------------------------------

REQUIRED_SLOTS: frozenset[str] = frozenset(
    {
        "idle",
        "walk_left",
        "walk_right",
        "fly_left",
        "fly_right",
        "sleep",
        "sit",
        "peck",
        "stand",
    }
)

# Optional slots – body will fall back to a required slot if missing.
OPTIONAL_SLOTS: frozenset[str] = frozenset(
    {
        "hurt",
        "happy",
        "surprised",
        "affectionate",
        "wake",
    }
)

ALL_SLOTS: frozenset[str] = REQUIRED_SLOTS | OPTIONAL_SLOTS

# Fallback map: if an optional slot is missing, use this slot instead.
SLOT_FALLBACK: dict[str, str] = {
    "hurt": "idle",
    "happy": "idle",
    "surprised": "stand",
    "affectionate": "idle",
    "wake": "stand",
}


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class ArtManifest(Protocol):
    """A species art manifest must satisfy this interface."""

    #: Unique species identifier, e.g. "pigeon", "cat"
    SPECIES_ID: str

    #: Maps slot name -> list of frame keys in frames.py
    SLOTS: dict[str, list[str]]

    #: Pixel size of each art cell
    PIXEL_SIZE: int

    #: Frame width and height in art cells
    FRAME_WIDTH: int
    FRAME_HEIGHT: int

    #: Colour palette: single letter -> hex colour or None (transparent)
    PALETTE: dict[str, str | None]
