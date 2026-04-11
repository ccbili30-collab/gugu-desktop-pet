"""macOS-specific platform helpers.

Replaces shared/platform.py (Windows ctypes) for the macOS port.
Provides the same public interface so pet_window_mac.py can call
get_cursor_pos() / get_work_area() / generate_pet() without changes.

Coordinate note
---------------
macOS origin is bottom-left; pygame / our window system uses top-left.
All returned values are already converted to top-left (screen) coords
using screen_h − mac_y.
"""

from __future__ import annotations

import hashlib
import random
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Try to import pyobjc modules; fall back gracefully if not installed yet
# so that the file can at least be imported for syntax checks.
# ---------------------------------------------------------------------------
try:
    from AppKit import NSScreen  # type: ignore

    _HAS_APPKIT = True
except ImportError:
    _HAS_APPKIT = False

try:
    import Quartz  # type: ignore

    _HAS_QUARTZ = True
except ImportError:
    _HAS_QUARTZ = False


# ---------------------------------------------------------------------------
# Compatibility stubs (keep same names as Windows platform.py)
# ---------------------------------------------------------------------------


class RECT(NamedTuple):
    left: int
    top: int
    right: int
    bottom: int


class POINT(NamedTuple):
    x: int
    y: int


def _screen_height() -> int:
    """Return the full pixel height of the main screen."""
    if _HAS_APPKIT:
        frame = NSScreen.mainScreen().frame()
        return int(frame.size.height)
    return 1080  # safe fallback


def get_work_area() -> tuple[int, int, int, int]:
    """Return (left, top, right, bottom) of the usable desktop area.

    macOS calls this the 'visibleFrame' (excludes Dock and menu bar).
    We convert from bottom-left origin to top-left origin.
    """
    if _HAS_APPKIT:
        screen = NSScreen.mainScreen()
        full_h = int(screen.frame().size.height)
        vf = screen.visibleFrame()
        left = int(vf.origin.x)
        # macOS y: bottom of visible area (from screen bottom)
        # In top-left coords: top = full_h - (vf.origin.y + vf.size.height)
        top = int(full_h - (vf.origin.y + vf.size.height))
        right = int(vf.origin.x + vf.size.width)
        bottom = int(full_h - vf.origin.y)
        return left, top, right, bottom
    # Fallback: assume 1920×1080 with a 24-px menu bar
    return 0, 24, 1920, 1080


def get_cursor_pos() -> tuple[int, int]:
    """Return (x, y) of the mouse cursor in top-left screen coordinates."""
    if _HAS_QUARTZ:
        event = Quartz.CGEventCreate(None)
        loc = Quartz.CGEventGetLocation(event)
        # loc.y is measured from the *bottom* of the primary screen in macOS
        sh = _screen_height()
        return int(loc.x), int(sh - loc.y)
    return 0, 0


def generate_pet(user_id: str = "default") -> dict[str, str]:
    """Deterministic pet name/color from user_id (identical to Windows version)."""
    digest = hashlib.md5(user_id.encode()).hexdigest()
    rng = random.Random(int(digest[:8], 16))
    return {
        "name": rng.choice(
            ["咕咕", "灰灰", "小胖", "团子", "麻子", "胖嘟", "灰团", "豆豆"]
        ),
        "color": rng.choice(["#909090", "#707070", "#808080", "#A0A0A0"]),
    }
