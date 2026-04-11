"""Cat pixel frames placeholder for gugupet_v2.

Replace these stub frames with real pixel art using the same
letter-based encoding as art/pigeon/frames.py.
"""

from __future__ import annotations

WIDTH = 16
HEIGHT = 16
TRANSPARENT = "."

FRAMES: dict[str, tuple[str, ...]] = {
    # Stub — all transparent until real art is added
    "cat_idle1": tuple(["." * WIDTH] * HEIGHT),
    "cat_idle2": tuple(["." * WIDTH] * HEIGHT),
    "cat_stand1": tuple(["." * WIDTH] * HEIGHT),
    "cat_walk_left1": tuple(["." * WIDTH] * HEIGHT),
    "cat_walk_left2": tuple(["." * WIDTH] * HEIGHT),
    "cat_walk_right1": tuple(["." * WIDTH] * HEIGHT),
    "cat_walk_right2": tuple(["." * WIDTH] * HEIGHT),
    "cat_jump_left": tuple(["." * WIDTH] * HEIGHT),
    "cat_jump_right": tuple(["." * WIDTH] * HEIGHT),
    "cat_sleep": tuple(["." * WIDTH] * HEIGHT),
    "cat_sit": tuple(["." * WIDTH] * HEIGHT),
    "cat_sniff": tuple(["." * WIDTH] * HEIGHT),
}

FRAME_GROUND_ROWS: dict[str, int] = {name: HEIGHT - 1 for name in FRAMES}
